from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Generator

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.jwt import decode_token
from app.core.security import hash_token
from app.db.session import get_db
from app.models.entities import LocalWorker, LocalWorkerStatus, WorkspaceApiKey, WorkspaceRole
from app.services.browser_auth_service import BrowserAuthService


@dataclass
class AuthContext:
    user_id: str
    email: str
    workspace_id: str
    workspace_role: WorkspaceRole
    session_id: str


@dataclass
class ApiKeyAuthContext:
    workspace_id: str
    api_key_id: str
    role_scope: WorkspaceRole


@dataclass
class LocalWorkerAuthContext:
    workspace_id: str
    worker_id: str


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
    db: Session = Depends(get_db_dep),
) -> AuthContext:
    if settings.disable_browser_auth_resolved:
        browser_auth = BrowserAuthService(db, settings)
        state = browser_auth.resolve_state(request.cookies.get(settings.dev_workspace_cookie_name))
        auth_context = AuthContext(
            user_id=str(state.user.id),
            email=state.user.email,
            workspace_id=str(state.active_workspace.id),
            workspace_role=state.active_membership.role,
            session_id="browser-auth-disabled",
        )
        request.state.auth_context = auth_context
        return auth_context

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


def _authorization_bearer_token(request: Request) -> str:
    header = request.headers.get("Authorization", "").strip()
    if not header.lower().startswith("bearer "):
        raise ApiError(401, "unauthorized", "Bearer authentication is required.")
    token = header[7:].strip()
    if not token:
        raise ApiError(401, "unauthorized", "Bearer authentication is required.")
    return token


def require_workspace_api_key(
    request: Request,
    db: Session = Depends(get_db_dep),
) -> ApiKeyAuthContext:
    token = _authorization_bearer_token(request)
    api_key = db.scalar(select(WorkspaceApiKey).where(WorkspaceApiKey.key_hash == hash_token(token)))
    now = datetime.now(timezone.utc)
    if not api_key or api_key.revoked_at is not None or (
        api_key.expires_at is not None and api_key.expires_at <= now
    ):
        raise ApiError(401, "unauthorized", "API key authentication failed.")
    api_key.last_used_at = now
    db.commit()
    return ApiKeyAuthContext(
        workspace_id=str(api_key.workspace_id),
        api_key_id=str(api_key.id),
        role_scope=api_key.role_scope,
    )


def require_local_worker_token(
    request: Request,
    db: Session = Depends(get_db_dep),
) -> LocalWorkerAuthContext:
    token = _authorization_bearer_token(request)
    worker = db.scalar(select(LocalWorker).where(LocalWorker.worker_token_hash == hash_token(token)))
    if not worker or worker.revoked_at is not None or worker.status == LocalWorkerStatus.revoked:
        raise ApiError(401, "unauthorized", "Worker authentication failed.")
    return LocalWorkerAuthContext(workspace_id=str(worker.workspace_id), worker_id=str(worker.id))
