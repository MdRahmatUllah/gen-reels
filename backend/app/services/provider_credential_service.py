from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.api.deps import AuthContext
from app.core.crypto import decrypt_json, encrypt_json
from app.core.errors import ApiError
from app.models.entities import WorkspaceProviderCredential
from app.schemas.execution import ProviderCredentialCreateRequest
from app.services.audit_service import record_audit_event
from app.services.permissions import require_workspace_admin


class ProviderCredentialService:
    def __init__(self, db, settings) -> None:
        self.db = db
        self.settings = settings

    def _to_dict(self, credential: WorkspaceProviderCredential) -> dict[str, object]:
        return {
            "id": credential.id,
            "workspace_id": credential.workspace_id,
            "created_by_user_id": credential.created_by_user_id,
            "name": credential.name,
            "modality": credential.modality,
            "provider_key": credential.provider_key,
            "public_config": credential.public_config,
            "last_used_at": credential.last_used_at,
            "expires_at": credential.expires_at,
            "revoked_at": credential.revoked_at,
            "created_at": credential.created_at,
            "updated_at": credential.updated_at,
        }

    def _credential(
        self,
        workspace_id: str | UUID,
        credential_id: str | UUID,
        *,
        include_revoked: bool = False,
    ) -> WorkspaceProviderCredential:
        credential = self.db.scalar(
            select(WorkspaceProviderCredential).where(
                WorkspaceProviderCredential.id == UUID(str(credential_id)),
                WorkspaceProviderCredential.workspace_id == UUID(str(workspace_id)),
            )
        )
        if not credential:
            raise ApiError(404, "provider_credential_not_found", "Provider credential not found.")
        if not include_revoked:
            self._assert_credential_active(credential)
        return credential

    def _assert_credential_active(self, credential: WorkspaceProviderCredential) -> None:
        now = datetime.now(UTC)
        if credential.revoked_at is not None:
            raise ApiError(400, "provider_credential_revoked", "That provider credential has been revoked.")
        if credential.expires_at is not None and credential.expires_at <= now:
            raise ApiError(400, "provider_credential_expired", "That provider credential has expired.")

    def list_credentials(self, auth: AuthContext) -> list[dict[str, object]]:
        require_workspace_admin(auth, message="Only workspace admins can manage provider credentials.")
        credentials = self.db.scalars(
            select(WorkspaceProviderCredential)
            .where(WorkspaceProviderCredential.workspace_id == UUID(auth.workspace_id))
            .order_by(WorkspaceProviderCredential.created_at.desc())
        ).all()
        return [self._to_dict(credential) for credential in credentials]

    def create_credential(
        self,
        auth: AuthContext,
        payload: ProviderCredentialCreateRequest,
    ) -> dict[str, object]:
        require_workspace_admin(auth, message="Only workspace admins can manage provider credentials.")
        if not payload.secret_config:
            raise ApiError(400, "provider_secret_required", "A provider secret payload is required.")
        credential = WorkspaceProviderCredential(
            workspace_id=UUID(auth.workspace_id),
            created_by_user_id=UUID(auth.user_id),
            name=payload.name,
            modality=payload.modality,
            provider_key=payload.provider_key,
            public_config=payload.public_config,
            secret_payload_encrypted=encrypt_json(self.settings, payload.secret_config),
            expires_at=payload.expires_at,
        )
        self.db.add(credential)
        self.db.flush()
        record_audit_event(
            self.db,
            workspace_id=credential.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="workspace.provider_credential_created",
            target_type="workspace_provider_credential",
            target_id=str(credential.id),
            payload={"modality": credential.modality, "provider_key": credential.provider_key},
        )
        self.db.commit()
        self.db.refresh(credential)
        return self._to_dict(credential)

    def revoke_credential(self, auth: AuthContext, credential_id: str) -> dict[str, object]:
        require_workspace_admin(auth, message="Only workspace admins can manage provider credentials.")
        credential = self._credential(auth.workspace_id, credential_id, include_revoked=True)
        credential.revoked_at = credential.revoked_at or datetime.now(UTC)
        record_audit_event(
            self.db,
            workspace_id=credential.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="workspace.provider_credential_revoked",
            target_type="workspace_provider_credential",
            target_id=str(credential.id),
            payload={},
        )
        self.db.commit()
        self.db.refresh(credential)
        return self._to_dict(credential)

    def get_runtime_credential(
        self,
        workspace_id: str | UUID,
        credential_id: str | UUID,
        *,
        modality: str | None = None,
    ) -> tuple[WorkspaceProviderCredential, dict[str, object]]:
        credential = self._credential(workspace_id, credential_id)
        if modality and credential.modality != modality:
            raise ApiError(
                400,
                "provider_credential_modality_mismatch",
                "That provider credential does not match the requested modality.",
            )
        return credential, decrypt_json(self.settings, credential.secret_payload_encrypted)

    def touch_runtime_use(self, credential: WorkspaceProviderCredential) -> None:
        credential.last_used_at = datetime.now(UTC)
