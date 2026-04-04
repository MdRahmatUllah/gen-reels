"""Add YouTube publishing, scheduling, and audit tables.

Revision ID: 20260404_0014
Revises: 20260403_0012
Create Date: 2026-04-04 18:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

from app.db.types import GUID, json_type


revision = "20260404_0014"
down_revision = "20260403_0012"
branch_labels = None
depends_on = None


video_lifecycle_status = sa.Enum(
    "uploaded",
    "transcribing",
    "metadata_ready",
    "scheduled",
    "publishing",
    "published",
    "failed",
    name="videolifecyclestatus",
)
video_metadata_source = sa.Enum("generated", "manual", name="videometadatasource")
publish_mode = sa.Enum("immediate", "scheduled", name="publishmode")
publish_visibility = sa.Enum("public", "private", "unlisted", name="publishvisibility")
publish_job_status = sa.Enum(
    "scheduled",
    "queued",
    "publishing",
    "published",
    "failed",
    "cancelled",
    name="publishjobstatus",
)


def _has_table(bind: Connection, table_name: str) -> bool:
    return sa.inspect(bind).has_table(table_name)


def _has_column(bind: Connection, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in sa.inspect(bind).get_columns(table_name))


def _has_index(bind: Connection, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in sa.inspect(bind).get_indexes(table_name))


def _has_unique_constraint(bind: Connection, table_name: str, constraint_name: str) -> bool:
    return any(
        constraint["name"] == constraint_name
        for constraint in sa.inspect(bind).get_unique_constraints(table_name)
    )


def _has_foreign_key(bind: Connection, table_name: str, constraint_name: str) -> bool:
    return any(
        constraint["name"] == constraint_name
        for constraint in sa.inspect(bind).get_foreign_keys(table_name)
    )


def _create_index_if_missing(
    bind: Connection,
    index_name: str,
    table_name: str,
    columns: list[str],
) -> None:
    if not _has_index(bind, table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=False)


def _create_unique_constraint_if_missing(
    bind: Connection,
    constraint_name: str,
    table_name: str,
    columns: list[str],
) -> None:
    if not _has_unique_constraint(bind, table_name, constraint_name):
        op.create_unique_constraint(constraint_name, table_name, columns)


def _create_foreign_key_if_missing(
    bind: Connection,
    constraint_name: str,
    source_table: str,
    referent_table: str,
    local_cols: list[str],
    remote_cols: list[str],
) -> None:
    if not _has_foreign_key(bind, source_table, constraint_name):
        op.create_foreign_key(
            constraint_name,
            source_table,
            referent_table,
            local_cols,
            remote_cols,
        )


def upgrade() -> None:
    bind = op.get_bind()
    video_lifecycle_status.create(bind, checkfirst=True)
    video_metadata_source.create(bind, checkfirst=True)
    publish_mode.create(bind, checkfirst=True)
    publish_visibility.create(bind, checkfirst=True)
    publish_job_status.create(bind, checkfirst=True)

    if not _has_table(bind, "youtube_accounts"):
        op.create_table(
            "youtube_accounts",
            sa.Column("id", GUID(), nullable=False),
            sa.Column("workspace_id", GUID(), nullable=False),
            sa.Column("owner_user_id", GUID(), nullable=False),
            sa.Column("google_subject", sa.String(length=255), nullable=True),
            sa.Column("google_account_email", sa.String(length=320), nullable=True),
            sa.Column("channel_id", sa.String(length=128), nullable=False),
            sa.Column("channel_title", sa.String(length=255), nullable=False),
            sa.Column("channel_handle", sa.String(length=255), nullable=True),
            sa.Column("access_token_encrypted", sa.Text(), nullable=False),
            sa.Column("refresh_token_encrypted", sa.Text(), nullable=False),
            sa.Column("scopes", json_type(), nullable=False, server_default="[]"),
            sa.Column("token_type", sa.String(length=32), nullable=False, server_default="Bearer"),
            sa.Column("token_expiry_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_token_refresh_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("disconnected_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "workspace_id",
                "owner_user_id",
                "channel_id",
                name="uq_youtube_accounts_owner_channel",
            ),
        )
    _create_unique_constraint_if_missing(
        bind,
        "uq_youtube_accounts_owner_channel",
        "youtube_accounts",
        ["workspace_id", "owner_user_id", "channel_id"],
    )
    _create_index_if_missing(
        bind,
        op.f("ix_youtube_accounts_owner_user_id"),
        "youtube_accounts",
        ["owner_user_id"],
    )
    _create_index_if_missing(
        bind,
        op.f("ix_youtube_accounts_workspace_id"),
        "youtube_accounts",
        ["workspace_id"],
    )

    if not _has_table(bind, "videos"):
        op.create_table(
            "videos",
            sa.Column("id", GUID(), nullable=False),
            sa.Column("workspace_id", GUID(), nullable=False),
            sa.Column("owner_user_id", GUID(), nullable=False),
            sa.Column("youtube_account_id", GUID(), nullable=True),
            sa.Column("approved_metadata_version_id", GUID(), nullable=True),
            sa.Column("original_file_name", sa.String(length=512), nullable=False),
            sa.Column("storage_bucket", sa.String(length=255), nullable=False),
            sa.Column("storage_object_name", sa.String(length=1024), nullable=False),
            sa.Column("content_type", sa.String(length=128), nullable=False, server_default="video/mp4"),
            sa.Column("size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
            sa.Column("duration_ms", sa.Integer(), nullable=True),
            sa.Column("width", sa.Integer(), nullable=True),
            sa.Column("height", sa.Integer(), nullable=True),
            sa.Column("status", video_lifecycle_status, nullable=False, server_default="uploaded"),
            sa.Column("transcript_ready_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("metadata_ready_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("scheduled_publish_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("youtube_video_id", sa.String(length=128), nullable=True),
            sa.Column("processing_error_code", sa.String(length=128), nullable=True),
            sa.Column("processing_error_message", sa.Text(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
            sa.ForeignKeyConstraint(["youtube_account_id"], ["youtube_accounts.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    elif not _has_column(bind, "videos", "approved_metadata_version_id"):
        op.add_column("videos", sa.Column("approved_metadata_version_id", GUID(), nullable=True))
    _create_index_if_missing(bind, op.f("ix_videos_owner_user_id"), "videos", ["owner_user_id"])
    _create_index_if_missing(bind, op.f("ix_videos_workspace_id"), "videos", ["workspace_id"])
    _create_index_if_missing(bind, op.f("ix_videos_youtube_account_id"), "videos", ["youtube_account_id"])

    if not _has_table(bind, "video_transcripts"):
        op.create_table(
            "video_transcripts",
            sa.Column("id", GUID(), nullable=False),
            sa.Column("workspace_id", GUID(), nullable=False),
            sa.Column("video_id", GUID(), nullable=False),
            sa.Column("transcript_text", sa.Text(), nullable=False),
            sa.Column("language_code", sa.String(length=32), nullable=False, server_default="unknown"),
            sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("words_payload", json_type(), nullable=False, server_default="[]"),
            sa.Column("whisper_model_size", sa.String(length=64), nullable=False, server_default="small"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["video_id"], ["videos.id"]),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("video_id", name="uq_video_transcripts_video"),
        )
    _create_unique_constraint_if_missing(
        bind,
        "uq_video_transcripts_video",
        "video_transcripts",
        ["video_id"],
    )
    _create_index_if_missing(bind, op.f("ix_video_transcripts_video_id"), "video_transcripts", ["video_id"])
    _create_index_if_missing(
        bind,
        op.f("ix_video_transcripts_workspace_id"),
        "video_transcripts",
        ["workspace_id"],
    )

    if not _has_table(bind, "video_metadata_versions"):
        op.create_table(
            "video_metadata_versions",
            sa.Column("id", GUID(), nullable=False),
            sa.Column("workspace_id", GUID(), nullable=False),
            sa.Column("video_id", GUID(), nullable=False),
            sa.Column("transcript_id", GUID(), nullable=True),
            sa.Column("created_by_user_id", GUID(), nullable=True),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("source_type", video_metadata_source, nullable=False),
            sa.Column("provider_name", sa.String(length=128), nullable=True),
            sa.Column("provider_model", sa.String(length=255), nullable=True),
            sa.Column("title_options", json_type(), nullable=False, server_default="[]"),
            sa.Column("recommended_title", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("title", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("tags", json_type(), nullable=False, server_default="[]"),
            sa.Column("hook_summary", sa.Text(), nullable=True),
            sa.Column("raw_response_payload", json_type(), nullable=False, server_default="{}"),
            sa.Column("is_approved", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["transcript_id"], ["video_transcripts.id"]),
            sa.ForeignKeyConstraint(["video_id"], ["videos.id"]),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("video_id", "version_number", name="uq_video_metadata_versions_video_version"),
        )
    _create_unique_constraint_if_missing(
        bind,
        "uq_video_metadata_versions_video_version",
        "video_metadata_versions",
        ["video_id", "version_number"],
    )
    _create_index_if_missing(
        bind,
        op.f("ix_video_metadata_versions_video_id"),
        "video_metadata_versions",
        ["video_id"],
    )
    _create_index_if_missing(
        bind,
        op.f("ix_video_metadata_versions_workspace_id"),
        "video_metadata_versions",
        ["workspace_id"],
    )

    _create_foreign_key_if_missing(
        bind,
        "fk_videos_approved_metadata_version_id_video_metadata_versions",
        "videos",
        "video_metadata_versions",
        ["approved_metadata_version_id"],
        ["id"],
    )

    if not _has_table(bind, "publish_schedules"):
        op.create_table(
            "publish_schedules",
            sa.Column("id", GUID(), nullable=False),
            sa.Column("workspace_id", GUID(), nullable=False),
            sa.Column("owner_user_id", GUID(), nullable=False),
            sa.Column("youtube_account_id", GUID(), nullable=False),
            sa.Column("timezone_name", sa.String(length=64), nullable=False),
            sa.Column("slots_local", json_type(), nullable=False, server_default="[]"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
            sa.ForeignKeyConstraint(["youtube_account_id"], ["youtube_accounts.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("youtube_account_id", name="uq_publish_schedules_account"),
        )
    _create_unique_constraint_if_missing(
        bind,
        "uq_publish_schedules_account",
        "publish_schedules",
        ["youtube_account_id"],
    )
    _create_index_if_missing(
        bind,
        op.f("ix_publish_schedules_owner_user_id"),
        "publish_schedules",
        ["owner_user_id"],
    )
    _create_index_if_missing(
        bind,
        op.f("ix_publish_schedules_workspace_id"),
        "publish_schedules",
        ["workspace_id"],
    )

    if not _has_table(bind, "publish_jobs"):
        op.create_table(
            "publish_jobs",
            sa.Column("id", GUID(), nullable=False),
            sa.Column("workspace_id", GUID(), nullable=False),
            sa.Column("owner_user_id", GUID(), nullable=False),
            sa.Column("video_id", GUID(), nullable=False),
            sa.Column("youtube_account_id", GUID(), nullable=False),
            sa.Column("metadata_version_id", GUID(), nullable=True),
            sa.Column("schedule_id", GUID(), nullable=True),
            sa.Column("publish_mode", publish_mode, nullable=False),
            sa.Column("visibility", publish_visibility, nullable=False),
            sa.Column("scheduled_publish_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", publish_job_status, nullable=False, server_default="scheduled"),
            sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("youtube_video_id", sa.String(length=128), nullable=True),
            sa.Column("youtube_video_url", sa.String(length=1024), nullable=True),
            sa.Column("youtube_response_payload", json_type(), nullable=False, server_default="{}"),
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_code", sa.String(length=128), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("last_progress_percent", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["metadata_version_id"], ["video_metadata_versions.id"]),
            sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["schedule_id"], ["publish_schedules.id"]),
            sa.ForeignKeyConstraint(["video_id"], ["videos.id"]),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
            sa.ForeignKeyConstraint(["youtube_account_id"], ["youtube_accounts.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing(bind, op.f("ix_publish_jobs_owner_user_id"), "publish_jobs", ["owner_user_id"])
    _create_index_if_missing(
        bind,
        op.f("ix_publish_jobs_scheduled_publish_at"),
        "publish_jobs",
        ["scheduled_publish_at"],
    )
    _create_index_if_missing(bind, op.f("ix_publish_jobs_status"), "publish_jobs", ["status"])
    _create_index_if_missing(bind, op.f("ix_publish_jobs_video_id"), "publish_jobs", ["video_id"])
    _create_index_if_missing(bind, op.f("ix_publish_jobs_workspace_id"), "publish_jobs", ["workspace_id"])
    _create_index_if_missing(
        bind,
        op.f("ix_publish_jobs_youtube_account_id"),
        "publish_jobs",
        ["youtube_account_id"],
    )

    if not _has_table(bind, "audit_logs"):
        op.create_table(
            "audit_logs",
            sa.Column("id", GUID(), nullable=False),
            sa.Column("workspace_id", GUID(), nullable=False),
            sa.Column("user_id", GUID(), nullable=True),
            sa.Column("action", sa.String(length=128), nullable=False),
            sa.Column("target_type", sa.String(length=64), nullable=False),
            sa.Column("target_id", sa.String(length=128), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="success"),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("payload", json_type(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing(bind, op.f("ix_audit_logs_user_id"), "audit_logs", ["user_id"])
    _create_index_if_missing(bind, op.f("ix_audit_logs_workspace_id"), "audit_logs", ["workspace_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_workspace_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_user_id"), table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index(op.f("ix_publish_jobs_youtube_account_id"), table_name="publish_jobs")
    op.drop_index(op.f("ix_publish_jobs_workspace_id"), table_name="publish_jobs")
    op.drop_index(op.f("ix_publish_jobs_video_id"), table_name="publish_jobs")
    op.drop_index(op.f("ix_publish_jobs_status"), table_name="publish_jobs")
    op.drop_index(op.f("ix_publish_jobs_scheduled_publish_at"), table_name="publish_jobs")
    op.drop_index(op.f("ix_publish_jobs_owner_user_id"), table_name="publish_jobs")
    op.drop_table("publish_jobs")

    op.drop_index(op.f("ix_publish_schedules_workspace_id"), table_name="publish_schedules")
    op.drop_index(op.f("ix_publish_schedules_owner_user_id"), table_name="publish_schedules")
    op.drop_table("publish_schedules")

    with op.batch_alter_table("videos") as batch_op:
        batch_op.drop_constraint(
            "fk_videos_approved_metadata_version_id_video_metadata_versions",
            type_="foreignkey",
        )

    op.drop_index(op.f("ix_video_metadata_versions_workspace_id"), table_name="video_metadata_versions")
    op.drop_index(op.f("ix_video_metadata_versions_video_id"), table_name="video_metadata_versions")
    op.drop_table("video_metadata_versions")

    op.drop_index(op.f("ix_video_transcripts_workspace_id"), table_name="video_transcripts")
    op.drop_index(op.f("ix_video_transcripts_video_id"), table_name="video_transcripts")
    op.drop_table("video_transcripts")

    op.drop_index(op.f("ix_videos_youtube_account_id"), table_name="videos")
    op.drop_index(op.f("ix_videos_workspace_id"), table_name="videos")
    op.drop_index(op.f("ix_videos_owner_user_id"), table_name="videos")
    op.drop_table("videos")

    op.drop_index(op.f("ix_youtube_accounts_workspace_id"), table_name="youtube_accounts")
    op.drop_index(op.f("ix_youtube_accounts_owner_user_id"), table_name="youtube_accounts")
    op.drop_table("youtube_accounts")

    bind = op.get_bind()
    publish_job_status.drop(bind, checkfirst=True)
    publish_visibility.drop(bind, checkfirst=True)
    publish_mode.drop(bind, checkfirst=True)
    video_metadata_source.drop(bind, checkfirst=True)
    video_lifecycle_status.drop(bind, checkfirst=True)
