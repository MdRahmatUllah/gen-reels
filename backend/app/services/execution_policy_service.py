from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select

from app.api.deps import AuthContext
from app.core.errors import ApiError
from app.models.entities import (
    ExecutionMode,
    LocalWorker,
    WorkspaceExecutionPolicy,
    WorkspaceProviderCredential,
)
from app.schemas.execution import ExecutionPolicyUpdateRequest
from app.services.audit_service import record_audit_event
from app.services.permissions import require_workspace_admin


@dataclass(frozen=True)
class PolicyRoute:
    mode: ExecutionMode
    provider_key: str
    credential_id: UUID | None


DEFAULT_POLICY = {
    "text": PolicyRoute(ExecutionMode.hosted, "azure_openai_text", None),
    "moderation": PolicyRoute(ExecutionMode.hosted, "azure_content_safety", None),
    "image": PolicyRoute(ExecutionMode.hosted, "azure_openai_image", None),
    "video": PolicyRoute(ExecutionMode.hosted, "veo_video", None),
    "speech": PolicyRoute(ExecutionMode.hosted, "azure_openai_speech", None),
}


class ExecutionPolicyService:
    def __init__(self, db) -> None:
        self.db = db

    def _to_dict(self, policy: WorkspaceExecutionPolicy | None, workspace_id: UUID) -> dict[str, object]:
        return {
            "id": policy.id if policy else None,
            "workspace_id": workspace_id,
            "text": self._route_to_dict(
                PolicyRoute(
                    (policy.text_mode if policy else DEFAULT_POLICY["text"].mode),
                    (policy.text_provider_key if policy else DEFAULT_POLICY["text"].provider_key),
                    (policy.text_credential_id if policy else DEFAULT_POLICY["text"].credential_id),
                )
            ),
            "moderation": self._route_to_dict(
                PolicyRoute(
                    (policy.moderation_mode if policy else DEFAULT_POLICY["moderation"].mode),
                    (policy.moderation_provider_key if policy else DEFAULT_POLICY["moderation"].provider_key),
                    (
                        policy.moderation_credential_id
                        if policy
                        else DEFAULT_POLICY["moderation"].credential_id
                    ),
                )
            ),
            "image": self._route_to_dict(
                PolicyRoute(
                    (policy.image_mode if policy else DEFAULT_POLICY["image"].mode),
                    (policy.image_provider_key if policy else DEFAULT_POLICY["image"].provider_key),
                    (policy.image_credential_id if policy else DEFAULT_POLICY["image"].credential_id),
                )
            ),
            "video": self._route_to_dict(
                PolicyRoute(
                    (policy.video_mode if policy else DEFAULT_POLICY["video"].mode),
                    (policy.video_provider_key if policy else DEFAULT_POLICY["video"].provider_key),
                    (policy.video_credential_id if policy else DEFAULT_POLICY["video"].credential_id),
                )
            ),
            "speech": self._route_to_dict(
                PolicyRoute(
                    (policy.speech_mode if policy else DEFAULT_POLICY["speech"].mode),
                    (policy.speech_provider_key if policy else DEFAULT_POLICY["speech"].provider_key),
                    (policy.speech_credential_id if policy else DEFAULT_POLICY["speech"].credential_id),
                )
            ),
            "preferred_local_worker_id": policy.preferred_local_worker_id if policy else None,
            "pause_render_generation": policy.pause_render_generation if policy else False,
            "pause_image_generation": policy.pause_image_generation if policy else False,
            "pause_video_generation": policy.pause_video_generation if policy else False,
            "pause_audio_generation": policy.pause_audio_generation if policy else False,
            "pause_reason": policy.pause_reason if policy else None,
            "created_at": policy.created_at if policy else None,
            "updated_at": policy.updated_at if policy else None,
        }

    @staticmethod
    def _route_to_dict(route: PolicyRoute) -> dict[str, object]:
        return {
            "mode": route.mode.value,
            "provider_key": route.provider_key,
            "credential_id": route.credential_id,
        }

    def _policy_row(self, workspace_id: str | UUID) -> WorkspaceExecutionPolicy | None:
        return self.db.scalar(
            select(WorkspaceExecutionPolicy).where(
                WorkspaceExecutionPolicy.workspace_id == UUID(str(workspace_id))
            )
        )

    def _ensure_policy_row(self, workspace_id: str | UUID, *, updated_by_user_id: UUID | None) -> WorkspaceExecutionPolicy:
        policy = self._policy_row(workspace_id)
        if policy:
            return policy
        policy = WorkspaceExecutionPolicy(
            workspace_id=UUID(str(workspace_id)),
            updated_by_user_id=updated_by_user_id,
        )
        self.db.add(policy)
        self.db.flush()
        return policy

    def get_policy(self, auth: AuthContext) -> dict[str, object]:
        require_workspace_admin(auth, message="Only workspace admins can manage execution policy.")
        return self._to_dict(self._policy_row(auth.workspace_id), UUID(auth.workspace_id))

    def get_effective_policy(self, workspace_id: str | UUID) -> dict[str, object]:
        return self._to_dict(self._policy_row(workspace_id), UUID(str(workspace_id)))

    def update_policy(self, auth: AuthContext, payload: ExecutionPolicyUpdateRequest) -> dict[str, object]:
        require_workspace_admin(auth, message="Only workspace admins can manage execution policy.")
        policy = self._ensure_policy_row(auth.workspace_id, updated_by_user_id=UUID(auth.user_id))
        for field_name in ("text", "moderation", "image", "video", "speech"):
            route = getattr(payload, field_name)
            if route is None:
                continue
            mode = ExecutionMode(route.mode)
            if field_name in {"text", "moderation"} and mode == ExecutionMode.local:
                raise ApiError(
                    400,
                    "local_mode_not_supported",
                    f"Local execution is not supported for {field_name}.",
                )
            setattr(policy, f"{field_name}_mode", mode)
            setattr(policy, f"{field_name}_provider_key", route.provider_key)
            setattr(policy, f"{field_name}_credential_id", route.credential_id)
            if mode == ExecutionMode.byo and route.credential_id is None:
                raise ApiError(
                    400,
                    "provider_credential_required",
                    f"BYO routing for {field_name} requires a credential_id.",
                )
            if mode == ExecutionMode.byo and route.credential_id is not None:
                credential = self.db.scalar(
                    select(WorkspaceProviderCredential).where(
                        WorkspaceProviderCredential.id == route.credential_id,
                        WorkspaceProviderCredential.workspace_id == UUID(auth.workspace_id),
                    )
                )
                if not credential:
                    raise ApiError(
                        404,
                        "provider_credential_not_found",
                        f"The credential for {field_name} routing was not found.",
                    )
                if credential.modality != field_name:
                    raise ApiError(
                        400,
                        "provider_credential_modality_mismatch",
                        f"The selected credential does not support {field_name}.",
                    )
            if mode != ExecutionMode.byo:
                setattr(policy, f"{field_name}_credential_id", None)

        if "preferred_local_worker_id" in payload.model_fields_set:
            preferred_worker_id = payload.preferred_local_worker_id
            if preferred_worker_id is not None:
                worker = self.db.scalar(
                    select(LocalWorker).where(
                        LocalWorker.id == preferred_worker_id,
                        LocalWorker.workspace_id == UUID(auth.workspace_id),
                    )
                )
                if not worker:
                    raise ApiError(404, "local_worker_not_found", "Preferred local worker not found.")
            policy.preferred_local_worker_id = preferred_worker_id
        for field_name in (
            "pause_render_generation",
            "pause_image_generation",
            "pause_video_generation",
            "pause_audio_generation",
            "pause_reason",
        ):
            if field_name in payload.model_fields_set:
                setattr(policy, field_name, getattr(payload, field_name))
        policy.updated_by_user_id = UUID(auth.user_id)
        record_audit_event(
            self.db,
            workspace_id=UUID(auth.workspace_id),
            user_id=UUID(auth.user_id),
            event_type="workspace.execution_policy_updated",
            target_type="workspace_execution_policy",
            target_id=str(policy.id),
            payload={},
        )
        self.db.commit()
        self.db.refresh(policy)
        return self._to_dict(policy, UUID(auth.workspace_id))
