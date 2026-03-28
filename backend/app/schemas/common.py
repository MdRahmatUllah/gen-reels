from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserSummary(OrmModel):
    id: UUID
    email: str
    full_name: str
    is_admin: bool


class WorkspaceMembershipSummary(BaseModel):
    workspace_id: UUID
    workspace_name: str
    role: str
    is_default: bool
    plan_name: str


class JobAcceptedResponse(BaseModel):
    job_id: UUID
    job_status: str
    project_id: UUID


class JobSummary(BaseModel):
    id: UUID
    job_kind: str
    status: str
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class MessageResponse(BaseModel):
    message: str


class StatusResponse(BaseModel):
    status: Literal["ok"]
