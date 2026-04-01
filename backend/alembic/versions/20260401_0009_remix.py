"""remix projects, jobs and videos

Revision ID: 20260401_0009
Revises: 20260401_0008
Create Date: 2026-04-01
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from app.db.types import GUID, json_type

revision = "20260401_0009"
down_revision = "20260401_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "remix_projects",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_project_id", GUID(), sa.ForeignKey("video_library_projects.id"), nullable=True),
        sa.Column("visual_effects", json_type(), nullable=False, server_default="{}"),
        sa.Column("target_duration_ms", sa.Integer, nullable=False),
        sa.Column("clip_mode", sa.String(32), nullable=False, server_default="random"),
        sa.Column("output_project_id", GUID(), sa.ForeignKey("video_library_projects.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "remix_jobs",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("remix_project_id", GUID(), sa.ForeignKey("remix_projects.id"), nullable=False, index=True),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False, index=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("total_videos", sa.Integer, nullable=False, server_default="0"),
        sa.Column("completed_videos", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failed_videos", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "remix_videos",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("job_id", GUID(), sa.ForeignKey("remix_jobs.id"), nullable=False, index=True),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False, index=True),
        sa.Column("output_item_id", GUID(), sa.ForeignKey("video_library_items.id"), nullable=True),
        sa.Column("clip_ids", json_type(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("remix_videos")
    op.drop_table("remix_jobs")
    op.drop_table("remix_projects")
