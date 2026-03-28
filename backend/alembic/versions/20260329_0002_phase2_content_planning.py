"""Phase 2 content planning schema.

Revision ID: 20260329_0002
Revises: 20260329_0001
Create Date: 2026-03-29 10:30:00
"""

from alembic import op
import sqlalchemy as sa

from app.db.types import GUID, json_type


revision = "20260329_0002"
down_revision = "20260329_0001"
branch_labels = None
depends_on = None


scene_plan_source = sa.Enum("generated", "manual", name="scene_plan_source")


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if _is_postgresql():
        op.execute("ALTER TYPE job_kind ADD VALUE IF NOT EXISTS 'scene_plan_generation'")
        op.execute("ALTER TYPE job_kind ADD VALUE IF NOT EXISTS 'prompt_pair_generation'")
        op.execute("ALTER TYPE step_kind ADD VALUE IF NOT EXISTS 'scene_plan_generation'")
        op.execute("ALTER TYPE step_kind ADD VALUE IF NOT EXISTS 'prompt_pair_generation'")

    scene_plan_source.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "visual_presets",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("created_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("prompt_prefix", sa.Text(), nullable=False, server_default=""),
        sa.Column("style_descriptor", sa.Text(), nullable=False, server_default=""),
        sa.Column("negative_prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("camera_defaults", sa.Text(), nullable=False, server_default=""),
        sa.Column("color_palette", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("reference_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_visual_presets_workspace_id", "visual_presets", ["workspace_id"], unique=False)

    op.create_table(
        "voice_presets",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("created_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("provider_voice", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("tone_descriptor", sa.Text(), nullable=False, server_default=""),
        sa.Column("language_code", sa.String(length=32), nullable=False, server_default="en-US"),
        sa.Column("pace_multiplier", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_voice_presets_workspace_id", "voice_presets", ["workspace_id"], unique=False)

    op.create_table(
        "scene_plans",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("project_id", GUID(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("based_on_script_version_id", GUID(), sa.ForeignKey("script_versions.id"), nullable=False),
        sa.Column("created_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("visual_preset_id", GUID(), sa.ForeignKey("visual_presets.id"), nullable=True),
        sa.Column("voice_preset_id", GUID(), sa.ForeignKey("voice_presets.id"), nullable=True),
        sa.Column("consistency_pack_id", GUID(), sa.ForeignKey("consistency_packs.id"), nullable=True),
        sa.Column("parent_scene_plan_id", GUID(), sa.ForeignKey("scene_plans.id"), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("source_type", scene_plan_source, nullable=False),
        sa.Column("approval_state", sa.String(length=64), nullable=False, server_default="draft"),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("total_estimated_duration_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scene_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("validation_warnings", json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "version_number", name="uq_scene_plan_version"),
    )
    op.create_index("ix_scene_plans_project_id", "scene_plans", ["project_id"], unique=False)

    op.create_table(
        "scene_segments",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("scene_plan_id", GUID(), sa.ForeignKey("scene_plans.id"), nullable=False),
        sa.Column("scene_index", sa.Integer(), nullable=False),
        sa.Column("source_line_ids", json_type(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("beat", sa.Text(), nullable=False, server_default=""),
        sa.Column("narration_text", sa.Text(), nullable=False),
        sa.Column("caption_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("visual_direction", sa.Text(), nullable=False, server_default=""),
        sa.Column("shot_type", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("motion", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("target_duration_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_voice_duration_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actual_voice_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("visual_prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("start_image_prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("end_image_prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("transition_mode", sa.String(length=32), nullable=False, server_default="hard_cut"),
        sa.Column("notes", json_type(), nullable=False),
        sa.Column("validation_warnings", json_type(), nullable=False),
        sa.Column("chained_from_asset_id", GUID(), nullable=True),
        sa.Column("start_image_asset_id", GUID(), nullable=True),
        sa.Column("end_image_asset_id", GUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("scene_plan_id", "scene_index", name="uq_scene_segment_index"),
    )
    op.create_index("ix_scene_segments_scene_plan_id", "scene_segments", ["scene_plan_id"], unique=False)

    with op.batch_alter_table("script_versions") as batch_op:
        batch_op.add_column(sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("approved_by_user_id", GUID(), nullable=True))
        batch_op.create_foreign_key(
            "fk_script_versions_approved_by_user_id",
            "users",
            ["approved_by_user_id"],
            ["id"],
        )

    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("active_scene_plan_id", GUID(), nullable=True))
        batch_op.add_column(sa.Column("default_visual_preset_id", GUID(), nullable=True))
        batch_op.add_column(sa.Column("default_voice_preset_id", GUID(), nullable=True))
        batch_op.create_foreign_key(
            "fk_projects_active_scene_plan_id",
            "scene_plans",
            ["active_scene_plan_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_projects_default_visual_preset_id",
            "visual_presets",
            ["default_visual_preset_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_projects_default_voice_preset_id",
            "voice_presets",
            ["default_voice_preset_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_constraint("fk_projects_default_voice_preset_id", type_="foreignkey")
        batch_op.drop_constraint("fk_projects_default_visual_preset_id", type_="foreignkey")
        batch_op.drop_constraint("fk_projects_active_scene_plan_id", type_="foreignkey")
        batch_op.drop_column("default_voice_preset_id")
        batch_op.drop_column("default_visual_preset_id")
        batch_op.drop_column("active_scene_plan_id")

    with op.batch_alter_table("script_versions") as batch_op:
        batch_op.drop_constraint("fk_script_versions_approved_by_user_id", type_="foreignkey")
        batch_op.drop_column("approved_by_user_id")
        batch_op.drop_column("approved_at")

    op.drop_index("ix_scene_segments_scene_plan_id", table_name="scene_segments")
    op.drop_table("scene_segments")
    op.drop_index("ix_scene_plans_project_id", table_name="scene_plans")
    op.drop_table("scene_plans")
    op.drop_index("ix_voice_presets_workspace_id", table_name="voice_presets")
    op.drop_table("voice_presets")
    op.drop_index("ix_visual_presets_workspace_id", table_name="visual_presets")
    op.drop_table("visual_presets")

    scene_plan_source.drop(op.get_bind(), checkfirst=True)
