"""Initial phase 1 schema.

Revision ID: 20260329_0001
Revises:
Create Date: 2026-03-29 00:01:00
"""

from alembic import op
import sqlalchemy as sa

from app.db.types import GUID, json_type


revision = "20260329_0001"
down_revision = None
branch_labels = None
depends_on = None


workspace_role = sa.Enum("admin", "member", "reviewer", "viewer", name="workspace_role")
project_stage = sa.Enum("brief", "script", "scenes", "renders", "exports", name="project_stage")
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
)
job_kind = sa.Enum("idea_generation", "script_generation", name="job_kind")
step_kind = sa.Enum("idea_generation", "script_generation", name="step_kind")
script_source = sa.Enum("generated", "manual", name="script_source")
idea_candidate_status = sa.Enum("generated", "selected", "superseded", name="idea_candidate_status")
provider_run_status = sa.Enum("queued", "running", "completed", "failed", name="provider_run_status")
provider_error_category = sa.Enum(
    "transient",
    "deterministic_input",
    "moderation_rejection",
    "internal",
    name="provider_error_category",
)
moderation_decision = sa.Enum("allowed", "blocked", name="moderation_decision")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "workspaces",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("plan_name", sa.String(length=100), nullable=False, server_default="Studio"),
        sa.Column("seats", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("credits_remaining", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("credits_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("monthly_budget_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_workspaces_slug", "workspaces", ["slug"], unique=True)

    op.create_table(
        "workspace_members",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", workspace_role, nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),
    )

    op.create_table(
        "sessions",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("active_workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=True),
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"], unique=False)

    op.create_table(
        "projects",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("owner_user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("active_brief_id", GUID(), nullable=True),
        sa.Column("selected_idea_id", GUID(), nullable=True),
        sa.Column("active_script_version_id", GUID(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("client", sa.String(length=255), nullable=True),
        sa.Column("aspect_ratio", sa.String(length=20), nullable=False, server_default="9:16"),
        sa.Column("duration_target_sec", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("stage", project_stage, nullable=False, server_default="brief"),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_projects_workspace_id", "projects", ["workspace_id"], unique=False)

    op.create_table(
        "project_briefs",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("project_id", GUID(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("hook", sa.Text(), nullable=False),
        sa.Column("target_audience", sa.Text(), nullable=False),
        sa.Column("call_to_action", sa.Text(), nullable=False),
        sa.Column("brand_north_star", sa.Text(), nullable=False),
        sa.Column("guardrails", json_type(), nullable=False),
        sa.Column("must_include", json_type(), nullable=False),
        sa.Column("approval_steps", json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "version_number", name="uq_project_brief_version"),
    )
    op.create_index("ix_project_briefs_project_id", "project_briefs", ["project_id"], unique=False)

    op.create_table(
        "idea_sets",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("project_id", GUID(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("source_brief_id", GUID(), sa.ForeignKey("project_briefs.id"), nullable=False),
        sa.Column("created_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("prompt_input", json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_idea_sets_project_id", "idea_sets", ["project_id"], unique=False)

    op.create_table(
        "idea_candidates",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("idea_set_id", GUID(), sa.ForeignKey("idea_sets.id"), nullable=False),
        sa.Column("project_id", GUID(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("hook", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("tags", json_type(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("status", idea_candidate_status, nullable=False, server_default="generated"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("idea_set_id", "order_index", name="uq_idea_candidate_order"),
    )
    op.create_index("ix_idea_candidates_project_id", "idea_candidates", ["project_id"], unique=False)
    op.create_index("ix_idea_candidates_idea_set_id", "idea_candidates", ["idea_set_id"], unique=False)

    op.create_table(
        "script_versions",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("project_id", GUID(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("based_on_idea_id", GUID(), sa.ForeignKey("idea_candidates.id"), nullable=True),
        sa.Column("created_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("parent_version_id", GUID(), sa.ForeignKey("script_versions.id"), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("source_type", script_source, nullable=False),
        sa.Column("approval_state", sa.String(length=64), nullable=False, server_default="draft"),
        sa.Column("total_words", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_duration_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reading_time_label", sa.String(length=64), nullable=False, server_default="0s draft"),
        sa.Column("lines", json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "version_number", name="uq_script_version"),
    )
    op.create_index("ix_script_versions_project_id", "script_versions", ["project_id"], unique=False)

    op.create_table(
        "render_jobs",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("project_id", GUID(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("created_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("job_kind", job_kind, nullable=False),
        sa.Column("queue_name", sa.String(length=64), nullable=False, server_default="planning"),
        sa.Column("status", job_status, nullable=False, server_default="queued"),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("payload", json_type(), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "created_by_user_id",
            "project_id",
            "job_kind",
            "idempotency_key",
            name="uq_render_job_idempotency",
        ),
    )
    op.create_index("ix_render_jobs_project_id", "render_jobs", ["project_id"], unique=False)

    op.create_table(
        "render_steps",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("render_job_id", GUID(), sa.ForeignKey("render_jobs.id"), nullable=False),
        sa.Column("project_id", GUID(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("step_kind", step_kind, nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", job_status, nullable=False, server_default="queued"),
        sa.Column("input_payload", json_type(), nullable=False),
        sa.Column("output_payload", json_type(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_render_steps_render_job_id", "render_steps", ["render_job_id"], unique=False)

    op.create_table(
        "provider_runs",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("render_job_id", GUID(), sa.ForeignKey("render_jobs.id"), nullable=True),
        sa.Column("render_step_id", GUID(), sa.ForeignKey("render_steps.id"), nullable=True),
        sa.Column("project_id", GUID(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=True),
        sa.Column("provider_name", sa.String(length=128), nullable=False),
        sa.Column("provider_model", sa.String(length=128), nullable=False),
        sa.Column("operation", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("status", provider_run_status, nullable=False, server_default="queued"),
        sa.Column("request_payload", json_type(), nullable=False),
        sa.Column("response_payload", json_type(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_category", provider_error_category, nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("cost_payload", json_type(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "moderation_events",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("project_id", GUID(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=True),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("decision", moderation_decision, nullable=False),
        sa.Column("provider_name", sa.String(length=128), nullable=False),
        sa.Column("severity_summary", json_type(), nullable=False),
        sa.Column("response_payload", json_type(), nullable=True),
        sa.Column("blocked_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_moderation_events_project_id", "moderation_events", ["project_id"], unique=False)
    op.create_index("ix_moderation_events_workspace_id", "moderation_events", ["workspace_id"], unique=False)
    op.create_index("ix_moderation_events_user_id", "moderation_events", ["user_id"], unique=False)

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=True)

    op.create_table(
        "audit_events",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=True),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("payload", json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_workspace_id", "audit_events", ["workspace_id"], unique=False)
    op.create_index("ix_audit_events_user_id", "audit_events", ["user_id"], unique=False)

    op.create_table(
        "consistency_packs",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("project_id", GUID(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("state", json_type(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    with op.batch_alter_table("projects") as batch_op:
        batch_op.create_foreign_key(
            "fk_projects_active_brief_id",
            "project_briefs",
            ["active_brief_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_projects_selected_idea_id",
            "idea_candidates",
            ["selected_idea_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_projects_active_script_version_id",
            "script_versions",
            ["active_script_version_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_constraint("fk_projects_active_script_version_id", type_="foreignkey")
        batch_op.drop_constraint("fk_projects_selected_idea_id", type_="foreignkey")
        batch_op.drop_constraint("fk_projects_active_brief_id", type_="foreignkey")
    op.drop_table("consistency_packs")
    op.drop_index("ix_audit_events_user_id", table_name="audit_events")
    op.drop_index("ix_audit_events_workspace_id", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_password_reset_tokens_token_hash", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_index("ix_moderation_events_user_id", table_name="moderation_events")
    op.drop_index("ix_moderation_events_workspace_id", table_name="moderation_events")
    op.drop_index("ix_moderation_events_project_id", table_name="moderation_events")
    op.drop_table("moderation_events")
    op.drop_table("provider_runs")
    op.drop_index("ix_render_steps_render_job_id", table_name="render_steps")
    op.drop_table("render_steps")
    op.drop_index("ix_render_jobs_project_id", table_name="render_jobs")
    op.drop_table("render_jobs")
    op.drop_index("ix_script_versions_project_id", table_name="script_versions")
    op.drop_table("script_versions")
    op.drop_index("ix_idea_candidates_idea_set_id", table_name="idea_candidates")
    op.drop_index("ix_idea_candidates_project_id", table_name="idea_candidates")
    op.drop_table("idea_candidates")
    op.drop_index("ix_idea_sets_project_id", table_name="idea_sets")
    op.drop_table("idea_sets")
    op.drop_index("ix_project_briefs_project_id", table_name="project_briefs")
    op.drop_table("project_briefs")
    op.drop_index("ix_projects_workspace_id", table_name="projects")
    op.drop_table("projects")
    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("workspace_members")
    op.drop_index("ix_workspaces_slug", table_name="workspaces")
    op.drop_table("workspaces")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    moderation_decision.drop(op.get_bind(), checkfirst=True)
    provider_error_category.drop(op.get_bind(), checkfirst=True)
    provider_run_status.drop(op.get_bind(), checkfirst=True)
    idea_candidate_status.drop(op.get_bind(), checkfirst=True)
    script_source.drop(op.get_bind(), checkfirst=True)
    step_kind.drop(op.get_bind(), checkfirst=True)
    job_kind.drop(op.get_bind(), checkfirst=True)
    job_status.drop(op.get_bind(), checkfirst=True)
    project_stage.drop(op.get_bind(), checkfirst=True)
    workspace_role.drop(op.get_bind(), checkfirst=True)
