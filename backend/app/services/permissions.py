from __future__ import annotations

from app.api.deps import AuthContext
from app.core.errors import ApiError
from app.models.entities import WorkspaceRole


EDIT_ROLES = {WorkspaceRole.admin, WorkspaceRole.member}
REVIEW_ROLES = {WorkspaceRole.admin, WorkspaceRole.member, WorkspaceRole.reviewer}


def can_edit_workspace_content(auth: AuthContext) -> bool:
    return auth.workspace_role in EDIT_ROLES


def require_workspace_edit(
    auth: AuthContext,
    *,
    code: str = "forbidden",
    message: str = "You do not have permission to edit workspace content.",
) -> None:
    if not can_edit_workspace_content(auth):
        raise ApiError(403, code, message)


def require_workspace_review(
    auth: AuthContext,
    *,
    code: str = "forbidden",
    message: str = "You do not have permission to review workspace content.",
) -> None:
    if auth.workspace_role not in REVIEW_ROLES:
        raise ApiError(403, code, message)


def require_workspace_admin(
    auth: AuthContext,
    *,
    code: str = "forbidden",
    message: str = "Workspace admin permission is required.",
) -> None:
    if auth.workspace_role != WorkspaceRole.admin:
        raise ApiError(403, code, message)
