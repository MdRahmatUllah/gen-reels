"""remix_videos.output_item_id FK: add ON DELETE SET NULL

Revision ID: 20260402_0010
Revises: 20260401_0009
Create Date: 2026-04-02
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260402_0010"
down_revision = "20260401_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old constraint (no ON DELETE action) and recreate with SET NULL
    op.drop_constraint(
        "remix_videos_output_item_id_fkey",
        "remix_videos",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "remix_videos_output_item_id_fkey",
        "remix_videos",
        "video_library_items",
        ["output_item_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "remix_videos_output_item_id_fkey",
        "remix_videos",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "remix_videos_output_item_id_fkey",
        "remix_videos",
        "video_library_items",
        ["output_item_id"],
        ["id"],
    )
