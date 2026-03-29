from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class NotificationEventResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    project_id: UUID | None
    render_job_id: UUID | None
    review_request_id: UUID | None
    event_type: str
    title: str
    body: str
    payload: dict[str, object]
    email_delivery_status: str | None
    email_error_message: str | None
    read_at: datetime | None
    created_at: datetime


class NotificationPreferenceResponse(BaseModel):
    workspace_id: UUID
    user_id: UUID
    render_email_enabled: bool
    review_email_enabled: bool
    membership_email_enabled: bool
    moderation_email_enabled: bool
    planning_email_enabled: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class NotificationPreferenceUpdateRequest(BaseModel):
    render_email_enabled: bool | None = None
    review_email_enabled: bool | None = None
    membership_email_enabled: bool | None = None
    moderation_email_enabled: bool | None = None
    planning_email_enabled: bool | None = None

