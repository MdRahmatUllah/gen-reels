from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OAuthConnectResponse(BaseModel):
    authorization_url: str


class YouTubeAccountResponse(BaseModel):
    id: UUID
    google_account_email: str | None
    channel_id: str
    channel_title: str
    channel_handle: str | None
    is_default: bool
    token_expiry_at: datetime | None
    connected_at: datetime
    created_at: datetime
    updated_at: datetime


class PublishScheduleUpsertRequest(BaseModel):
    youtube_account_id: UUID
    timezone_name: str
    slots_local: list[str] = Field(default_factory=list)
    is_active: bool = True


class PublishScheduleResponse(BaseModel):
    id: UUID
    youtube_account_id: UUID
    timezone_name: str
    slots_local: list[str]
    is_active: bool
    next_available_slots_utc: list[datetime] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
