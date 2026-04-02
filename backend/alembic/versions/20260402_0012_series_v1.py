"""Add Series V1 tables for configurable series and script runs.

Revision ID: 20260402_0012
Revises: 20260402_0011
Create Date: 2026-04-02 11:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.db.types import GUID, json_type


revision = "20260402_0012"
down_revision = "20260402_0011"
branch_labels = None
depends_on = None


job_status = sa.Enum(
    "draft",
    "queued",
    "running",
    "review",
    "approved",
    "completed",
    "blocked",
    "failed",
    "cancelled",
    name="job_status",
    create_type=False,
)


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(index["name"] == index_name for index in sa.inspect(op.get_bind()).get_indexes(table_name))


def upgrade() -> None:
    if not _has_table("series"):
        op.create_table(
            "series",
            sa.Column("id", GUID(), primary_key=True, nullable=False),
            sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
            sa.Column("owner_user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.String(length=500), nullable=False, server_default=""),
            sa.Column("content_mode", sa.String(length=32), nullable=False),
            sa.Column("preset_key", sa.String(length=64), nullable=True),
            sa.Column("custom_topic", sa.Text(), nullable=False, server_default=""),
            sa.Column("custom_example_script", sa.Text(), nullable=False, server_default=""),
            sa.Column("language_key", sa.String(length=32), nullable=False, server_default="en"),
            sa.Column("voice_key", sa.String(length=64), nullable=False),
            sa.Column("music_mode", sa.String(length=32), nullable=False, server_default="none"),
            sa.Column("music_keys", json_type(), nullable=False, server_default="[]"),
            sa.Column("art_style_key", sa.String(length=64), nullable=False),
            sa.Column("caption_style_key", sa.String(length=64), nullable=False),
            sa.Column("effect_keys", json_type(), nullable=False, server_default="[]"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not _has_index("series", "ix_series_workspace_id"):
        op.create_index("ix_series_workspace_id", "series", ["workspace_id"], unique=False)

    if not _has_table("series_runs"):
        op.create_table(
            "series_runs",
            sa.Column("id", GUID(), primary_key=True, nullable=False),
            sa.Column("series_id", GUID(), sa.ForeignKey("series.id"), nullable=False),
            sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
            sa.Column("created_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("status", job_status, nullable=False, server_default="queued"),
            sa.Column("requested_script_count", sa.Integer(), nullable=False),
            sa.Column("completed_script_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("failed_script_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("idempotency_key", sa.String(length=255), nullable=False),
            sa.Column("request_hash", sa.String(length=64), nullable=False),
            sa.Column("payload", json_type(), nullable=False, server_default="{}"),
            sa.Column("error_code", sa.String(length=64), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "created_by_user_id",
                "series_id",
                "idempotency_key",
                name="uq_series_run_idempotency",
            ),
        )
    if not _has_index("series_runs", "ix_series_runs_series_id"):
        op.create_index("ix_series_runs_series_id", "series_runs", ["series_id"], unique=False)
    if not _has_index("series_runs", "ix_series_runs_workspace_id"):
        op.create_index("ix_series_runs_workspace_id", "series_runs", ["workspace_id"], unique=False)

    if not _has_table("series_scripts"):
        op.create_table(
            "series_scripts",
            sa.Column("id", GUID(), primary_key=True, nullable=False),
            sa.Column("series_id", GUID(), sa.ForeignKey("series.id"), nullable=False),
            sa.Column("series_run_id", GUID(), sa.ForeignKey("series_runs.id"), nullable=False),
            sa.Column("created_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("sequence_number", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False, server_default=""),
            sa.Column("estimated_duration_seconds", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "reading_time_label",
                sa.String(length=64),
                nullable=False,
                server_default="0s draft narration",
            ),
            sa.Column("total_words", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("lines", json_type(), nullable=False, server_default="[]"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("series_id", "sequence_number", name="uq_series_script_sequence"),
        )
    if not _has_index("series_scripts", "ix_series_scripts_series_id"):
        op.create_index("ix_series_scripts_series_id", "series_scripts", ["series_id"], unique=False)
    if not _has_index("series_scripts", "ix_series_scripts_series_run_id"):
        op.create_index("ix_series_scripts_series_run_id", "series_scripts", ["series_run_id"], unique=False)

    if not _has_table("series_run_steps"):
        op.create_table(
            "series_run_steps",
            sa.Column("id", GUID(), primary_key=True, nullable=False),
            sa.Column("series_run_id", GUID(), sa.ForeignKey("series_runs.id"), nullable=False),
            sa.Column("series_id", GUID(), sa.ForeignKey("series.id"), nullable=False),
            sa.Column("series_script_id", GUID(), sa.ForeignKey("series_scripts.id"), nullable=True),
            sa.Column("step_index", sa.Integer(), nullable=False),
            sa.Column("sequence_number", sa.Integer(), nullable=False),
            sa.Column("status", job_status, nullable=False, server_default="queued"),
            sa.Column("input_payload", json_type(), nullable=False, server_default="{}"),
            sa.Column("output_payload", json_type(), nullable=True),
            sa.Column("error_code", sa.String(length=64), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("series_run_id", "step_index", name="uq_series_run_step_index"),
        )
    if not _has_index("series_run_steps", "ix_series_run_steps_series_run_id"):
        op.create_index("ix_series_run_steps_series_run_id", "series_run_steps", ["series_run_id"], unique=False)
    if not _has_index("series_run_steps", "ix_series_run_steps_series_id"):
        op.create_index("ix_series_run_steps_series_id", "series_run_steps", ["series_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_series_run_steps_series_id", table_name="series_run_steps")
    op.drop_index("ix_series_run_steps_series_run_id", table_name="series_run_steps")
    op.drop_table("series_run_steps")

    op.drop_index("ix_series_scripts_series_run_id", table_name="series_scripts")
    op.drop_index("ix_series_scripts_series_id", table_name="series_scripts")
    op.drop_table("series_scripts")

    op.drop_index("ix_series_runs_workspace_id", table_name="series_runs")
    op.drop_index("ix_series_runs_series_id", table_name="series_runs")
    op.drop_table("series_runs")

    op.drop_index("ix_series_workspace_id", table_name="series")
    op.drop_table("series")
