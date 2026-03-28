from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import UserSummary, WorkspaceMembershipSummary


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12)
    workspace_id: str | None = None


class SessionResponse(BaseModel):
    user: UserSummary
    workspaces: list[WorkspaceMembershipSummary]
    active_workspace_id: str
    active_role: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=12)


class WorkspaceSelectRequest(BaseModel):
    workspace_id: str
