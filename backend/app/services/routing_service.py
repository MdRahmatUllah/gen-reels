from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from app.core.errors import AdapterError, ApiError
from app.integrations.azure import (
    AzureContentSafetyProvider,
    AzureOpenAITextProvider,
    ModerationProvider,
    StubModerationProvider,
    StubTextProvider,
    TextProvider,
)
from app.integrations.media import (
    AzureOpenAIImageProvider,
    AzureOpenAISpeechProvider,
    ImageProvider,
    SpeechProvider,
    StubImageProvider,
    StubSpeechProvider,
    StubVideoProvider,
    VeoVideoProvider,
    VideoProvider,
)
from app.integrations.third_party import ElevenLabsSpeechProvider, RunwayVideoProvider, StabilityImageProvider
from app.models.entities import ExecutionMode, LocalWorker, LocalWorkerStatus, WorkspaceProviderCredential
from app.services.execution_policy_service import DEFAULT_POLICY, ExecutionPolicyService
from app.services.provider_credential_service import ProviderCredentialService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RoutingDecision:
    modality: str
    execution_mode: ExecutionMode
    provider_key: str
    provider_name: str
    provider_model: str
    provider_credential_id: UUID | None = None
    worker_id: UUID | None = None
    public_config: dict[str, object] = field(default_factory=dict)
    secret_config: dict[str, object] = field(default_factory=dict)
    reason: str = "policy_default"

    def to_payload(self) -> dict[str, object]:
        return {
            "modality": self.modality,
            "execution_mode": self.execution_mode.value,
            "provider_key": self.provider_key,
            "provider_name": self.provider_name,
            "provider_model": self.provider_model,
            "provider_credential_id": str(self.provider_credential_id) if self.provider_credential_id else None,
            "worker_id": str(self.worker_id) if self.worker_id else None,
            "public_config": self.public_config,
            "reason": self.reason,
        }


class RoutingService:
    def __init__(self, db, settings) -> None:
        self.db = db
        self.settings = settings
        self.policy_service = ExecutionPolicyService(db)
        self.credential_service = ProviderCredentialService(db, settings)

    def _worker_is_online(self, worker: LocalWorker) -> bool:
        if worker.revoked_at is not None or worker.status == LocalWorkerStatus.revoked:
            return False
        heartbeat_at = self._normalized_datetime(worker.last_heartbeat_at)
        if not heartbeat_at:
            return False
        threshold = datetime.now(UTC) - timedelta(
            seconds=self.settings.local_worker_heartbeat_timeout_seconds
        )
        return heartbeat_at >= threshold

    @staticmethod
    def _normalized_datetime(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def refresh_worker_statuses(self) -> int:
        updated = 0
        threshold = datetime.now(UTC) - timedelta(
            seconds=self.settings.local_worker_heartbeat_timeout_seconds
        )
        workers = self.db.scalars(select(LocalWorker)).all()
        for worker in workers:
            next_status = worker.status
            if worker.revoked_at is not None:
                next_status = LocalWorkerStatus.revoked
            elif (
                self._normalized_datetime(worker.last_heartbeat_at) is None
                or self._normalized_datetime(worker.last_heartbeat_at) < threshold
            ):
                next_status = LocalWorkerStatus.offline
            else:
                next_status = LocalWorkerStatus.online
            if next_status != worker.status:
                worker.status = next_status
                updated += 1
        if updated:
            self.db.commit()
        return updated

    def _resolve_byo_credential(
        self,
        workspace_id: UUID,
        credential_id: UUID,
        *,
        modality: str,
    ) -> tuple[WorkspaceProviderCredential, dict[str, object]]:
        try:
            credential, secret_config = self.credential_service.get_runtime_credential(
                workspace_id,
                credential_id,
                modality=modality,
            )
        except ApiError as exc:
            raise AdapterError("deterministic_input", exc.code, exc.message) from exc
        self.credential_service.touch_runtime_use(credential)
        return credential, secret_config

    def _select_local_worker(
        self,
        workspace_id: UUID,
        *,
        requires_ordered_reference_images: bool = False,
        requires_first_last_frame_video: bool = False,
        requires_tts: bool = False,
        preferred_worker_id: UUID | None = None,
    ) -> LocalWorker:
        self.refresh_worker_statuses()
        query = select(LocalWorker).where(LocalWorker.workspace_id == workspace_id)
        if preferred_worker_id:
            query = query.where(LocalWorker.id == preferred_worker_id)
        workers = self.db.scalars(query.order_by(LocalWorker.updated_at.desc())).all()
        for worker in workers:
            if not self._worker_is_online(worker):
                continue
            if requires_ordered_reference_images and not worker.supports_ordered_reference_images:
                continue
            if requires_first_last_frame_video and not worker.supports_first_last_frame_video:
                continue
            if requires_tts and not worker.supports_tts:
                continue
            return worker
        raise AdapterError(
            "deterministic_input",
            "local_worker_unavailable",
            "No online local worker matches the requested capabilities.",
        )

    def resolve_runtime_route(
        self,
        workspace_id: str | UUID,
        modality: str,
        *,
        requires_ordered_reference_images: bool = False,
        requires_first_last_frame_video: bool = False,
        requires_tts: bool = False,
    ) -> RoutingDecision:
        workspace_uuid = UUID(str(workspace_id))
        policy = self.policy_service.get_effective_policy(workspace_uuid)
        route = policy.get(modality) or self.policy_service._route_to_dict(DEFAULT_POLICY[modality])
        mode = ExecutionMode(route["mode"])
        provider_key = str(route["provider_key"])
        credential_id = route.get("credential_id")
        preferred_local_worker_id = policy.get("preferred_local_worker_id")

        if mode == ExecutionMode.local:
            if modality in {"text", "moderation"}:
                raise AdapterError(
                    "deterministic_input",
                    "local_mode_not_supported",
                    f"Local execution is not supported for {modality}.",
                )
            worker = self._select_local_worker(
                workspace_uuid,
                requires_ordered_reference_images=requires_ordered_reference_images,
                requires_first_last_frame_video=requires_first_last_frame_video,
                requires_tts=requires_tts,
                preferred_worker_id=UUID(str(preferred_local_worker_id))
                if preferred_local_worker_id
                else None,
            )
            return RoutingDecision(
                modality=modality,
                execution_mode=mode,
                provider_key=provider_key,
                provider_name="local_worker",
                provider_model="local-agent-v1",
                worker_id=worker.id,
                public_config={"worker_name": worker.name},
                reason="workspace_policy_local",
            )

        if mode == ExecutionMode.byo:
            if not credential_id:
                raise AdapterError(
                    "deterministic_input",
                    "provider_credential_required",
                    f"BYO execution for {modality} requires a credential.",
                )
            credential, secret_config = self._resolve_byo_credential(
                workspace_uuid,
                UUID(str(credential_id)),
                modality=modality,
            )
            provider_model = (
                str(credential.public_config.get("deployment"))
                or str(credential.public_config.get("model"))
                or provider_key
            )
            return RoutingDecision(
                modality=modality,
                execution_mode=mode,
                provider_key=provider_key,
                provider_name=provider_key,
                provider_model=provider_model,
                provider_credential_id=credential.id,
                public_config=dict(credential.public_config or {}),
                secret_config=secret_config,
                reason="workspace_policy_byo",
            )

        default_route = DEFAULT_POLICY[modality]
        provider_model = provider_key
        if modality == "text":
            provider_model = self.settings.azure_openai_chat_deployment or provider_key
        return RoutingDecision(
            modality=modality,
            execution_mode=ExecutionMode.hosted,
            provider_key=provider_key,
            provider_name=provider_key,
            provider_model=provider_model,
            reason="workspace_policy_hosted",
        )

    def build_text_provider_for_workspace(self, workspace_id: str | UUID) -> tuple[TextProvider, RoutingDecision]:
        decision = self.resolve_runtime_route(workspace_id, "text")
        if self.settings.use_stub_providers or self.settings.environment == "test":
            return StubTextProvider(), decision
        if decision.execution_mode == ExecutionMode.byo:
            return (
                AzureOpenAITextProvider(
                    self.settings,
                    endpoint=str(decision.public_config.get("endpoint") or ""),
                    api_key=str(decision.secret_config.get("api_key") or ""),
                    deployment=str(decision.public_config.get("deployment") or ""),
                    api_version=str(
                        decision.public_config.get("api_version") or self.settings.azure_openai_api_version
                    ),
                ),
                decision,
            )
        return AzureOpenAITextProvider(self.settings), decision

    def build_moderation_provider_for_workspace(
        self,
        workspace_id: str | UUID,
    ) -> tuple[ModerationProvider, RoutingDecision]:
        decision = self.resolve_runtime_route(workspace_id, "moderation")
        if self.settings.use_stub_providers or self.settings.environment == "test":
            return StubModerationProvider(), decision
        if decision.execution_mode == ExecutionMode.byo:
            return (
                AzureContentSafetyProvider(
                    self.settings,
                    endpoint=str(decision.public_config.get("endpoint") or ""),
                    api_key=str(decision.secret_config.get("api_key") or ""),
                    api_version=str(
                        decision.public_config.get("api_version")
                        or self.settings.azure_content_safety_api_version
                    ),
                ),
                decision,
            )
        try:
            return AzureContentSafetyProvider(self.settings), decision
        except AdapterError as error:
            if (
                self.settings.environment == "development"
                and error.code == "missing_content_safety_config"
            ):
                logger.warning(
                    "moderation_fallback_stub workspace_id=%s reason=%s",
                    workspace_id,
                    error.code,
                )
                return StubModerationProvider(), decision
            raise

    def build_image_provider_for_workspace(
        self,
        workspace_id: str | UUID,
    ) -> tuple[ImageProvider | None, RoutingDecision]:
        decision = self.resolve_runtime_route(
            workspace_id,
            "image",
            requires_ordered_reference_images=True,
        )
        if decision.execution_mode == ExecutionMode.local:
            return None, decision
        if self.settings.use_stub_providers or self.settings.environment == "test":
            return (
                StubImageProvider(provider_name=decision.provider_name, provider_model=decision.provider_model),
                decision,
            )
        if decision.execution_mode == ExecutionMode.byo:
            if decision.provider_key == "stability_image":
                return (
                    StabilityImageProvider(
                        self.settings,
                        api_key=str(decision.secret_config.get("api_key") or ""),
                        model=str(
                            decision.public_config.get("model_name")
                            or decision.public_config.get("model")
                            or decision.provider_model
                        ),
                        endpoint=str(decision.public_config.get("endpoint") or "https://api.stability.ai"),
                    ),
                    decision,
                )
            return (
                AzureOpenAIImageProvider(
                    self.settings,
                    endpoint=str(decision.public_config.get("endpoint") or self.settings.azure_openai_endpoint or ""),
                    api_key=str(decision.secret_config.get("api_key") or ""),
                    deployment=str(
                        decision.public_config.get("deployment")
                        or decision.public_config.get("model")
                        or decision.provider_model
                    ),
                    api_version=str(
                        decision.public_config.get("api_version")
                        or self.settings.azure_openai_image_api_version
                    ),
                    model=str(
                        decision.public_config.get("model_name") or self.settings.azure_openai_image_model
                    ),
                ),
                decision,
            )
        return AzureOpenAIImageProvider(self.settings), decision

    def build_video_provider_for_workspace(
        self,
        workspace_id: str | UUID,
    ) -> tuple[VideoProvider | None, RoutingDecision]:
        decision = self.resolve_runtime_route(
            workspace_id,
            "video",
            requires_first_last_frame_video=True,
        )
        if decision.execution_mode == ExecutionMode.local:
            return None, decision
        if self.settings.use_stub_providers or self.settings.environment == "test":
            return (
                StubVideoProvider(
                    settings=self.settings,
                    provider_name=decision.provider_name,
                    provider_model=decision.provider_model,
                ),
                decision,
            )
        if decision.execution_mode == ExecutionMode.byo and decision.provider_key == "runway_video":
            return (
                RunwayVideoProvider(
                    self.settings,
                    api_key=str(decision.secret_config.get("api_key") or ""),
                    model=str(
                        decision.public_config.get("model_name")
                        or decision.public_config.get("model")
                        or decision.provider_model
                    ),
                    endpoint=str(decision.public_config.get("endpoint") or "https://api.dev.runwayml.com"),
                ),
                decision,
            )
        return VeoVideoProvider(self.settings), decision

    def build_speech_provider_for_workspace(
        self,
        workspace_id: str | UUID,
    ) -> tuple[SpeechProvider | None, RoutingDecision]:
        decision = self.resolve_runtime_route(workspace_id, "speech", requires_tts=True)
        if decision.execution_mode == ExecutionMode.local:
            return None, decision
        if self.settings.use_stub_providers or self.settings.environment == "test":
            return (
                StubSpeechProvider(provider_name=decision.provider_name, provider_model=decision.provider_model),
                decision,
            )
        if decision.execution_mode == ExecutionMode.byo:
            if decision.provider_key == "elevenlabs_speech":
                return (
                    ElevenLabsSpeechProvider(
                        self.settings,
                        api_key=str(decision.secret_config.get("api_key") or ""),
                        model=str(
                            decision.public_config.get("model_name")
                            or decision.public_config.get("model")
                            or decision.provider_model
                        ),
                        voice=str(decision.public_config.get("voice") or ""),
                        endpoint=str(decision.public_config.get("endpoint") or "https://api.elevenlabs.io"),
                    ),
                    decision,
                )
            return (
                AzureOpenAISpeechProvider(
                    self.settings,
                    endpoint=str(decision.public_config.get("endpoint") or self.settings.azure_openai_endpoint or ""),
                    api_key=str(decision.secret_config.get("api_key") or ""),
                    deployment=str(
                        decision.public_config.get("deployment")
                        or decision.public_config.get("model")
                        or decision.provider_model
                    ),
                    api_version=str(
                        decision.public_config.get("api_version")
                        or self.settings.azure_openai_speech_api_version
                    ),
                    model=str(
                        decision.public_config.get("model_name") or self.settings.azure_openai_speech_model
                    ),
                    default_voice=str(
                        decision.public_config.get("voice") or self.settings.azure_openai_speech_voice
                    ),
                ),
                decision,
            )
        return AzureOpenAISpeechProvider(self.settings), decision
