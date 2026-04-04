from __future__ import annotations

import uuid
from datetime import UTC, datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext
from app.core.config import Settings
from app.core.crypto import decrypt_text, encrypt_text
from app.core.errors import AdapterError, ApiError
from app.integrations.youtube import GoogleTokenBundle, YouTubeIntegrationService
from app.models.youtube import YouTubeAccount
from app.services.audit_service import record_structured_audit_log
from app.services.publishing_presenters import youtube_account_to_dict

UuidLike = str | uuid.UUID


def _coerce_uuid(value: UuidLike) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


class YouTubeAccountService:
    def __init__(self, db: Session, settings: Settings, redis_client=None) -> None:
        self.db = db
        self.settings = settings
        self.integration = YouTubeIntegrationService(settings, redis_client=redis_client)

    def request_connect_url(self, auth: AuthContext, *, redirect_path: str | None = None) -> str:
        return self.integration.build_connect_url(
            user_id=auth.user_id,
            workspace_id=auth.workspace_id,
            redirect_path=redirect_path or "/app/publishing/accounts",
        )

    def list_accounts(self, auth: AuthContext) -> list[dict[str, object]]:
        rows = self._active_accounts_query(
            workspace_id=uuid.UUID(auth.workspace_id),
            owner_user_id=uuid.UUID(auth.user_id),
        )
        return [youtube_account_to_dict(row) for row in rows]

    def complete_callback(self, *, state: str, code: str) -> tuple[dict[str, object], str]:
        completion = self.integration.complete_callback(state=state, code=code)
        workspace_id = uuid.UUID(completion.state_payload.workspace_id)
        owner_user_id = uuid.UUID(completion.state_payload.user_id)

        account = self.db.scalar(
            select(YouTubeAccount).where(
                YouTubeAccount.workspace_id == workspace_id,
                YouTubeAccount.owner_user_id == owner_user_id,
                YouTubeAccount.channel_id == completion.channel.channel_id,
            )
        )
        if account is None:
            account = YouTubeAccount(
                workspace_id=workspace_id,
                owner_user_id=owner_user_id,
                channel_id=completion.channel.channel_id,
                channel_title=completion.channel.title,
                channel_handle=completion.channel.handle,
                google_subject=completion.google_profile.subject,
                google_account_email=completion.google_profile.email,
                access_token_encrypted="",
                refresh_token_encrypted="",
                scopes=list(completion.token_bundle.scopes),
                token_type=completion.token_bundle.token_type,
                token_expiry_at=completion.token_bundle.expiry,
                connected_at=datetime.now(UTC),
            )
            self.db.add(account)

        existing_refresh_token = (
            decrypt_text(self.settings, account.refresh_token_encrypted)
            if account.refresh_token_encrypted
            else ""
        )
        resolved_refresh_token = completion.token_bundle.refresh_token or existing_refresh_token
        if not resolved_refresh_token:
            raise AdapterError(
                "deterministic_input",
                "youtube_refresh_token_missing",
                "Google did not return a refresh token for this YouTube account.",
            )
        account.google_subject = completion.google_profile.subject
        account.google_account_email = completion.google_profile.email
        account.channel_title = completion.channel.title
        account.channel_handle = completion.channel.handle
        account.access_token_encrypted = encrypt_text(self.settings, completion.token_bundle.access_token)
        account.refresh_token_encrypted = encrypt_text(self.settings, resolved_refresh_token)
        account.scopes = list(completion.token_bundle.scopes)
        account.token_type = completion.token_bundle.token_type
        account.token_expiry_at = completion.token_bundle.expiry
        account.last_token_refresh_at = datetime.now(UTC)
        account.connected_at = datetime.now(UTC)
        account.disconnected_at = None
        self.db.flush()

        active_accounts = self._active_accounts_query(workspace_id=workspace_id, owner_user_id=owner_user_id)
        if len(active_accounts) == 1 or not any(item.is_default for item in active_accounts):
            self._set_default_account(workspace_id=workspace_id, owner_user_id=owner_user_id, account_id=account.id)

        record_structured_audit_log(
            self.db,
            workspace_id=workspace_id,
            user_id=owner_user_id,
            action="youtube_account_connected",
            target_type="youtube_account",
            target_id=str(account.id),
            payload={
                "channel_id": account.channel_id,
                "channel_title": account.channel_title,
                "google_account_email": account.google_account_email,
            },
        )
        self.db.commit()
        self.db.refresh(account)
        return youtube_account_to_dict(account), self._build_frontend_redirect(
            completion.state_payload.redirect_path,
            {"youtube": "connected", "account_id": str(account.id)},
        )

    def disconnect(self, auth: AuthContext, youtube_account_id: str) -> None:
        account = self.get_owned_account(
            workspace_id=auth.workspace_id,
            owner_user_id=auth.user_id,
            youtube_account_id=youtube_account_id,
        )
        account.disconnected_at = datetime.now(UTC)
        was_default = account.is_default
        account.is_default = False

        if was_default:
            replacement = self.db.scalar(
                select(YouTubeAccount).where(
                    YouTubeAccount.workspace_id == uuid.UUID(auth.workspace_id),
                    YouTubeAccount.owner_user_id == uuid.UUID(auth.user_id),
                    YouTubeAccount.disconnected_at.is_(None),
                    YouTubeAccount.id != account.id,
                )
            )
            if replacement is not None:
                replacement.is_default = True

        record_structured_audit_log(
            self.db,
            workspace_id=uuid.UUID(auth.workspace_id),
            user_id=uuid.UUID(auth.user_id),
            action="youtube_account_disconnected",
            target_type="youtube_account",
            target_id=str(account.id),
            payload={"channel_id": account.channel_id, "channel_title": account.channel_title},
        )
        self.db.commit()

    def set_default(self, auth: AuthContext, youtube_account_id: str) -> dict[str, object]:
        account = self.get_owned_account(
            workspace_id=auth.workspace_id,
            owner_user_id=auth.user_id,
            youtube_account_id=youtube_account_id,
        )
        self._set_default_account(
            workspace_id=uuid.UUID(auth.workspace_id),
            owner_user_id=uuid.UUID(auth.user_id),
            account_id=account.id,
        )
        record_structured_audit_log(
            self.db,
            workspace_id=uuid.UUID(auth.workspace_id),
            user_id=uuid.UUID(auth.user_id),
            action="youtube_account_default_set",
            target_type="youtube_account",
            target_id=str(account.id),
            payload={"channel_id": account.channel_id},
        )
        self.db.commit()
        self.db.refresh(account)
        return youtube_account_to_dict(account)

    def get_owned_account(
        self,
        *,
        workspace_id: UuidLike,
        owner_user_id: UuidLike,
        youtube_account_id: UuidLike,
    ) -> YouTubeAccount:
        account = self.db.scalar(
            select(YouTubeAccount).where(
                YouTubeAccount.id == _coerce_uuid(youtube_account_id),
                YouTubeAccount.workspace_id == _coerce_uuid(workspace_id),
                YouTubeAccount.owner_user_id == _coerce_uuid(owner_user_id),
                YouTubeAccount.disconnected_at.is_(None),
            )
        )
        if account is None:
            raise ApiError(404, "youtube_account_not_found", "YouTube account not found.")
        return account

    def get_default_account(self, *, workspace_id: UuidLike, owner_user_id: UuidLike) -> YouTubeAccount | None:
        account = self.db.scalar(
            select(YouTubeAccount).where(
                YouTubeAccount.workspace_id == _coerce_uuid(workspace_id),
                YouTubeAccount.owner_user_id == _coerce_uuid(owner_user_id),
                YouTubeAccount.disconnected_at.is_(None),
                YouTubeAccount.is_default.is_(True),
            )
        )
        if account is not None:
            return account
        return self.db.scalar(
            select(YouTubeAccount).where(
                YouTubeAccount.workspace_id == _coerce_uuid(workspace_id),
                YouTubeAccount.owner_user_id == _coerce_uuid(owner_user_id),
                YouTubeAccount.disconnected_at.is_(None),
            )
        )

    def ensure_runtime_token_bundle(self, account: YouTubeAccount) -> GoogleTokenBundle:
        refresh_token = decrypt_text(self.settings, account.refresh_token_encrypted)
        access_token = decrypt_text(self.settings, account.access_token_encrypted)
        scopes = list(account.scopes or self.integration.oauth.scopes())
        token_bundle = GoogleTokenBundle(
            access_token=access_token,
            refresh_token=refresh_token,
            expiry=account.token_expiry_at,
            scopes=scopes,
            token_type=account.token_type or "Bearer",
        )
        if not refresh_token:
            raise AdapterError(
                "deterministic_input",
                "youtube_refresh_token_missing",
                "The connected YouTube account does not have a usable refresh token.",
            )
        if self.integration.token_expiring_soon(account.token_expiry_at):
            refreshed = self.integration.refresh_token(refresh_token=refresh_token, scopes=scopes)
            account.access_token_encrypted = encrypt_text(self.settings, refreshed.access_token)
            account.refresh_token_encrypted = encrypt_text(
                self.settings, refreshed.refresh_token or refresh_token
            )
            account.token_expiry_at = refreshed.expiry
            account.token_type = refreshed.token_type
            account.last_token_refresh_at = datetime.now(UTC)
            self.db.commit()
            return refreshed
        return token_bundle

    def _active_accounts_query(
        self,
        *,
        workspace_id: uuid.UUID,
        owner_user_id: uuid.UUID,
    ) -> list[YouTubeAccount]:
        return self.db.scalars(
            select(YouTubeAccount)
            .where(
                YouTubeAccount.workspace_id == workspace_id,
                YouTubeAccount.owner_user_id == owner_user_id,
                YouTubeAccount.disconnected_at.is_(None),
            )
            .order_by(YouTubeAccount.is_default.desc(), YouTubeAccount.connected_at.desc())
        ).all()

    def _set_default_account(
        self,
        *,
        workspace_id: uuid.UUID,
        owner_user_id: uuid.UUID,
        account_id: uuid.UUID,
    ) -> None:
        for account in self._active_accounts_query(workspace_id=workspace_id, owner_user_id=owner_user_id):
            account.is_default = account.id == account_id

    def _build_frontend_redirect(self, redirect_path: str, query_params: dict[str, str]) -> str:
        path = redirect_path if redirect_path.startswith("/") else "/app/publishing/accounts"
        split = urlsplit(f"{self.settings.frontend_url_resolved}{path}")
        merged = dict(parse_qsl(split.query, keep_blank_values=True))
        merged.update(query_params)
        return urlunsplit((split.scheme, split.netloc, split.path, urlencode(merged), split.fragment))
