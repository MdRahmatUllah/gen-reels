"""Phase 4 reliability and billing schema.

Revision ID: 20260329_0004
Revises: 20260329_0003
Create Date: 2026-03-29 18:15:00
"""

from alembic import op
import sqlalchemy as sa

from app.db.types import GUID, json_type


revision = "20260329_0004"
down_revision = "20260329_0003"
branch_labels = None
depends_on = None


moderation_review_status = sa.Enum(
    "none",
    "pending",
    "released",
    "rejected",
    name="moderation_review_status",
)
subscription_status = sa.Enum(
    "not_configured",
    "checkout_pending",
    "trialing",
    "active",
    "past_due",
    "cancelled",
    name="subscription_status",
)
credit_ledger_entry_kind = sa.Enum(
    "provider_run",
    "export_event",
    "manual_adjustment",
    "reconciliation",
    name="credit_ledger_entry_kind",
)


def upgrade() -> None:
    moderation_review_status.create(op.get_bind(), checkfirst=True)
    subscription_status.create(op.get_bind(), checkfirst=True)
    credit_ledger_entry_kind.create(op.get_bind(), checkfirst=True)

    with op.batch_alter_table("render_steps") as batch_op:
        batch_op.add_column(sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("retry_history", json_type(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("recovery_source_step_id", GUID(), nullable=True))
        batch_op.add_column(sa.Column("checkpoint_payload", json_type(), nullable=False, server_default="{}"))
        batch_op.add_column(sa.Column("last_checkpoint_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key(
            "fk_render_steps_recovery_source_step_id",
            "render_steps",
            ["recovery_source_step_id"],
            ["id"],
        )

    with op.batch_alter_table("assets") as batch_op:
        batch_op.add_column(sa.Column("quarantine_bucket_name", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("quarantine_object_name", sa.String(length=1024), nullable=True))
        batch_op.add_column(sa.Column("quarantined_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("released_at", sa.DateTime(timezone=True), nullable=True))

    with op.batch_alter_table("provider_runs") as batch_op:
        batch_op.add_column(sa.Column("external_request_id", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("normalized_cost_cents", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"))
        batch_op.add_column(sa.Column("billable_quantity", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("continuity_mode", sa.String(length=64), nullable=True))

    with op.batch_alter_table("moderation_events") as batch_op:
        batch_op.add_column(sa.Column("related_asset_id", GUID(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "review_status",
                moderation_review_status,
                nullable=False,
                server_default="none",
            )
        )
        batch_op.add_column(sa.Column("reviewed_by_user_id", GUID(), nullable=True))
        batch_op.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("review_notes", sa.Text(), nullable=True))
        batch_op.create_foreign_key(
            "fk_moderation_events_related_asset_id",
            "assets",
            ["related_asset_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_moderation_events_reviewed_by_user_id",
            "users",
            ["reviewed_by_user_id"],
            ["id"],
        )

    op.create_table(
        "subscriptions",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("provider_name", sa.String(length=128), nullable=False, server_default="stub_billing"),
        sa.Column("provider_customer_id", sa.String(length=255), nullable=True),
        sa.Column("provider_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("plan_name", sa.String(length=100), nullable=False, server_default="Studio"),
        sa.Column("status", subscription_status, nullable=False, server_default="not_configured"),
        sa.Column("monthly_credit_allowance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_period_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("metadata_payload", json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_id", name="uq_subscription_workspace"),
    )
    op.create_index("ix_subscriptions_workspace_id", "subscriptions", ["workspace_id"], unique=False)

    op.create_table(
        "credit_ledger_entries",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("project_id", GUID(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("render_job_id", GUID(), sa.ForeignKey("render_jobs.id"), nullable=True),
        sa.Column("render_step_id", GUID(), sa.ForeignKey("render_steps.id"), nullable=True),
        sa.Column("provider_run_id", GUID(), sa.ForeignKey("provider_runs.id"), nullable=True),
        sa.Column("export_id", GUID(), sa.ForeignKey("exports.id"), nullable=True),
        sa.Column("kind", credit_ledger_entry_kind, nullable=False),
        sa.Column("billable_unit", sa.String(length=128), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("credits_delta", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("amount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("balance_after", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("metadata_payload", json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_credit_ledger_idempotency_key"),
    )
    op.create_index("ix_credit_ledger_entries_workspace_id", "credit_ledger_entries", ["workspace_id"], unique=False)
    op.create_index("ix_credit_ledger_entries_project_id", "credit_ledger_entries", ["project_id"], unique=False)
    op.create_index(
        "ix_credit_ledger_entries_render_job_id",
        "credit_ledger_entries",
        ["render_job_id"],
        unique=False,
    )
    op.create_index(
        "ix_credit_ledger_entries_provider_run_id",
        "credit_ledger_entries",
        ["provider_run_id"],
        unique=False,
    )
    op.create_index("ix_credit_ledger_entries_export_id", "credit_ledger_entries", ["export_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_credit_ledger_entries_export_id", table_name="credit_ledger_entries")
    op.drop_index("ix_credit_ledger_entries_provider_run_id", table_name="credit_ledger_entries")
    op.drop_index("ix_credit_ledger_entries_render_job_id", table_name="credit_ledger_entries")
    op.drop_index("ix_credit_ledger_entries_project_id", table_name="credit_ledger_entries")
    op.drop_index("ix_credit_ledger_entries_workspace_id", table_name="credit_ledger_entries")
    op.drop_table("credit_ledger_entries")

    op.drop_index("ix_subscriptions_workspace_id", table_name="subscriptions")
    op.drop_table("subscriptions")

    with op.batch_alter_table("moderation_events") as batch_op:
        batch_op.drop_constraint("fk_moderation_events_reviewed_by_user_id", type_="foreignkey")
        batch_op.drop_constraint("fk_moderation_events_related_asset_id", type_="foreignkey")
        batch_op.drop_column("review_notes")
        batch_op.drop_column("reviewed_at")
        batch_op.drop_column("reviewed_by_user_id")
        batch_op.drop_column("review_status")
        batch_op.drop_column("related_asset_id")

    with op.batch_alter_table("provider_runs") as batch_op:
        batch_op.drop_column("continuity_mode")
        batch_op.drop_column("billable_quantity")
        batch_op.drop_column("currency")
        batch_op.drop_column("normalized_cost_cents")
        batch_op.drop_column("external_request_id")

    with op.batch_alter_table("assets") as batch_op:
        batch_op.drop_column("released_at")
        batch_op.drop_column("quarantined_at")
        batch_op.drop_column("quarantine_object_name")
        batch_op.drop_column("quarantine_bucket_name")

    with op.batch_alter_table("render_steps") as batch_op:
        batch_op.drop_constraint("fk_render_steps_recovery_source_step_id", type_="foreignkey")
        batch_op.drop_column("last_checkpoint_at")
        batch_op.drop_column("checkpoint_payload")
        batch_op.drop_column("recovery_source_step_id")
        batch_op.drop_column("retry_history")
        batch_op.drop_column("retry_count")

    credit_ledger_entry_kind.drop(op.get_bind(), checkfirst=True)
    subscription_status.drop(op.get_bind(), checkfirst=True)
    moderation_review_status.drop(op.get_bind(), checkfirst=True)
