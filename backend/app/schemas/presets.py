from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class VisualPresetCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str
    prompt_prefix: str = ""
    style_descriptor: str = ""
    negative_prompt: str = ""
    camera_defaults: str = ""
    color_palette: str = ""
    reference_notes: str = ""


class VisualPresetUpdateRequest(BaseModel):
    version: int | None = Field(default=None, ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    prompt_prefix: str | None = None
    style_descriptor: str | None = None
    negative_prompt: str | None = None
    camera_defaults: str | None = None
    color_palette: str | None = None
    reference_notes: str | None = None
    is_archived: bool | None = None


class VisualPresetResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    created_by_user_id: UUID | None
    version: int
    name: str
    description: str
    prompt_prefix: str
    style_descriptor: str
    negative_prompt: str
    camera_defaults: str
    color_palette: str
    reference_notes: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class VoicePresetCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str
    provider_voice: str = ""
    tone_descriptor: str = ""
    language_code: str = "en-US"
    pace_multiplier: float = Field(default=1.0, ge=0.5, le=2.0)


class VoicePresetUpdateRequest(BaseModel):
    version: int | None = Field(default=None, ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    provider_voice: str | None = None
    tone_descriptor: str | None = None
    language_code: str | None = None
    pace_multiplier: float | None = Field(default=None, ge=0.5, le=2.0)
    is_archived: bool | None = None


class VoicePresetResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    created_by_user_id: UUID | None
    version: int
    name: str
    description: str
    provider_voice: str
    tone_descriptor: str
    language_code: str
    pace_multiplier: float
    is_archived: bool
    created_at: datetime
    updated_at: datetime
