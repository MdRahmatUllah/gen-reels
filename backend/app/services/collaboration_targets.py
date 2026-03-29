from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select

from app.core.errors import ApiError
from app.models.entities import (
    ExportRecord,
    Project,
    ProjectTemplate,
    ScenePlan,
    SceneSegment,
    ScriptVersion,
    TemplateVersion,
    VisualPreset,
    VoicePreset,
)
from app.services.presenters import (
    export_to_dict,
    scene_plan_to_dict,
    script_version_to_dict,
    template_to_dict,
    template_version_to_dict,
    visual_preset_to_dict,
    voice_preset_to_dict,
)


@dataclass
class CollaborationTarget:
    target_type: str
    target_id: str
    workspace_id: UUID
    project_id: UUID | None
    version: int | None
    payload: dict[str, object]
    raw: object


def resolve_workspace_target(db, workspace_id: str, target_type: str, target_id: str) -> CollaborationTarget:
    workspace_uuid = UUID(workspace_id)
    if target_type == "script_version":
        script = db.scalar(
            select(ScriptVersion)
            .join(Project, Project.id == ScriptVersion.project_id)
            .where(ScriptVersion.id == UUID(target_id), Project.workspace_id == workspace_uuid)
        )
        if not script:
            raise ApiError(404, "target_not_found", "Review target not found.")
        return CollaborationTarget(
            target_type=target_type,
            target_id=target_id,
            workspace_id=workspace_uuid,
            project_id=script.project_id,
            version=script.version,
            payload=script_version_to_dict(script),
            raw=script,
        )

    if target_type == "scene_plan":
        scene_plan = db.scalar(
            select(ScenePlan)
            .join(Project, Project.id == ScenePlan.project_id)
            .where(ScenePlan.id == UUID(target_id), Project.workspace_id == workspace_uuid)
        )
        if not scene_plan:
            raise ApiError(404, "target_not_found", "Review target not found.")
        segments = db.scalars(
            select(SceneSegment)
            .where(SceneSegment.scene_plan_id == scene_plan.id)
            .order_by(SceneSegment.scene_index.asc())
        ).all()
        return CollaborationTarget(
            target_type=target_type,
            target_id=target_id,
            workspace_id=workspace_uuid,
            project_id=scene_plan.project_id,
            version=scene_plan.version,
            payload=scene_plan_to_dict(scene_plan, segments),
            raw=scene_plan,
        )

    if target_type == "scene_segment":
        segment = db.scalar(
            select(SceneSegment)
            .join(ScenePlan, ScenePlan.id == SceneSegment.scene_plan_id)
            .join(Project, Project.id == ScenePlan.project_id)
            .where(SceneSegment.id == UUID(target_id), Project.workspace_id == workspace_uuid)
        )
        if not segment:
            raise ApiError(404, "target_not_found", "Comment target not found.")
        return CollaborationTarget(
            target_type=target_type,
            target_id=target_id,
            workspace_id=workspace_uuid,
            project_id=db.scalar(
                select(ScenePlan.project_id).where(ScenePlan.id == segment.scene_plan_id)
            ),
            version=None,
            payload={
                "id": str(segment.id),
                "scene_index": segment.scene_index,
                "title": segment.title,
                "beat": segment.beat,
            },
            raw=segment,
        )

    if target_type == "export":
        export = db.scalar(
            select(ExportRecord)
            .join(Project, Project.id == ExportRecord.project_id)
            .where(ExportRecord.id == UUID(target_id), Project.workspace_id == workspace_uuid)
        )
        if not export:
            raise ApiError(404, "target_not_found", "Review target not found.")
        return CollaborationTarget(
            target_type=target_type,
            target_id=target_id,
            workspace_id=workspace_uuid,
            project_id=export.project_id,
            version=None,
            payload=export_to_dict(export),
            raw=export,
        )

    if target_type == "template_version":
        version = db.scalar(
            select(TemplateVersion)
            .join(ProjectTemplate, ProjectTemplate.id == TemplateVersion.template_id)
            .where(TemplateVersion.id == UUID(target_id), ProjectTemplate.workspace_id == workspace_uuid)
        )
        if not version:
            raise ApiError(404, "target_not_found", "Review target not found.")
        return CollaborationTarget(
            target_type=target_type,
            target_id=target_id,
            workspace_id=workspace_uuid,
            project_id=version.source_project_id,
            version=None,
            payload=template_version_to_dict(version),
            raw=version,
        )

    if target_type == "visual_preset":
        preset = db.scalar(
            select(VisualPreset).where(
                VisualPreset.id == UUID(target_id),
                VisualPreset.workspace_id == workspace_uuid,
            )
        )
        if not preset:
            raise ApiError(404, "target_not_found", "Comment target not found.")
        return CollaborationTarget(
            target_type=target_type,
            target_id=target_id,
            workspace_id=workspace_uuid,
            project_id=None,
            version=preset.version,
            payload=visual_preset_to_dict(preset),
            raw=preset,
        )

    if target_type == "voice_preset":
        preset = db.scalar(
            select(VoicePreset).where(
                VoicePreset.id == UUID(target_id),
                VoicePreset.workspace_id == workspace_uuid,
            )
        )
        if not preset:
            raise ApiError(404, "target_not_found", "Comment target not found.")
        return CollaborationTarget(
            target_type=target_type,
            target_id=target_id,
            workspace_id=workspace_uuid,
            project_id=None,
            version=preset.version,
            payload=voice_preset_to_dict(preset),
            raw=preset,
        )

    if target_type == "project":
        project = db.scalar(
            select(Project).where(Project.id == UUID(target_id), Project.workspace_id == workspace_uuid)
        )
        if not project:
            raise ApiError(404, "target_not_found", "Comment target not found.")
        return CollaborationTarget(
            target_type=target_type,
            target_id=target_id,
            workspace_id=workspace_uuid,
            project_id=project.id,
            version=None,
            payload={
                "id": project.id,
                "title": project.title,
                "stage": project.stage.value,
            },
            raw=project,
        )

    if target_type == "project_template":
        template = db.scalar(
            select(ProjectTemplate).where(
                ProjectTemplate.id == UUID(target_id),
                ProjectTemplate.workspace_id == workspace_uuid,
            )
        )
        if not template:
            raise ApiError(404, "target_not_found", "Comment target not found.")
        return CollaborationTarget(
            target_type=target_type,
            target_id=target_id,
            workspace_id=workspace_uuid,
            project_id=None,
            version=template.version,
            payload=template_to_dict(template),
            raw=template,
        )

    raise ApiError(400, "unsupported_target_type", "Unsupported collaboration target type.")
