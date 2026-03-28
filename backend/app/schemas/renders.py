from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import JobAcceptedResponse


class RenderCreateRequest(BaseModel):
    scene_plan_id: str | None = None
    allow_export_without_music: bool = True


class RenderStepResponse(BaseModel):
    id: UUID
    render_job_id: UUID
    project_id: UUID
    scene_segment_id: UUID | None
    step_kind: str
    step_index: int
    status: str
    is_stale: bool
    input_payload: dict[str, object]
    output_payload: dict[str, object] | None
    error_code: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AssetResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    project_id: UUID
    render_job_id: UUID | None
    render_step_id: UUID | None
    scene_segment_id: UUID | None
    parent_asset_id: UUID | None
    provider_run_id: UUID | None
    consistency_pack_snapshot_id: UUID | None
    asset_type: str
    asset_role: str
    status: str
    bucket_name: str
    object_name: str
    file_name: str
    content_type: str
    size_bytes: int
    duration_ms: int | None
    width: int | None
    height: int | None
    frame_rate: float | None
    has_audio_stream: bool
    source_audio_policy: str
    timing_alignment_strategy: str
    metadata_payload: dict[str, object]
    download_url: str | None = None
    created_at: datetime
    updated_at: datetime


class ExportResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    project_id: UUID
    render_job_id: UUID
    asset_id: UUID
    status: str
    file_name: str
    format: str
    bucket_name: str
    object_name: str
    duration_ms: int | None
    metadata_payload: dict[str, object]
    download_url: str | None = None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RenderJobResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    project_id: UUID
    created_by_user_id: UUID
    script_version_id: UUID | None
    scene_plan_id: UUID | None
    consistency_pack_id: UUID | None
    voice_preset_id: UUID | None
    job_kind: str
    queue_name: str
    status: str
    idempotency_key: str
    request_hash: str
    payload: dict[str, object]
    allow_export_without_music: bool
    error_code: str | None
    error_message: str | None
    retry_count: int
    started_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime
    steps: list[RenderStepResponse]
    assets: list[AssetResponse]
    exports: list[ExportResponse]


class RenderEventResponse(BaseModel):
    at: datetime
    event_type: str
    target_type: str
    target_id: str | None
    payload: dict[str, object]


class AssetSignedUrlResponse(BaseModel):
    asset_id: UUID
    url: str


class RenderCreateResponse(JobAcceptedResponse):
    pass
