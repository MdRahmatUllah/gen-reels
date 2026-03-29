from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class BrandKitCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    status: Literal["draft", "active", "archived"] = "active"
    enforcement_mode: Literal["advisory", "enforced"] = "advisory"
    is_default: bool = False
    default_visual_preset_id: str | None = None
    default_voice_preset_id: str | None = None
    required_terms: list[str] = Field(default_factory=list)
    banned_terms: list[str] = Field(default_factory=list)
    subtitle_style_override: dict[str, object] = Field(default_factory=dict)
    export_profile_override: dict[str, object] = Field(default_factory=dict)
    audio_mix_profile_override: dict[str, object] = Field(default_factory=dict)
    brand_rules: dict[str, object] = Field(default_factory=dict)


class BrandKitUpdateRequest(BaseModel):
    version: int | None = Field(default=None, ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: Literal["draft", "active", "archived"] | None = None
    enforcement_mode: Literal["advisory", "enforced"] | None = None
    is_default: bool | None = None
    default_visual_preset_id: str | None = None
    default_voice_preset_id: str | None = None
    required_terms: list[str] | None = None
    banned_terms: list[str] | None = None
    subtitle_style_override: dict[str, object] | None = None
    export_profile_override: dict[str, object] | None = None
    audio_mix_profile_override: dict[str, object] | None = None
    brand_rules: dict[str, object] | None = None


class BrandKitResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    created_by_user_id: UUID | None
    default_visual_preset_id: UUID | None
    default_voice_preset_id: UUID | None
    name: str
    description: str
    version: int
    status: str
    enforcement_mode: str
    is_default: bool
    required_terms: list[str]
    banned_terms: list[str]
    subtitle_style_override: dict[str, object]
    export_profile_override: dict[str, object]
    audio_mix_profile_override: dict[str, object]
    brand_rules: dict[str, object]
    created_at: datetime
    updated_at: datetime
