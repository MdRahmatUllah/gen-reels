from __future__ import annotations

import argparse
import re
from typing import Sequence

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import get_session_factory
from app.models.entities import Project, User, Workspace, WorkspaceMember, WorkspaceRole


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def seed() -> None:
    settings = get_settings()
    session = get_session_factory(settings.database_url)()
    try:
        admin = session.scalar(select(User).where(User.email == "admin@example.com"))
        if not admin:
            admin = User(
                email="admin@example.com",
                full_name="Reels Admin",
                password_hash=hash_password("ChangeMe123!"),
                is_admin=True,
            )
            session.add(admin)
            session.flush()

        workspace = session.scalar(select(Workspace).where(Workspace.slug == "north-star-studio"))
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
            session.add(workspace)
            session.flush()

        membership = session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.user_id == admin.id,
            )
        )
        if not membership:
            session.add(
                WorkspaceMember(
                    workspace_id=workspace.id,
                    user_id=admin.id,
                    role=WorkspaceRole.admin,
                    is_default=True,
                )
            )

        project = session.scalar(
            select(Project).where(Project.workspace_id == workspace.id, Project.title == "Aurora Serum Launch")
        )
        if not project:
            session.add(
                Project(
                    workspace_id=workspace.id,
                    owner_user_id=admin.id,
                    title="Aurora Serum Launch",
                    client="North Star Studio",
                    aspect_ratio="9:16",
                    duration_target_sec=90,
                )
            )
        session.commit()
        print("Seed complete. Admin login: admin@example.com / ChangeMe123!")
    finally:
        session.close()


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Reels backend CLI")
    parser.add_argument("command", choices=["seed"])
    args = parser.parse_args(argv)
    if args.command == "seed":
        seed()
