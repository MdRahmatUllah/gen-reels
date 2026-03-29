from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ProviderCredentialCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    modality: Literal["text", "moderation", "image", "video", "speech"]
    provider_key: str = Field(min_length=1, max_length=128)
    public_config: dict[str, object] = Field(default_factory=dict)
    secret_config: dict[str, str] = Field(default_factory=dict)
    expires_at: datetime | None = None


class ProviderCredentialUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    modality: Literal["text", "moderation", "image", "video", "speech"] | None = None
    provider_key: str | None = Field(default=None, min_length=1, max_length=128)
    public_config: dict[str, object] | None = None
    secret_config: dict[str, str] | None = None
    expires_at: datetime | None = None


class ProviderCredentialResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    created_by_user_id: UUID | None
    name: str
    modality: str
    provider_key: str
    public_config: dict[str, object]
    last_used_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
    updated_at: datetime
    secret_configured: bool = True
    validation_status: str | None = None
    last_validated_at: datetime | None = None
    last_validation_error: str | None = None


class ModalityExecutionPolicyRequest(BaseModel):
    mode: Literal["hosted", "byo", "local"]
    provider_key: str = Field(min_length=1, max_length=128)
    credential_id: UUID | None = None


class ModalityExecutionPolicyResponse(BaseModel):
    mode: str
    provider_key: str
    credential_id: UUID | None


class ExecutionPolicyUpdateRequest(BaseModel):
    text: ModalityExecutionPolicyRequest | None = None
    moderation: ModalityExecutionPolicyRequest | None = None
    image: ModalityExecutionPolicyRequest | None = None
    video: ModalityExecutionPolicyRequest | None = None
    speech: ModalityExecutionPolicyRequest | None = None
    preferred_local_worker_id: UUID | None = None
    pause_render_generation: bool | None = None
    pause_image_generation: bool | None = None
    pause_video_generation: bool | None = None
    pause_audio_generation: bool | None = None
    pause_reason: str | None = None


class ExecutionPolicyResponse(BaseModel):
    id: UUID | None = None
    workspace_id: UUID
    text: ModalityExecutionPolicyResponse
    moderation: ModalityExecutionPolicyResponse
    image: ModalityExecutionPolicyResponse
    video: ModalityExecutionPolicyResponse
    speech: ModalityExecutionPolicyResponse
    preferred_local_worker_id: UUID | None
    pause_render_generation: bool = False
    pause_image_generation: bool = False
    pause_video_generation: bool = False
    pause_audio_generation: bool = False
    pause_reason: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class WorkspaceAuthConfigurationCreateRequest(BaseModel):
    provider_type: Literal["oidc", "saml"]
    display_name: str = Field(min_length=1, max_length=255)
    config_public: dict[str, object] = Field(default_factory=dict)
    secret_config: dict[str, str] = Field(default_factory=dict)
    is_enabled: bool = True


class WorkspaceAuthConfigurationUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    config_public: dict[str, object] | None = None
    secret_config: dict[str, str] | None = None
    is_enabled: bool | None = None


class WorkspaceAuthConfigurationResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    created_by_user_id: UUID | None
    updated_by_user_id: UUID | None
    provider_type: str
    display_name: str
    config_public: dict[str, object]
    is_enabled: bool
    last_validated_at: datetime | None
    last_validation_error: str | None
    created_at: datetime
    updated_at: datetime


class LocalWorkerRegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    supports_ordered_reference_images: bool = False
    supports_first_last_frame_video: bool = False
    supports_tts: bool = False
    supports_clip_retime: bool = False
    metadata_payload: dict[str, object] = Field(default_factory=dict)


class LocalWorkerHeartbeatRequest(BaseModel):
    metadata_payload: dict[str, object] = Field(default_factory=dict)


class LocalWorkerResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    registered_by_api_key_id: UUID | None
    name: str
    status: str
    token_prefix: str
    supports_ordered_reference_images: bool
    supports_first_last_frame_video: bool
    supports_tts: bool
    supports_clip_retime: bool
    metadata_payload: dict[str, object]
    last_heartbeat_at: datetime | None
    last_polled_at: datetime | None
    last_job_claimed_at: datetime | None
    last_error_at: datetime | None
    last_error_code: str | None
    last_error_message: str | None
    revoked_at: datetime | None
    created_at: datetime
    updated_at: datetime


class LocalWorkerRegisterResponse(LocalWorkerResponse):
    worker_token: str


class LocalWorkerJobOutputUpload(BaseModel):
    role: str
    bucket_name: str
    object_name: str
    upload_url: str
    content_type: str
    file_name: str


class LocalWorkerJobResponse(BaseModel):
    provider_run_id: UUID | None = None
    render_job_id: UUID | None = None
    render_step_id: UUID | None = None
    step_kind: str | None = None
    modality: str | None = None
    scene_index: int | None = None
    prompt: str | None = None
    start_prompt: str | None = None
    end_prompt: str | None = None
    negative_prompt: str | None = None
    narration_text: str | None = None
    duration_seconds: int | None = None
    start_frame_url: str | None = None
    end_frame_url: str | None = None
    reference_image_urls: list[str] = Field(default_factory=list)
    voice_preset: dict[str, object] = Field(default_factory=dict)
    outputs: list[LocalWorkerJobOutputUpload] = Field(default_factory=list)
    provider_metadata: dict[str, object] = Field(default_factory=dict)


class LocalWorkerJobPollResponse(BaseModel):
    job: LocalWorkerJobResponse | None = None


class LocalWorkerJobResultOutput(BaseModel):
    role: str
    bucket_name: str
    object_name: str
    content_type: str
    file_name: str
    metadata_payload: dict[str, object] = Field(default_factory=dict)


class LocalWorkerJobResultRequest(BaseModel):
    status: Literal["completed", "failed"]
    outputs: list[LocalWorkerJobResultOutput] = Field(default_factory=list)
    provider_metadata: dict[str, object] = Field(default_factory=dict)
    duration_seconds: float | None = None
    has_audio_stream: bool | None = None
    error_code: str | None = None
    error_message: str | None = None
    is_retryable: bool = False


class LocalWorkerJobResultResponse(BaseModel):
    render_job_id: UUID
    render_step_id: UUID
    provider_run_id: UUID
    status: str
