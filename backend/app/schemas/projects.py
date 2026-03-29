from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import JobSummary


class ProjectCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    client: str | None = Field(default=None, max_length=255)
    aspect_ratio: str = "9:16"
    duration_target_sec: int = Field(default=90, ge=60, le=120)
    brand_kit_id: str | None = None


class QuickStartCreateRequest(BaseModel):
    idea_prompt: str = Field(min_length=1, max_length=4000)
    starter_mode: str = Field(default="studio_default", pattern="^(studio_default|template)$")
    template_id: str | None = None


class ProjectUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    client: str | None = Field(default=None, max_length=255)
    aspect_ratio: str | None = None
    duration_target_sec: int | None = Field(default=None, ge=60, le=120)
    stage: str | None = None
    archived: bool | None = None
    default_visual_preset_id: str | None = None
    default_voice_preset_id: str | None = None
    brand_kit_id: str | None = None
    subtitle_style_profile: dict[str, Any] | None = None
    export_profile: dict[str, Any] | None = None
    audio_mix_profile: dict[str, Any] | None = None


class ProjectResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    owner_user_id: UUID
    source_template_version_id: UUID | None
    brand_kit_id: UUID | None
    title: str
    client: str | None
    aspect_ratio: str
    duration_target_sec: int
    subtitle_style_profile: dict[str, Any]
    export_profile: dict[str, Any]
    audio_mix_profile: dict[str, Any]
    stage: str
    active_brief_id: UUID | None
    selected_idea_id: UUID | None
    active_script_version_id: UUID | None
    active_scene_plan_id: UUID | None
    default_visual_preset_id: UUID | None
    default_voice_preset_id: UUID | None
    archived_at: datetime | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class BriefWriteRequest(BaseModel):
    objective: str
    hook: str
    target_audience: str
    call_to_action: str
    brand_north_star: str
    guardrails: list[str] = Field(default_factory=list)
    must_include: list[str] = Field(default_factory=list)
    approval_steps: list[str] = Field(default_factory=list)


class BriefVersionResponse(BaseModel):
    id: UUID
    project_id: UUID
    version_number: int
    objective: str
    hook: str
    target_audience: str
    call_to_action: str
    brand_north_star: str
    guardrails: list[str]
    must_include: list[str]
    approval_steps: list[str]
    created_at: datetime


class IdeaCandidateResponse(BaseModel):
    id: UUID
    idea_set_id: UUID
    project_id: UUID
    title: str
    hook: str
    summary: str
    tags: list[str]
    order_index: int
    status: str
    created_at: datetime


class IdeaSetResponse(BaseModel):
    id: UUID
    project_id: UUID
    source_brief_id: UUID
    created_at: datetime
    candidates: list[IdeaCandidateResponse]


class ScriptLineResponse(BaseModel):
    id: str
    scene_id: str
    beat: str
    narration: str
    caption: str
    duration_sec: int
    status: str
    visual_direction: str
    voice_pacing: str


class ScriptVersionResponse(BaseModel):
    id: UUID
    project_id: UUID
    based_on_idea_id: UUID | None
    parent_version_id: UUID | None
    version_number: int
    version: int
    source_type: str
    approval_state: str
    approved_at: datetime | None
    approved_by_user_id: UUID | None
    total_words: int
    estimated_duration_seconds: int
    reading_time_label: str
    lines: list[dict[str, Any]]
    created_at: datetime


class ProjectDetailResponse(BaseModel):
    project: ProjectResponse
    active_brief: BriefVersionResponse | None = None
    selected_idea: IdeaCandidateResponse | None = None
    latest_idea_set: IdeaSetResponse | None = None
    active_script_version: ScriptVersionResponse | None = None
    active_scene_plan: dict[str, Any] | None = None
    brief_versions: list[BriefVersionResponse]
    script_versions: list[ScriptVersionResponse]
    scene_plans: list[dict[str, Any]]
    recent_jobs: list[JobSummary]


class QuickStartStepResponse(BaseModel):
    step_kind: str
    step_index: int
    status: str
    error_code: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class QuickStartCreateResponse(BaseModel):
    project: ProjectResponse
    job: JobSummary
    redirect_path: str


class QuickStartStatusResponse(BaseModel):
    project: ProjectResponse
    job: JobSummary
    steps: list[QuickStartStepResponse]
    current_step: str | None = None
    completed_steps: list[str] = Field(default_factory=list)
    redirect_path: str
    recovery_path: str


class PromptHistoryResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    project_id: UUID | None
    scene_plan_id: UUID | None
    scene_segment_id: UUID | None
    render_job_id: UUID | None
    render_step_id: UUID | None
    provider_run_id: UUID | None
    asset_id: UUID | None
    export_id: UUID | None
    prompt_role: str
    prompt_text: str
    source_asset_id: UUID | None
    source_prompt_history_id: UUID | None
    metadata_payload: dict[str, Any]
    created_at: datetime


class ProjectLineageResponse(BaseModel):
    project: ProjectResponse
    source_template_version: dict[str, Any] | None = None
    visual_preset: dict[str, Any] | None = None
    voice_preset: dict[str, Any] | None = None
    exports: list[dict[str, Any]]
    library_assets: list[dict[str, Any]]
    prompt_history: list[PromptHistoryResponse]
