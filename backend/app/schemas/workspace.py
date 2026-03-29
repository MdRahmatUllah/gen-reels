from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class WorkspaceMemberCreateRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    role: str


class WorkspaceMemberUpdateRequest(BaseModel):
    role: str | None = None
    is_default: bool | None = None


class WorkspaceMemberResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    email: str
    full_name: str
    role: str
    is_default: bool
    created_at: datetime
    updated_at: datetime
