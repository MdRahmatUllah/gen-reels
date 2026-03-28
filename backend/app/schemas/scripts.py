from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ScriptLineWriteRequest(BaseModel):
    id: str
    scene_id: str
    beat: str
    narration: str
    caption: str
    duration_sec: int = Field(ge=1, le=120)
    status: str = "draft"
    visual_direction: str
    voice_pacing: str


class ScriptPatchRequest(BaseModel):
    approval_state: str = "draft"
    lines: list[ScriptLineWriteRequest]
    metadata: dict[str, Any] = Field(default_factory=dict)
