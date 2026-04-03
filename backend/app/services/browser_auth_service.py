from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import ApiError
from app.core.security import hash_password
from app.models.entities import Project, User, Workspace, WorkspaceMember, WorkspaceRole


@dataclass
class BrowserAuthState:
    user: User
    active_membership: WorkspaceMember
    active_workspace: Workspace
    memberships: list[tuple[WorkspaceMember, Workspace]]


class BrowserAuthService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def ensure_development_identity(self) -> None:
        if self.settings.environment != "development":
            return

        changed = False
        admin = self.db.scalar(select(User).where(User.email == self.settings.dev_browser_auth_email.lower()))
        if not admin:
            admin = User(
                email=self.settings.dev_browser_auth_email.lower(),
                full_name="Reels Admin",
                password_hash=hash_password("ChangeMe123!"),
                is_admin=True,
                is_active=True,
            )
            self.db.add(admin)
            self.db.flush()
            changed = True
        else:
            if not admin.is_active:
                admin.is_active = True
                changed = True
            if not admin.is_admin:
                admin.is_admin = True
                changed = True

        workspace = self.db.scalar(select(Workspace).where(Workspace.slug == "north-star-studio"))
        if not workspace:
            workspace = Workspace(
                name="North Star Studio",
                slug="north-star-studio",
                plan_name="Pro Studio",
                seats=5,
                credits_remaining=1000,
                credits_total=1000,
                monthly_budget_cents=500000,
            )
            self.db.add(workspace)
            self.db.flush()
            changed = True

        membership = self.db.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.user_id == admin.id,
            )
        )
        if not membership:
            membership = WorkspaceMember(
                workspace_id=workspace.id,
                user_id=admin.id,
                role=WorkspaceRole.admin,
                is_default=True,
            )
            self.db.add(membership)
            changed = True
        else:
            if membership.role != WorkspaceRole.admin:
                membership.role = WorkspaceRole.admin
                changed = True
            if not membership.is_default:
                membership.is_default = True
                changed = True

        project = self.db.scalar(
            select(Project).where(Project.workspace_id == workspace.id, Project.title == "Aurora Serum Launch")
        )
        if not project:
            self.db.add(
                Project(
                    workspace_id=workspace.id,
                    owner_user_id=admin.id,
                    title="Aurora Serum Launch",
                    client="North Star Studio",
                    aspect_ratio="9:16",
                    duration_target_sec=90,
                )
            )
            changed = True

        if changed:
            self.db.commit()

    def _memberships(self, user_id) -> list[tuple[WorkspaceMember, Workspace]]:
        result = self.db.execute(
            select(WorkspaceMember, Workspace)
            .join(Workspace, Workspace.id == WorkspaceMember.workspace_id)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(WorkspaceMember.is_default.desc(), Workspace.name.asc())
        )
        return list(result.all())

    def resolve_state(
        self,
        requested_workspace_id: str | None = None,
        *,
        strict_workspace: bool = False,
    ) -> BrowserAuthState:
        if self.settings.environment == "development":
            self.ensure_development_identity()

        user = self.db.scalar(
            select(User).where(
                User.email == self.settings.dev_browser_auth_email.lower(),
                User.is_active.is_(True),
            )
        )
        if not user:
            raise ApiError(
                503,
                "browser_auth_identity_not_configured",
                "Development browser auth is enabled, but the dev admin account is missing.",
            )

        memberships = self._memberships(user.id)
        if not memberships:
            raise ApiError(
                503,
                "browser_auth_workspace_not_configured",
                "Development browser auth is enabled, but the dev admin has no workspace membership.",
            )

        active_membership: WorkspaceMember | None = None
        active_workspace: Workspace | None = None
        if requested_workspace_id:
            for membership, workspace in memberships:
                if str(workspace.id) == requested_workspace_id:
                    active_membership = membership
                    active_workspace = workspace
                    break
            if strict_workspace and active_workspace is None:
                raise ApiError(403, "workspace_not_available", "You do not belong to that workspace.")

        if active_membership is None or active_workspace is None:
            active_membership, active_workspace = memberships[0]

        return BrowserAuthState(
            user=user,
            active_membership=active_membership,
            active_workspace=active_workspace,
            memberships=memberships,
        )

    def session_payload(self, state: BrowserAuthState) -> dict[str, Any]:
        return {
            "user": {
                "id": state.user.id,
                "email": state.user.email,
                "full_name": state.user.full_name,
                "is_admin": state.user.is_admin,
            },
            "workspaces": [
                {
                    "member_id": membership.id,
                    "workspace_id": workspace.id,
                    "workspace_name": workspace.name,
                    "role": membership.role.value,
                    "is_default": membership.is_default,
                    "plan_name": workspace.plan_name,
                }
                for membership, workspace in state.memberships
            ],
            "active_workspace_id": str(state.active_workspace.id),
            "active_role": state.active_membership.role.value,
        }

    def set_workspace_cookie(self, response: Response, workspace_id: str) -> None:
        response.set_cookie(
            key=self.settings.dev_workspace_cookie_name,
            value=workspace_id,
            httponly=True,
            secure=self.settings.cookie_secure,
            samesite=self.settings.cookie_samesite,
            max_age=self.settings.jwt_refresh_token_ttl_days * 86400,
            path="/",
        )

    def clear_workspace_cookie(self, response: Response) -> None:
        response.delete_cookie(self.settings.dev_workspace_cookie_name, path="/")
