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


# ── Music presets ────────────────────────────────────────────────────────────


class MusicPresetCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str
    track_name: str = ""
    genre: str = ""
    ducking_db: int = Field(default=-14, ge=-30, le=0)
    fade_in_sec: float = Field(default=0.0, ge=0.0, le=10.0)
    fade_out_sec: float = Field(default=0.0, ge=0.0, le=10.0)
    reference_notes: str = ""


class MusicPresetUpdateRequest(BaseModel):
    version: int | None = Field(default=None, ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    track_name: str | None = None
    genre: str | None = None
    ducking_db: int | None = Field(default=None, ge=-30, le=0)
    fade_in_sec: float | None = Field(default=None, ge=0.0, le=10.0)
    fade_out_sec: float | None = Field(default=None, ge=0.0, le=10.0)
    reference_notes: str | None = None
    is_archived: bool | None = None


class MusicPresetResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    created_by_user_id: UUID | None
    version: int
    name: str
    description: str
    track_name: str
    genre: str
    ducking_db: int
    fade_in_sec: float
    fade_out_sec: float
    reference_notes: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime


# ── Subtitle presets ─────────────────────────────────────────────────────────


class SubtitlePresetCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str
    subtitle_style: str = "burned_in"
    font_family: str = "Inter"
    position: str = "bottom"
    color_scheme: str = "white_on_black_stroke"
    highlight_mode: str = "word"
    reference_notes: str = ""


class SubtitlePresetUpdateRequest(BaseModel):
    version: int | None = Field(default=None, ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    subtitle_style: str | None = None
    font_family: str | None = None
    position: str | None = None
    color_scheme: str | None = None
    highlight_mode: str | None = None
    reference_notes: str | None = None
    is_archived: bool | None = None


class SubtitlePresetResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    created_by_user_id: UUID | None
    version: int
    name: str
    description: str
    subtitle_style: str
    font_family: str
    position: str
    color_scheme: str
    highlight_mode: str
    reference_notes: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime
