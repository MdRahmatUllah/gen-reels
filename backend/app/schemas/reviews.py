from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReviewCreateRequest(BaseModel):
    project_id: str | None = None
    target_type: str = Field(min_length=1, max_length=64)
    target_id: str = Field(min_length=1, max_length=64)
    requested_version: int | None = Field(default=None, ge=1)
    assigned_to_user_id: str | None = None
    request_notes: str = ""


class ReviewDecisionRequest(BaseModel):
    decision_notes: str = ""


class ReviewResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    project_id: UUID | None
    target_type: str
    target_id: str
    requested_by_user_id: UUID
    assigned_to_user_id: UUID | None
    requested_version: int | None
    status: str
    request_notes: str
    decision_notes: str | None
    decided_by_user_id: UUID | None
    decided_at: datetime | None
    created_at: datetime
    updated_at: datetime
