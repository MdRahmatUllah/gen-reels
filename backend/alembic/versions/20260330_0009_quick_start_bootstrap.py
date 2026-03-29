"""Add quick-start bootstrap job and brief generation step enums.

Revision ID: 20260330_0009
Revises: 20260329_0008
Create Date: 2026-03-30 10:10:00
"""

from __future__ import annotations

from alembic import op


revision = "20260330_0009"
down_revision = "20260329_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE job_kind ADD VALUE IF NOT EXISTS 'project_bootstrap'")
        op.execute("ALTER TYPE step_kind ADD VALUE IF NOT EXISTS 'brief_generation'")


def downgrade() -> None:
    # Postgres enum value removal is intentionally omitted. Existing tables remain compatible.
    pass
