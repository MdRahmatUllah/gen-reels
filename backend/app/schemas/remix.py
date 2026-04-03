from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class RemixProjectCreate(BaseModel):
    name: str
    source_project_id: str | None = None  # video_library_projects.id; None = "No Project"
    visual_effects: dict[str, object] = {}
    subtitle_config: dict[str, object] = {}
    target_duration_ms: int
    clip_mode: str = "random"  # "random" | "unique"


class RemixProjectResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    source_project_id: str | None
    visual_effects: dict[str, object]
    subtitle_config: dict[str, object]
    target_duration_ms: int
    clip_mode: str
    output_project_id: str | None
    created_at: datetime
    updated_at: datetime


class RemixAnalyzeResponse(BaseModel):
    possible_videos: int
    total_clips: int
    total_duration_ms: int
    clips_with_duration: int


class RemixJobCreate(BaseModel):
    pass  # no extra payload — runs all possible videos


class RemixVideoResponse(BaseModel):
    id: str
    job_id: str
    status: str
    clip_ids: list[str]
    output_item_id: str | None
    error_message: str | None
    created_at: datetime


class RemixJobResponse(BaseModel):
    id: str
    remix_project_id: str
    workspace_id: str
    status: str
    total_videos: int
    completed_videos: int
    failed_videos: int
    videos: list[RemixVideoResponse]
    created_at: datetime
    updated_at: datetime
