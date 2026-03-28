from __future__ import annotations

from dataclasses import dataclass
from typing import Generator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.jwt import decode_token
from app.db.session import get_db
from app.models.entities import WorkspaceRole


@dataclass
class AuthContext:
    user_id: str
    email: str
    workspace_id: str
    workspace_role: WorkspaceRole
    session_id: str


def get_settings_dep(request: Request):
    return request.app.state.settings


def get_redis_dep(request: Request):
    return request.app.state.redis


def get_storage_dep(request: Request):
    return request.app.state.storage


def get_db_dep() -> Generator[Session, None, None]:
    yield from get_db()


def require_auth(
    request: Request,
    settings=Depends(get_settings_dep),
) -> AuthContext:
    token = request.cookies.get(settings.access_cookie_name)
    if not token:
        raise ApiError(401, "unauthorized", "Authentication required.")

    payload = decode_token(token, settings.jwt_public_key_resolved, expected_type="access")
    workspace_role = WorkspaceRole(payload["workspace_role"])
    auth_context = AuthContext(
        user_id=payload["sub"],
        email=payload["email"],
        workspace_id=payload["workspace_id"],
        workspace_role=workspace_role,
        session_id=payload["session_id"],
    )
    request.state.auth_context = auth_context
    return auth_context


def require_workspace_role(minimum_role: WorkspaceRole):
    rank = {
        WorkspaceRole.viewer: 0,
        WorkspaceRole.reviewer: 1,
        WorkspaceRole.member: 2,
        WorkspaceRole.admin: 3,
    }

    def dependency(auth: AuthContext = Depends(require_auth)) -> AuthContext:
        if rank[auth.workspace_role] < rank[minimum_role]:
            raise ApiError(403, "forbidden", "You do not have permission for this operation.")
        return auth

    return dependency
