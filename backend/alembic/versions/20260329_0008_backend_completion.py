"""Backend completion schema for events, quotas, notifications, and SSO.

Revision ID: 20260329_0008
Revises: 20260329_0007
Create Date: 2026-03-29 23:59:00
"""

from __future__ import annotations

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

from app.db.types import GUID, json_type


revision = "20260329_0008"
down_revision = "20260329_0007"
branch_labels = None
depends_on = None


moderation_report_status = sa.Enum(
    "pending",
    "released",
    "rejected",
    "passed",
    name="moderation_report_status",
    create_type=False,
)
workspace_auth_provider_type = sa.Enum(
    "oidc", "saml", name="workspace_auth_provider_type", create_type=False
)
webhook_delivery_status_old = sa.Enum(
    "queued",
    "delivered",
    "failed",
    name="webhook_delivery_status",
)
webhook_delivery_status_new = sa.Enum(
    "queued",
    "delivered",
    "failed",
    "exhausted",
    name="webhook_delivery_status",
)


def _dialect_name() -> str:
    return op.get_bind().dialect.name


def upgrade() -> None:
    bind = op.get_bind()
    if _dialect_name() == "postgresql":
        op.execute("ALTER TYPE webhook_delivery_status ADD VALUE IF NOT EXISTS 'exhausted'")

    op.create_table(
        "render_events",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("project_id", GUID(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("render_job_id", GUID(), sa.ForeignKey("render_jobs.id"), nullable=False),
        sa.Column("render_step_id", GUID(), sa.ForeignKey("render_steps.id"), nullable=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("payload", json_type(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("render_job_id", "sequence_number", name="uq_render_event_sequence"),
    )
    op.create_index("ix_render_events_workspace_id", "render_events", ["workspace_id"], unique=False)
    op.create_index("ix_render_events_project_id", "render_events", ["project_id"], unique=False)
    op.create_index("ix_render_events_render_job_id", "render_events", ["render_job_id"], unique=False)

    op.create_table(
        "moderation_reports",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("project_id", GUID(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("render_job_id", GUID(), sa.ForeignKey("render_jobs.id"), nullable=True),
        sa.Column("export_id", GUID(), sa.ForeignKey("exports.id"), nullable=True),
        sa.Column("related_asset_id", GUID(), sa.ForeignKey("assets.id"), nullable=True),
        sa.Column("status", moderation_report_status, nullable=False, server_default="pending"),
        sa.Column("sample_reason", sa.String(length=128), nullable=False),
        sa.Column(
            "provider_name",
            sa.String(length=128),
            nullable=False,
            server_default="azure_content_safety",
        ),
        sa.Column("blocked_event_count_30d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("findings_payload", json_type(), nullable=False, server_default="{}"),
        sa.Column("reviewed_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_moderation_reports_workspace_id", "moderation_reports", ["workspace_id"], unique=False
    )
    op.create_index(
        "ix_moderation_reports_project_id", "moderation_reports", ["project_id"], unique=False
    )
    op.create_index(
        "ix_moderation_reports_render_job_id", "moderation_reports", ["render_job_id"], unique=False
    )
    op.create_index("ix_moderation_reports_export_id", "moderation_reports", ["export_id"], unique=False)
    op.create_index(
        "ix_moderation_reports_related_asset_id",
        "moderation_reports",
        ["related_asset_id"],
        unique=False,
    )

    op.create_table(
        "plans",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("monthly_credit_allowance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("monthly_render_limit", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_concurrent_renders", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_scenes_per_render", sa.Integer(), nullable=False, server_default="12"),
        sa.Column("metadata_payload", json_type(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("slug", name="uq_plan_slug"),
    )
    plan_table = sa.table(
        "plans",
        sa.column("id", GUID()),
        sa.column("slug", sa.String()),
        sa.column("name", sa.String()),
        sa.column("monthly_credit_allowance", sa.Integer()),
        sa.column("monthly_render_limit", sa.Integer()),
        sa.column("max_concurrent_renders", sa.Integer()),
        sa.column("max_scenes_per_render", sa.Integer()),
        sa.column("metadata_payload", json_type()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(timezone.utc)
    op.bulk_insert(
        plan_table,
        [
            {
                "id": "0f74cc4f-4c37-4dc3-8939-eac7e6f4e111",
                "slug": "free",
                "name": "Free",
                "monthly_credit_allowance": 100,
                "monthly_render_limit": 3,
                "max_concurrent_renders": 1,
                "max_scenes_per_render": 10,
                "metadata_payload": {"export_moderation_rate": 0.25},
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": "7bd97926-b374-4d60-a731-9a7cb302f222",
                "slug": "creator",
                "name": "Creator",
                "monthly_credit_allowance": 1000,
                "monthly_render_limit": 20,
                "max_concurrent_renders": 2,
                "max_scenes_per_render": 18,
                "metadata_payload": {"export_moderation_rate": 0.10},
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": "67a5e39a-5485-4c64-b655-91288e85d333",
                "slug": "pro",
                "name": "Pro",
                "monthly_credit_allowance": 5000,
                "monthly_render_limit": 100,
                "max_concurrent_renders": 4,
                "max_scenes_per_render": 24,
                "metadata_payload": {"export_moderation_rate": 0.10},
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": "d0108070-b953-43cb-87a6-c8f2a2ead444",
                "slug": "studio",
                "name": "Studio",
                "monthly_credit_allowance": 25000,
                "monthly_render_limit": 500,
                "max_concurrent_renders": 10,
                "max_scenes_per_render": 40,
                "metadata_payload": {"export_moderation_rate": 0.10},
                "created_at": now,
                "updated_at": now,
            },
        ],
    )

    op.create_table(
        "notification_preferences",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("render_email_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("review_email_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("membership_email_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("moderation_email_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("planning_email_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "workspace_id", "user_id", name="uq_notification_preference_user_workspace"
        ),
    )
    op.create_index(
        "ix_notification_preferences_workspace_id",
        "notification_preferences",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_notification_preferences_user_id",
        "notification_preferences",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "notification_events",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("project_id", GUID(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("render_job_id", GUID(), sa.ForeignKey("render_jobs.id"), nullable=True),
        sa.Column("review_request_id", GUID(), sa.ForeignKey("review_requests.id"), nullable=True),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("payload", json_type(), nullable=False, server_default="{}"),
        sa.Column("email_delivery_status", sa.String(length=32), nullable=True),
        sa.Column("email_error_message", sa.Text(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_notification_events_workspace_id", "notification_events", ["workspace_id"], unique=False)
    op.create_index("ix_notification_events_user_id", "notification_events", ["user_id"], unique=False)
    op.create_index("ix_notification_events_project_id", "notification_events", ["project_id"], unique=False)
    op.create_index(
        "ix_notification_events_render_job_id", "notification_events", ["render_job_id"], unique=False
    )

    op.create_table(
        "workspace_auth_configurations",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("created_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("provider_type", workspace_auth_provider_type, nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("config_public", json_type(), nullable=False, server_default="{}"),
        sa.Column("secret_payload_encrypted", sa.Text(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_validation_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_workspace_auth_configurations_workspace_id",
        "workspace_auth_configurations",
        ["workspace_id"],
        unique=False,
    )

    with op.batch_alter_table("workspaces") as batch_op:
        batch_op.add_column(sa.Column("credits_reserved", sa.Integer(), nullable=False, server_default="0"))

    with op.batch_alter_table("render_jobs") as batch_op:
        batch_op.add_column(sa.Column("reserved_credits", sa.Integer(), nullable=False, server_default="0"))

    with op.batch_alter_table("assets") as batch_op:
        batch_op.add_column(sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    with op.batch_alter_table("exports") as batch_op:
        batch_op.add_column(
            sa.Column("availability_status", sa.String(length=32), nullable=False, server_default="available")
        )
        batch_op.add_column(sa.Column("held_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("available_at", sa.DateTime(timezone=True), nullable=True))

    op.execute("UPDATE exports SET available_at = completed_at WHERE completed_at IS NOT NULL")

    with op.batch_alter_table("workspace_execution_policies") as batch_op:
        batch_op.add_column(
            sa.Column("pause_render_generation", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(
            sa.Column("pause_image_generation", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(
            sa.Column("pause_video_generation", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(
            sa.Column("pause_audio_generation", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(sa.Column("pause_reason", sa.Text(), nullable=True))
        batch_op.alter_column(
            "image_provider_key",
            existing_type=sa.String(length=128),
            server_default="azure_openai_image",
        )
        batch_op.alter_column(
            "video_provider_key",
            existing_type=sa.String(length=128),
            server_default="veo_video",
        )
        batch_op.alter_column(
            "speech_provider_key",
            existing_type=sa.String(length=128),
            server_default="azure_openai_speech",
        )

    op.execute(
        "UPDATE workspace_execution_policies "
        "SET image_provider_key = 'azure_openai_image' "
        "WHERE image_provider_key = 'stub_image_provider'"
    )
    op.execute(
        "UPDATE workspace_execution_policies "
        "SET video_provider_key = 'veo_video' "
        "WHERE video_provider_key = 'stub_video_provider'"
    )
    op.execute(
        "UPDATE workspace_execution_policies "
        "SET speech_provider_key = 'azure_openai_speech' "
        "WHERE speech_provider_key = 'stub_speech_provider'"
    )

    with op.batch_alter_table("webhook_deliveries") as batch_op:
        if _dialect_name() == "sqlite":
            batch_op.alter_column(
                "status",
                existing_type=webhook_delivery_status_old,
                type_=webhook_delivery_status_new,
                existing_nullable=False,
                server_default="queued",
            )
        batch_op.add_column(sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("exhausted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("webhook_deliveries") as batch_op:
        batch_op.drop_column("exhausted_at")
        batch_op.drop_column("last_attempt_at")
        batch_op.drop_column("next_attempt_at")

    with op.batch_alter_table("workspace_execution_policies") as batch_op:
        batch_op.alter_column(
            "speech_provider_key",
            existing_type=sa.String(length=128),
            server_default="stub_speech_provider",
        )
        batch_op.alter_column(
            "video_provider_key",
            existing_type=sa.String(length=128),
            server_default="stub_video_provider",
        )
        batch_op.alter_column(
            "image_provider_key",
            existing_type=sa.String(length=128),
            server_default="stub_image_provider",
        )
        batch_op.drop_column("pause_reason")
        batch_op.drop_column("pause_audio_generation")
        batch_op.drop_column("pause_video_generation")
        batch_op.drop_column("pause_image_generation")
        batch_op.drop_column("pause_render_generation")

    with op.batch_alter_table("exports") as batch_op:
        batch_op.drop_column("available_at")
        batch_op.drop_column("held_at")
        batch_op.drop_column("availability_status")

    with op.batch_alter_table("assets") as batch_op:
        batch_op.drop_column("deleted_at")
        batch_op.drop_column("expires_at")

    with op.batch_alter_table("render_jobs") as batch_op:
        batch_op.drop_column("reserved_credits")

    with op.batch_alter_table("workspaces") as batch_op:
        batch_op.drop_column("credits_reserved")

    op.drop_index(
        "ix_workspace_auth_configurations_workspace_id",
        table_name="workspace_auth_configurations",
    )
    op.drop_table("workspace_auth_configurations")

    op.drop_index("ix_notification_events_render_job_id", table_name="notification_events")
    op.drop_index("ix_notification_events_project_id", table_name="notification_events")
    op.drop_index("ix_notification_events_user_id", table_name="notification_events")
    op.drop_index("ix_notification_events_workspace_id", table_name="notification_events")
    op.drop_table("notification_events")

    op.drop_index(
        "ix_notification_preferences_user_id", table_name="notification_preferences"
    )
    op.drop_index(
        "ix_notification_preferences_workspace_id",
        table_name="notification_preferences",
    )
    op.drop_table("notification_preferences")

    op.drop_table("plans")

    op.drop_index("ix_moderation_reports_related_asset_id", table_name="moderation_reports")
    op.drop_index("ix_moderation_reports_export_id", table_name="moderation_reports")
    op.drop_index("ix_moderation_reports_render_job_id", table_name="moderation_reports")
    op.drop_index("ix_moderation_reports_project_id", table_name="moderation_reports")
    op.drop_index("ix_moderation_reports_workspace_id", table_name="moderation_reports")
    op.drop_table("moderation_reports")

    op.drop_index("ix_render_events_render_job_id", table_name="render_events")
    op.drop_index("ix_render_events_project_id", table_name="render_events")
    op.drop_index("ix_render_events_workspace_id", table_name="render_events")
    op.drop_table("render_events")

    workspace_auth_provider_type.drop(op.get_bind(), checkfirst=True)
    moderation_report_status.drop(op.get_bind(), checkfirst=True)
