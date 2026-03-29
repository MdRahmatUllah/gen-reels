from __future__ import annotations

import hashlib
import hmac
import json
from urllib import error as urllib_error
from urllib import request as urllib_request
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.api.deps import AuthContext
from app.core.errors import ApiError
from app.core.security import generate_token, hash_password, hash_token
from app.models.entities import (
    AuditEvent,
    User,
    WebhookDelivery,
    WebhookDeliveryStatus,
    WebhookEndpoint,
    Workspace,
    WorkspaceApiKey,
    WorkspaceMember,
    WorkspaceRole,
)
from app.schemas.automation import (
    WebhookEndpointCreateRequest,
    WebhookEndpointUpdateRequest,
    WorkspaceApiKeyCreateRequest,
)
from app.schemas.workspace import WorkspaceMemberCreateRequest, WorkspaceMemberUpdateRequest
from app.services.audit_service import record_audit_event
from app.services.permissions import require_workspace_admin
from app.services.presenters import (
    webhook_delivery_to_dict,
    webhook_endpoint_to_dict,
    workspace_api_key_to_dict,
    workspace_member_to_dict,
)
from app.services.notification_service import NotificationService


class WorkspaceService:
    def __init__(self, db, settings=None) -> None:
        self.db = db
        self.settings = settings

    def _workspace(self, workspace_id: str) -> Workspace:
        workspace = self.db.get(Workspace, UUID(workspace_id))
        if not workspace:
            raise ApiError(404, "workspace_not_found", "Workspace not found.")
        return workspace

    def _notification_service(self) -> NotificationService | None:
        if not self.settings:
            return None
        return NotificationService(self.db, self.settings)

    def _dispatch_delivery(self, endpoint: WebhookEndpoint, delivery: WebhookDelivery) -> None:
        if not self.settings or self.settings.environment == "test":
            return

        body = json.dumps(delivery.payload, sort_keys=True, default=str).encode("utf-8")
        request = urllib_request.Request(
            endpoint.target_url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "User-Agent": "reels-generation-webhooks/1.0",
                "X-Reels-Event": delivery.event_type,
                "X-Reels-Replay-Id": delivery.replay_id,
                "X-Reels-Signature": f"sha256={delivery.signature}",
            },
        )
        delivery.attempt_count += 1
        try:
            with urllib_request.urlopen(request, timeout=5) as response:  # pragma: no cover - external I/O
                response_body = response.read().decode("utf-8", errors="replace")
                delivery.response_status_code = response.status
                delivery.response_body = response_body[:4000]
                if 200 <= response.status < 300:
                    delivery.status = WebhookDeliveryStatus.delivered
                    delivery.delivered_at = datetime.now(UTC)
                else:
                    delivery.status = WebhookDeliveryStatus.failed
        except urllib_error.HTTPError as exc:  # pragma: no cover - external I/O
            delivery.status = WebhookDeliveryStatus.failed
            delivery.response_status_code = exc.code
            delivery.response_body = exc.read().decode("utf-8", errors="replace")[:4000]
        except Exception as exc:  # pragma: no cover - external I/O
            delivery.status = WebhookDeliveryStatus.failed
            delivery.response_body = str(exc)[:4000]

    def _member(self, workspace_id: str, member_id: str) -> WorkspaceMember:
        member = self.db.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.id == UUID(member_id),
                WorkspaceMember.workspace_id == UUID(workspace_id),
            )
        )
        if not member:
            raise ApiError(404, "workspace_member_not_found", "Workspace member not found.")
        return member

    def _user(self, user_id: UUID) -> User:
        user = self.db.get(User, user_id)
        if not user:
            raise ApiError(404, "user_not_found", "User not found.")
        return user

    def list_members(self, auth: AuthContext) -> list[dict[str, object]]:
        results = self.db.execute(
            select(WorkspaceMember, User)
            .join(User, User.id == WorkspaceMember.user_id)
            .where(WorkspaceMember.workspace_id == UUID(auth.workspace_id))
            .order_by(WorkspaceMember.created_at.asc())
        ).all()
        return [workspace_member_to_dict(member, user) for member, user in results]

    def create_member(self, auth: AuthContext, payload: WorkspaceMemberCreateRequest) -> dict[str, object]:
        require_workspace_admin(auth, message="Only workspace admins can manage members.")
        workspace_id = UUID(auth.workspace_id)
        role = WorkspaceRole(payload.role)

        user = self.db.scalar(select(User).where(User.email == payload.email.lower()))
        if not user:
            user = User(
                email=payload.email.lower(),
                full_name=payload.full_name,
                password_hash=hash_password(generate_token(24)),
                is_active=True,
                is_admin=False,
            )
            self.db.add(user)
            self.db.flush()

        existing = self.db.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user.id,
            )
        )
        if existing:
            raise ApiError(409, "workspace_member_exists", "That user is already a member of this workspace.")

        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user.id,
            role=role,
            is_default=False,
        )
        self.db.add(member)
        self.db.flush()
        record_audit_event(
            self.db,
            workspace_id=workspace_id,
            user_id=UUID(auth.user_id),
            event_type="workspace.membership_created",
            target_type="workspace_member",
            target_id=str(member.id),
            payload={"email": user.email, "role": role.value},
        )
        self.emit_workspace_event(
            workspace_id,
            "workspace.membership_created",
            {"member_id": str(member.id), "user_id": str(user.id), "role": role.value},
        )
        notifier = self._notification_service()
        if notifier:
            notifier.notify_membership_added(member, user)
        self.db.commit()
        self.db.refresh(member)
        return workspace_member_to_dict(member, user)

    def update_member(
        self,
        auth: AuthContext,
        member_id: str,
        payload: WorkspaceMemberUpdateRequest,
    ) -> dict[str, object]:
        require_workspace_admin(auth, message="Only workspace admins can manage members.")
        member = self._member(auth.workspace_id, member_id)
        user = self._user(member.user_id)

        if payload.role is not None:
            target_role = WorkspaceRole(payload.role)
            if member.role == WorkspaceRole.admin and target_role != WorkspaceRole.admin:
                admin_count = self.db.scalar(
                    select(func.count())
                    .select_from(WorkspaceMember)
                    .where(
                        WorkspaceMember.workspace_id == member.workspace_id,
                        WorkspaceMember.role == WorkspaceRole.admin,
                    )
                )
                if admin_count == 1:
                    raise ApiError(400, "last_admin_protected", "The last workspace admin cannot be demoted.")
            member.role = target_role

        if payload.is_default is not None:
            if payload.is_default:
                for existing in self.db.scalars(
                    select(WorkspaceMember).where(
                        WorkspaceMember.user_id == member.user_id,
                        WorkspaceMember.is_default.is_(True),
                    )
                ).all():
                    existing.is_default = False
            member.is_default = payload.is_default

        record_audit_event(
            self.db,
            workspace_id=member.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="workspace.membership_updated",
            target_type="workspace_member",
            target_id=str(member.id),
            payload={"role": member.role.value, "is_default": member.is_default},
        )
        self.emit_workspace_event(
            member.workspace_id,
            "workspace.membership_updated",
            {"member_id": str(member.id), "user_id": str(member.user_id), "role": member.role.value},
        )
        self.db.commit()
        self.db.refresh(member)
        return workspace_member_to_dict(member, user)

    def remove_member(self, auth: AuthContext, member_id: str) -> None:
        require_workspace_admin(auth, message="Only workspace admins can manage members.")
        member = self._member(auth.workspace_id, member_id)
        if member.role == WorkspaceRole.admin:
            admin_count = len(
                self.db.scalars(
                    select(WorkspaceMember).where(
                        WorkspaceMember.workspace_id == member.workspace_id,
                        WorkspaceMember.role == WorkspaceRole.admin,
                    )
                ).all()
            )
            if admin_count == 1:
                raise ApiError(400, "last_admin_protected", "The last workspace admin cannot be removed.")

        record_audit_event(
            self.db,
            workspace_id=member.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="workspace.membership_removed",
            target_type="workspace_member",
            target_id=str(member.id),
            payload={"user_id": str(member.user_id)},
        )
        self.emit_workspace_event(
            member.workspace_id,
            "workspace.membership_removed",
            {"member_id": str(member.id), "user_id": str(member.user_id)},
        )
        self.db.delete(member)
        self.db.commit()

    def list_audit_events(
        self,
        auth: AuthContext,
        *,
        project_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        require_workspace_admin(auth, message="Only workspace admins can view the full audit trail.")
        query = select(AuditEvent).where(AuditEvent.workspace_id == UUID(auth.workspace_id))
        raw_limit = limit if not project_id else max(limit * 3, limit)
        events = self.db.scalars(query.order_by(AuditEvent.created_at.desc()).limit(raw_limit)).all()
        if project_id:
            events = [
                event
                for event in events
                if str((event.payload or {}).get("project_id") or "") == project_id
            ]
        events = events[:limit]
        return [
            {
                "id": event.id,
                "workspace_id": event.workspace_id,
                "user_id": event.user_id,
                "event_type": event.event_type,
                "target_type": event.target_type,
                "target_id": event.target_id,
                "payload": event.payload,
                "created_at": event.created_at,
            }
            for event in events
        ]

    def list_api_keys(self, auth: AuthContext) -> list[dict[str, object]]:
        require_workspace_admin(auth, message="Only workspace admins can manage API keys.")
        api_keys = self.db.scalars(
            select(WorkspaceApiKey)
            .where(WorkspaceApiKey.workspace_id == UUID(auth.workspace_id))
            .order_by(WorkspaceApiKey.created_at.desc())
        ).all()
        return [workspace_api_key_to_dict(api_key) for api_key in api_keys]

    def create_api_key(self, auth: AuthContext, payload: WorkspaceApiKeyCreateRequest) -> dict[str, object]:
        require_workspace_admin(auth, message="Only workspace admins can manage API keys.")
        role_scope = WorkspaceRole(payload.role_scope)
        raw_secret = f"rgwk_{generate_token(32)}"
        api_key = WorkspaceApiKey(
            workspace_id=UUID(auth.workspace_id),
            created_by_user_id=UUID(auth.user_id),
            name=payload.name,
            role_scope=role_scope,
            key_prefix=raw_secret[:12],
            key_hash=hash_token(raw_secret),
            expires_at=payload.expires_at,
        )
        self.db.add(api_key)
        self.db.flush()
        record_audit_event(
            self.db,
            workspace_id=api_key.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="workspace.api_key_created",
            target_type="workspace_api_key",
            target_id=str(api_key.id),
            payload={"name": api_key.name, "role_scope": api_key.role_scope.value},
        )
        self.db.commit()
        self.db.refresh(api_key)
        return {**workspace_api_key_to_dict(api_key), "api_key": raw_secret}

    def revoke_api_key(self, auth: AuthContext, api_key_id: str) -> dict[str, object]:
        require_workspace_admin(auth, message="Only workspace admins can manage API keys.")
        api_key = self.db.scalar(
            select(WorkspaceApiKey).where(
                WorkspaceApiKey.id == UUID(api_key_id),
                WorkspaceApiKey.workspace_id == UUID(auth.workspace_id),
            )
        )
        if not api_key:
            raise ApiError(404, "workspace_api_key_not_found", "Workspace API key not found.")
        api_key.revoked_at = datetime.now(UTC)
        record_audit_event(
            self.db,
            workspace_id=api_key.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="workspace.api_key_revoked",
            target_type="workspace_api_key",
            target_id=str(api_key.id),
            payload={},
        )
        self.db.commit()
        self.db.refresh(api_key)
        return workspace_api_key_to_dict(api_key)

    def list_webhook_endpoints(self, auth: AuthContext) -> list[dict[str, object]]:
        require_workspace_admin(auth, message="Only workspace admins can manage webhooks.")
        endpoints = self.db.scalars(
            select(WebhookEndpoint)
            .where(WebhookEndpoint.workspace_id == UUID(auth.workspace_id))
            .order_by(WebhookEndpoint.created_at.desc())
        ).all()
        return [webhook_endpoint_to_dict(endpoint) for endpoint in endpoints]

    def create_webhook_endpoint(
        self,
        auth: AuthContext,
        payload: WebhookEndpointCreateRequest,
    ) -> dict[str, object]:
        require_workspace_admin(auth, message="Only workspace admins can manage webhooks.")
        endpoint = WebhookEndpoint(
            workspace_id=UUID(auth.workspace_id),
            created_by_user_id=UUID(auth.user_id),
            name=payload.name,
            target_url=str(payload.target_url),
            event_types=payload.event_types,
            signing_secret=generate_token(24),
        )
        self.db.add(endpoint)
        self.db.flush()
        record_audit_event(
            self.db,
            workspace_id=endpoint.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="workspace.webhook_created",
            target_type="webhook_endpoint",
            target_id=str(endpoint.id),
            payload={"name": endpoint.name},
        )
        self.db.commit()
        self.db.refresh(endpoint)
        return webhook_endpoint_to_dict(endpoint)

    def update_webhook_endpoint(
        self,
        auth: AuthContext,
        endpoint_id: str,
        payload: WebhookEndpointUpdateRequest,
    ) -> dict[str, object]:
        require_workspace_admin(auth, message="Only workspace admins can manage webhooks.")
        endpoint = self.db.scalar(
            select(WebhookEndpoint).where(
                WebhookEndpoint.id == UUID(endpoint_id),
                WebhookEndpoint.workspace_id == UUID(auth.workspace_id),
            )
        )
        if not endpoint:
            raise ApiError(404, "webhook_endpoint_not_found", "Webhook endpoint not found.")
        for field_name in payload.model_fields_set:
            value = getattr(payload, field_name)
            if field_name == "target_url" and value is not None:
                value = str(value)
            setattr(endpoint, field_name, value)
        record_audit_event(
            self.db,
            workspace_id=endpoint.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="workspace.webhook_updated",
            target_type="webhook_endpoint",
            target_id=str(endpoint.id),
            payload={},
        )
        self.db.commit()
        self.db.refresh(endpoint)
        return webhook_endpoint_to_dict(endpoint)

    def delete_webhook_endpoint(self, auth: AuthContext, endpoint_id: str) -> None:
        require_workspace_admin(auth, message="Only workspace admins can manage webhooks.")
        endpoint = self.db.scalar(
            select(WebhookEndpoint).where(
                WebhookEndpoint.id == UUID(endpoint_id),
                WebhookEndpoint.workspace_id == UUID(auth.workspace_id),
            )
        )
        if not endpoint:
            raise ApiError(404, "webhook_endpoint_not_found", "Webhook endpoint not found.")
        record_audit_event(
            self.db,
            workspace_id=endpoint.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="workspace.webhook_deleted",
            target_type="webhook_endpoint",
            target_id=str(endpoint.id),
            payload={},
        )
        self.db.delete(endpoint)
        self.db.commit()

    def list_webhook_deliveries(self, auth: AuthContext, endpoint_id: str | None = None) -> list[dict[str, object]]:
        require_workspace_admin(auth, message="Only workspace admins can manage webhooks.")
        query = select(WebhookDelivery).where(WebhookDelivery.workspace_id == UUID(auth.workspace_id))
        if endpoint_id:
            query = query.where(WebhookDelivery.endpoint_id == UUID(endpoint_id))
        deliveries = self.db.scalars(query.order_by(WebhookDelivery.created_at.desc()).limit(200)).all()
        return [webhook_delivery_to_dict(delivery) for delivery in deliveries]

    def test_webhook_endpoint(self, auth: AuthContext, endpoint_id: str) -> dict[str, object]:
        require_workspace_admin(auth, message="Only workspace admins can manage webhooks.")
        endpoint = self.db.scalar(
            select(WebhookEndpoint).where(
                WebhookEndpoint.id == UUID(endpoint_id),
                WebhookEndpoint.workspace_id == UUID(auth.workspace_id),
            )
        )
        if not endpoint:
            raise ApiError(404, "webhook_endpoint_not_found", "Webhook endpoint not found.")
        endpoint.last_tested_at = datetime.now(UTC)
        delivery = self.emit_workspace_event(
            endpoint.workspace_id,
            "workspace.webhook_test",
            {"endpoint_id": str(endpoint.id), "name": endpoint.name},
            endpoint_ids=[endpoint.id],
        )
        self.db.commit()
        return webhook_delivery_to_dict(delivery[0])

    def emit_workspace_event(
        self,
        workspace_id: UUID,
        event_type: str,
        payload: dict[str, object],
        *,
        endpoint_ids: list[UUID] | None = None,
    ) -> list[WebhookDelivery]:
        endpoints_query = select(WebhookEndpoint).where(
            WebhookEndpoint.workspace_id == workspace_id,
            WebhookEndpoint.is_active.is_(True),
        )
        endpoints = self.db.scalars(endpoints_query).all()
        deliveries: list[WebhookDelivery] = []
        body = json.dumps(payload, sort_keys=True, default=str)
        for endpoint in endpoints:
            if endpoint_ids is not None and endpoint.id not in endpoint_ids:
                continue
            if endpoint.event_types and event_type not in endpoint.event_types:
                continue
            replay_id = str(uuid4())
            signature = hmac.new(
                endpoint.signing_secret.encode("utf-8"),
                f"{replay_id}.{body}".encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            delivery = WebhookDelivery(
                endpoint_id=endpoint.id,
                workspace_id=workspace_id,
                event_type=event_type,
                replay_id=replay_id,
                signature=signature,
                status=WebhookDeliveryStatus.queued,
                payload={**payload, "event_type": event_type},
                attempt_count=0,
            )
            self.db.add(delivery)
            deliveries.append(delivery)
            self._dispatch_delivery(endpoint, delivery)
        return deliveries
