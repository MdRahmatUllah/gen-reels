from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ModerationReviewRequest(BaseModel):
    notes: str | None = None


class AdminModerationItemResponse(BaseModel):
    id: UUID
    project_id: UUID | None
    workspace_id: UUID | None
    user_id: UUID | None
    related_asset_id: UUID | None
    render_job_id: UUID | None
    render_step_id: UUID | None
    target_type: str
    target_id: str | None
    input_text: str
    decision: str
    review_status: str
    reviewed_by_user_id: UUID | None
    reviewed_at: datetime | None
    review_notes: str | None
    provider_name: str
    severity_summary: dict[str, object]
    blocked_message: str | None
    asset_status: str | None = None
    asset_download_url: str | None = None
    created_at: datetime


class AdminRenderSummaryResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    project_id: UUID
    created_by_user_id: UUID
    status: str
    queue_name: str
    retry_count: int
    error_code: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    step_count: int
    failed_step_count: int
    blocked_step_count: int
    latest_step_kind: str | None = None
    latest_provider_cost_cents: int
    provider_run_count: int


class AdminModerationReportResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    project_id: UUID | None
    render_job_id: UUID | None
    export_id: UUID | None
    related_asset_id: UUID | None
    status: str
    sample_reason: str
    provider_name: str
    blocked_event_count_30d: int
    findings_payload: dict[str, object]
    reviewed_by_user_id: UUID | None
    reviewed_at: datetime | None
    review_notes: str | None
    created_at: datetime
    updated_at: datetime
