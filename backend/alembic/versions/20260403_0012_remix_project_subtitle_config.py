"""remix_projects: add subtitle_config JSON column

Revision ID: 20260403_0012
Revises: 20260402_0011
Create Date: 2026-04-03
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260403_0012"
down_revision = "20260402_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("remix_projects") as batch_op:
        batch_op.add_column(
            sa.Column(
                "subtitle_config",
                sa.JSON(),
                nullable=False,
                server_default="{}",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("remix_projects") as batch_op:
        batch_op.drop_column("subtitle_config")
