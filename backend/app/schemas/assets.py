from __future__ import annotations

from pydantic import BaseModel, Field


class AssetReuseRequest(BaseModel):
    project_id: str
    library_label: str | None = Field(default=None, max_length=255)
    target_scene_plan_id: str | None = None
    target_scene_index: int | None = Field(default=None, ge=1)
    attach_as: str = Field(default="library_copy", pattern="^(library_copy|continuity_anchor|start_frame|end_frame)$")
