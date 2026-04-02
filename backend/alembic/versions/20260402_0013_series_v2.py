"""Extend Series with revisions, hidden projects, and video runs.

Revision ID: 20260402_0013
Revises: 20260402_0012
Create Date: 2026-04-02 15:45:00
"""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa

from app.db.types import GUID, json_type


revision = "20260402_0013"
down_revision = "20260402_0012"
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


def _column_names(table_name: str) -> set[str]:
    if not _has_table(table_name):
        return set()
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(index["name"] == index_name for index in sa.inspect(op.get_bind()).get_indexes(table_name))


def _has_foreign_key(table_name: str, constraint_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(
        foreign_key.get("name") == constraint_name
        for foreign_key in sa.inspect(op.get_bind()).get_foreign_keys(table_name)
    )


def _has_unique_constraint(table_name: str, constraint_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(
        constraint.get("name") == constraint_name
        for constraint in sa.inspect(op.get_bind()).get_unique_constraints(table_name)
    )


def upgrade() -> None:
    if not _has_table("series_script_revisions"):
        op.create_table(
            "series_script_revisions",
            sa.Column("id", GUID(), primary_key=True, nullable=False),
            sa.Column("series_script_id", GUID(), sa.ForeignKey("series_scripts.id"), nullable=False),
            sa.Column("series_id", GUID(), sa.ForeignKey("series.id"), nullable=False),
            sa.Column("created_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("source_series_run_id", GUID(), sa.ForeignKey("series_runs.id"), nullable=True),
            sa.Column("revision_number", sa.Integer(), nullable=False),
            sa.Column("approval_state", sa.String(length=32), nullable=False, server_default="needs_review"),
            sa.Column("moderation_summary", json_type(), nullable=False, server_default="{}"),
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
            sa.Column("video_title", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("video_description", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("series_script_id", "revision_number", name="uq_series_script_revision_number"),
        )
    if not _has_index("series_script_revisions", "ix_series_script_revisions_series_script_id"):
        op.create_index(
            "ix_series_script_revisions_series_script_id",
            "series_script_revisions",
            ["series_script_id"],
            unique=False,
        )
    if not _has_index("series_script_revisions", "ix_series_script_revisions_series_id"):
        op.create_index(
            "ix_series_script_revisions_series_id",
            "series_script_revisions",
            ["series_id"],
            unique=False,
        )
    if not _has_index("series_script_revisions", "ix_series_script_revisions_source_series_run_id"):
        op.create_index(
            "ix_series_script_revisions_source_series_run_id",
            "series_script_revisions",
            ["source_series_run_id"],
            unique=False,
        )

    if not _has_table("series_video_runs"):
        op.create_table(
            "series_video_runs",
            sa.Column("id", GUID(), primary_key=True, nullable=False),
            sa.Column("series_id", GUID(), sa.ForeignKey("series.id"), nullable=False),
            sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
            sa.Column("created_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("status", job_status, nullable=False, server_default="queued"),
            sa.Column("requested_video_count", sa.Integer(), nullable=False),
            sa.Column("completed_video_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("failed_video_count", sa.Integer(), nullable=False, server_default="0"),
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
                name="uq_series_video_run_idempotency",
            ),
        )
    if not _has_index("series_video_runs", "ix_series_video_runs_series_id"):
        op.create_index("ix_series_video_runs_series_id", "series_video_runs", ["series_id"], unique=False)
    if not _has_index("series_video_runs", "ix_series_video_runs_workspace_id"):
        op.create_index("ix_series_video_runs_workspace_id", "series_video_runs", ["workspace_id"], unique=False)

    if not _has_table("series_video_run_steps"):
        op.create_table(
            "series_video_run_steps",
            sa.Column("id", GUID(), primary_key=True, nullable=False),
            sa.Column("series_video_run_id", GUID(), sa.ForeignKey("series_video_runs.id"), nullable=False),
            sa.Column("series_id", GUID(), sa.ForeignKey("series.id"), nullable=False),
            sa.Column("series_script_id", GUID(), sa.ForeignKey("series_scripts.id"), nullable=False),
            sa.Column("series_script_revision_id", GUID(), sa.ForeignKey("series_script_revisions.id"), nullable=False),
            sa.Column("step_index", sa.Integer(), nullable=False),
            sa.Column("sequence_number", sa.Integer(), nullable=False),
            sa.Column("status", job_status, nullable=False, server_default="queued"),
            sa.Column("phase", sa.String(length=64), nullable=False, server_default="queued"),
            sa.Column("hidden_project_id", GUID(), sa.ForeignKey("projects.id"), nullable=True),
            sa.Column("render_job_id", GUID(), sa.ForeignKey("render_jobs.id"), nullable=True),
            sa.Column("last_render_event_sequence", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("current_scene_index", sa.Integer(), nullable=True),
            sa.Column("current_scene_count", sa.Integer(), nullable=True),
            sa.Column("input_payload", json_type(), nullable=False, server_default="{}"),
            sa.Column("output_payload", json_type(), nullable=True),
            sa.Column("error_code", sa.String(length=64), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("series_video_run_id", "step_index", name="uq_series_video_run_step_index"),
        )
    if not _has_index("series_video_run_steps", "ix_series_video_run_steps_series_video_run_id"):
        op.create_index(
            "ix_series_video_run_steps_series_video_run_id",
            "series_video_run_steps",
            ["series_video_run_id"],
            unique=False,
        )
    if not _has_index("series_video_run_steps", "ix_series_video_run_steps_series_id"):
        op.create_index("ix_series_video_run_steps_series_id", "series_video_run_steps", ["series_id"], unique=False)
    if not _has_index("series_video_run_steps", "ix_series_video_run_steps_series_script_id"):
        op.create_index(
            "ix_series_video_run_steps_series_script_id",
            "series_video_run_steps",
            ["series_script_id"],
            unique=False,
        )
    if not _has_index("series_video_run_steps", "ix_series_video_run_steps_series_script_revision_id"):
        op.create_index(
            "ix_series_video_run_steps_series_script_revision_id",
            "series_video_run_steps",
            ["series_script_revision_id"],
            unique=False,
        )

    project_columns = _column_names("projects")
    needs_project_series_script_id = "series_script_id" not in project_columns
    needs_project_is_internal = "is_internal" not in project_columns
    needs_project_fk = not _has_foreign_key("projects", "fk_projects_series_script_id")
    needs_project_unique = not _has_unique_constraint("projects", "uq_projects_series_script_id")
    if (
        needs_project_series_script_id
        or needs_project_is_internal
        or needs_project_fk
        or needs_project_unique
    ):
        with op.batch_alter_table("projects") as batch_op:
            if needs_project_series_script_id:
                batch_op.add_column(sa.Column("series_script_id", GUID(), nullable=True))
            if needs_project_is_internal:
                batch_op.add_column(sa.Column("is_internal", sa.Boolean(), nullable=False, server_default=sa.false()))
            if needs_project_fk:
                batch_op.create_foreign_key(
                    "fk_projects_series_script_id",
                    "series_scripts",
                    ["series_script_id"],
                    ["id"],
                )
            if needs_project_unique:
                batch_op.create_unique_constraint("uq_projects_series_script_id", ["series_script_id"])

    series_script_columns = _column_names("series_scripts")
    needs_current_revision_id = "current_revision_id" not in series_script_columns
    needs_approved_revision_id = "approved_revision_id" not in series_script_columns
    needs_published_revision_id = "published_revision_id" not in series_script_columns
    needs_published_project_id = "published_project_id" not in series_script_columns
    needs_published_render_job_id = "published_render_job_id" not in series_script_columns
    needs_published_export_id = "published_export_id" not in series_script_columns
    needs_current_fk = not _has_foreign_key("series_scripts", "fk_series_scripts_current_revision_id")
    needs_approved_fk = not _has_foreign_key("series_scripts", "fk_series_scripts_approved_revision_id")
    needs_published_revision_fk = not _has_foreign_key("series_scripts", "fk_series_scripts_published_revision_id")
    needs_published_project_fk = not _has_foreign_key("series_scripts", "fk_series_scripts_published_project_id")
    needs_published_render_job_fk = not _has_foreign_key("series_scripts", "fk_series_scripts_published_render_job_id")
    needs_published_export_fk = not _has_foreign_key("series_scripts", "fk_series_scripts_published_export_id")
    if (
        needs_current_revision_id
        or needs_approved_revision_id
        or needs_published_revision_id
        or needs_published_project_id
        or needs_published_render_job_id
        or needs_published_export_id
        or needs_current_fk
        or needs_approved_fk
        or needs_published_revision_fk
        or needs_published_project_fk
        or needs_published_render_job_fk
        or needs_published_export_fk
    ):
        with op.batch_alter_table("series_scripts") as batch_op:
            if needs_current_revision_id:
                batch_op.add_column(sa.Column("current_revision_id", GUID(), nullable=True))
            if needs_approved_revision_id:
                batch_op.add_column(sa.Column("approved_revision_id", GUID(), nullable=True))
            if needs_published_revision_id:
                batch_op.add_column(sa.Column("published_revision_id", GUID(), nullable=True))
            if needs_published_project_id:
                batch_op.add_column(sa.Column("published_project_id", GUID(), nullable=True))
            if needs_published_render_job_id:
                batch_op.add_column(sa.Column("published_render_job_id", GUID(), nullable=True))
            if needs_published_export_id:
                batch_op.add_column(sa.Column("published_export_id", GUID(), nullable=True))
            if needs_current_fk:
                batch_op.create_foreign_key(
                    "fk_series_scripts_current_revision_id",
                    "series_script_revisions",
                    ["current_revision_id"],
                    ["id"],
                )
            if needs_approved_fk:
                batch_op.create_foreign_key(
                    "fk_series_scripts_approved_revision_id",
                    "series_script_revisions",
                    ["approved_revision_id"],
                    ["id"],
                )
            if needs_published_revision_fk:
                batch_op.create_foreign_key(
                    "fk_series_scripts_published_revision_id",
                    "series_script_revisions",
                    ["published_revision_id"],
                    ["id"],
                )
            if needs_published_project_fk:
                batch_op.create_foreign_key(
                    "fk_series_scripts_published_project_id",
                    "projects",
                    ["published_project_id"],
                    ["id"],
                )
            if needs_published_render_job_fk:
                batch_op.create_foreign_key(
                    "fk_series_scripts_published_render_job_id",
                    "render_jobs",
                    ["published_render_job_id"],
                    ["id"],
                )
            if needs_published_export_fk:
                batch_op.create_foreign_key(
                    "fk_series_scripts_published_export_id",
                    "exports",
                    ["published_export_id"],
                    ["id"],
                )

    conn = op.get_bind()
    series_scripts = sa.table(
        "series_scripts",
        sa.column("id", GUID()),
        sa.column("series_id", GUID()),
        sa.column("series_run_id", GUID()),
        sa.column("created_by_user_id", GUID()),
        sa.column("title", sa.String()),
        sa.column("summary", sa.Text()),
        sa.column("estimated_duration_seconds", sa.Integer()),
        sa.column("reading_time_label", sa.String()),
        sa.column("total_words", sa.Integer()),
        sa.column("lines", json_type()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    revisions = sa.table(
        "series_script_revisions",
        sa.column("id", GUID()),
        sa.column("series_script_id", GUID()),
        sa.column("series_id", GUID()),
        sa.column("created_by_user_id", GUID()),
        sa.column("source_series_run_id", GUID()),
        sa.column("revision_number", sa.Integer()),
        sa.column("approval_state", sa.String()),
        sa.column("moderation_summary", json_type()),
        sa.column("title", sa.String()),
        sa.column("summary", sa.Text()),
        sa.column("estimated_duration_seconds", sa.Integer()),
        sa.column("reading_time_label", sa.String()),
        sa.column("total_words", sa.Integer()),
        sa.column("lines", json_type()),
        sa.column("video_title", sa.String()),
        sa.column("video_description", sa.Text()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    rows = conn.execute(sa.select(series_scripts)).mappings().all()
    for row in rows:
        existing_revisions = conn.execute(
            sa.select(revisions.c.id, revisions.c.revision_number)
            .where(revisions.c.series_script_id == row["id"])
            .order_by(revisions.c.revision_number.asc())
        ).mappings().all()
        if existing_revisions:
            revision_id = existing_revisions[-1]["id"]
        else:
            revision_id = uuid.uuid4()
            conn.execute(
                revisions.insert().values(
                    id=revision_id,
                    series_script_id=row["id"],
                    series_id=row["series_id"],
                    created_by_user_id=row["created_by_user_id"],
                    source_series_run_id=row["series_run_id"],
                    revision_number=1,
                    approval_state="needs_review",
                    moderation_summary={},
                    title=row["title"],
                    summary=row["summary"],
                    estimated_duration_seconds=row["estimated_duration_seconds"],
                    reading_time_label=row["reading_time_label"],
                    total_words=row["total_words"],
                    lines=row["lines"],
                    video_title="",
                    video_description="",
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            )
        if row.get("current_revision_id") != revision_id:
            conn.execute(
                sa.text(
                    "UPDATE series_scripts SET current_revision_id = :revision_id WHERE id = :series_script_id"
                ),
                {"revision_id": revision_id, "series_script_id": row["id"]},
            )


def downgrade() -> None:
    with op.batch_alter_table("series_scripts") as batch_op:
        batch_op.drop_constraint("fk_series_scripts_published_export_id", type_="foreignkey")
        batch_op.drop_constraint("fk_series_scripts_published_render_job_id", type_="foreignkey")
        batch_op.drop_constraint("fk_series_scripts_published_project_id", type_="foreignkey")
        batch_op.drop_constraint("fk_series_scripts_published_revision_id", type_="foreignkey")
        batch_op.drop_constraint("fk_series_scripts_approved_revision_id", type_="foreignkey")
        batch_op.drop_constraint("fk_series_scripts_current_revision_id", type_="foreignkey")
        batch_op.drop_column("published_export_id")
        batch_op.drop_column("published_render_job_id")
        batch_op.drop_column("published_project_id")
        batch_op.drop_column("published_revision_id")
        batch_op.drop_column("approved_revision_id")
        batch_op.drop_column("current_revision_id")

    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_constraint("uq_projects_series_script_id", type_="unique")
        batch_op.drop_constraint("fk_projects_series_script_id", type_="foreignkey")
        batch_op.drop_column("is_internal")
        batch_op.drop_column("series_script_id")

    op.drop_index("ix_series_video_run_steps_series_script_revision_id", table_name="series_video_run_steps")
    op.drop_index("ix_series_video_run_steps_series_script_id", table_name="series_video_run_steps")
    op.drop_index("ix_series_video_run_steps_series_id", table_name="series_video_run_steps")
    op.drop_index("ix_series_video_run_steps_series_video_run_id", table_name="series_video_run_steps")
    op.drop_table("series_video_run_steps")

    op.drop_index("ix_series_video_runs_workspace_id", table_name="series_video_runs")
    op.drop_index("ix_series_video_runs_series_id", table_name="series_video_runs")
    op.drop_table("series_video_runs")

    op.drop_index("ix_series_script_revisions_source_series_run_id", table_name="series_script_revisions")
    op.drop_index("ix_series_script_revisions_series_id", table_name="series_script_revisions")
    op.drop_index("ix_series_script_revisions_series_script_id", table_name="series_script_revisions")
    op.drop_table("series_script_revisions")
