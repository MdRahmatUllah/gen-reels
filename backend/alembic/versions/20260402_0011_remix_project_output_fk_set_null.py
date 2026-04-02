"""remix_projects.output_project_id FK: add ON DELETE SET NULL

Revision ID: 20260402_0011
Revises: 20260402_0010
Create Date: 2026-04-02
"""
from __future__ import annotations

from alembic import op

revision = "20260402_0011"
down_revision = "20260402_0010"
branch_labels = None
depends_on = None


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == "sqlite"


def upgrade() -> None:
    if _is_sqlite():
        return
    with op.batch_alter_table("remix_projects") as batch_op:
        batch_op.drop_constraint(
            "remix_projects_output_project_id_fkey",
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            "remix_projects_output_project_id_fkey",
            "video_library_projects",
            ["output_project_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    if _is_sqlite():
        return
    with op.batch_alter_table("remix_projects") as batch_op:
        batch_op.drop_constraint(
            "remix_projects_output_project_id_fkey",
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            "remix_projects_output_project_id_fkey",
            "video_library_projects",
            ["output_project_id"],
            ["id"],
        )
