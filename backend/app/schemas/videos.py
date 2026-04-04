from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class VideoTranscriptResponse(BaseModel):
    id: UUID
    language_code: str
    word_count: int
    transcript_text: str
    whisper_model_size: str
    created_at: datetime
    updated_at: datetime


class VideoMetadataVersionResponse(BaseModel):
    id: UUID
    video_id: UUID
    version_number: int
    source_type: str
    provider_name: str | None
    provider_model: str | None
    title_options: list[str]
    recommended_title: str
    title: str
    description: str
    tags: list[str]
    hook_summary: str | None
    is_approved: bool
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class VideoResponse(BaseModel):
    id: UUID
    youtube_account_id: UUID | None
    approved_metadata_version_id: UUID | None
    original_file_name: str
    content_type: str
    size_bytes: int
    duration_ms: int | None
    width: int | None
    height: int | None
    status: str
    scheduled_publish_at: datetime | None
    published_at: datetime | None
    youtube_video_id: str | None
    processing_error_code: str | None
    processing_error_message: str | None
    created_at: datetime
    updated_at: datetime
    transcript: VideoTranscriptResponse | None = None
    metadata_versions: list[VideoMetadataVersionResponse] = Field(default_factory=list)
    approved_metadata_version: VideoMetadataVersionResponse | None = None


class VideoActionAcceptedResponse(BaseModel):
    video_id: UUID
    status: str
    message: str


class ApproveVideoMetadataRequest(BaseModel):
    metadata_version_id: UUID | None = None
    title: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    hook_summary: str | None = None
    youtube_account_id: UUID | None = None


class ScheduleVideoRequest(BaseModel):
    youtube_account_id: UUID | None = None
    publish_mode: Literal["immediate", "scheduled"]
    visibility: Literal["public", "private", "unlisted"] = "public"
    scheduled_publish_at_utc: datetime | None = None
    use_next_available_slot: bool = False


class BatchScheduleRequest(BaseModel):
    youtube_account_id: UUID
    video_ids: list[UUID]
    preview_only: bool = True


class BatchScheduleAssignmentResponse(BaseModel):
    video_id: UUID
    original_file_name: str
    publish_at_utc: datetime
    publish_at_local_label: str


class BatchScheduleResponse(BaseModel):
    preview_only: bool
    assignments: list[BatchScheduleAssignmentResponse] = Field(default_factory=list)
    created_job_ids: list[UUID] = Field(default_factory=list)


class PublishJobResponse(BaseModel):
    id: UUID
    video_id: UUID
    youtube_account_id: UUID
    metadata_version_id: UUID | None
    publish_mode: str
    visibility: str
    scheduled_publish_at: datetime | None
    status: str
    queued_at: datetime | None
    started_at: datetime | None
    published_at: datetime | None
    failed_at: datetime | None
    cancelled_at: datetime | None
    youtube_video_id: str | None
    youtube_video_url: str | None
    attempt_count: int
    error_code: str | None
    error_message: str | None
    last_progress_percent: int | None
    created_at: datetime
    updated_at: datetime
    original_file_name: str | None = None
    channel_title: str | None = None
