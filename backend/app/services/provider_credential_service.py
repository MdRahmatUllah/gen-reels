from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import select

from app.api.deps import AuthContext
from app.core.crypto import decrypt_json, encrypt_json
from app.core.errors import ApiError
from app.models.entities import ExecutionMode, WorkspaceExecutionPolicy, WorkspaceProviderCredential
from app.schemas.execution import ProviderCredentialCreateRequest, ProviderCredentialUpdateRequest
from app.services.audit_service import record_audit_event
from app.services.provider_capabilities import HOSTED_DEFAULT_PROVIDER_KEYS_BY_MODALITY
from app.services.permissions import require_workspace_admin


class ProviderCredentialService:
    def __init__(self, db, settings) -> None:
        self.db = db
        self.settings = settings

    @staticmethod
    def _validation_metadata(public_config: dict[str, object] | None) -> dict[str, object]:
        if not isinstance(public_config, dict):
            return {}
        metadata = public_config.get("_validation")
        return metadata if isinstance(metadata, dict) else {}

    def _public_config_for_response(self, credential: WorkspaceProviderCredential) -> dict[str, object]:
        public_config = dict(credential.public_config or {})
        public_config.pop("_validation", None)
        return public_config

    def _reset_validation_metadata(self, credential: WorkspaceProviderCredential) -> None:
        public_config = dict(credential.public_config or {})
        public_config["_validation"] = {
            "status": "not_validated",
            "last_validated_at": None,
            "last_validation_error": None,
        }
        credential.public_config = public_config

    def _set_validation_metadata(
        self,
        credential: WorkspaceProviderCredential,
        *,
        status: str,
        validated_at: datetime,
        error_message: str | None,
    ) -> None:
        public_config = dict(credential.public_config or {})
        public_config["_validation"] = {
            "status": status,
            "last_validated_at": validated_at.isoformat(),
            "last_validation_error": error_message,
        }
        credential.public_config = public_config

    def _to_dict(self, credential: WorkspaceProviderCredential) -> dict[str, object]:
        validation = self._validation_metadata(credential.public_config)
        return {
            "id": credential.id,
            "workspace_id": credential.workspace_id,
            "created_by_user_id": credential.created_by_user_id,
            "name": credential.name,
            "modality": credential.modality,
            "provider_key": credential.provider_key,
            "public_config": self._public_config_for_response(credential),
            "last_used_at": credential.last_used_at,
            "expires_at": credential.expires_at,
            "revoked_at": credential.revoked_at,
            "created_at": credential.created_at,
            "updated_at": credential.updated_at,
            "secret_configured": bool(credential.secret_payload_encrypted),
            "validation_status": validation.get("status") or "not_validated",
            "last_validated_at": validation.get("last_validated_at"),
            "last_validation_error": validation.get("last_validation_error"),
        }

    @staticmethod
    def _looks_like_url(value: str) -> bool:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    def _validate_secret_and_config(
        self,
        credential: WorkspaceProviderCredential,
        secret_config: dict[str, object],
    ) -> list[str]:
        errors: list[str] = []
        api_key = str(secret_config.get("api_key") or "").strip()
        public_config = dict(credential.public_config or {})
        endpoint = str(public_config.get("endpoint") or "").strip()
        api_version = str(public_config.get("api_version") or "").strip()
        deployment = str(public_config.get("deployment") or "").strip()
        model_name = str(public_config.get("model_name") or public_config.get("model") or "").strip()

        if not api_key:
            errors.append("API key is missing.")

        if credential.provider_key.startswith("azure_openai"):
            if not endpoint:
                errors.append("Endpoint is required for Azure OpenAI credentials.")
            elif not self._looks_like_url(endpoint):
                errors.append("Endpoint must be a valid http or https URL.")
            elif "azure.com" not in endpoint:
                errors.append("Azure OpenAI endpoint should target an Azure host.")
            if not api_version:
                errors.append("API version is required for Azure OpenAI credentials.")
            if credential.modality in {"text", "image", "speech"} and not (deployment or model_name):
                errors.append("Provide a deployment name or model name for Azure OpenAI runtime use.")
        elif credential.provider_key == "azure_content_safety":
            if not endpoint:
                errors.append("Endpoint is required for Azure Content Safety credentials.")
            elif not self._looks_like_url(endpoint):
                errors.append("Endpoint must be a valid http or https URL.")
            elif "azure.com" not in endpoint:
                errors.append("Azure Content Safety endpoint should target an Azure host.")
        elif endpoint and not self._looks_like_url(endpoint):
            errors.append("Endpoint must be a valid http or https URL.")

        return errors

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

    def _detach_credential_from_policy(
        self,
        workspace_id: UUID,
        credential_id: UUID,
        *,
        replacement_modality: str | None = None,
        replacement_provider_key: str | None = None,
    ) -> None:
        policy = self.db.scalar(
            select(WorkspaceExecutionPolicy).where(WorkspaceExecutionPolicy.workspace_id == workspace_id)
        )
        if not policy:
            return
        for modality in ("text", "moderation", "image", "video", "speech"):
            if getattr(policy, f"{modality}_credential_id") != credential_id:
                continue
            should_keep_binding = (
                replacement_modality == modality
                and replacement_provider_key == getattr(policy, f"{modality}_provider_key")
            )
            if should_keep_binding:
                continue
            setattr(policy, f"{modality}_mode", ExecutionMode.hosted)
            setattr(
                policy,
                f"{modality}_provider_key",
                HOSTED_DEFAULT_PROVIDER_KEYS_BY_MODALITY[modality],
            )
            setattr(policy, f"{modality}_credential_id", None)

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
        self._reset_validation_metadata(credential)
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

    def update_credential(
        self,
        auth: AuthContext,
        credential_id: str,
        payload: ProviderCredentialUpdateRequest,
    ) -> dict[str, object]:
        require_workspace_admin(auth, message="Only workspace admins can manage provider credentials.")
        credential = self._credential(auth.workspace_id, credential_id)
        next_modality = payload.modality or credential.modality
        next_provider_key = payload.provider_key or credential.provider_key

        if payload.name is not None:
            credential.name = payload.name
        if payload.modality is not None:
            credential.modality = payload.modality
        if payload.provider_key is not None:
            credential.provider_key = payload.provider_key
        if payload.public_config is not None:
            credential.public_config = payload.public_config
        if payload.secret_config is not None:
            if not payload.secret_config:
                raise ApiError(400, "provider_secret_required", "A provider secret payload is required.")
            credential.secret_payload_encrypted = encrypt_json(self.settings, payload.secret_config)
        if "expires_at" in payload.model_fields_set:
            credential.expires_at = payload.expires_at
        if any(
            field in payload.model_fields_set
            for field in ("modality", "provider_key", "public_config", "secret_config")
        ):
            self._reset_validation_metadata(credential)

        self._detach_credential_from_policy(
            credential.workspace_id,
            credential.id,
            replacement_modality=next_modality,
            replacement_provider_key=next_provider_key,
        )
        record_audit_event(
            self.db,
            workspace_id=credential.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="workspace.provider_credential_updated",
            target_type="workspace_provider_credential",
            target_id=str(credential.id),
            payload={"modality": credential.modality, "provider_key": credential.provider_key},
        )
        self.db.commit()
        self.db.refresh(credential)
        return self._to_dict(credential)

    def validate_credential(self, auth: AuthContext, credential_id: str) -> dict[str, object]:
        require_workspace_admin(auth, message="Only workspace admins can manage provider credentials.")
        credential = self._credential(auth.workspace_id, credential_id)
        secret_config = decrypt_json(self.settings, credential.secret_payload_encrypted)
        errors = self._validate_secret_and_config(credential, secret_config)
        validated_at = datetime.now(UTC)
        error_message = "; ".join(errors) if errors else None
        self._set_validation_metadata(
            credential,
            status="invalid" if errors else "valid",
            validated_at=validated_at,
            error_message=error_message,
        )
        record_audit_event(
            self.db,
            workspace_id=credential.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="workspace.provider_credential_validated",
            target_type="workspace_provider_credential",
            target_id=str(credential.id),
            payload={"status": "invalid" if errors else "valid", "provider_key": credential.provider_key},
        )
        self.db.commit()
        self.db.refresh(credential)
        return self._to_dict(credential)

    def revoke_credential(self, auth: AuthContext, credential_id: str) -> dict[str, object]:
        require_workspace_admin(auth, message="Only workspace admins can manage provider credentials.")
        credential = self._credential(auth.workspace_id, credential_id, include_revoked=True)
        credential.revoked_at = credential.revoked_at or datetime.now(UTC)
        self._detach_credential_from_policy(credential.workspace_id, credential.id)
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
