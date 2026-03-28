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
    idea_generation = "idea_generation"
    script_generation = "script_generation"
    scene_plan_generation = "scene_plan_generation"
    prompt_pair_generation = "prompt_pair_generation"


class StepKind(str, enum.Enum):
    idea_generation = "idea_generation"
    script_generation = "script_generation"
    scene_plan_generation = "scene_plan_generation"
    prompt_pair_generation = "prompt_pair_generation"


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


class ModerationDecision(str, enum.Enum):
    allowed = "allowed"
    blocked = "blocked"


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
    job_kind: Mapped[JobKind] = mapped_column(sa.Enum(JobKind), nullable=False)
    queue_name: Mapped[str] = mapped_column(sa.String(64), default="planning", nullable=False)
    status: Mapped[JobStatus] = mapped_column(sa.Enum(JobStatus), default=JobStatus.queued)
    idempotency_key: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)
    error_code: Mapped[str | None] = mapped_column(sa.String(64))
    error_message: Mapped[str | None] = mapped_column(sa.Text)
    retry_count: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))


class RenderStep(Base, TimestampMixin):
    __tablename__ = "render_steps"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    render_job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("render_jobs.id"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    step_kind: Mapped[StepKind] = mapped_column(sa.Enum(StepKind), nullable=False)
    step_index: Mapped[int] = mapped_column(sa.Integer, default=1, nullable=False)
    status: Mapped[JobStatus] = mapped_column(sa.Enum(JobStatus), default=JobStatus.queued)
    input_payload: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)
    output_payload: Mapped[dict[str, object] | None] = mapped_column(json_type())
    error_code: Mapped[str | None] = mapped_column(sa.String(64))
    error_message: Mapped[str | None] = mapped_column(sa.Text)
    started_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))


class ProviderRun(Base):
    __tablename__ = "provider_runs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    render_job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("render_jobs.id"))
    render_step_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("render_steps.id"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"))
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workspaces.id"))
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
    error_category: Mapped[ProviderErrorCategory | None] = mapped_column(
        sa.Enum(ProviderErrorCategory)
    )
    error_code: Mapped[str | None] = mapped_column(sa.String(64))
    error_message: Mapped[str | None] = mapped_column(sa.Text)
    cost_payload: Mapped[dict[str, object] | None] = mapped_column(json_type())
    started_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))


class ModerationEvent(Base):
    __tablename__ = "moderation_events"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"), index=True)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workspaces.id"), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    target_type: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    target_id: Mapped[str | None] = mapped_column(sa.String(64))
    input_text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    decision: Mapped[ModerationDecision] = mapped_column(sa.Enum(ModerationDecision), nullable=False)
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


class ConsistencyPack(Base):
    __tablename__ = "consistency_packs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("projects.id"))
    version_number: Mapped[int] = mapped_column(sa.Integer, default=1, nullable=False)
    state: Mapped[dict[str, object]] = mapped_column(json_type(), default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=utcnow)
