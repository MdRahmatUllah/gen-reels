from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class WorkspaceMemberCreateRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    role: Literal["admin", "member", "reviewer", "viewer"]


class WorkspaceMemberUpdateRequest(BaseModel):
    role: Literal["admin", "member", "reviewer", "viewer"] | None = None
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


class AuditEventResponse(BaseModel):
    id: UUID
    workspace_id: UUID | None
    user_id: UUID | None
    event_type: str
    target_type: str
    target_id: str | None
    payload: dict[str, object]
    created_at: datetime
