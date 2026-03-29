"""Phase 6 collaboration and studio schema.

Revision ID: 20260329_0006
Revises: 20260329_0005
Create Date: 2026-03-29 23:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.db.types import GUID, json_type


revision = "20260329_0006"
down_revision = "20260329_0005"
branch_labels = None
depends_on = None


brand_kit_status = sa.Enum("draft", "active", "archived", name="brand_kit_status")
brand_enforcement_mode = sa.Enum("advisory", "enforced", name="brand_enforcement_mode")
review_status = sa.Enum("pending", "approved", "rejected", "cancelled", name="review_status")
review_target_type = sa.Enum(
    "script_version",
    "scene_plan",
    "export",
    "template_version",
    name="review_target_type",
)
webhook_delivery_status = sa.Enum("queued", "delivered", "failed", name="webhook_delivery_status")


def upgrade() -> None:
    brand_kit_status.create(op.get_bind(), checkfirst=True)
    brand_enforcement_mode.create(op.get_bind(), checkfirst=True)
    review_status.create(op.get_bind(), checkfirst=True)
    review_target_type.create(op.get_bind(), checkfirst=True)
    webhook_delivery_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "brand_kits",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("created_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("default_visual_preset_id", GUID(), sa.ForeignKey("visual_presets.id"), nullable=True),
        sa.Column("default_voice_preset_id", GUID(), sa.ForeignKey("voice_presets.id"), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", brand_kit_status, nullable=False, server_default="active"),
        sa.Column(
            "enforcement_mode",
            brand_enforcement_mode,
            nullable=False,
            server_default="advisory",
        ),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("required_terms", json_type(), nullable=False, server_default="[]"),
        sa.Column("banned_terms", json_type(), nullable=False, server_default="[]"),
        sa.Column("subtitle_style_override", json_type(), nullable=False, server_default="{}"),
        sa.Column("export_profile_override", json_type(), nullable=False, server_default="{}"),
        sa.Column("audio_mix_profile_override", json_type(), nullable=False, server_default="{}"),
        sa.Column("brand_rules", json_type(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_brand_kits_workspace_id", "brand_kits", ["workspace_id"], unique=False)

    op.create_table(
        "comments",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("project_id", GUID(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=False),
        sa.Column("author_user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("metadata_payload", json_type(), nullable=False, server_default="{}"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_comments_workspace_id", "comments", ["workspace_id"], unique=False)
    op.create_index("ix_comments_project_id", "comments", ["project_id"], unique=False)

    op.create_table(
        "review_requests",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("project_id", GUID(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("target_type", review_target_type, nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=False),
        sa.Column("requested_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assigned_to_user_id", GUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("requested_version", sa.Integer(), nullable=True),
        sa.Column("status", review_status, nullable=False, server_default="pending"),
        sa.Column("request_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("decision_notes", sa.Text(), nullable=True),
        sa.Column("decided_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_review_requests_workspace_id", "review_requests", ["workspace_id"], unique=False)
    op.create_index("ix_review_requests_project_id", "review_requests", ["project_id"], unique=False)

    op.create_table(
        "workspace_api_keys",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("created_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "role_scope",
            sa.Enum(
                "admin",
                "member",
                "reviewer",
                "viewer",
                name="workspace_role",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("key_prefix", sa.String(length=32), nullable=False),
        sa.Column("key_hash", sa.String(length=128), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("key_hash", name="uq_workspace_api_key_hash"),
    )
    op.create_index("ix_workspace_api_keys_workspace_id", "workspace_api_keys", ["workspace_id"], unique=False)

    op.create_table(
        "webhook_endpoints",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("created_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("target_url", sa.String(length=2048), nullable=False),
        sa.Column("event_types", json_type(), nullable=False, server_default="[]"),
        sa.Column("signing_secret", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_webhook_endpoints_workspace_id", "webhook_endpoints", ["workspace_id"], unique=False)

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("endpoint_id", GUID(), sa.ForeignKey("webhook_endpoints.id"), nullable=False),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("replay_id", sa.String(length=128), nullable=False),
        sa.Column("signature", sa.String(length=255), nullable=False),
        sa.Column("status", webhook_delivery_status, nullable=False, server_default="queued"),
        sa.Column("payload", json_type(), nullable=False, server_default="{}"),
        sa.Column("response_status_code", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("replay_id", name="uq_webhook_delivery_replay_id"),
    )
    op.create_index("ix_webhook_deliveries_endpoint_id", "webhook_deliveries", ["endpoint_id"], unique=False)
    op.create_index("ix_webhook_deliveries_workspace_id", "webhook_deliveries", ["workspace_id"], unique=False)

    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("brand_kit_id", GUID(), nullable=True))
        batch_op.create_foreign_key("fk_projects_brand_kit_id", "brand_kits", ["brand_kit_id"], ["id"])

    with op.batch_alter_table("script_versions") as batch_op:
        batch_op.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))

    with op.batch_alter_table("scene_plans") as batch_op:
        batch_op.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))

    with op.batch_alter_table("visual_presets") as batch_op:
        batch_op.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))

    with op.batch_alter_table("voice_presets") as batch_op:
        batch_op.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))

    with op.batch_alter_table("project_templates") as batch_op:
        batch_op.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))


def downgrade() -> None:
    with op.batch_alter_table("project_templates") as batch_op:
        batch_op.drop_column("version")

    with op.batch_alter_table("voice_presets") as batch_op:
        batch_op.drop_column("version")

    with op.batch_alter_table("visual_presets") as batch_op:
        batch_op.drop_column("version")

    with op.batch_alter_table("scene_plans") as batch_op:
        batch_op.drop_column("version")

    with op.batch_alter_table("script_versions") as batch_op:
        batch_op.drop_column("version")

    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_constraint("fk_projects_brand_kit_id", type_="foreignkey")
        batch_op.drop_column("brand_kit_id")

    op.drop_index("ix_webhook_deliveries_workspace_id", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_endpoint_id", table_name="webhook_deliveries")
    op.drop_table("webhook_deliveries")

    op.drop_index("ix_webhook_endpoints_workspace_id", table_name="webhook_endpoints")
    op.drop_table("webhook_endpoints")

    op.drop_index("ix_workspace_api_keys_workspace_id", table_name="workspace_api_keys")
    op.drop_table("workspace_api_keys")

    op.drop_index("ix_review_requests_project_id", table_name="review_requests")
    op.drop_index("ix_review_requests_workspace_id", table_name="review_requests")
    op.drop_table("review_requests")

    op.drop_index("ix_comments_project_id", table_name="comments")
    op.drop_index("ix_comments_workspace_id", table_name="comments")
    op.drop_table("comments")

    op.drop_index("ix_brand_kits_workspace_id", table_name="brand_kits")
    op.drop_table("brand_kits")

    webhook_delivery_status.drop(op.get_bind(), checkfirst=True)
    review_target_type.drop(op.get_bind(), checkfirst=True)
    review_status.drop(op.get_bind(), checkfirst=True)
    brand_enforcement_mode.drop(op.get_bind(), checkfirst=True)
    brand_kit_status.drop(op.get_bind(), checkfirst=True)
