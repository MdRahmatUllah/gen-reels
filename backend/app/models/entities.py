from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import GUID, json_type


def utcnow() -> datetime:
    return datetime.now(UTC)


class WorkspaceRole(str, enum.Enum):
    admin = "admin"
    member = "member"
    reviewer = "reviewer"
    viewer = "viewer"


class ProjectStage(str, enum.Enum):
    brief = "brief"
    script = "script"
    scenes = "scenes"
    frames = "frames"
    renders = "renders"
    exports = "exports"


class JobStatus(str, enum.Enum):
    draft = "draft"
    queued = "queued"
    running = "running"
    review = "review"
    approved = "approved"
    completed = "completed"
    blocked = "blocked"
    failed = "failed"
    cancelled = "cancelled"


class JobKind(str, enum.Enum):
    project_bootstrap = "project_bootstrap"
    idea_generation = "idea_generation"
    script_generation = "script_generation"
    scene_plan_generation = "scene_plan_generation"
    prompt_pair_generation = "prompt_pair_generation"
    render_generation = "render_generation"


class StepKind(str, enum.Enum):
    brief_generation = "brief_generation"
    idea_generation = "idea_generation"
    script_generation = "script_generation"
    scene_plan_generation = "scene_plan_generation"
    prompt_pair_generation = "prompt_pair_generation"
    frame_pair_generation = "frame_pair_generation"
    video_generation = "video_generation"
    audio_normalization = "audio_normalization"
    narration_generation = "narration_generation"
    music_preparation = "music_preparation"
    subtitle_generation = "subtitle_generation"
    clip_retime = "clip_retime"
    composition = "composition"


class ScriptSource(str, enum.Enum):
    generated = "generated"
    manual = "manual"


class ScenePlanSource(str, enum.Enum):
    generated = "generated"
    manual = "manual"


class IdeaCandidateStatus(str, enum.Enum):
    generated = "generated"
    selected = "selected"
    superseded = "superseded"


class ProviderRunStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class ProviderErrorCategory(str, enum.Enum):
    transient = "transient"
    deterministic_input = "deterministic_input"
    moderation_rejection = "moderation_rejection"
    internal = "internal"


class ExecutionMode(str, enum.Enum):
    hosted = "hosted"
    byo = "byo"
    local = "local"


class LocalWorkerStatus(str, enum.Enum):
    online = "online"
    offline = "offline"
    revoked = "revoked"


class ModerationDecision(str, enum.Enum):
    allowed = "allowed"
    blocked = "blocked"


class ModerationReviewStatus(str, enum.Enum):
    none = "none"
    pending = "pending"
    released = "released"
    rejected = "rejected"


class BrandKitStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    archived = "archived"


class BrandEnforcementMode(str, enum.Enum):
    advisory = "advisory"
    enforced = "enforced"


class ReviewStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"


class ReviewTargetType(str, enum.Enum):
    script_version = "script_version"
    scene_plan = "scene_plan"
    export = "export"
    template_version = "template_version"


class WebhookDeliveryStatus(str, enum.Enum):
    queued = "queued"
    delivered = "delivered"
    failed = "failed"
    exhausted = "exhausted"


class SubscriptionStatus(str, enum.Enum):
    not_configured = "not_configured"
    checkout_pending = "checkout_pending"
    trialing = "trialing"
    active = "active"
    past_due = "past_due"
    cancelled = "cancelled"


class CreditLedgerEntryKind(str, enum.Enum):
    provider_run = "provider_run"
    export_event = "export_event"
    manual_adjustment = "manual_adjustment"
    reconciliation = "reconciliation"


class AssetType(str, enum.Enum):
    image = "image"
    video_clip = "video_clip"
    narration = "narration"
    music = "music"
    subtitle = "subtitle"
    export = "export"
    reference_image = "reference_image"
    upload = "upload"


class AssetRole(str, enum.Enum):
    scene_start_frame = "scene_start_frame"
    scene_end_frame = "scene_end_frame"
    continuity_anchor = "continuity_anchor"
    raw_video_clip = "raw_video_clip"
    silent_video_clip = "silent_video_clip"
    retimed_video_clip = "retimed_video_clip"
    narration_track = "narration_track"
    music_bed = "music_bed"
    subtitle_file = "subtitle_file"
    final_export = "final_export"


class ModerationReportStatus(str, enum.Enum):
    pending = "pending"
    released = "released"
    rejected = "rejected"
    passed = "passed"


class WorkspaceAuthProviderType(str, enum.Enum):
    oidc = "oidc"
    saml = "saml"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(sa.String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(sa.String(255))
    password_hash: Mapped[str] = mapped_column(sa.String(255))
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)


class Workspace(Base, TimestampMixin):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(sa.String(255))
    slug: Mapped[str] = mapped_column(sa.String(255), unique=True, index=True)
    plan_name: Mapped[str] = mapped_column(sa.String(100), default="Studio", nullable=False)
    seats: Mapped[int] = mapped_column(sa.Integer, default=1, nullable=False)
    credits_remaining: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    credits_reserved: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    credits_total: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    monthly_budget_cents: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)


class WorkspaceMember(Base, TimestampMixin):
    __tablename__ = "workspace_members"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[WorkspaceRole] = mapped_column(sa.Enum(WorkspaceRole), nullable=False)
    is_default: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)


class SessionRecord(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    active_workspace_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workspaces.id"))
    refresh_token_hash: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(sa.String(512))
    ip_address: Mapped[str | None] = mapped_column(sa.String(64))
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=utcnow)
    last_used_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    source_template_version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("template_versions.id"))
    brand_kit_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("brand_kits.id"))
    active_brief_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("project_briefs.id"))
    selected_idea_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("idea_candidates.id"))
    active_script_version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("script_versions.id"))
    active_scene_plan_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("scene_plans.id"))
    default_visual_preset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("visual_presets.id"))
    default_voice_preset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("voice_presets.id"))
    title: Mapped[str] = mapped_column(sa.String(255))
    client: Mapped[str | None] = mapped_column(sa.String(255))
    aspect_ratio: Mapped[str] = mapped_column(sa.String(20), default="9:16", nullable=False)
    duration_target_sec: Mapped[int] = mapped_column(sa.Integer, default=90, nullable=False)
    subtitle_style_profile: Mapped[dict[str, object]] = mapped_column(
        json_type(), default=dict, nullable=False
    )
    export_profile: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)
    audio_mix_profile: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)
    stage: Mapped[ProjectStage] = mapped_column(
        sa.Enum(ProjectStage), default=ProjectStage.brief, nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))


class ProjectBrief(Base):
    __tablename__ = "project_briefs"
    __table_args__ = (UniqueConstraint("project_id", "version_number", name="uq_project_brief_version"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    objective: Mapped[str] = mapped_column(sa.Text, nullable=False)
    hook: Mapped[str] = mapped_column(sa.Text, nullable=False)
    target_audience: Mapped[str] = mapped_column(sa.Text, nullable=False)
    call_to_action: Mapped[str] = mapped_column(sa.Text, nullable=False)
    brand_north_star: Mapped[str] = mapped_column(sa.Text, nullable=False)
    guardrails: Mapped[list[str]] = mapped_column(json_type(), default=list, nullable=False)
    must_include: Mapped[list[str]] = mapped_column(json_type(), default=list, nullable=False)
    approval_steps: Mapped[list[str]] = mapped_column(json_type(), default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=utcnow)


class IdeaSet(Base):
    __tablename__ = "idea_sets"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    source_brief_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("project_briefs.id"), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    prompt_input: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=utcnow)


class IdeaCandidate(Base):
    __tablename__ = "idea_candidates"
    __table_args__ = (
        UniqueConstraint("idea_set_id", "order_index", name="uq_idea_candidate_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    idea_set_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("idea_sets.id"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    hook: Mapped[str] = mapped_column(sa.Text, nullable=False)
    summary: Mapped[str] = mapped_column(sa.Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(json_type(), default=list, nullable=False)
    order_index: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    status: Mapped[IdeaCandidateStatus] = mapped_column(
        sa.Enum(IdeaCandidateStatus), default=IdeaCandidateStatus.generated, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=utcnow)


class ScriptVersion(Base):
    __tablename__ = "script_versions"
    __table_args__ = (UniqueConstraint("project_id", "version_number", name="uq_script_version"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    based_on_idea_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("idea_candidates.id"))
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("script_versions.id"))
    version_number: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    version: Mapped[int] = mapped_column(sa.Integer, default=1, nullable=False)
    source_type: Mapped[ScriptSource] = mapped_column(sa.Enum(ScriptSource), nullable=False)
    approval_state: Mapped[str] = mapped_column(sa.String(64), default="draft", nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    total_words: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    estimated_duration_seconds: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    reading_time_label: Mapped[str] = mapped_column(sa.String(64), default="0s draft", nullable=False)
    lines: Mapped[list[dict[str, object]]] = mapped_column(json_type(), default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=utcnow)


class VisualPreset(Base, TimestampMixin):
    __tablename__ = "visual_presets"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(sa.Integer, default=1, nullable=False)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[str] = mapped_column(sa.Text, nullable=False)
    prompt_prefix: Mapped[str] = mapped_column(sa.Text, default="", nullable=False)
    style_descriptor: Mapped[str] = mapped_column(sa.Text, default="", nullable=False)
    negative_prompt: Mapped[str] = mapped_column(sa.Text, default="", nullable=False)
    camera_defaults: Mapped[str] = mapped_column(sa.Text, default="", nullable=False)
    color_palette: Mapped[str] = mapped_column(sa.String(255), default="", nullable=False)
    reference_notes: Mapped[str] = mapped_column(sa.Text, default="", nullable=False)
    is_archived: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)


class VoicePreset(Base, TimestampMixin):
    __tablename__ = "voice_presets"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(sa.Integer, default=1, nullable=False)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[str] = mapped_column(sa.Text, nullable=False)
    provider_voice: Mapped[str] = mapped_column(sa.String(255), default="", nullable=False)
    tone_descriptor: Mapped[str] = mapped_column(sa.Text, default="", nullable=False)
    language_code: Mapped[str] = mapped_column(sa.String(32), default="en-US", nullable=False)
    pace_multiplier: Mapped[float] = mapped_column(sa.Float, default=1.0, nullable=False)
    is_archived: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)


class ScenePlan(Base, TimestampMixin):
    __tablename__ = "scene_plans"
    __table_args__ = (UniqueConstraint("project_id", "version_number", name="uq_scene_plan_version"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    based_on_script_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("script_versions.id"), nullable=False
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    visual_preset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("visual_presets.id"))
    voice_preset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("voice_presets.id"))
    consistency_pack_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("consistency_packs.id"))
    parent_scene_plan_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("scene_plans.id"))
    version_number: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    version: Mapped[int] = mapped_column(sa.Integer, default=1, nullable=False)
    source_type: Mapped[ScenePlanSource] = mapped_column(sa.Enum(ScenePlanSource), nullable=False)
    approval_state: Mapped[str] = mapped_column(sa.String(64), default="draft", nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    total_estimated_duration_seconds: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    scene_count: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    validation_warnings: Mapped[list[dict[str, object]]] = mapped_column(
        json_type(), default=list, nullable=False
    )


class SceneSegment(Base, TimestampMixin):
    __tablename__ = "scene_segments"
    __table_args__ = (UniqueConstraint("scene_plan_id", "scene_index", name="uq_scene_segment_index"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    scene_plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scene_plans.id"), nullable=False, index=True)
    scene_index: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    source_line_ids: Mapped[list[str]] = mapped_column(json_type(), default=list, nullable=False)
    title: Mapped[str] = mapped_column(sa.String(255), default="", nullable=False)
    beat: Mapped[str] = mapped_column(sa.Text, default="", nullable=False)
    narration_text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    caption_text: Mapped[str] = mapped_column(sa.Text, default="", nullable=False)
    visual_direction: Mapped[str] = mapped_column(sa.Text, default="", nullable=False)
    shot_type: Mapped[str] = mapped_column(sa.String(128), default="", nullable=False)
    motion: Mapped[str] = mapped_column(sa.String(255), default="", nullable=False)
    target_duration_seconds: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    estimated_voice_duration_seconds: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    actual_voice_duration_seconds: Mapped[int | None] = mapped_column(sa.Integer)
    visual_prompt: Mapped[str] = mapped_column(sa.Text, default="", nullable=False)
    start_image_prompt: Mapped[str] = mapped_column(sa.Text, default="", nullable=False)
    end_image_prompt: Mapped[str] = mapped_column(sa.Text, default="", nullable=False)
    transition_mode: Mapped[str] = mapped_column(sa.String(32), default="hard_cut", nullable=False)
    notes: Mapped[list[str]] = mapped_column(json_type(), default=list, nullable=False)
    validation_warnings: Mapped[list[dict[str, object]]] = mapped_column(
        json_type(), default=list, nullable=False
    )
    chained_from_asset_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    start_image_asset_id: Mapped[uuid.UUID | None] = mapped_column(GUID())
    end_image_asset_id: Mapped[uuid.UUID | None] = mapped_column(GUID())


class RenderJob(Base, TimestampMixin):
    __tablename__ = "render_jobs"
    __table_args__ = (
        UniqueConstraint(
            "created_by_user_id",
            "project_id",
            "job_kind",
            "idempotency_key",
            name="uq_render_job_idempotency",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    script_version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("script_versions.id"))
    scene_plan_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("scene_plans.id"))
    consistency_pack_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("consistency_packs.id"))
    voice_preset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("voice_presets.id"))
    job_kind: Mapped[JobKind] = mapped_column(sa.Enum(JobKind), nullable=False)
    queue_name: Mapped[str] = mapped_column(sa.String(64), default="planning", nullable=False)
    status: Mapped[JobStatus] = mapped_column(sa.Enum(JobStatus), default=JobStatus.queued)
    idempotency_key: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)
    allow_export_without_music: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    reserved_credits: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    error_code: Mapped[str | None] = mapped_column(sa.String(64))
    error_message: Mapped[str | None] = mapped_column(sa.Text)
    retry_count: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))


class RenderStep(Base, TimestampMixin):
    __tablename__ = "render_steps"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    render_job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("render_jobs.id"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    scene_segment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("scene_segments.id"))
    step_kind: Mapped[StepKind] = mapped_column(sa.Enum(StepKind), nullable=False)
    step_index: Mapped[int] = mapped_column(sa.Integer, default=1, nullable=False)
    status: Mapped[JobStatus] = mapped_column(sa.Enum(JobStatus), default=JobStatus.queued)
    is_stale: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    retry_count: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    retry_history: Mapped[list[dict[str, object]]] = mapped_column(json_type(), default=list, nullable=False)
    recovery_source_step_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("render_steps.id"))
    checkpoint_payload: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)
    last_checkpoint_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    input_payload: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)
    output_payload: Mapped[dict[str, object] | None] = mapped_column(json_type())
    error_code: Mapped[str | None] = mapped_column(sa.String(64))
    error_message: Mapped[str | None] = mapped_column(sa.Text)
    started_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))


class Asset(Base, TimestampMixin):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    render_job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("render_jobs.id"))
    render_step_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("render_steps.id"))
    scene_segment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("scene_segments.id"))
    parent_asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assets.id"))
    provider_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("provider_runs.id"))
    consistency_pack_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("consistency_packs.id")
    )
    asset_type: Mapped[AssetType] = mapped_column(sa.Enum(AssetType), nullable=False)
    asset_role: Mapped[AssetRole] = mapped_column(sa.Enum(AssetRole), nullable=False)
    status: Mapped[str] = mapped_column(sa.String(32), default="completed", nullable=False)
    bucket_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    object_name: Mapped[str] = mapped_column(sa.String(1024), nullable=False, unique=True)
    file_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(sa.Integer)
    width: Mapped[int | None] = mapped_column(sa.Integer)
    height: Mapped[int | None] = mapped_column(sa.Integer)
    frame_rate: Mapped[float | None] = mapped_column(sa.Float)
    library_label: Mapped[str | None] = mapped_column(sa.String(255))
    is_library_asset: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    is_reusable: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    reused_from_asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assets.id"))
    continuity_score: Mapped[float | None] = mapped_column(sa.Float)
    reuse_count: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    quarantine_bucket_name: Mapped[str | None] = mapped_column(sa.String(255))
    quarantine_object_name: Mapped[str | None] = mapped_column(sa.String(1024))
    quarantined_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    released_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    has_audio_stream: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    source_audio_policy: Mapped[str] = mapped_column(
        sa.String(32), default="request_silent", nullable=False
    )
    timing_alignment_strategy: Mapped[str] = mapped_column(
        sa.String(32), default="none", nullable=False
    )
    metadata_payload: Mapped[dict[str, object]] = mapped_column(
        json_type(), default=dict, nullable=False
    )


class AssetVariant(Base):
    __tablename__ = "asset_variants"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assets.id"), nullable=False, index=True)
    variant_asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assets.id"), nullable=False)
    variant_kind: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    metadata_payload: Mapped[dict[str, object]] = mapped_column(
        json_type(), default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=utcnow)


class ExportRecord(Base, TimestampMixin):
    __tablename__ = "exports"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    render_job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("render_jobs.id"), nullable=False)
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assets.id"), nullable=False)
    status: Mapped[str] = mapped_column(sa.String(32), default="completed", nullable=False)
    file_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    format: Mapped[str] = mapped_column(sa.String(32), default="mp4", nullable=False)
    bucket_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    object_name: Mapped[str] = mapped_column(sa.String(1024), nullable=False, unique=True)
    duration_ms: Mapped[int | None] = mapped_column(sa.Integer)
    availability_status: Mapped[str] = mapped_column(
        sa.String(32), default="available", nullable=False
    )
    held_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    available_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    subtitle_style_profile: Mapped[dict[str, object]] = mapped_column(
        json_type(), default=dict, nullable=False
    )
    export_profile: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)
    audio_mix_profile: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)
    metadata_payload: Mapped[dict[str, object]] = mapped_column(
        json_type(), default=dict, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))


class ProviderRun(Base):
    __tablename__ = "provider_runs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    render_job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("render_jobs.id"))
    render_step_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("render_steps.id"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"))
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workspaces.id"))
    execution_mode: Mapped[ExecutionMode] = mapped_column(
        sa.Enum(ExecutionMode), default=ExecutionMode.hosted, nullable=False
    )
    worker_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("local_workers.id"))
    provider_credential_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workspace_provider_credentials.id")
    )
    provider_name: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    provider_model: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    operation: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    status: Mapped[ProviderRunStatus] = mapped_column(
        sa.Enum(ProviderRunStatus), default=ProviderRunStatus.queued, nullable=False
    )
    request_payload: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)
    response_payload: Mapped[dict[str, object] | None] = mapped_column(json_type())
    latency_ms: Mapped[int | None] = mapped_column(sa.Integer)
    external_request_id: Mapped[str | None] = mapped_column(sa.String(255))
    normalized_cost_cents: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(sa.String(8), default="USD", nullable=False)
    billable_quantity: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    continuity_mode: Mapped[str | None] = mapped_column(sa.String(64))
    error_category: Mapped[ProviderErrorCategory | None] = mapped_column(
        sa.Enum(ProviderErrorCategory)
    )
    error_code: Mapped[str | None] = mapped_column(sa.String(64))
    error_message: Mapped[str | None] = mapped_column(sa.Text)
    cost_payload: Mapped[dict[str, object] | None] = mapped_column(json_type())
    routing_decision_payload: Mapped[dict[str, object]] = mapped_column(
        json_type(), default=dict, nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))


class ModerationEvent(Base):
    __tablename__ = "moderation_events"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"), index=True)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workspaces.id"), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    related_asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assets.id"), index=True)
    target_type: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    target_id: Mapped[str | None] = mapped_column(sa.String(64))
    input_text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    decision: Mapped[ModerationDecision] = mapped_column(sa.Enum(ModerationDecision), nullable=False)
    review_status: Mapped[ModerationReviewStatus] = mapped_column(
        sa.Enum(ModerationReviewStatus),
        default=ModerationReviewStatus.none,
        nullable=False,
    )
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    review_notes: Mapped[str | None] = mapped_column(sa.Text)
    provider_name: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    severity_summary: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)
    response_payload: Mapped[dict[str, object] | None] = mapped_column(json_type())
    blocked_message: Mapped[str | None] = mapped_column(sa.Text)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=utcnow)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(sa.String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workspaces.id"), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    event_type: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    target_type: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    target_id: Mapped[str | None] = mapped_column(sa.String(64))
    payload: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=utcnow)


class RenderEvent(Base):
    __tablename__ = "render_events"
    __table_args__ = (
        UniqueConstraint("render_job_id", "sequence_number", name="uq_render_event_sequence"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    render_job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("render_jobs.id"), nullable=False, index=True)
    render_step_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("render_steps.id"))
    sequence_number: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    target_type: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    target_id: Mapped[str | None] = mapped_column(sa.String(64))
    payload: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=utcnow)


class ModerationReport(Base, TimestampMixin):
    __tablename__ = "moderation_reports"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"), index=True)
    render_job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("render_jobs.id"), index=True)
    export_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("exports.id"), index=True)
    related_asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assets.id"), index=True)
    status: Mapped[ModerationReportStatus] = mapped_column(
        sa.Enum(ModerationReportStatus),
        default=ModerationReportStatus.pending,
        nullable=False,
    )
    sample_reason: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    provider_name: Mapped[str] = mapped_column(sa.String(128), default="azure_content_safety", nullable=False)
    blocked_event_count_30d: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    findings_payload: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    review_notes: Mapped[str | None] = mapped_column(sa.Text)


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"
    __table_args__ = (UniqueConstraint("workspace_id", name="uq_subscription_workspace"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    provider_name: Mapped[str] = mapped_column(sa.String(128), default="stub_billing", nullable=False)
    provider_customer_id: Mapped[str | None] = mapped_column(sa.String(255))
    provider_subscription_id: Mapped[str | None] = mapped_column(sa.String(255))
    plan_name: Mapped[str] = mapped_column(sa.String(100), default="Studio", nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(
        sa.Enum(SubscriptionStatus),
        default=SubscriptionStatus.not_configured,
        nullable=False,
    )
    monthly_credit_allowance: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    current_period_start_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    current_period_end_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    metadata_payload: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)


class Plan(Base, TimestampMixin):
    __tablename__ = "plans"
    __table_args__ = (UniqueConstraint("slug", name="uq_plan_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    monthly_credit_allowance: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    monthly_render_limit: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    max_concurrent_renders: Mapped[int] = mapped_column(sa.Integer, default=1, nullable=False)
    max_scenes_per_render: Mapped[int] = mapped_column(sa.Integer, default=12, nullable=False)
    metadata_payload: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)


class ProjectTemplate(Base, TimestampMixin):
    __tablename__ = "project_templates"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(sa.Integer, default=1, nullable=False)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[str] = mapped_column(sa.Text, default="", nullable=False)
    is_archived: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)


class TemplateVersion(Base):
    __tablename__ = "template_versions"
    __table_args__ = (UniqueConstraint("template_id", "version_number", name="uq_template_version"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("project_templates.id"), nullable=False, index=True)
    source_project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"))
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    version_number: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    snapshot_payload: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=utcnow)


class CreditLedgerEntry(Base):
    __tablename__ = "credit_ledger_entries"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_credit_ledger_idempotency_key"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"), index=True)
    render_job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("render_jobs.id"), index=True)
    render_step_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("render_steps.id"))
    provider_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("provider_runs.id"), index=True)
    export_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("exports.id"), index=True)
    kind: Mapped[CreditLedgerEntryKind] = mapped_column(sa.Enum(CreditLedgerEntryKind), nullable=False)
    billable_unit: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    quantity: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    credits_delta: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    amount_cents: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(sa.String(8), default="USD", nullable=False)
    balance_after: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    metadata_payload: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=utcnow)


class PromptHistoryEntry(Base):
    __tablename__ = "prompt_history_entries"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"), index=True)
    scene_plan_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("scene_plans.id"))
    scene_segment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("scene_segments.id"), index=True)
    render_job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("render_jobs.id"))
    render_step_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("render_steps.id"))
    provider_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("provider_runs.id"))
    asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assets.id"), index=True)
    export_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("exports.id"), index=True)
    prompt_role: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    prompt_text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    source_asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("assets.id"))
    source_prompt_history_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("prompt_history_entries.id"))
    metadata_payload: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=utcnow)


class ConsistencyPack(Base):
    __tablename__ = "consistency_packs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"))
    version_number: Mapped[int] = mapped_column(sa.Integer, default=1, nullable=False)
    state: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=utcnow)


class BrandKit(Base, TimestampMixin):
    __tablename__ = "brand_kits"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    default_visual_preset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("visual_presets.id"))
    default_voice_preset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("voice_presets.id"))
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[str] = mapped_column(sa.Text, default="", nullable=False)
    version: Mapped[int] = mapped_column(sa.Integer, default=1, nullable=False)
    status: Mapped[BrandKitStatus] = mapped_column(
        sa.Enum(BrandKitStatus),
        default=BrandKitStatus.active,
        nullable=False,
    )
    enforcement_mode: Mapped[BrandEnforcementMode] = mapped_column(
        sa.Enum(BrandEnforcementMode),
        default=BrandEnforcementMode.advisory,
        nullable=False,
    )
    is_default: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    required_terms: Mapped[list[str]] = mapped_column(json_type(), default=list, nullable=False)
    banned_terms: Mapped[list[str]] = mapped_column(json_type(), default=list, nullable=False)
    subtitle_style_override: Mapped[dict[str, object]] = mapped_column(
        json_type(), default=dict, nullable=False
    )
    export_profile_override: Mapped[dict[str, object]] = mapped_column(
        json_type(), default=dict, nullable=False
    )
    audio_mix_profile_override: Mapped[dict[str, object]] = mapped_column(
        json_type(), default=dict, nullable=False
    )
    brand_rules: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)


class Comment(Base, TimestampMixin):
    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"), index=True)
    target_type: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    author_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(sa.Text, nullable=False)
    metadata_payload: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))


class ReviewRequest(Base, TimestampMixin):
    __tablename__ = "review_requests"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"), index=True)
    target_type: Mapped[ReviewTargetType] = mapped_column(sa.Enum(ReviewTargetType), nullable=False)
    target_id: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    requested_version: Mapped[int | None] = mapped_column(sa.Integer)
    status: Mapped[ReviewStatus] = mapped_column(
        sa.Enum(ReviewStatus),
        default=ReviewStatus.pending,
        nullable=False,
    )
    request_notes: Mapped[str] = mapped_column(sa.Text, default="", nullable=False)
    decision_notes: Mapped[str | None] = mapped_column(sa.Text)
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))


class NotificationPreference(Base, TimestampMixin):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_notification_preference_user_workspace"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    render_email_enabled: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    review_email_enabled: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    membership_email_enabled: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    moderation_email_enabled: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    planning_email_enabled: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)


class NotificationEvent(Base):
    __tablename__ = "notification_events"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"), index=True)
    render_job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("render_jobs.id"), index=True)
    review_request_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("review_requests.id"))
    event_type: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    title: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    body: Mapped[str] = mapped_column(sa.Text, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)
    email_delivery_status: Mapped[str | None] = mapped_column(sa.String(32))
    email_error_message: Mapped[str | None] = mapped_column(sa.Text)
    read_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=utcnow)


class WorkspaceApiKey(Base):
    __tablename__ = "workspace_api_keys"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    role_scope: Mapped[WorkspaceRole] = mapped_column(sa.Enum(WorkspaceRole), nullable=False)
    key_prefix: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    key_hash: Mapped[str] = mapped_column(sa.String(128), nullable=False, unique=True)
    last_used_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=utcnow)


class WorkspaceProviderCredential(Base, TimestampMixin):
    __tablename__ = "workspace_provider_credentials"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    modality: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    provider_key: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    public_config: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)
    secret_payload_encrypted: Mapped[str] = mapped_column(sa.Text, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))


class WorkspaceAuthConfiguration(Base, TimestampMixin):
    __tablename__ = "workspace_auth_configurations"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    provider_type: Mapped[WorkspaceAuthProviderType] = mapped_column(
        sa.Enum(WorkspaceAuthProviderType), nullable=False
    )
    display_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    config_public: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)
    secret_payload_encrypted: Mapped[str] = mapped_column(sa.Text, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    last_validated_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    last_validation_error: Mapped[str | None] = mapped_column(sa.Text)


class LocalWorker(Base, TimestampMixin):
    __tablename__ = "local_workers"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    registered_by_api_key_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workspace_api_keys.id"))
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    status: Mapped[LocalWorkerStatus] = mapped_column(
        sa.Enum(LocalWorkerStatus), default=LocalWorkerStatus.online, nullable=False
    )
    worker_token_hash: Mapped[str] = mapped_column(sa.String(128), nullable=False, unique=True)
    token_prefix: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    supports_ordered_reference_images: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, nullable=False
    )
    supports_first_last_frame_video: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, nullable=False
    )
    supports_tts: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    supports_clip_retime: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    metadata_payload: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    last_polled_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    last_job_claimed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    last_error_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(sa.String(64))
    last_error_message: Mapped[str | None] = mapped_column(sa.Text)
    revoked_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))


class WorkspaceExecutionPolicy(Base, TimestampMixin):
    __tablename__ = "workspace_execution_policies"
    __table_args__ = (UniqueConstraint("workspace_id", name="uq_workspace_execution_policy_workspace"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    text_mode: Mapped[ExecutionMode] = mapped_column(
        sa.Enum(ExecutionMode), default=ExecutionMode.hosted, nullable=False
    )
    text_provider_key: Mapped[str] = mapped_column(sa.String(128), default="azure_openai_text", nullable=False)
    text_credential_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workspace_provider_credentials.id")
    )
    moderation_mode: Mapped[ExecutionMode] = mapped_column(
        sa.Enum(ExecutionMode), default=ExecutionMode.hosted, nullable=False
    )
    moderation_provider_key: Mapped[str] = mapped_column(
        sa.String(128), default="azure_content_safety", nullable=False
    )
    moderation_credential_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workspace_provider_credentials.id")
    )
    image_mode: Mapped[ExecutionMode] = mapped_column(
        sa.Enum(ExecutionMode), default=ExecutionMode.hosted, nullable=False
    )
    image_provider_key: Mapped[str] = mapped_column(
        sa.String(128), default="azure_openai_image", nullable=False
    )
    image_credential_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workspace_provider_credentials.id")
    )
    video_mode: Mapped[ExecutionMode] = mapped_column(
        sa.Enum(ExecutionMode), default=ExecutionMode.hosted, nullable=False
    )
    video_provider_key: Mapped[str] = mapped_column(
        sa.String(128), default="veo_video", nullable=False
    )
    video_credential_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workspace_provider_credentials.id")
    )
    speech_mode: Mapped[ExecutionMode] = mapped_column(
        sa.Enum(ExecutionMode), default=ExecutionMode.hosted, nullable=False
    )
    speech_provider_key: Mapped[str] = mapped_column(
        sa.String(128), default="azure_openai_speech", nullable=False
    )
    speech_credential_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workspace_provider_credentials.id")
    )
    preferred_local_worker_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("local_workers.id"))
    pause_render_generation: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    pause_image_generation: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    pause_video_generation: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    pause_audio_generation: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    pause_reason: Mapped[str | None] = mapped_column(sa.Text)


class LocalWorkerHeartbeat(Base):
    __tablename__ = "local_worker_heartbeats"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    worker_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("local_workers.id"), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    status: Mapped[LocalWorkerStatus] = mapped_column(sa.Enum(LocalWorkerStatus), nullable=False)
    metadata_payload: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=utcnow)


class WebhookEndpoint(Base, TimestampMixin):
    __tablename__ = "webhook_endpoints"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    target_url: Mapped[str] = mapped_column(sa.String(2048), nullable=False)
    event_types: Mapped[list[str]] = mapped_column(json_type(), default=list, nullable=False)
    signing_secret: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    last_tested_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    endpoint_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("webhook_endpoints.id"), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    replay_id: Mapped[str] = mapped_column(sa.String(128), nullable=False, unique=True)
    signature: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    status: Mapped[WebhookDeliveryStatus] = mapped_column(
        sa.Enum(WebhookDeliveryStatus),
        default=WebhookDeliveryStatus.queued,
        nullable=False,
    )
    payload: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)
    response_status_code: Mapped[int | None] = mapped_column(sa.Integer)
    response_body: Mapped[str | None] = mapped_column(sa.Text)
    attempt_count: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    next_attempt_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    last_attempt_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=utcnow)
    delivered_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    exhausted_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
