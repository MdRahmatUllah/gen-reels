from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import Response
from sqlalchemy import and_, select, update
from sqlalchemy.orm import Session

from app.api.deps import AuthContext
from app.core.config import Settings
from app.core.errors import ApiError
from app.core.jwt import create_access_token, create_refresh_token, decode_token
from app.core.security import generate_token, hash_password, hash_token, verify_password
from app.integrations.email import EmailSender
from app.models.entities import PasswordResetToken, SessionRecord, User, Workspace, WorkspaceMember
from app.services.audit_service import record_audit_event


class AuthService:
    def __init__(self, db: Session, settings: Settings, redis_client) -> None:
        self.db = db
        self.settings = settings
        self.redis = redis_client
        self.email_sender = EmailSender(settings)

    def _failed_login_key(self, email: str) -> str:
        return f"auth:fail:{email.lower()}"

    def _lockout_key(self, email: str) -> str:
        return f"auth:lockout:{email.lower()}"

    def _check_login_lockout(self, email: str) -> None:
        if self.redis.get(self._lockout_key(email)):
            raise ApiError(429, "login_locked_out", "Too many failed login attempts. Try again later.")

    def _record_failed_login(self, email: str) -> None:
        fail_key = self._failed_login_key(email)
        failures = self.redis.incr(fail_key)
        if failures == 1:
            self.redis.expire(fail_key, 600)
        if failures >= 5:
            self.redis.setex(self._lockout_key(email), 900, "1")

    def _clear_failed_login(self, email: str) -> None:
        self.redis.delete(self._failed_login_key(email), self._lockout_key(email))

    def _workspace_memberships(self, user_id: UUID) -> list[tuple[WorkspaceMember, Workspace]]:
        result = self.db.execute(
            select(WorkspaceMember, Workspace)
            .join(Workspace, Workspace.id == WorkspaceMember.workspace_id)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(WorkspaceMember.is_default.desc(), Workspace.name.asc())
        )
        return list(result.all())

    def _normalize_datetime(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _select_active_workspace(
        self,
        memberships: list[tuple[WorkspaceMember, Workspace]],
        requested_workspace_id: str | None,
    ) -> tuple[WorkspaceMember, Workspace]:
        if requested_workspace_id:
            for membership, workspace in memberships:
                if str(workspace.id) == requested_workspace_id:
                    return membership, workspace
            raise ApiError(403, "workspace_not_available", "You do not belong to that workspace.")
        return memberships[0]

    def _session_payload(
        self,
        *,
        user: User,
        active_membership: WorkspaceMember,
        active_workspace: Workspace,
        memberships: list[tuple[WorkspaceMember, Workspace]],
    ) -> dict[str, Any]:
        return {
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "is_admin": user.is_admin,
            },
            "workspaces": [
                {
                    "member_id": membership.id,
                    "workspace_id": workspace.id,
                    "workspace_name": workspace.name,
                    "role": membership.role.value,
                    "is_default": membership.is_default,
                    "plan_name": workspace.plan_name,
                }
                for membership, workspace in memberships
            ],
            "active_workspace_id": str(active_workspace.id),
            "active_role": active_membership.role.value,
        }

    def _issue_tokens(
        self,
        *,
        user: User,
        workspace: Workspace,
        role: str,
        session_id: UUID,
    ) -> tuple[str, str]:
        access_token = create_access_token(
            private_key=self.settings.jwt_private_key_resolved,
            user_id=str(user.id),
            email=user.email,
            workspace_id=str(workspace.id),
            workspace_role=role,
            session_id=str(session_id),
            expires_in_minutes=self.settings.jwt_access_token_ttl_minutes,
        )
        refresh_token = create_refresh_token(
            private_key=self.settings.jwt_private_key_resolved,
            user_id=str(user.id),
            session_id=str(session_id),
            expires_in_days=self.settings.jwt_refresh_token_ttl_days,
        )
        return access_token, refresh_token

    def set_auth_cookies(self, response: Response, *, access_token: str, refresh_token: str | None) -> None:
        response.set_cookie(
            key=self.settings.access_cookie_name,
            value=access_token,
            httponly=True,
            secure=self.settings.cookie_secure,
            samesite=self.settings.cookie_samesite,
            max_age=self.settings.jwt_access_token_ttl_minutes * 60,
            path="/",
        )
        if refresh_token is not None:
            response.set_cookie(
                key=self.settings.refresh_cookie_name,
                value=refresh_token,
                httponly=True,
                secure=self.settings.cookie_secure,
                samesite=self.settings.cookie_samesite,
                max_age=self.settings.jwt_refresh_token_ttl_days * 86400,
                path="/",
            )

    def clear_auth_cookies(self, response: Response) -> None:
        response.delete_cookie(self.settings.access_cookie_name, path="/")
        response.delete_cookie(self.settings.refresh_cookie_name, path="/")

    def login(
        self,
        *,
        email: str,
        password: str,
        workspace_id: str | None,
        user_agent: str | None,
        ip_address: str | None,
    ) -> tuple[dict[str, Any], str, str]:
        self._check_login_lockout(email)
        user = self.db.scalar(select(User).where(User.email == email.lower()))
        if not user or not user.is_active or not verify_password(password, user.password_hash):
            self._record_failed_login(email)
            raise ApiError(401, "invalid_credentials", "Invalid email or password.")

        memberships = self._workspace_memberships(user.id)
        if not memberships:
            raise ApiError(403, "workspace_not_available", "No workspace membership found.")
        active_membership, active_workspace = self._select_active_workspace(memberships, workspace_id)

        self._clear_failed_login(email)
        session_record = SessionRecord(
            user_id=user.id,
            active_workspace_id=active_workspace.id,
            refresh_token_hash="pending",
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=datetime.now(timezone.utc) + timedelta(days=self.settings.jwt_refresh_token_ttl_days),
        )
        self.db.add(session_record)
        self.db.flush()

        access_token, refresh_token = self._issue_tokens(
            user=user,
            workspace=active_workspace,
            role=active_membership.role.value,
            session_id=session_record.id,
        )
        session_record.refresh_token_hash = hash_token(refresh_token)
        session_record.last_used_at = datetime.now(timezone.utc)

        record_audit_event(
            self.db,
            workspace_id=active_workspace.id,
            user_id=user.id,
            event_type="auth.login",
            target_type="session",
            target_id=str(session_record.id),
            payload={"ip_address": ip_address},
        )
        self.db.commit()
        return (
            self._session_payload(
                user=user,
                active_membership=active_membership,
                active_workspace=active_workspace,
                memberships=memberships,
            ),
            access_token,
            refresh_token,
        )

    def session_snapshot(self, auth: AuthContext) -> dict[str, Any]:
        user = self.db.get(User, UUID(auth.user_id))
        if not user:
            raise ApiError(401, "unauthorized", "User not found.")
        memberships = self._workspace_memberships(user.id)
        active = next(
            ((membership, workspace) for membership, workspace in memberships if str(workspace.id) == auth.workspace_id),
            None,
        )
        if not active:
            raise ApiError(403, "workspace_not_available", "Active workspace is no longer available.")
        membership, workspace = active
        return self._session_payload(
            user=user,
            active_membership=membership,
            active_workspace=workspace,
            memberships=memberships,
        )

    def refresh(self, refresh_token: str) -> tuple[dict[str, Any], str, str]:
        payload = decode_token(
            refresh_token,
            self.settings.jwt_public_key_resolved,
            expected_type="refresh",
        )
        session_record = self.db.get(SessionRecord, UUID(payload["session_id"]))
        if (
            not session_record
            or session_record.revoked_at
            or self._normalize_datetime(session_record.expires_at) <= datetime.now(timezone.utc)
        ):
            raise ApiError(401, "invalid_session", "Session is no longer valid.")

        hashed = hash_token(refresh_token)
        if session_record.refresh_token_hash != hashed:
            self.db.execute(
                update(SessionRecord)
                .where(SessionRecord.user_id == session_record.user_id, SessionRecord.revoked_at.is_(None))
                .values(revoked_at=datetime.now(timezone.utc))
            )
            self.db.commit()
            raise ApiError(401, "refresh_reuse_detected", "Refresh token reuse detected.")

        user = self.db.get(User, session_record.user_id)
        memberships = self._workspace_memberships(session_record.user_id)
        active = next(
            (
                (membership, workspace)
                for membership, workspace in memberships
                if workspace.id == session_record.active_workspace_id
            ),
            None,
        )
        if not user or not active:
            raise ApiError(401, "invalid_session", "Session is no longer valid.")

        membership, workspace = active
        access_token, new_refresh_token = self._issue_tokens(
            user=user,
            workspace=workspace,
            role=membership.role.value,
            session_id=session_record.id,
        )
        session_record.refresh_token_hash = hash_token(new_refresh_token)
        session_record.last_used_at = datetime.now(timezone.utc)
        self.db.commit()
        return (
            self._session_payload(
                user=user,
                active_membership=membership,
                active_workspace=workspace,
                memberships=memberships,
            ),
            access_token,
            new_refresh_token,
        )

    def logout(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        try:
            payload = decode_token(
                refresh_token,
                self.settings.jwt_public_key_resolved,
                expected_type="refresh",
            )
        except ApiError:
            return
        session_record = self.db.get(SessionRecord, UUID(payload["session_id"]))
        if session_record and not session_record.revoked_at:
            session_record.revoked_at = datetime.now(timezone.utc)
            self.db.commit()

    def select_workspace(self, auth: AuthContext, workspace_id: str) -> tuple[dict[str, Any], str]:
        user = self.db.get(User, UUID(auth.user_id))
        if not user:
            raise ApiError(401, "unauthorized", "User not found.")

        memberships = self._workspace_memberships(user.id)
        active = self._select_active_workspace(memberships, workspace_id)
        membership, workspace = active

        session_record = self.db.get(SessionRecord, UUID(auth.session_id))
        if not session_record or session_record.revoked_at:
            raise ApiError(401, "invalid_session", "Session is no longer valid.")
        session_record.active_workspace_id = workspace.id
        session_record.last_used_at = datetime.now(timezone.utc)

        access_token = create_access_token(
            private_key=self.settings.jwt_private_key_resolved,
            user_id=str(user.id),
            email=user.email,
            workspace_id=str(workspace.id),
            workspace_role=membership.role.value,
            session_id=str(session_record.id),
            expires_in_minutes=self.settings.jwt_access_token_ttl_minutes,
        )
        record_audit_event(
            self.db,
            workspace_id=workspace.id,
            user_id=user.id,
            event_type="auth.workspace_select",
            target_type="workspace",
            target_id=str(workspace.id),
            payload={"session_id": str(session_record.id)},
        )
        self.db.commit()
        return (
            self._session_payload(
                user=user,
                active_membership=membership,
                active_workspace=workspace,
                memberships=memberships,
            ),
            access_token,
        )

    def request_password_reset(self, email: str) -> None:
        user = self.db.scalar(select(User).where(User.email == email.lower()))
        if not user:
            return
        token = generate_token(24)
        reset = PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=self.settings.password_reset_ttl_minutes),
        )
        self.db.add(reset)
        record_audit_event(
            self.db,
            workspace_id=None,
            user_id=user.id,
            event_type="auth.password_reset_requested",
            target_type="user",
            target_id=str(user.id),
            payload={},
        )
        self.db.commit()
        self.email_sender.send_password_reset(recipient=user.email, token=token)

    def confirm_password_reset(self, token: str, new_password: str) -> None:
        token_hash_value = hash_token(token)
        reset = self.db.scalar(
            select(PasswordResetToken).where(
                and_(
                    PasswordResetToken.token_hash == token_hash_value,
                    PasswordResetToken.used_at.is_(None),
                )
            )
        )
        if not reset or self._normalize_datetime(reset.expires_at) <= datetime.now(timezone.utc):
            raise ApiError(400, "invalid_reset_token", "Password reset token is invalid or expired.")

        user = self.db.get(User, reset.user_id)
        if not user:
            raise ApiError(400, "invalid_reset_token", "Password reset token is invalid or expired.")

        user.password_hash = hash_password(new_password)
        reset.used_at = datetime.now(timezone.utc)
        self.db.execute(
            update(SessionRecord)
            .where(SessionRecord.user_id == user.id, SessionRecord.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        record_audit_event(
            self.db,
            workspace_id=None,
            user_id=user.id,
            event_type="auth.password_reset_confirmed",
            target_type="user",
            target_id=str(user.id),
            payload={},
        )
        self.db.commit()
