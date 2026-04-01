"""Add music_presets and subtitle_presets tables (merge heads).

Revision ID: 20260401_0008
Revises: 20260401_0007, 20260330_0010
Create Date: 2026-04-01 12:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.db.types import GUID

revision = "20260401_0008"
down_revision = ("20260401_0007", "20260330_0010")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "music_presets",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False, index=True),
        sa.Column("created_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("track_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("genre", sa.String(128), nullable=False, server_default=""),
        sa.Column("ducking_db", sa.Integer, nullable=False, server_default="-14"),
        sa.Column("fade_in_sec", sa.Float, nullable=False, server_default="0"),
        sa.Column("fade_out_sec", sa.Float, nullable=False, server_default="0"),
        sa.Column("reference_notes", sa.Text, nullable=False, server_default=""),
        sa.Column("is_archived", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "subtitle_presets",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False, index=True),
        sa.Column("created_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("subtitle_style", sa.String(128), nullable=False, server_default="burned_in"),
        sa.Column("font_family", sa.String(128), nullable=False, server_default="Inter"),
        sa.Column("position", sa.String(64), nullable=False, server_default="bottom"),
        sa.Column("color_scheme", sa.String(255), nullable=False, server_default="white_on_black_stroke"),
        sa.Column("highlight_mode", sa.String(64), nullable=False, server_default="word"),
        sa.Column("reference_notes", sa.Text, nullable=False, server_default=""),
        sa.Column("is_archived", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("subtitle_presets")
    op.drop_table("music_presets")
