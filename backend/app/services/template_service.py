from __future__ import annotations

from uuid import UUID

import json

from sqlalchemy import func, select

from app.api.deps import AuthContext
from app.core.errors import ApiError
from app.models.entities import (
    Project,
    ProjectBrief,
    ProjectStage,
    ProjectTemplate,
    TemplateVersion,
    VisualPreset,
    VoicePreset,
)
from app.schemas.templates import ProjectFromTemplateRequest, TemplateCreateRequest
from app.services.audit_service import record_audit_event
from app.services.project_profiles import (
    normalize_audio_mix_profile,
    normalize_export_profile,
    normalize_subtitle_style_profile,
)
from app.services.presenters import brief_to_dict, project_to_dict, template_to_dict


class TemplateService:
    def __init__(self, db) -> None:
        self.db = db

    def _get_template(self, workspace_id: str, template_id: str) -> ProjectTemplate:
        template = self.db.scalar(
            select(ProjectTemplate).where(
                ProjectTemplate.id == UUID(template_id),
                ProjectTemplate.workspace_id == UUID(workspace_id),
            )
        )
        if not template:
            raise ApiError(404, "template_not_found", "Template not found.")
        return template

    def _latest_version(self, template_id: UUID) -> TemplateVersion | None:
        return self.db.scalar(
            select(TemplateVersion)
            .where(TemplateVersion.template_id == template_id)
            .order_by(TemplateVersion.version_number.desc())
        )

    def _version_list(self, template_id: UUID) -> list[TemplateVersion]:
        return self.db.scalars(
            select(TemplateVersion)
            .where(TemplateVersion.template_id == template_id)
            .order_by(TemplateVersion.version_number.desc())
        ).all()

    def _project_template_snapshot(self, project: Project, brief: ProjectBrief | None) -> dict[str, object]:
        brief_snapshot = None
        if brief:
            brief_snapshot = {
                "objective": brief.objective,
                "hook": brief.hook,
                "target_audience": brief.target_audience,
                "call_to_action": brief.call_to_action,
                "brand_north_star": brief.brand_north_star,
                "guardrails": list(brief.guardrails or []),
                "must_include": list(brief.must_include or []),
                "approval_steps": list(brief.approval_steps or []),
            }
        return {
            "project_defaults": {
                "aspect_ratio": project.aspect_ratio,
                "duration_target_sec": project.duration_target_sec,
                "default_visual_preset_id": str(project.default_visual_preset_id) if project.default_visual_preset_id else None,
                "default_voice_preset_id": str(project.default_voice_preset_id) if project.default_voice_preset_id else None,
                "subtitle_style_profile": normalize_subtitle_style_profile(project.subtitle_style_profile),
                "export_profile": normalize_export_profile(project.export_profile),
                "audio_mix_profile": normalize_audio_mix_profile(project.audio_mix_profile),
            },
            "brief": json.loads(json.dumps(brief_snapshot, default=str)) if brief_snapshot else None,
        }

    def _transferable_preset_id(self, workspace_id: UUID, preset_model, preset_id: str | None) -> UUID | None:
        if not preset_id:
            return None
        preset = self.db.scalar(
            select(preset_model).where(
                preset_model.id == UUID(str(preset_id)),
                preset_model.workspace_id == workspace_id,
            )
        )
        return preset.id if preset else None

    def list_templates(self, auth: AuthContext) -> list[dict[str, object]]:
        templates = self.db.scalars(
            select(ProjectTemplate)
            .where(ProjectTemplate.workspace_id == UUID(auth.workspace_id))
            .order_by(ProjectTemplate.updated_at.desc())
        ).all()
        latest_versions = {
            template.id: self._latest_version(template.id)
            for template in templates
        }
        return [
            template_to_dict(template, latest_version=latest_versions.get(template.id))
            for template in templates
        ]

    def get_template_detail(self, auth: AuthContext, template_id: str) -> dict[str, object]:
        template = self._get_template(auth.workspace_id, template_id)
        latest_version = self._latest_version(template.id)
        versions = self._version_list(template.id)
        return template_to_dict(template, latest_version=latest_version, versions=versions)

    def create_template_from_project(
        self,
        auth: AuthContext,
        project: Project,
        payload: TemplateCreateRequest,
    ) -> dict[str, object]:
        active_brief = self.db.get(ProjectBrief, project.active_brief_id) if project.active_brief_id else None
        template = ProjectTemplate(
            workspace_id=project.workspace_id,
            created_by_user_id=UUID(auth.user_id),
            name=payload.name,
            description=payload.description,
        )
        self.db.add(template)
        self.db.flush()
        version = TemplateVersion(
            template_id=template.id,
            source_project_id=project.id,
            created_by_user_id=UUID(auth.user_id),
            version_number=1,
            snapshot_payload=self._project_template_snapshot(project, active_brief),
        )
        self.db.add(version)
        self.db.flush()
        record_audit_event(
            self.db,
            workspace_id=project.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="templates.created",
            target_type="project_template",
            target_id=str(template.id),
            payload={"project_id": str(project.id), "template_version_id": str(version.id)},
        )
        self.db.commit()
        self.db.refresh(template)
        return template_to_dict(template, latest_version=version)

    def create_project_from_template(
        self,
        auth: AuthContext,
        template_id: str,
        payload: ProjectFromTemplateRequest,
    ) -> dict[str, object]:
        template = self._get_template(auth.workspace_id, template_id)
        if template.is_archived:
            raise ApiError(400, "template_archived", "Archived templates cannot create new projects.")
        version = self._latest_version(template.id)
        if not version:
            raise ApiError(400, "template_missing_version", "Template does not have a version snapshot.")

        snapshot = dict(version.snapshot_payload or {})
        project_defaults = dict(snapshot.get("project_defaults") or {})
        brief_snapshot = snapshot.get("brief")
        project = Project(
            workspace_id=UUID(auth.workspace_id),
            owner_user_id=UUID(auth.user_id),
            source_template_version_id=version.id,
            title=payload.title,
            client=payload.client,
            aspect_ratio=str(project_defaults.get("aspect_ratio") or "9:16"),
            duration_target_sec=int(project_defaults.get("duration_target_sec") or 90),
            default_visual_preset_id=self._transferable_preset_id(
                UUID(auth.workspace_id),
                VisualPreset,
                project_defaults.get("default_visual_preset_id"),
            ),
            default_voice_preset_id=self._transferable_preset_id(
                UUID(auth.workspace_id),
                VoicePreset,
                project_defaults.get("default_voice_preset_id"),
            ),
            subtitle_style_profile=normalize_subtitle_style_profile(project_defaults.get("subtitle_style_profile")),
            export_profile=normalize_export_profile(project_defaults.get("export_profile")),
            audio_mix_profile=normalize_audio_mix_profile(project_defaults.get("audio_mix_profile")),
            stage=ProjectStage.brief,
        )
        self.db.add(project)
        self.db.flush()

        brief_payload = None
        if isinstance(brief_snapshot, dict):
            brief = ProjectBrief(
                project_id=project.id,
                version_number=1,
                created_by_user_id=UUID(auth.user_id),
                objective=str(brief_snapshot.get("objective") or ""),
                hook=str(brief_snapshot.get("hook") or ""),
                target_audience=str(brief_snapshot.get("target_audience") or ""),
                call_to_action=str(brief_snapshot.get("call_to_action") or ""),
                brand_north_star=str(brief_snapshot.get("brand_north_star") or ""),
                guardrails=list(brief_snapshot.get("guardrails") or []),
                must_include=list(brief_snapshot.get("must_include") or []),
                approval_steps=list(brief_snapshot.get("approval_steps") or []),
            )
            self.db.add(brief)
            self.db.flush()
            project.active_brief_id = brief.id
            brief_payload = brief_to_dict(brief)

        record_audit_event(
            self.db,
            workspace_id=project.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="templates.project_created",
            target_type="project",
            target_id=str(project.id),
            payload={"template_id": str(template.id), "template_version_id": str(version.id)},
        )
        self.db.commit()
        self.db.refresh(project)
        return {
            "template": template_to_dict(template, latest_version=version),
            "project": project_to_dict(project),
            "brief": brief_payload,
        }
