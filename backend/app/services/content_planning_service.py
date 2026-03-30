from __future__ import annotations

import time
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select

from app.api.deps import AuthContext
from app.core.errors import AdapterError, ApiError
from app.integrations.azure import TextProvider
from app.models.entities import (
    ConsistencyPack,
    ExecutionMode,
    IdeaCandidate,
    JobKind,
    JobStatus,
    Project,
    ProjectBrief,
    ProjectStage,
    ProviderErrorCategory,
    ProviderRun,
    ProviderRunStatus,
    RenderJob,
    RenderStep,
    ScenePlan,
    ScenePlanSource,
    SceneSegment,
    ScriptVersion,
    StepKind,
    VisualPreset,
    VoicePreset,
)
from app.schemas.scene_plans import ScenePlanPatchRequest
from app.services.audit_service import record_audit_event
from app.services.brand_kit_service import BrandKitService
from app.services.generation_service import GenerationService
from app.services.permissions import require_workspace_review
from app.services.presenters import scene_plan_to_dict, script_version_to_dict
from app.services.preset_service import PresetService
from app.services.routing_service import RoutingService


class ContentPlanningService(GenerationService):
    def __init__(self, db, settings) -> None:
        super().__init__(db, settings)
        self.preset_service = PresetService(db)

    def _get_script(self, project: Project, script_version_id: str) -> ScriptVersion:
        script = self.db.scalar(
            select(ScriptVersion).where(
                ScriptVersion.id == UUID(script_version_id),
                ScriptVersion.project_id == project.id,
            )
        )
        if not script:
            raise ApiError(404, "script_not_found", "Script version not found.")
        return script

    def _get_scene_plan(self, project: Project, scene_plan_id: str) -> ScenePlan:
        scene_plan = self.db.scalar(
            select(ScenePlan).where(
                ScenePlan.id == UUID(scene_plan_id),
                ScenePlan.project_id == project.id,
            )
        )
        if not scene_plan:
            raise ApiError(404, "scene_plan_not_found", "Scene plan not found.")
        return scene_plan

    def _list_scene_segments(self, scene_plan_id: UUID) -> list[SceneSegment]:
        return self.db.scalars(
            select(SceneSegment)
            .where(SceneSegment.scene_plan_id == scene_plan_id)
            .order_by(SceneSegment.scene_index.asc())
        ).all()

    def _script_payload(self, script: ScriptVersion) -> dict[str, object]:
        return {
            "id": str(script.id),
            "version_number": script.version_number,
            "approval_state": script.approval_state,
            "estimated_duration_seconds": script.estimated_duration_seconds,
            "reading_time_label": script.reading_time_label,
            "lines": script.lines,
        }

    def _visual_preset_payload(self, preset: VisualPreset | None) -> dict[str, object] | None:
        if not preset:
            return None
        return {
            "id": str(preset.id),
            "name": preset.name,
            "description": preset.description,
            "prompt_prefix": preset.prompt_prefix,
            "style_descriptor": preset.style_descriptor,
            "negative_prompt": preset.negative_prompt,
            "camera_defaults": preset.camera_defaults,
            "color_palette": preset.color_palette,
            "reference_notes": preset.reference_notes,
        }

    def _voice_preset_payload(self, preset: VoicePreset | None) -> dict[str, object] | None:
        if not preset:
            return None
        return {
            "id": str(preset.id),
            "name": preset.name,
            "description": preset.description,
            "provider_voice": preset.provider_voice,
            "tone_descriptor": preset.tone_descriptor,
            "language_code": preset.language_code,
            "pace_multiplier": preset.pace_multiplier,
        }

    def _scene_segment_model_to_payload(self, segment: SceneSegment) -> dict[str, object]:
        return {
            "scene_index": segment.scene_index,
            "source_line_ids": segment.source_line_ids,
            "title": segment.title,
            "beat": segment.beat,
            "narration_text": segment.narration_text,
            "caption_text": segment.caption_text,
            "visual_direction": segment.visual_direction,
            "shot_type": segment.shot_type,
            "motion": segment.motion,
            "target_duration_seconds": segment.target_duration_seconds,
            "estimated_voice_duration_seconds": segment.estimated_voice_duration_seconds,
            "actual_voice_duration_seconds": segment.actual_voice_duration_seconds,
            "visual_prompt": segment.visual_prompt,
            "start_image_prompt": segment.start_image_prompt,
            "end_image_prompt": segment.end_image_prompt,
            "transition_mode": segment.transition_mode,
            "notes": segment.notes,
            "validation_warnings": segment.validation_warnings,
            "chained_from_asset_id": segment.chained_from_asset_id,
            "start_image_asset_id": segment.start_image_asset_id,
            "end_image_asset_id": segment.end_image_asset_id,
        }

    def _scene_plan_provider_payload(
        self,
        scene_plan: ScenePlan,
        segments: list[SceneSegment],
    ) -> dict[str, object]:
        return {
            "scene_plan_id": str(scene_plan.id),
            "version_number": scene_plan.version_number,
            "total_estimated_duration_seconds": scene_plan.total_estimated_duration_seconds,
            "scene_count": scene_plan.scene_count,
            "segments": [self._scene_segment_model_to_payload(segment) for segment in segments],
        }

    def _segment_warnings(self, *, target_duration_seconds: int) -> list[dict[str, object]]:
        warnings: list[dict[str, object]] = []
        if target_duration_seconds > 8:
            warnings.append(
                {
                    "code": "segment_duration_high",
                    "message": "Estimated scene duration exceeds the recommended 8 second target.",
                }
            )
        if target_duration_seconds < 5:
            warnings.append(
                {
                    "code": "segment_duration_low",
                    "message": "Estimated scene duration is shorter than the recommended 5 second target.",
                }
            )
        return warnings

    def _scene_plan_warnings(self, *, total_duration_seconds: int) -> list[dict[str, object]]:
        warnings: list[dict[str, object]] = []
        if total_duration_seconds < 60 or total_duration_seconds > 120:
            warnings.append(
                {
                    "code": "total_duration_out_of_range",
                    "message": "Estimated total duration is outside the recommended 60-120 second range.",
                }
            )
        return warnings

    def _normalize_segment_payload(
        self,
        raw_segment: dict[str, object],
        *,
        scene_index: int,
    ) -> dict[str, object]:
        target_duration_seconds = int(raw_segment.get("target_duration_seconds") or 6)
        estimated_voice_duration_seconds = int(
            raw_segment.get("estimated_voice_duration_seconds") or target_duration_seconds
        )
        raw_warnings = list(raw_segment.get("validation_warnings") or [])
        warnings = []
        for w in raw_warnings:
            if isinstance(w, str):
                warnings.append({"code": "llm_warning", "message": w})
            elif isinstance(w, dict):
                warnings.append(w)
        warnings.extend(self._segment_warnings(target_duration_seconds=target_duration_seconds))
        return {
            "scene_index": int(raw_segment.get("scene_index") or scene_index),
            "source_line_ids": [str(item) for item in raw_segment.get("source_line_ids") or []],
            "title": str(raw_segment.get("title") or ""),
            "beat": str(raw_segment.get("beat") or ""),
            "narration_text": str(raw_segment.get("narration_text") or ""),
            "caption_text": str(raw_segment.get("caption_text") or ""),
            "visual_direction": str(raw_segment.get("visual_direction") or ""),
            "shot_type": str(raw_segment.get("shot_type") or ""),
            "motion": str(raw_segment.get("motion") or ""),
            "target_duration_seconds": target_duration_seconds,
            "estimated_voice_duration_seconds": estimated_voice_duration_seconds,
            "actual_voice_duration_seconds": raw_segment.get("actual_voice_duration_seconds"),
            "visual_prompt": str(raw_segment.get("visual_prompt") or ""),
            "start_image_prompt": str(raw_segment.get("start_image_prompt") or ""),
            "end_image_prompt": str(raw_segment.get("end_image_prompt") or ""),
            "transition_mode": str(raw_segment.get("transition_mode") or "hard_cut"),
            "notes": [str(item) for item in raw_segment.get("notes") or []],
            "validation_warnings": warnings,
            "chained_from_asset_id": raw_segment.get("chained_from_asset_id"),
            "start_image_asset_id": raw_segment.get("start_image_asset_id"),
            "end_image_asset_id": raw_segment.get("end_image_asset_id"),
        }

    def _upsert_scene_plan_segments(
        self,
        scene_plan: ScenePlan,
        segments_payload: list[dict[str, object]],
    ) -> list[SceneSegment]:
        existing_segments = self._list_scene_segments(scene_plan.id)
        for segment in existing_segments:
            self.db.delete(segment)
        self.db.flush()

        normalized_segments = [
            self._normalize_segment_payload(payload, scene_index=index)
            for index, payload in enumerate(segments_payload, start=1)
        ]
        for payload in normalized_segments:
            self.db.add(SceneSegment(scene_plan_id=scene_plan.id, **payload))

        total_duration_seconds = sum(
            int(payload["target_duration_seconds"]) for payload in normalized_segments
        )
        scene_plan.scene_count = len(normalized_segments)
        scene_plan.total_estimated_duration_seconds = total_duration_seconds
        scene_plan.validation_warnings = self._scene_plan_warnings(
            total_duration_seconds=total_duration_seconds
        )
        self.db.flush()
        return self._list_scene_segments(scene_plan.id)

    def approve_script(
        self,
        auth: AuthContext,
        project_id: str,
        script_version_id: str,
    ) -> dict[str, object]:
        project = self._get_project(project_id, auth.workspace_id)
        require_workspace_review(
            auth,
            message="Only reviewers, members, or admins can approve scripts.",
        )
        script = self._get_script(project, script_version_id)
        script_text = "\n".join(
            f"{line.get('beat', '')}\n{line.get('narration', '')}\n{line.get('caption', '')}"
            for line in (script.lines or [])
        )
        BrandKitService(self.db).validate_text_against_brand_kit(project, script_text)

        script.approval_state = "approved"
        script.approved_at = datetime.now(UTC)
        script.approved_by_user_id = UUID(auth.user_id)
        script.version += 1
        project.active_script_version_id = script.id
        project.active_scene_plan_id = None
        project.stage = ProjectStage.scenes
        record_audit_event(
            self.db,
            workspace_id=project.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="scripts.approved",
            target_type="script_version",
            target_id=str(script.id),
            payload={"version_number": script.version_number},
        )
        self.db.commit()
        self.db.refresh(script)
        return script_version_to_dict(script)

    def list_scene_plans(self, auth: AuthContext, project_id: str) -> list[dict[str, object]]:
        project = self._get_project(project_id, auth.workspace_id)
        scene_plans = self.db.scalars(
            select(ScenePlan)
            .where(ScenePlan.project_id == project.id)
            .order_by(ScenePlan.version_number.desc())
        ).all()
        return [
            scene_plan_to_dict(scene_plan, self._list_scene_segments(scene_plan.id))
            for scene_plan in scene_plans
        ]

    def get_scene_plan_detail(
        self,
        auth: AuthContext,
        project_id: str,
        scene_plan_id: str,
    ) -> dict[str, object]:
        project = self._get_project(project_id, auth.workspace_id)
        scene_plan = self._get_scene_plan(project, scene_plan_id)
        return scene_plan_to_dict(scene_plan, self._list_scene_segments(scene_plan.id))

    def queue_scene_plan_generation(
        self,
        auth: AuthContext,
        project_id: str,
        *,
        idempotency_key: str,
    ) -> dict[str, object]:
        if not idempotency_key:
            raise ApiError(400, "missing_idempotency_key", "Idempotency-Key header is required.")

        project = self._get_project(project_id, auth.workspace_id)
        self._assert_mutation_rights(project, auth)
        if not project.active_brief_id:
            raise ApiError(400, "missing_brief", "A saved brief is required before scene planning.")
        if not project.selected_idea_id:
            raise ApiError(400, "missing_selected_idea", "Select an idea before scene planning.")
        if not project.active_script_version_id:
            raise ApiError(400, "missing_script", "An approved script is required before scene planning.")
        if not project.default_visual_preset_id or not project.default_voice_preset_id:
            raise ApiError(
                400,
                "missing_project_presets",
                "Set project visual and voice presets before generating a scene plan.",
            )

        script = self.db.get(ScriptVersion, project.active_script_version_id)
        if not script or script.approval_state != "approved":
            raise ApiError(
                400,
                "script_not_approved",
                "Approve the active script before generating a scene plan.",
            )

        request_payload = {
            "project_id": project_id,
            "script_version_id": str(script.id),
            "script_version_number": script.version_number,
            "visual_preset_id": str(project.default_visual_preset_id),
            "voice_preset_id": str(project.default_voice_preset_id),
        }
        request_hash = self._hash_request(request_payload)
        existing = self._get_idempotent_job(
            project_id=project.id,
            user_id=UUID(auth.user_id),
            job_kind=JobKind.scene_plan_generation,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if existing:
            return {"job_id": existing.id, "job_status": existing.status.value, "project_id": project.id}

        job = RenderJob(
            workspace_id=project.workspace_id,
            project_id=project.id,
            created_by_user_id=UUID(auth.user_id),
            job_kind=JobKind.scene_plan_generation,
            status=JobStatus.queued,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            payload=request_payload,
        )
        self.db.add(job)
        self.db.flush()
        self.db.add(
            RenderStep(
                render_job_id=job.id,
                project_id=project.id,
                step_kind=StepKind.scene_plan_generation,
                status=JobStatus.queued,
                input_payload=request_payload,
            )
        )
        record_audit_event(
            self.db,
            workspace_id=project.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="scene_plans.generation_queued",
            target_type="render_job",
            target_id=str(job.id),
            payload=request_payload,
        )
        self.db.commit()
        from app.workers.tasks import generate_scene_plan_task

        generate_scene_plan_task.delay(str(job.id))
        return {"job_id": job.id, "job_status": job.status.value, "project_id": project.id}

    def queue_prompt_pair_generation(
        self,
        auth: AuthContext,
        project_id: str,
        scene_plan_id: str,
        *,
        idempotency_key: str,
    ) -> dict[str, object]:
        if not idempotency_key:
            raise ApiError(400, "missing_idempotency_key", "Idempotency-Key header is required.")

        project = self._get_project(project_id, auth.workspace_id)
        self._assert_mutation_rights(project, auth)
        scene_plan = self._get_scene_plan(project, scene_plan_id)
        if scene_plan.approval_state == "approved":
            raise ApiError(
                400,
                "scene_plan_locked",
                "Approved scene plans are immutable. Create a new draft before regenerating prompts.",
            )
        if not scene_plan.visual_preset_id:
            raise ApiError(
                400,
                "missing_visual_preset",
                "Assign a visual preset before generating prompt pairs.",
            )
        segments = self._list_scene_segments(scene_plan.id)
        if not segments:
            raise ApiError(
                400,
                "missing_scene_segments",
                "Generate or add scene segments before generating prompt pairs.",
            )

        request_payload = {
            "project_id": project_id,
            "scene_plan_id": str(scene_plan.id),
            "scene_plan_version": scene_plan.version_number,
            "scene_plan_updated_at": scene_plan.updated_at.isoformat(),
            "visual_preset_id": str(scene_plan.visual_preset_id),
        }
        request_hash = self._hash_request(request_payload)
        existing = self._get_idempotent_job(
            project_id=project.id,
            user_id=UUID(auth.user_id),
            job_kind=JobKind.prompt_pair_generation,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if existing:
            return {"job_id": existing.id, "job_status": existing.status.value, "project_id": project.id}

        job = RenderJob(
            workspace_id=project.workspace_id,
            project_id=project.id,
            created_by_user_id=UUID(auth.user_id),
            job_kind=JobKind.prompt_pair_generation,
            status=JobStatus.queued,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            payload=request_payload,
        )
        self.db.add(job)
        self.db.flush()
        self.db.add(
            RenderStep(
                render_job_id=job.id,
                project_id=project.id,
                step_kind=StepKind.prompt_pair_generation,
                status=JobStatus.queued,
                input_payload=request_payload,
            )
        )
        record_audit_event(
            self.db,
            workspace_id=project.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="scene_plans.prompt_pairs_queued",
            target_type="render_job",
            target_id=str(job.id),
            payload=request_payload,
        )
        self.db.commit()
        from app.workers.tasks import generate_prompt_pairs_task

        generate_prompt_pairs_task.delay(str(job.id))
        return {"job_id": job.id, "job_status": job.status.value, "project_id": project.id}

    def patch_scene_plan(
        self,
        auth: AuthContext,
        project_id: str,
        scene_plan_id: str,
        payload: ScenePlanPatchRequest,
    ) -> dict[str, object]:
        project = self._get_project(project_id, auth.workspace_id)
        self._assert_mutation_rights(project, auth)
        scene_plan = self._get_scene_plan(project, scene_plan_id)
        if payload.version is not None and payload.version != scene_plan.version:
            raise ApiError(
                409,
                "scene_plan_conflict",
                "This scene plan changed since you last loaded it.",
                details={
                    "expected_version": payload.version,
                    "current_version": scene_plan.version,
                    "current": scene_plan_to_dict(scene_plan, self._list_scene_segments(scene_plan.id)),
                },
            )

        if "segments" in payload.model_fields_set and not payload.segments:
            raise ApiError(400, "invalid_scene_plan", "Scene plan updates must include at least one scene segment.")

        target_visual_preset_id = scene_plan.visual_preset_id
        target_voice_preset_id = scene_plan.voice_preset_id
        if "visual_preset_id" in payload.model_fields_set:
            target_visual_preset_id = (
                None
                if payload.visual_preset_id is None
                else self.preset_service.get_visual_preset(auth.workspace_id, payload.visual_preset_id).id
            )
        if "voice_preset_id" in payload.model_fields_set:
            target_voice_preset_id = (
                None
                if payload.voice_preset_id is None
                else self.preset_service.get_voice_preset(auth.workspace_id, payload.voice_preset_id).id
            )

        if scene_plan.approval_state == "approved":
            next_version = (
                self.db.scalar(
                    select(func.max(ScenePlan.version_number)).where(ScenePlan.project_id == project.id)
                )
                or 0
            ) + 1
            new_scene_plan = ScenePlan(
                project_id=project.id,
                based_on_script_version_id=scene_plan.based_on_script_version_id,
                created_by_user_id=UUID(auth.user_id),
                visual_preset_id=target_visual_preset_id,
                voice_preset_id=target_voice_preset_id,
                parent_scene_plan_id=scene_plan.id,
                version_number=next_version,
                source_type=ScenePlanSource.manual,
                approval_state="draft",
            )
            self.db.add(new_scene_plan)
            self.db.flush()
            segment_payloads = (
                [segment.model_dump() for segment in payload.segments]
                if "segments" in payload.model_fields_set
                else [self._scene_segment_model_to_payload(segment) for segment in self._list_scene_segments(scene_plan.id)]
            )
            segments = self._upsert_scene_plan_segments(new_scene_plan, segment_payloads)
            project.active_scene_plan_id = new_scene_plan.id
            project.stage = ProjectStage.scenes
            record_audit_event(
                self.db,
                workspace_id=project.workspace_id,
                user_id=UUID(auth.user_id),
                event_type="scene_plans.version_created",
                target_type="scene_plan",
                target_id=str(new_scene_plan.id),
                payload={"parent_scene_plan_id": str(scene_plan.id)},
            )
            self.db.commit()
            return scene_plan_to_dict(new_scene_plan, segments)

        if "visual_preset_id" in payload.model_fields_set:
            scene_plan.visual_preset_id = target_visual_preset_id
        if "voice_preset_id" in payload.model_fields_set:
            scene_plan.voice_preset_id = target_voice_preset_id
        changed_fields = set(payload.model_fields_set) - {"version"}
        if changed_fields:
            scene_plan.source_type = ScenePlanSource.manual
            scene_plan.version += 1
        scene_plan.approval_state = "draft"
        scene_plan.approved_at = None
        scene_plan.approved_by_user_id = None
        scene_plan.consistency_pack_id = None

        if "segments" in payload.model_fields_set:
            self._upsert_scene_plan_segments(
                scene_plan,
                [segment.model_dump() for segment in payload.segments],
            )
        else:
            segments = self._list_scene_segments(scene_plan.id)
            scene_plan.scene_count = len(segments)
            scene_plan.total_estimated_duration_seconds = sum(
                segment.target_duration_seconds for segment in segments
            )
            scene_plan.validation_warnings = self._scene_plan_warnings(
                total_duration_seconds=scene_plan.total_estimated_duration_seconds
            )

        project.active_scene_plan_id = scene_plan.id
        project.stage = ProjectStage.scenes
        record_audit_event(
            self.db,
            workspace_id=project.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="scene_plans.updated",
            target_type="scene_plan",
            target_id=str(scene_plan.id),
            payload={},
        )
        self.db.commit()
        self.db.refresh(scene_plan)
        return scene_plan_to_dict(scene_plan, self._list_scene_segments(scene_plan.id))

    def approve_scene_plan(
        self,
        auth: AuthContext,
        project_id: str,
        scene_plan_id: str,
    ) -> dict[str, object]:
        project = self._get_project(project_id, auth.workspace_id)
        require_workspace_review(
            auth,
            message="Only reviewers, members, or admins can approve scene plans.",
        )
        scene_plan = self._get_scene_plan(project, scene_plan_id)
        segments = self._list_scene_segments(scene_plan.id)
        if not segments:
            raise ApiError(400, "invalid_scene_plan", "Scene plan approval requires at least one scene segment.")
        if not scene_plan.visual_preset_id or not scene_plan.voice_preset_id:
            raise ApiError(
                400,
                "missing_scene_plan_presets",
                "A scene plan needs both a visual preset and a voice preset before approval.",
            )
        if any(not segment.start_image_prompt.strip() or not segment.end_image_prompt.strip() for segment in segments):
            raise ApiError(
                400,
                "prompt_pairs_incomplete",
                "Every scene segment needs both start and end image prompts before approval.",
            )

        visual_preset = self.preset_service.get_visual_preset(auth.workspace_id, str(scene_plan.visual_preset_id))
        voice_preset = self.preset_service.get_voice_preset(auth.workspace_id, str(scene_plan.voice_preset_id))
        for existing_pack in self.db.scalars(
            select(ConsistencyPack).where(
                ConsistencyPack.project_id == project.id,
                ConsistencyPack.is_active.is_(True),
            )
        ).all():
            existing_pack.is_active = False

        next_pack_version = (
            self.db.scalar(
                select(func.max(ConsistencyPack.version_number)).where(ConsistencyPack.project_id == project.id)
            )
            or 0
        ) + 1
        consistency_pack = ConsistencyPack(
            workspace_id=project.workspace_id,
            project_id=project.id,
            version_number=next_pack_version,
            is_active=True,
            state={
                "scene_plan_id": str(scene_plan.id),
                "based_on_script_version_id": str(scene_plan.based_on_script_version_id),
                "visual_preset": self._visual_preset_payload(visual_preset),
                "voice_preset": self._voice_preset_payload(voice_preset),
                "approved_segment_count": len(segments),
            },
        )
        self.db.add(consistency_pack)
        self.db.flush()

        scene_plan.consistency_pack_id = consistency_pack.id
        scene_plan.approval_state = "approved"
        scene_plan.approved_at = datetime.now(UTC)
        scene_plan.approved_by_user_id = UUID(auth.user_id)
        scene_plan.version += 1
        project.active_scene_plan_id = scene_plan.id
        project.stage = ProjectStage.frames
        record_audit_event(
            self.db,
            workspace_id=project.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="scene_plans.approved",
            target_type="scene_plan",
            target_id=str(scene_plan.id),
            payload={"consistency_pack_id": str(consistency_pack.id)},
        )
        self.db.commit()
        self.db.refresh(scene_plan)
        return scene_plan_to_dict(scene_plan, self._list_scene_segments(scene_plan.id))

    def execute_scene_plan_job(self, job_id: str, text_provider: TextProvider | None = None) -> None:
        job, step = self._get_job_and_step(job_id, StepKind.scene_plan_generation)
        project = self.db.get(Project, job.project_id)
        brief = self.db.get(ProjectBrief, project.active_brief_id if project else None) if project else None
        script = self.db.get(ScriptVersion, project.active_script_version_id if project else None) if project else None
        idea = self.db.get(IdeaCandidate, project.selected_idea_id if project else None) if project else None
        if not project or not brief or not script or not idea:
            raise AdapterError("internal", "missing_job_input", "Scene plan generation inputs are missing.")
        visual_preset = self.db.get(VisualPreset, project.default_visual_preset_id)
        voice_preset = self.db.get(VoicePreset, project.default_voice_preset_id)
        if not visual_preset or not voice_preset:
            raise AdapterError("deterministic_input", "missing_project_presets", "Project presets are required.")

        resolved_text_provider, routing_decision = (
            (text_provider, None)
            if text_provider is not None
            else RoutingService(self.db, self.settings).build_text_provider_for_workspace(project.workspace_id)
        )

        job.status = JobStatus.running
        job.started_at = datetime.now(UTC)
        step.status = JobStatus.running
        step.started_at = datetime.now(UTC)
        provider_run = ProviderRun(
            render_job_id=job.id,
            render_step_id=step.id,
            project_id=project.id,
            workspace_id=project.workspace_id,
            execution_mode=routing_decision.execution_mode if routing_decision else ExecutionMode.hosted,
            worker_id=routing_decision.worker_id if routing_decision else None,
            provider_credential_id=(
                routing_decision.provider_credential_id if routing_decision else None
            ),
            provider_name=(
                routing_decision.provider_name
                if routing_decision
                else ("azure_openai" if not self.settings.use_stub_providers else "stub_text_provider")
            ),
            provider_model=(
                routing_decision.provider_model
                if routing_decision
                else (self.settings.azure_openai_chat_deployment or "stub")
            ),
            operation="scene_plan_generation",
            request_hash=job.request_hash,
            status=ProviderRunStatus.running,
            request_payload={
                "brief": self._brief_payload(brief),
                "selected_idea": self._idea_payload(idea),
                "script": self._script_payload(script),
                "visual_preset": self._visual_preset_payload(visual_preset),
                "voice_preset": self._voice_preset_payload(voice_preset),
            },
            routing_decision_payload=self._provider_run_payload(routing_decision),
        )
        self.db.add(provider_run)
        self.db.commit()

        started = time.perf_counter()
        try:
            output = resolved_text_provider.generate_scene_plan(
                brief_payload=self._brief_payload(brief),
                selected_idea=self._idea_payload(idea),
                script_payload=self._script_payload(script),
                visual_preset=self._visual_preset_payload(visual_preset),
                voice_preset=self._voice_preset_payload(voice_preset),
            )
        except AdapterError as error:
            self._finalize_provider_run(provider_run, started_at=started, error=error)
            self.db.commit()
            raise

        scenes = output.get("scenes") or []
        if not scenes:
            raise AdapterError("internal", "empty_scene_plan_output", "Provider returned an empty scene plan.")

        next_version = (
            self.db.scalar(select(func.max(ScenePlan.version_number)).where(ScenePlan.project_id == project.id))
            or 0
        ) + 1
        scene_plan = ScenePlan(
            project_id=project.id,
            based_on_script_version_id=script.id,
            created_by_user_id=job.created_by_user_id,
            visual_preset_id=visual_preset.id,
            voice_preset_id=voice_preset.id,
            version_number=next_version,
            source_type=ScenePlanSource.generated,
            approval_state="draft",
        )
        self.db.add(scene_plan)
        self.db.flush()
        segments = self._upsert_scene_plan_segments(scene_plan, scenes)
        project.active_scene_plan_id = scene_plan.id
        project.stage = ProjectStage.scenes

        self._finalize_provider_run(provider_run, started_at=started, response_payload=output)
        job.status = JobStatus.completed
        job.completed_at = datetime.now(UTC)
        step.status = JobStatus.completed
        step.completed_at = datetime.now(UTC)
        step.output_payload = {"scene_plan_id": str(scene_plan.id)}
        self._set_step_checkpoint(step, {"scene_plan_id": str(scene_plan.id)})
        record_audit_event(
            self.db,
            workspace_id=project.workspace_id,
            user_id=job.created_by_user_id,
            event_type="scene_plans.generated",
            target_type="scene_plan",
            target_id=str(scene_plan.id),
            payload={"scene_count": len(segments)},
        )
        self.db.commit()

    def execute_prompt_pair_job(self, job_id: str, text_provider: TextProvider | None = None) -> None:
        job, step = self._get_job_and_step(job_id, StepKind.prompt_pair_generation)
        project = self.db.get(Project, job.project_id)
        if not project:
            raise AdapterError("internal", "missing_job_input", "Prompt pair generation inputs are missing.")
        scene_plan_id = job.payload.get("scene_plan_id")
        if not scene_plan_id:
            raise AdapterError("internal", "missing_job_input", "Prompt pair generation inputs are missing.")
        scene_plan = self.db.get(ScenePlan, UUID(str(scene_plan_id)))
        if not scene_plan:
            raise AdapterError("internal", "missing_job_input", "Prompt pair generation inputs are missing.")
        segments = self._list_scene_segments(scene_plan.id)
        if not segments:
            raise AdapterError("internal", "missing_job_input", "Scene plan segments are missing.")
        visual_preset = self.db.get(VisualPreset, scene_plan.visual_preset_id)
        if not visual_preset:
            raise AdapterError("deterministic_input", "missing_visual_preset", "Visual preset is required.")

        resolved_text_provider, routing_decision = (
            (text_provider, None)
            if text_provider is not None
            else RoutingService(self.db, self.settings).build_text_provider_for_workspace(project.workspace_id)
        )

        job.status = JobStatus.running
        job.started_at = datetime.now(UTC)
        step.status = JobStatus.running
        step.started_at = datetime.now(UTC)
        provider_run = ProviderRun(
            render_job_id=job.id,
            render_step_id=step.id,
            project_id=project.id,
            workspace_id=project.workspace_id,
            execution_mode=routing_decision.execution_mode if routing_decision else ExecutionMode.hosted,
            worker_id=routing_decision.worker_id if routing_decision else None,
            provider_credential_id=(
                routing_decision.provider_credential_id if routing_decision else None
            ),
            provider_name=(
                routing_decision.provider_name
                if routing_decision
                else ("azure_openai" if not self.settings.use_stub_providers else "stub_text_provider")
            ),
            provider_model=(
                routing_decision.provider_model
                if routing_decision
                else (self.settings.azure_openai_chat_deployment or "stub")
            ),
            operation="prompt_pair_generation",
            request_hash=job.request_hash,
            status=ProviderRunStatus.running,
            request_payload={
                "scene_plan": self._scene_plan_provider_payload(scene_plan, segments),
                "visual_preset": self._visual_preset_payload(visual_preset),
            },
            routing_decision_payload=self._provider_run_payload(routing_decision),
        )
        self.db.add(provider_run)
        self.db.commit()

        started = time.perf_counter()
        try:
            output = resolved_text_provider.generate_prompt_pairs(
                scene_plan_payload=self._scene_plan_provider_payload(scene_plan, segments),
                visual_preset=self._visual_preset_payload(visual_preset),
            )
        except AdapterError as error:
            self._finalize_provider_run(provider_run, started_at=started, error=error)
            self.db.commit()
            raise

        prompts_by_index = {
            int(item["scene_index"]): item for item in (output.get("segments") or [])
        }
        if len(prompts_by_index) != len(segments):
            raise AdapterError(
                "internal",
                "invalid_prompt_pair_output",
                "Provider returned prompt pairs for an unexpected number of scenes.",
            )
        for segment in segments:
            prompt_pair = prompts_by_index.get(segment.scene_index)
            if not prompt_pair:
                raise AdapterError(
                    "internal",
                    "missing_scene_prompt_pair",
                    "Provider missed one or more scene prompt pairs.",
                )
            segment.visual_prompt = str(prompt_pair.get("visual_prompt") or segment.visual_prompt)
            segment.start_image_prompt = str(prompt_pair.get("start_image_prompt") or "")
            segment.end_image_prompt = str(prompt_pair.get("end_image_prompt") or "")
            raw_warnings = list(prompt_pair.get("validation_warnings") or segment.validation_warnings)
            parsed_warnings = []
            for w in raw_warnings:
                if isinstance(w, str):
                    parsed_warnings.append({"code": "llm_warning", "message": w})
                elif isinstance(w, dict):
                    parsed_warnings.append(w)
            segment.validation_warnings = parsed_warnings

        scene_plan.validation_warnings = self._scene_plan_warnings(
            total_duration_seconds=scene_plan.total_estimated_duration_seconds
        )
        scene_plan.version += 1
        self._finalize_provider_run(provider_run, started_at=started, response_payload=output)
        job.status = JobStatus.completed
        job.completed_at = datetime.now(UTC)
        step.status = JobStatus.completed
        step.completed_at = datetime.now(UTC)
        step.output_payload = {"scene_plan_id": str(scene_plan.id)}
        self._set_step_checkpoint(step, {"scene_plan_id": str(scene_plan.id)})
        record_audit_event(
            self.db,
            workspace_id=project.workspace_id,
            user_id=job.created_by_user_id,
            event_type="scene_plans.prompt_pairs_generated",
            target_type="scene_plan",
            target_id=str(scene_plan.id),
            payload={"scene_count": len(segments)},
        )
        self.db.commit()
