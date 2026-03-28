from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import JobAcceptedResponse


class SceneSegmentWriteRequest(BaseModel):
    scene_index: int = Field(ge=1)
    source_line_ids: list[str] = Field(default_factory=list)
    title: str = ""
    beat: str = ""
    narration_text: str
    caption_text: str = ""
    visual_direction: str = ""
    shot_type: str = ""
    motion: str = ""
    target_duration_seconds: int = Field(ge=1, le=30)
    estimated_voice_duration_seconds: int = Field(ge=1, le=30)
    visual_prompt: str = ""
    start_image_prompt: str = ""
    end_image_prompt: str = ""
    transition_mode: str = "hard_cut"
    notes: list[str] = Field(default_factory=list)


class SceneSegmentResponse(BaseModel):
    id: UUID
    scene_plan_id: UUID
    scene_index: int
    source_line_ids: list[str]
    title: str
    beat: str
    narration_text: str
    caption_text: str
    visual_direction: str
    shot_type: str
    motion: str
    target_duration_seconds: int
    estimated_voice_duration_seconds: int
    actual_voice_duration_seconds: int | None
    visual_prompt: str
    start_image_prompt: str
    end_image_prompt: str
    transition_mode: str
    notes: list[str]
    validation_warnings: list[dict[str, object]]
    chained_from_asset_id: UUID | None
    start_image_asset_id: UUID | None
    end_image_asset_id: UUID | None
    created_at: datetime
    updated_at: datetime


class ScenePlanPatchRequest(BaseModel):
    visual_preset_id: str | None = None
    voice_preset_id: str | None = None
    segments: list[SceneSegmentWriteRequest] = Field(default_factory=list)


class ScenePlanResponse(BaseModel):
    id: UUID
    project_id: UUID
    based_on_script_version_id: UUID
    created_by_user_id: UUID | None
    visual_preset_id: UUID | None
    voice_preset_id: UUID | None
    consistency_pack_id: UUID | None
    parent_scene_plan_id: UUID | None
    version_number: int
    source_type: str
    approval_state: str
    approved_at: datetime | None
    approved_by_user_id: UUID | None
    total_estimated_duration_seconds: int
    scene_count: int
    validation_warnings: list[dict[str, object]]
    created_at: datetime
    updated_at: datetime
    segments: list[SceneSegmentResponse]


class ScenePlanJobResponse(JobAcceptedResponse):
    pass
