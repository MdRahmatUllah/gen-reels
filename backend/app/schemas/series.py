from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class SeriesCatalogOptionResponse(BaseModel):
    key: str
    label: str
    description: str
    gender: str | None = None
    badge: str | None = None


class SeriesCatalogResponse(BaseModel):
    content_presets: list[SeriesCatalogOptionResponse]
    languages: list[SeriesCatalogOptionResponse]
    voices: list[SeriesCatalogOptionResponse]
    music: list[SeriesCatalogOptionResponse]
    art_styles: list[SeriesCatalogOptionResponse]
    caption_styles: list[SeriesCatalogOptionResponse]
    effects: list[SeriesCatalogOptionResponse]


class SeriesWriteRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=500)
    content_mode: Literal["preset", "custom"]
    preset_key: str | None = None
    custom_topic: str = Field(default="", max_length=5000)
    custom_example_script: str = Field(default="", max_length=2000)
    language_key: str = Field(default="en", min_length=1, max_length=32)
    voice_key: str = Field(min_length=1, max_length=64)
    music_mode: Literal["none", "preset"] = "none"
    music_keys: list[str] = Field(default_factory=list)
    art_style_key: str = Field(min_length=1, max_length=64)
    caption_style_key: str = Field(min_length=1, max_length=64)
    effect_keys: list[str] = Field(default_factory=list)

    @field_validator("music_keys", "effect_keys")
    @classmethod
    def _trim_keys(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]

    @model_validator(mode="after")
    def _validate_cross_fields(self) -> "SeriesWriteRequest":
        if self.content_mode == "preset" and not self.preset_key:
            raise ValueError("preset_key is required when content_mode is preset.")
        if self.content_mode == "custom" and not self.custom_topic.strip():
            raise ValueError("custom_topic is required when content_mode is custom.")
        if self.music_mode == "none" and self.music_keys:
            raise ValueError("music_keys must be empty when music_mode is none.")
        if self.music_mode == "preset" and not self.music_keys:
            raise ValueError("music_keys must contain at least one item when music_mode is preset.")
        if len(set(self.effect_keys)) != len(self.effect_keys):
            raise ValueError("effect_keys must be unique.")
        if len(set(self.music_keys)) != len(self.music_keys):
            raise ValueError("music_keys must be unique.")
        return self


class SeriesCreateRequest(SeriesWriteRequest):
    pass


class SeriesUpdateRequest(SeriesWriteRequest):
    pass


class SeriesSummaryResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    owner_user_id: UUID
    title: str
    description: str
    content_mode: str
    preset_key: str | None
    language_key: str
    voice_key: str
    music_mode: str
    music_keys: list[str]
    art_style_key: str
    caption_style_key: str
    effect_keys: list[str]
    total_script_count: int
    scripts_awaiting_review_count: int
    approved_script_count: int
    completed_video_count: int
    latest_run_id: UUID | None
    latest_run_status: str | None
    active_run_id: UUID | None
    active_run_status: str | None
    active_video_run_id: UUID | None
    active_video_run_status: str | None
    primary_cta: str
    can_edit: bool | None = None
    last_activity_at: datetime
    created_at: datetime
    updated_at: datetime


class SeriesDetailResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    owner_user_id: UUID
    title: str
    description: str
    content_mode: str
    preset_key: str | None
    custom_topic: str
    custom_example_script: str
    language_key: str
    voice_key: str
    music_mode: str
    music_keys: list[str]
    art_style_key: str
    caption_style_key: str
    effect_keys: list[str]
    total_script_count: int
    scripts_awaiting_review_count: int
    approved_script_count: int
    completed_video_count: int
    latest_run_id: UUID | None
    latest_run_status: str | None
    active_run_id: UUID | None
    active_run_status: str | None
    active_video_run_id: UUID | None
    active_video_run_status: str | None
    primary_cta: str
    can_edit: bool
    last_activity_at: datetime
    created_at: datetime
    updated_at: datetime


class SeriesLineResponse(BaseModel):
    id: str
    scene_id: str
    beat: str
    narration: str
    caption: str
    duration_sec: int
    status: str
    visual_direction: str
    voice_pacing: str


class SeriesRevisionSummaryResponse(BaseModel):
    id: UUID
    series_script_id: UUID
    revision_number: int
    approval_state: str
    title: str
    summary: str
    estimated_duration_seconds: int
    reading_time_label: str
    total_words: int
    lines: list[dict[str, Any]]
    video_title: str
    video_description: str
    created_at: datetime
    updated_at: datetime


class SeriesPublishedVideoResponse(BaseModel):
    project_id: UUID | None = None
    render_job_id: UUID | None = None
    export_id: UUID | None = None
    download_url: str | None = None
    title: str = ""
    description: str = ""
    completed_at: datetime | None = None


class SeriesScriptResponse(BaseModel):
    id: UUID
    series_id: UUID
    series_run_id: UUID
    created_by_user_id: UUID | None
    sequence_number: int
    title: str
    summary: str
    estimated_duration_seconds: int
    reading_time_label: str
    total_words: int
    lines: list[dict[str, Any]]
    approval_state: str
    video_status: str | None = None
    video_phase: str | None = None
    video_current_scene_index: int | None = None
    video_current_scene_count: int | None = None
    video_render_job_id: UUID | None = None
    video_hidden_project_id: UUID | None = None
    current_revision: SeriesRevisionSummaryResponse | None = None
    approved_revision: SeriesRevisionSummaryResponse | None = None
    published_revision: SeriesRevisionSummaryResponse | None = None
    published_video: SeriesPublishedVideoResponse | None = None
    can_approve: bool
    can_reject: bool
    can_regenerate: bool
    can_create_video: bool
    created_at: datetime
    updated_at: datetime


class SeriesSceneAssetResponse(BaseModel):
    asset_id: UUID
    download_url: str | None = None


class SeriesScenePreviewResponse(BaseModel):
    scene_segment_id: UUID
    scene_index: int
    title: str
    beat: str
    narration_text: str
    caption_text: str
    target_duration_seconds: int
    visual_prompt: str
    start_image_prompt: str
    end_image_prompt: str
    start_frame_asset: SeriesSceneAssetResponse | None = None
    end_frame_asset: SeriesSceneAssetResponse | None = None
    narration_asset: SeriesSceneAssetResponse | None = None
    slide_asset: SeriesSceneAssetResponse | None = None


class SeriesScriptDetailResponse(BaseModel):
    script: SeriesScriptResponse
    revisions: list[SeriesRevisionSummaryResponse]
    scenes: list[SeriesScenePreviewResponse]
    latest_render_job_id: UUID | None = None
    latest_render_status: str | None = None
    latest_scene_plan_id: UUID | None = None


class SeriesRunStepResponse(BaseModel):
    id: UUID
    series_run_id: UUID
    series_id: UUID
    series_script_id: UUID | None
    step_index: int
    sequence_number: int
    status: str
    input_payload: dict[str, Any]
    output_payload: dict[str, Any] | None
    error_code: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SeriesRunResponse(BaseModel):
    id: UUID
    series_id: UUID
    workspace_id: UUID
    created_by_user_id: UUID
    status: str
    requested_script_count: int
    completed_script_count: int
    failed_script_count: int
    idempotency_key: str
    request_hash: str
    payload: dict[str, Any]
    error_code: str | None = None
    error_message: str | None = None
    retry_count: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    steps: list[SeriesRunStepResponse] = Field(default_factory=list)
    current_step: int | None = None


class SeriesRunCreateRequest(BaseModel):
    requested_script_count: int = Field(ge=1, le=50)


class SeriesVideoRunStepResponse(BaseModel):
    id: UUID
    series_video_run_id: UUID
    series_id: UUID
    series_script_id: UUID
    series_script_revision_id: UUID
    step_index: int
    sequence_number: int
    status: str
    phase: str
    hidden_project_id: UUID | None = None
    render_job_id: UUID | None = None
    last_render_event_sequence: int
    current_scene_index: int | None = None
    current_scene_count: int | None = None
    input_payload: dict[str, Any]
    output_payload: dict[str, Any] | None
    error_code: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SeriesVideoRunResponse(BaseModel):
    id: UUID
    series_id: UUID
    workspace_id: UUID
    created_by_user_id: UUID
    status: str
    requested_video_count: int
    completed_video_count: int
    failed_video_count: int
    idempotency_key: str
    request_hash: str
    payload: dict[str, Any]
    error_code: str | None = None
    error_message: str | None = None
    retry_count: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    steps: list[SeriesVideoRunStepResponse] = Field(default_factory=list)
    current_step: int | None = None


class SeriesVideoRunCreateRequest(BaseModel):
    series_script_ids: list[str] = Field(default_factory=list)

    @field_validator("series_script_ids")
    @classmethod
    def _strip_ids(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]
