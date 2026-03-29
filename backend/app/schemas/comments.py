from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CommentCreateRequest(BaseModel):
    project_id: str | None = None
    target_type: str = Field(min_length=1, max_length=64)
    target_id: str = Field(min_length=1, max_length=64)
    body: str = Field(min_length=1)
    metadata_payload: dict[str, object] = Field(default_factory=dict)


class CommentResolveRequest(BaseModel):
    note: str | None = None


class CommentResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    project_id: UUID | None
    target_type: str
    target_id: str
    author_user_id: UUID
    body: str
    metadata_payload: dict[str, object]
    resolved_at: datetime | None
    resolved_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
