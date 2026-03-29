from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class WorkspaceApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    role_scope: Literal["admin", "member", "reviewer", "viewer"]
    expires_at: datetime | None = None


class WorkspaceApiKeyResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    created_by_user_id: UUID | None
    name: str
    role_scope: str
    key_prefix: str
    last_used_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class WorkspaceApiKeyCreateResponse(WorkspaceApiKeyResponse):
    api_key: str


class WebhookEndpointCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    target_url: HttpUrl
    event_types: list[str] = Field(default_factory=list)


class WebhookEndpointUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    target_url: HttpUrl | None = None
    event_types: list[str] | None = None
    is_active: bool | None = None


class WebhookEndpointResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    created_by_user_id: UUID | None
    name: str
    target_url: str
    event_types: list[str]
    is_active: bool
    last_tested_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WebhookEndpointCreateResponse(WebhookEndpointResponse):
    signing_secret: str


class WebhookDeliveryResponse(BaseModel):
    id: UUID
    endpoint_id: UUID
    workspace_id: UUID
    event_type: str
    replay_id: str
    signature: str
    status: str
    payload: dict[str, object]
    response_status_code: int | None
    response_body: str | None
    attempt_count: int
    created_at: datetime
    delivered_at: datetime | None
