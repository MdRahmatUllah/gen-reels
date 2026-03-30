"""Add project_stage.frames enum value.

Revision ID: 20260330_0010
Revises: 20260330_0009
Create Date: 2026-03-30 12:00:00
"""

from __future__ import annotations

from alembic import op


revision = "20260330_0010"
down_revision = "20260330_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE project_stage ADD VALUE IF NOT EXISTS 'frames'")


def downgrade() -> None:
    pass
