"""Phase 7 local worker and BYO expansion schema.

Revision ID: 20260329_0007
Revises: 20260329_0006
Create Date: 2026-03-29 23:55:00
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

from app.db.types import GUID, json_type


revision = "20260329_0007"
down_revision = "20260329_0006"
branch_labels = None
depends_on = None


execution_mode = postgresql.ENUM("hosted", "byo", "local", name="execution_mode", create_type=False)
local_worker_status = sa.Enum(
    "online", "offline", "revoked", name="local_worker_status", create_type=False
)


def upgrade() -> None:
    execution_mode.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "workspace_provider_credentials",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("created_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("modality", sa.String(length=64), nullable=False),
        sa.Column("provider_key", sa.String(length=128), nullable=False),
        sa.Column("public_config", json_type(), nullable=False, server_default="{}"),
        sa.Column("secret_payload_encrypted", sa.Text(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_workspace_provider_credentials_workspace_id",
        "workspace_provider_credentials",
        ["workspace_id"],
        unique=False,
    )

    op.create_table(
        "local_workers",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("registered_by_api_key_id", GUID(), sa.ForeignKey("workspace_api_keys.id"), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", local_worker_status, nullable=False, server_default="online"),
        sa.Column("worker_token_hash", sa.String(length=128), nullable=False),
        sa.Column("token_prefix", sa.String(length=32), nullable=False),
        sa.Column("supports_ordered_reference_images", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("supports_first_last_frame_video", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("supports_tts", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("supports_clip_retime", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("metadata_payload", json_type(), nullable=False, server_default="{}"),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_polled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_job_claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("worker_token_hash", name="uq_local_worker_token_hash"),
    )
    op.create_index("ix_local_workers_workspace_id", "local_workers", ["workspace_id"], unique=False)

    op.create_table(
        "workspace_execution_policies",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("updated_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("text_mode", execution_mode, nullable=False, server_default="hosted"),
        sa.Column("text_provider_key", sa.String(length=128), nullable=False, server_default="azure_openai_text"),
        sa.Column("text_credential_id", GUID(), sa.ForeignKey("workspace_provider_credentials.id"), nullable=True),
        sa.Column("moderation_mode", execution_mode, nullable=False, server_default="hosted"),
        sa.Column(
            "moderation_provider_key",
            sa.String(length=128),
            nullable=False,
            server_default="azure_content_safety",
        ),
        sa.Column(
            "moderation_credential_id",
            GUID(),
            sa.ForeignKey("workspace_provider_credentials.id"),
            nullable=True,
        ),
        sa.Column("image_mode", execution_mode, nullable=False, server_default="hosted"),
        sa.Column("image_provider_key", sa.String(length=128), nullable=False, server_default="stub_image_provider"),
        sa.Column("image_credential_id", GUID(), sa.ForeignKey("workspace_provider_credentials.id"), nullable=True),
        sa.Column("video_mode", execution_mode, nullable=False, server_default="hosted"),
        sa.Column("video_provider_key", sa.String(length=128), nullable=False, server_default="stub_video_provider"),
        sa.Column("video_credential_id", GUID(), sa.ForeignKey("workspace_provider_credentials.id"), nullable=True),
        sa.Column("speech_mode", execution_mode, nullable=False, server_default="hosted"),
        sa.Column(
            "speech_provider_key",
            sa.String(length=128),
            nullable=False,
            server_default="stub_speech_provider",
        ),
        sa.Column(
            "speech_credential_id",
            GUID(),
            sa.ForeignKey("workspace_provider_credentials.id"),
            nullable=True,
        ),
        sa.Column("preferred_local_worker_id", GUID(), sa.ForeignKey("local_workers.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_id", name="uq_workspace_execution_policy_workspace"),
    )
    op.create_index(
        "ix_workspace_execution_policies_workspace_id",
        "workspace_execution_policies",
        ["workspace_id"],
        unique=False,
    )

    op.create_table(
        "local_worker_heartbeats",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("worker_id", GUID(), sa.ForeignKey("local_workers.id"), nullable=False),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("status", local_worker_status, nullable=False),
        sa.Column("metadata_payload", json_type(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_local_worker_heartbeats_worker_id", "local_worker_heartbeats", ["worker_id"], unique=False)
    op.create_index(
        "ix_local_worker_heartbeats_workspace_id",
        "local_worker_heartbeats",
        ["workspace_id"],
        unique=False,
    )

    with op.batch_alter_table("provider_runs") as batch_op:
        batch_op.add_column(
            sa.Column("execution_mode", execution_mode, nullable=False, server_default="hosted")
        )
        batch_op.add_column(sa.Column("worker_id", GUID(), nullable=True))
        batch_op.add_column(sa.Column("provider_credential_id", GUID(), nullable=True))
        batch_op.add_column(
            sa.Column("routing_decision_payload", json_type(), nullable=False, server_default="{}")
        )
        batch_op.create_foreign_key("fk_provider_runs_worker_id", "local_workers", ["worker_id"], ["id"])
        batch_op.create_foreign_key(
            "fk_provider_runs_provider_credential_id",
            "workspace_provider_credentials",
            ["provider_credential_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("provider_runs") as batch_op:
        batch_op.drop_constraint("fk_provider_runs_provider_credential_id", type_="foreignkey")
        batch_op.drop_constraint("fk_provider_runs_worker_id", type_="foreignkey")
        batch_op.drop_column("routing_decision_payload")
        batch_op.drop_column("provider_credential_id")
        batch_op.drop_column("worker_id")
        batch_op.drop_column("execution_mode")

    op.drop_index("ix_local_worker_heartbeats_workspace_id", table_name="local_worker_heartbeats")
    op.drop_index("ix_local_worker_heartbeats_worker_id", table_name="local_worker_heartbeats")
    op.drop_table("local_worker_heartbeats")

    op.drop_index("ix_workspace_execution_policies_workspace_id", table_name="workspace_execution_policies")
    op.drop_table("workspace_execution_policies")

    op.drop_index("ix_local_workers_workspace_id", table_name="local_workers")
    op.drop_table("local_workers")

    op.drop_index(
        "ix_workspace_provider_credentials_workspace_id",
        table_name="workspace_provider_credentials",
    )
    op.drop_table("workspace_provider_credentials")

    local_worker_status.drop(op.get_bind(), checkfirst=True)
    execution_mode.drop(op.get_bind(), checkfirst=True)
