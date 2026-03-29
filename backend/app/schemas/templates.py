from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.projects import BriefVersionResponse, ProjectResponse


class TemplateCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=4000)


class ProjectFromTemplateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    client: str | None = Field(default=None, max_length=255)


class TemplateVersionResponse(BaseModel):
    id: UUID
    template_id: UUID
    source_project_id: UUID | None
    created_by_user_id: UUID | None
    version_number: int
    snapshot_payload: dict[str, Any]
    created_at: datetime


class TemplateResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    created_by_user_id: UUID | None
    name: str
    description: str
    version: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    latest_version: TemplateVersionResponse | None = None


class TemplateDetailResponse(TemplateResponse):
    versions: list[TemplateVersionResponse]


class TemplateProjectCreateResponse(BaseModel):
    template: TemplateResponse
    project: ProjectResponse
    brief: BriefVersionResponse | None = None
