"""Phase 3 render MVP schema.

Revision ID: 20260329_0003
Revises: 20260329_0002
Create Date: 2026-03-29 13:30:00
"""

from alembic import op
import sqlalchemy as sa

from app.db.types import GUID, json_type


revision = "20260329_0003"
down_revision = "20260329_0002"
branch_labels = None
depends_on = None


asset_type = sa.Enum(
    "image",
    "video_clip",
    "narration",
    "music",
    "subtitle",
    "export",
    "reference_image",
    "upload",
    name="asset_type",
    create_type=False,
)
asset_role = sa.Enum(
    "scene_start_frame",
    "scene_end_frame",
    "continuity_anchor",
    "raw_video_clip",
    "silent_video_clip",
    "retimed_video_clip",
    "narration_track",
    "music_bed",
    "subtitle_file",
    "final_export",
    name="asset_role",
    create_type=False,
)


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if _is_postgresql():
        op.execute("ALTER TYPE job_kind ADD VALUE IF NOT EXISTS 'render_generation'")
        op.execute("ALTER TYPE step_kind ADD VALUE IF NOT EXISTS 'frame_pair_generation'")
        op.execute("ALTER TYPE step_kind ADD VALUE IF NOT EXISTS 'video_generation'")
        op.execute("ALTER TYPE step_kind ADD VALUE IF NOT EXISTS 'audio_normalization'")
        op.execute("ALTER TYPE step_kind ADD VALUE IF NOT EXISTS 'narration_generation'")
        op.execute("ALTER TYPE step_kind ADD VALUE IF NOT EXISTS 'music_preparation'")
        op.execute("ALTER TYPE step_kind ADD VALUE IF NOT EXISTS 'subtitle_generation'")
        op.execute("ALTER TYPE step_kind ADD VALUE IF NOT EXISTS 'clip_retime'")
        op.execute("ALTER TYPE step_kind ADD VALUE IF NOT EXISTS 'composition'")

    with op.batch_alter_table("render_jobs") as batch_op:
        batch_op.add_column(sa.Column("script_version_id", GUID(), nullable=True))
        batch_op.add_column(sa.Column("scene_plan_id", GUID(), nullable=True))
        batch_op.add_column(sa.Column("consistency_pack_id", GUID(), nullable=True))
        batch_op.add_column(sa.Column("voice_preset_id", GUID(), nullable=True))
        batch_op.add_column(
            sa.Column("allow_export_without_music", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch_op.add_column(sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key(
            "fk_render_jobs_script_version_id", "script_versions", ["script_version_id"], ["id"]
        )
        batch_op.create_foreign_key(
            "fk_render_jobs_scene_plan_id", "scene_plans", ["scene_plan_id"], ["id"]
        )
        batch_op.create_foreign_key(
            "fk_render_jobs_consistency_pack_id",
            "consistency_packs",
            ["consistency_pack_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_render_jobs_voice_preset_id", "voice_presets", ["voice_preset_id"], ["id"]
        )

    with op.batch_alter_table("render_steps") as batch_op:
        batch_op.add_column(sa.Column("scene_segment_id", GUID(), nullable=True))
        batch_op.add_column(sa.Column("is_stale", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.create_foreign_key(
            "fk_render_steps_scene_segment_id", "scene_segments", ["scene_segment_id"], ["id"]
        )

    op.create_table(
        "assets",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("project_id", GUID(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("render_job_id", GUID(), sa.ForeignKey("render_jobs.id"), nullable=True),
        sa.Column("render_step_id", GUID(), sa.ForeignKey("render_steps.id"), nullable=True),
        sa.Column("scene_segment_id", GUID(), sa.ForeignKey("scene_segments.id"), nullable=True),
        sa.Column("parent_asset_id", GUID(), sa.ForeignKey("assets.id"), nullable=True),
        sa.Column("provider_run_id", GUID(), sa.ForeignKey("provider_runs.id"), nullable=True),
        sa.Column(
            "consistency_pack_snapshot_id",
            GUID(),
            sa.ForeignKey("consistency_packs.id"),
            nullable=True,
        ),
        sa.Column("asset_type", asset_type, nullable=False),
        sa.Column("asset_role", asset_role, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="completed"),
        sa.Column("bucket_name", sa.String(length=255), nullable=False),
        sa.Column("object_name", sa.String(length=1024), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("frame_rate", sa.Float(), nullable=True),
        sa.Column("has_audio_stream", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "source_audio_policy",
            sa.String(length=32),
            nullable=False,
            server_default="request_silent",
        ),
        sa.Column(
            "timing_alignment_strategy",
            sa.String(length=32),
            nullable=False,
            server_default="none",
        ),
        sa.Column("metadata_payload", json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_assets_project_id", "assets", ["project_id"], unique=False)
    op.create_index("ix_assets_object_name", "assets", ["object_name"], unique=True)

    op.create_table(
        "asset_variants",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("asset_id", GUID(), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("variant_asset_id", GUID(), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("variant_kind", sa.String(length=64), nullable=False),
        sa.Column("metadata_payload", json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_asset_variants_asset_id", "asset_variants", ["asset_id"], unique=False)

    op.create_table(
        "exports",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("project_id", GUID(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("render_job_id", GUID(), sa.ForeignKey("render_jobs.id"), nullable=False),
        sa.Column("asset_id", GUID(), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="completed"),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("format", sa.String(length=32), nullable=False, server_default="mp4"),
        sa.Column("bucket_name", sa.String(length=255), nullable=False),
        sa.Column("object_name", sa.String(length=1024), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("metadata_payload", json_type(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_exports_project_id", "exports", ["project_id"], unique=False)
    op.create_index("ix_exports_object_name", "exports", ["object_name"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_exports_object_name", table_name="exports")
    op.drop_index("ix_exports_project_id", table_name="exports")
    op.drop_table("exports")
    op.drop_index("ix_asset_variants_asset_id", table_name="asset_variants")
    op.drop_table("asset_variants")
    op.drop_index("ix_assets_object_name", table_name="assets")
    op.drop_index("ix_assets_project_id", table_name="assets")
    op.drop_table("assets")

    with op.batch_alter_table("render_steps") as batch_op:
        batch_op.drop_constraint("fk_render_steps_scene_segment_id", type_="foreignkey")
        batch_op.drop_column("is_stale")
        batch_op.drop_column("scene_segment_id")

    with op.batch_alter_table("render_jobs") as batch_op:
        batch_op.drop_constraint("fk_render_jobs_voice_preset_id", type_="foreignkey")
        batch_op.drop_constraint("fk_render_jobs_consistency_pack_id", type_="foreignkey")
        batch_op.drop_constraint("fk_render_jobs_scene_plan_id", type_="foreignkey")
        batch_op.drop_constraint("fk_render_jobs_script_version_id", type_="foreignkey")
        batch_op.drop_column("cancelled_at")
        batch_op.drop_column("allow_export_without_music")
        batch_op.drop_column("voice_preset_id")
        batch_op.drop_column("consistency_pack_id")
        batch_op.drop_column("scene_plan_id")
        batch_op.drop_column("script_version_id")

    asset_role.drop(op.get_bind(), checkfirst=True)
    asset_type.drop(op.get_bind(), checkfirst=True)
