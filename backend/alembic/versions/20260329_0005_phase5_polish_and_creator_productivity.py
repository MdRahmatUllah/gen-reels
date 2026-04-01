"""Phase 5 polish and creator productivity schema.

Revision ID: 20260329_0005
Revises: 20260329_0004
Create Date: 2026-03-29 22:00:00
"""

from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa

from app.db.types import GUID, json_type


revision = "20260329_0005"
down_revision = "20260329_0004"
branch_labels = None
depends_on = None


DEFAULT_SUBTITLE_STYLE_PROFILE = json.dumps(
    {
        "preset": "clean_bold",
        "burn_in": False,
        "font_family": "Montserrat SemiBold",
        "font_size": 56,
        "max_width_pct": 82,
        "alignment": "center",
        "placement": {"x_pct": 50, "y_pct": 82},
        "text_color": "#FFFFFF",
        "stroke_color": "#101010",
        "stroke_width": 3,
        "shadow_strength": 0.45,
    }
)
DEFAULT_EXPORT_PROFILE = json.dumps(
    {
        "format": "mp4",
        "container": "mp4",
        "video_codec": "h264",
        "audio_codec": "aac",
        "resolution": {"width": 1080, "height": 1920},
        "frame_rate": 24,
        "video_bitrate_kbps": 8000,
        "caption_burn_in": False,
    }
)
DEFAULT_AUDIO_MIX_PROFILE = json.dumps(
    {
        "music_enabled": False,
        "music_source": "generated_or_curated",
        "music_gain_db": -20.0,
        "ducking_gain_db": -12.0,
        "ducking_fade_seconds": 0.3,
        "music_fade_out_seconds": 1.5,
        "target_lufs": -14.0,
        "true_peak_dbtp": -1.0,
        "crossfade_enabled": True,
        "crossfade_duration_seconds": 0.2,
    }
)


def upgrade() -> None:
    op.create_table(
        "project_templates",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("created_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_project_templates_workspace_id", "project_templates", ["workspace_id"], unique=False)

    op.create_table(
        "template_versions",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("template_id", GUID(), sa.ForeignKey("project_templates.id"), nullable=False),
        sa.Column("source_project_id", GUID(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("created_by_user_id", GUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("snapshot_payload", json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("template_id", "version_number", name="uq_template_version"),
    )
    op.create_index("ix_template_versions_template_id", "template_versions", ["template_id"], unique=False)

    op.create_table(
        "prompt_history_entries",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("workspace_id", GUID(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("project_id", GUID(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("scene_plan_id", GUID(), sa.ForeignKey("scene_plans.id"), nullable=True),
        sa.Column("scene_segment_id", GUID(), sa.ForeignKey("scene_segments.id"), nullable=True),
        sa.Column("render_job_id", GUID(), sa.ForeignKey("render_jobs.id"), nullable=True),
        sa.Column("render_step_id", GUID(), sa.ForeignKey("render_steps.id"), nullable=True),
        sa.Column("provider_run_id", GUID(), sa.ForeignKey("provider_runs.id"), nullable=True),
        sa.Column("asset_id", GUID(), sa.ForeignKey("assets.id"), nullable=True),
        sa.Column("export_id", GUID(), sa.ForeignKey("exports.id"), nullable=True),
        sa.Column("prompt_role", sa.String(length=64), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("source_asset_id", GUID(), sa.ForeignKey("assets.id"), nullable=True),
        sa.Column(
            "source_prompt_history_id",
            GUID(),
            sa.ForeignKey("prompt_history_entries.id"),
            nullable=True,
        ),
        sa.Column("metadata_payload", json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_prompt_history_entries_workspace_id", "prompt_history_entries", ["workspace_id"], unique=False)
    op.create_index("ix_prompt_history_entries_project_id", "prompt_history_entries", ["project_id"], unique=False)
    op.create_index(
        "ix_prompt_history_entries_scene_segment_id",
        "prompt_history_entries",
        ["scene_segment_id"],
        unique=False,
    )
    op.create_index("ix_prompt_history_entries_asset_id", "prompt_history_entries", ["asset_id"], unique=False)
    op.create_index("ix_prompt_history_entries_export_id", "prompt_history_entries", ["export_id"], unique=False)

    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("source_template_version_id", GUID(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "subtitle_style_profile",
                json_type(),
                nullable=False,
                server_default=DEFAULT_SUBTITLE_STYLE_PROFILE,
            )
        )
        batch_op.add_column(
            sa.Column(
                "export_profile",
                json_type(),
                nullable=False,
                server_default=DEFAULT_EXPORT_PROFILE,
            )
        )
        batch_op.add_column(
            sa.Column(
                "audio_mix_profile",
                json_type(),
                nullable=False,
                server_default=DEFAULT_AUDIO_MIX_PROFILE,
            )
        )
        batch_op.create_foreign_key(
            "fk_projects_source_template_version_id",
            "template_versions",
            ["source_template_version_id"],
            ["id"],
        )

    with op.batch_alter_table("assets") as batch_op:
        batch_op.add_column(sa.Column("library_label", sa.String(length=255), nullable=True))
        batch_op.add_column(
            sa.Column("is_library_asset", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(sa.Column("is_reusable", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("reused_from_asset_id", GUID(), nullable=True))
        batch_op.add_column(sa.Column("continuity_score", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("reuse_count", sa.Integer(), nullable=False, server_default="0"))
        batch_op.create_foreign_key(
            "fk_assets_reused_from_asset_id",
            "assets",
            ["reused_from_asset_id"],
            ["id"],
        )

    with op.batch_alter_table("exports") as batch_op:
        batch_op.add_column(
            sa.Column(
                "subtitle_style_profile",
                json_type(),
                nullable=False,
                server_default=DEFAULT_SUBTITLE_STYLE_PROFILE,
            )
        )
        batch_op.add_column(
            sa.Column(
                "export_profile",
                json_type(),
                nullable=False,
                server_default=DEFAULT_EXPORT_PROFILE,
            )
        )
        batch_op.add_column(
            sa.Column(
                "audio_mix_profile",
                json_type(),
                nullable=False,
                server_default=DEFAULT_AUDIO_MIX_PROFILE,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("exports") as batch_op:
        batch_op.drop_column("audio_mix_profile")
        batch_op.drop_column("export_profile")
        batch_op.drop_column("subtitle_style_profile")

    with op.batch_alter_table("assets") as batch_op:
        batch_op.drop_constraint("fk_assets_reused_from_asset_id", type_="foreignkey")
        batch_op.drop_column("reuse_count")
        batch_op.drop_column("continuity_score")
        batch_op.drop_column("reused_from_asset_id")
        batch_op.drop_column("is_reusable")
        batch_op.drop_column("is_library_asset")
        batch_op.drop_column("library_label")

    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_constraint("fk_projects_source_template_version_id", type_="foreignkey")
        batch_op.drop_column("audio_mix_profile")
        batch_op.drop_column("export_profile")
        batch_op.drop_column("subtitle_style_profile")
        batch_op.drop_column("source_template_version_id")

    op.drop_index("ix_prompt_history_entries_export_id", table_name="prompt_history_entries")
    op.drop_index("ix_prompt_history_entries_asset_id", table_name="prompt_history_entries")
    op.drop_index("ix_prompt_history_entries_scene_segment_id", table_name="prompt_history_entries")
    op.drop_index("ix_prompt_history_entries_project_id", table_name="prompt_history_entries")
    op.drop_index("ix_prompt_history_entries_workspace_id", table_name="prompt_history_entries")
    op.drop_table("prompt_history_entries")

    op.drop_index("ix_template_versions_template_id", table_name="template_versions")
    op.drop_table("template_versions")

    op.drop_index("ix_project_templates_workspace_id", table_name="project_templates")
    op.drop_table("project_templates")
