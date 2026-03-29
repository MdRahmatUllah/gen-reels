from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import AuthContext
from app.core.errors import ApiError
from app.integrations.azure import ModerationProvider
from app.models.entities import (
    Asset,
    ExportRecord,
    IdeaCandidate,
    IdeaSet,
    Project,
    ProjectBrief,
    ProjectStage,
    PromptHistoryEntry,
    RenderJob,
    ScenePlan,
    SceneSegment,
    ScriptVersion,
    TemplateVersion,
    VisualPreset,
    VoicePreset,
    WorkspaceRole,
)
from app.schemas.projects import BriefWriteRequest, ProjectCreateRequest, ProjectUpdateRequest
from app.services.audit_service import record_audit_event
from app.services.brand_kit_service import BrandKitService
from app.services.moderation_service import moderate_text_or_raise
from app.services.permissions import require_workspace_edit
from app.services.preset_service import PresetService
from app.services.project_profiles import (
    normalize_audio_mix_profile,
    normalize_export_profile,
    normalize_subtitle_style_profile,
)
from app.services.presenters import (
    brief_to_dict,
    idea_candidate_to_dict,
    idea_set_to_dict,
    job_to_dict,
    prompt_history_to_dict,
    project_to_dict,
    scene_plan_to_dict,
    script_version_to_dict,
    template_version_to_dict,
    asset_to_dict,
    export_to_dict,
    visual_preset_to_dict,
    voice_preset_to_dict,
)


class ProjectService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _get_project(self, project_id: str, workspace_id: str) -> Project:
        project = self.db.scalar(
            select(Project).where(
                Project.id == UUID(project_id),
                Project.workspace_id == UUID(workspace_id),
                Project.deleted_at.is_(None),
            )
        )
        if not project:
            raise ApiError(404, "project_not_found", "Project not found.")
        return project

    def _assert_mutation_rights(self, project: Project, auth: AuthContext) -> None:
        require_workspace_edit(
            auth,
            message="Only workspace members or admins can update this project.",
        )

    def list_projects(self, auth: AuthContext) -> list[dict[str, object]]:
        projects = self.db.scalars(
            select(Project)
            .where(Project.workspace_id == UUID(auth.workspace_id), Project.deleted_at.is_(None))
            .order_by(Project.updated_at.desc())
        ).all()
        return [project_to_dict(project) for project in projects]

    def create_project(self, auth: AuthContext, payload: ProjectCreateRequest) -> dict[str, object]:
        brand_kit_service = BrandKitService(self.db)
        brand_kit = brand_kit_service.resolve_brand_kit(auth.workspace_id, payload.brand_kit_id)
        project = Project(
            workspace_id=UUID(auth.workspace_id),
            owner_user_id=UUID(auth.user_id),
            title=payload.title,
            client=payload.client,
            aspect_ratio=payload.aspect_ratio,
            duration_target_sec=payload.duration_target_sec,
            subtitle_style_profile=normalize_subtitle_style_profile(None),
            export_profile=normalize_export_profile(None),
            audio_mix_profile=normalize_audio_mix_profile(None),
            stage=ProjectStage.brief,
        )
        brand_kit_service.apply_brand_kit_defaults(project, brand_kit)
        self.db.add(project)
        self.db.flush()
        record_audit_event(
            self.db,
            workspace_id=project.workspace_id,
            user_id=project.owner_user_id,
            event_type="project.created",
            target_type="project",
            target_id=str(project.id),
            payload={"title": project.title},
        )
        self.db.commit()
        self.db.refresh(project)
        return project_to_dict(project)

    def get_project_detail(self, auth: AuthContext, project_id: str) -> dict[str, object]:
        project = self._get_project(project_id, auth.workspace_id)
        brief_versions = self.db.scalars(
            select(ProjectBrief)
            .where(ProjectBrief.project_id == project.id)
            .order_by(ProjectBrief.version_number.desc())
        ).all()
        script_versions = self.db.scalars(
            select(ScriptVersion)
            .where(ScriptVersion.project_id == project.id)
            .order_by(ScriptVersion.version_number.desc())
        ).all()
        scene_plans = self.db.scalars(
            select(ScenePlan)
            .where(ScenePlan.project_id == project.id)
            .order_by(ScenePlan.version_number.desc())
        ).all()
        recent_jobs = self.db.scalars(
            select(RenderJob)
            .where(RenderJob.project_id == project.id)
            .order_by(RenderJob.created_at.desc())
            .limit(10)
        ).all()

        active_brief = self.db.get(ProjectBrief, project.active_brief_id) if project.active_brief_id else None
        selected_idea = self.db.get(IdeaCandidate, project.selected_idea_id) if project.selected_idea_id else None
        active_script = (
            self.db.get(ScriptVersion, project.active_script_version_id)
            if project.active_script_version_id
            else None
        )
        active_scene_plan = (
            self.db.get(ScenePlan, project.active_scene_plan_id)
            if project.active_scene_plan_id
            else None
        )
        latest_idea_set = self.db.scalar(
            select(IdeaSet)
            .where(IdeaSet.project_id == project.id)
            .order_by(IdeaSet.created_at.desc())
        )
        latest_candidates = []
        if latest_idea_set:
            latest_candidates = self.db.scalars(
                select(IdeaCandidate)
                .where(IdeaCandidate.idea_set_id == latest_idea_set.id)
                .order_by(IdeaCandidate.order_index.asc())
            ).all()

        scene_plan_segments: dict[str, list[SceneSegment]] = {}
        if scene_plans:
            scene_plan_ids = [scene_plan.id for scene_plan in scene_plans]
            for segment in self.db.scalars(
                select(SceneSegment)
                .where(SceneSegment.scene_plan_id.in_(scene_plan_ids))
                .order_by(SceneSegment.scene_index.asc())
            ).all():
                scene_plan_segments.setdefault(str(segment.scene_plan_id), []).append(segment)

        return {
            "project": project_to_dict(project),
            "active_brief": brief_to_dict(active_brief) if active_brief else None,
            "selected_idea": idea_candidate_to_dict(selected_idea) if selected_idea else None,
            "latest_idea_set": idea_set_to_dict(latest_idea_set, latest_candidates) if latest_idea_set else None,
            "active_script_version": script_version_to_dict(active_script) if active_script else None,
            "active_scene_plan": (
                scene_plan_to_dict(
                    active_scene_plan,
                    scene_plan_segments.get(str(active_scene_plan.id), []),
                )
                if active_scene_plan
                else None
            ),
            "brief_versions": [brief_to_dict(brief) for brief in brief_versions],
            "script_versions": [script_version_to_dict(script) for script in script_versions],
            "scene_plans": [
                scene_plan_to_dict(scene_plan, scene_plan_segments.get(str(scene_plan.id), []))
                for scene_plan in scene_plans
            ],
            "recent_jobs": [job_to_dict(job) for job in recent_jobs],
        }

    def get_project_lineage(self, auth: AuthContext, project_id: str) -> dict[str, object]:
        project = self._get_project(project_id, auth.workspace_id)
        visual_preset = (
            self.db.get(VisualPreset, project.default_visual_preset_id)
            if project.default_visual_preset_id
            else None
        )
        voice_preset = (
            self.db.get(VoicePreset, project.default_voice_preset_id)
            if project.default_voice_preset_id
            else None
        )
        source_template_version = (
            self.db.get(TemplateVersion, project.source_template_version_id)
            if project.source_template_version_id
            else None
        )
        exports = self.db.scalars(
            select(ExportRecord)
            .where(ExportRecord.project_id == project.id)
            .order_by(ExportRecord.created_at.desc())
        ).all()
        library_assets = self.db.scalars(
            select(Asset)
            .where(
                Asset.project_id == project.id,
                or_(
                    Asset.is_library_asset.is_(True),
                    Asset.is_reusable.is_(True),
                    Asset.reused_from_asset_id.is_not(None),
                ),
            )
            .order_by(Asset.created_at.asc())
        ).all()
        prompt_history = self.db.scalars(
            select(PromptHistoryEntry)
            .where(PromptHistoryEntry.project_id == project.id)
            .order_by(PromptHistoryEntry.created_at.asc())
        ).all()
        return {
            "project": project_to_dict(project),
            "source_template_version": (
                template_version_to_dict(source_template_version) if source_template_version else None
            ),
            "visual_preset": visual_preset_to_dict(visual_preset) if visual_preset else None,
            "voice_preset": voice_preset_to_dict(voice_preset) if voice_preset else None,
            "exports": [export_to_dict(export) for export in exports],
            "library_assets": [asset_to_dict(asset) for asset in library_assets],
            "prompt_history": [prompt_history_to_dict(entry) for entry in prompt_history],
        }

    def update_project(
        self,
        auth: AuthContext,
        project_id: str,
        payload: ProjectUpdateRequest,
    ) -> dict[str, object]:
        project = self._get_project(project_id, auth.workspace_id)
        self._assert_mutation_rights(project, auth)
        preset_service = PresetService(self.db)
        brand_kit_service = BrandKitService(self.db)

        if "title" in payload.model_fields_set and payload.title is not None:
            project.title = payload.title
        if "client" in payload.model_fields_set:
            project.client = payload.client
        if "aspect_ratio" in payload.model_fields_set and payload.aspect_ratio is not None:
            project.aspect_ratio = payload.aspect_ratio
        if (
            "duration_target_sec" in payload.model_fields_set
            and payload.duration_target_sec is not None
        ):
            project.duration_target_sec = payload.duration_target_sec
        if "stage" in payload.model_fields_set and payload.stage is not None:
            project.stage = ProjectStage(payload.stage)
        if "archived" in payload.model_fields_set and payload.archived is not None:
            project.archived_at = datetime.now(UTC) if payload.archived else None
        if "default_visual_preset_id" in payload.model_fields_set:
            if payload.default_visual_preset_id is None:
                project.default_visual_preset_id = None
            else:
                preset = preset_service.get_visual_preset(auth.workspace_id, payload.default_visual_preset_id)
                project.default_visual_preset_id = preset.id
        if "default_voice_preset_id" in payload.model_fields_set:
            if payload.default_voice_preset_id is None:
                project.default_voice_preset_id = None
            else:
                preset = preset_service.get_voice_preset(auth.workspace_id, payload.default_voice_preset_id)
                project.default_voice_preset_id = preset.id
        if "brand_kit_id" in payload.model_fields_set:
            if payload.brand_kit_id is None:
                project.brand_kit_id = None
            else:
                project.brand_kit_id = brand_kit_service.get_brand_kit(auth.workspace_id, payload.brand_kit_id).id
        if "subtitle_style_profile" in payload.model_fields_set:
            project.subtitle_style_profile = normalize_subtitle_style_profile(payload.subtitle_style_profile)
        if "export_profile" in payload.model_fields_set:
            project.export_profile = normalize_export_profile(payload.export_profile)
        if "audio_mix_profile" in payload.model_fields_set:
            project.audio_mix_profile = normalize_audio_mix_profile(payload.audio_mix_profile)

        active_brand_kit = brand_kit_service.resolve_brand_kit(
            auth.workspace_id,
            str(project.brand_kit_id) if project.brand_kit_id else None,
        )
        brand_kit_service.apply_brand_kit_defaults(project, active_brand_kit)

        record_audit_event(
            self.db,
            workspace_id=project.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="project.updated",
            target_type="project",
            target_id=str(project.id),
            payload={},
        )
        self.db.commit()
        self.db.refresh(project)
        return project_to_dict(project)

    def delete_project(self, auth: AuthContext, project_id: str) -> None:
        project = self._get_project(project_id, auth.workspace_id)
        self._assert_mutation_rights(project, auth)
        project.deleted_at = datetime.now(UTC)
        record_audit_event(
            self.db,
            workspace_id=project.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="project.deleted",
            target_type="project",
            target_id=str(project.id),
            payload={},
        )
        self.db.commit()

    def save_brief_version(
        self,
        auth: AuthContext,
        project_id: str,
        payload: BriefWriteRequest,
        moderation_provider: ModerationProvider,
    ) -> dict[str, object]:
        project = self._get_project(project_id, auth.workspace_id)
        self._assert_mutation_rights(project, auth)

        moderation_text = "\n".join(
            [
                payload.objective,
                payload.hook,
                payload.target_audience,
                payload.call_to_action,
                payload.brand_north_star,
                *payload.guardrails,
                *payload.must_include,
                *payload.approval_steps,
            ]
        )
        moderate_text_or_raise(
            self.db,
            provider=moderation_provider,
            text=moderation_text,
            target_type="brief_input",
            user_id=UUID(auth.user_id),
            project_id=project.id,
            workspace_id=project.workspace_id,
            target_id=project_id,
        )
        BrandKitService(self.db).validate_text_against_brand_kit(project, moderation_text)

        next_version = (
            self.db.scalar(
                select(func.max(ProjectBrief.version_number)).where(ProjectBrief.project_id == project.id)
            )
            or 0
        ) + 1
        brief = ProjectBrief(
            project_id=project.id,
            version_number=next_version,
            created_by_user_id=UUID(auth.user_id),
            objective=payload.objective,
            hook=payload.hook,
            target_audience=payload.target_audience,
            call_to_action=payload.call_to_action,
            brand_north_star=payload.brand_north_star,
            guardrails=payload.guardrails,
            must_include=payload.must_include,
            approval_steps=payload.approval_steps,
        )
        self.db.add(brief)
        self.db.flush()
        project.active_brief_id = brief.id
        project.selected_idea_id = None
        project.active_script_version_id = None
        project.active_scene_plan_id = None
        project.stage = ProjectStage.brief
        record_audit_event(
            self.db,
            workspace_id=project.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="project.brief_version_created",
            target_type="project_brief",
            target_id=str(brief.id),
            payload={"version_number": next_version},
        )
        self.db.commit()
        return brief_to_dict(brief)
