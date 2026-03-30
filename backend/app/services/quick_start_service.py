from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select

from app.api.deps import AuthContext
from app.core.errors import AdapterError, ApiError
from app.models.entities import (
    BrandKit,
    ConsistencyPack,
    IdeaCandidate,
    IdeaCandidateStatus,
    IdeaSet,
    JobKind,
    JobStatus,
    Project,
    ProjectBrief,
    ProjectStage,
    ProviderRun,
    ProviderRunStatus,
    RenderJob,
    RenderStep,
    ScenePlan,
    ScenePlanSource,
    ScriptSource,
    ScriptVersion,
    StepKind,
    TemplateVersion,
    VisualPreset,
    VoicePreset,
)
from app.schemas.projects import QuickStartCreateRequest
from app.services.audit_service import record_audit_event
from app.services.brand_kit_service import BrandKitService
from app.services.content_planning_service import ContentPlanningService
from app.services.moderation_service import moderate_text_or_raise
from app.services.permissions import require_workspace_edit
from app.services.presenters import job_to_dict, project_to_dict
from app.services.project_profiles import (
    normalize_audio_mix_profile,
    normalize_export_profile,
    normalize_subtitle_style_profile,
)
from app.services.routing_service import RoutingService
from app.services.template_service import TemplateService

STUDIO_DEFAULT_PROJECT_DEFAULTS = {
    "aspect_ratio": "9:16",
    "duration_target_sec": 90,
    "subtitle_style_profile": {
        "font_size": 60,
        "placement": {"y_pct": 78},
        "text_color": "#FFF8E8",
    },
    "export_profile": {
        "caption_burn_in": True,
        "video_bitrate_kbps": 12000,
    },
    "audio_mix_profile": {
        "crossfade_duration_seconds": 0.35,
        "music_gain_db": -18.0,
        "ducking_gain_db": -10.0,
    },
}

STUDIO_DEFAULT_VISUAL_PRESET = {
    "name": "Studio Default Visual",
    "description": "Balanced studio starter for fast short-form concept generation.",
    "prompt_prefix": "Short-form social video storyboard.",
    "style_descriptor": "Clean, premium, high-clarity commercial framing.",
    "negative_prompt": "Avoid clutter, distorted anatomy, and unreadable props.",
    "camera_defaults": "Commercial product cinematography with controlled motion.",
    "color_palette": "Neutral highlights with confident brand-led contrast.",
    "reference_notes": "Optimize for strong first-frame clarity and short-form retention.",
}

STUDIO_DEFAULT_VOICE_PRESET = {
    "name": "Studio Default Voice",
    "description": "Balanced narration starter for creator-first short-form videos.",
    "provider_voice": "alloy",
    "tone_descriptor": "Clear, confident, warm, and concise.",
    "language_code": "en-US",
    "pace_multiplier": 1.0,
}


class QuickStartService(ContentPlanningService):
    def _bootstrap_step_order(self) -> list[StepKind]:
        return [
            StepKind.brief_generation,
            StepKind.idea_generation,
            StepKind.script_generation,
            StepKind.scene_plan_generation,
            StepKind.prompt_pair_generation,
        ]

    def _project_progress_path(self, project_id: str | UUID) -> str:
        return f"/app/projects/{project_id}/quick-start"

    def _project_completion_path(self, project_id: str | UUID) -> str:
        return f"/app/projects/{project_id}/scenes"

    def _job_summary(self, job: RenderJob) -> dict[str, object]:
        raw = job_to_dict(job)
        return {
            "id": raw["id"],
            "job_kind": raw["job_kind"],
            "status": raw["status"],
            "error_code": raw["error_code"],
            "error_message": raw["error_message"],
            "created_at": raw["created_at"],
            "updated_at": raw["updated_at"],
            "completed_at": raw["completed_at"],
        }

    def _step_summary(self, step: RenderStep) -> dict[str, object]:
        return {
            "step_kind": step.step_kind.value,
            "step_index": step.step_index,
            "status": step.status.value if isinstance(step.status, JobStatus) else str(step.status),
            "error_code": step.error_code,
            "error_message": step.error_message,
            "started_at": step.started_at,
            "completed_at": step.completed_at,
        }

    def _fallback_project_title(self, idea_prompt: str) -> str:
        cleaned = " ".join(idea_prompt.strip().split())
        if not cleaned:
            return "Untitled Project"
        return " ".join(cleaned.split()[:8]).title()[:80]

    def _normalize_brief_output(self, output: dict[str, object], *, idea_prompt: str) -> dict[str, object]:
        raw_brief = output.get("brief")
        brief = raw_brief if isinstance(raw_brief, dict) else output

        def _strings(value: object) -> list[str]:
            if not isinstance(value, list):
                return []
            return [str(item).strip() for item in value if str(item).strip()]

        title = str(output.get("title") or self._fallback_project_title(idea_prompt)).strip()[:255]
        return {
            "title": title or self._fallback_project_title(idea_prompt),
            "objective": str(brief.get("objective") or f"Create a short-form video about {idea_prompt}.").strip(),
            "hook": str(brief.get("hook") or idea_prompt).strip(),
            "target_audience": str(
                brief.get("target_audience") or "Short-form viewers looking for clear, valuable storytelling."
            ).strip(),
            "call_to_action": str(
                brief.get("call_to_action") or "Invite the viewer to take the next clear step."
            ).strip(),
            "brand_north_star": str(
                brief.get("brand_north_star") or "Confident, clear, conversion-oriented creative."
            ).strip(),
            "guardrails": _strings(brief.get("guardrails")),
            "must_include": _strings(brief.get("must_include")),
            "approval_steps": _strings(brief.get("approval_steps")) or [
                "Script review",
                "Visual sign-off",
                "Final export approval",
            ],
        }

    def _transferable_snapshot_ids(self, workspace_id: UUID, version: TemplateVersion) -> dict[str, UUID | None]:
        snapshot = dict(version.snapshot_payload or {})
        project_defaults = dict(snapshot.get("project_defaults") or {})
        template_service = TemplateService(self.db)
        return {
            "brand_kit_id": template_service._transferable_preset_id(
                workspace_id, BrandKit, project_defaults.get("brand_kit_id")
            ),
            "default_visual_preset_id": template_service._transferable_preset_id(
                workspace_id, VisualPreset, project_defaults.get("default_visual_preset_id")
            ),
            "default_voice_preset_id": template_service._transferable_preset_id(
                workspace_id, VoicePreset, project_defaults.get("default_voice_preset_id")
            ),
        }

    def _resolve_starter_state(self, auth: AuthContext, payload: QuickStartCreateRequest) -> dict[str, object]:
        if payload.starter_mode == "studio_default":
            return {
                "starter_name": "Studio Default",
                "starter_description": "Balanced short-form starter with reusable defaults.",
                "source_template_version_id": None,
                "brand_kit_id": None,
                "default_visual_preset_id": None,
                "default_voice_preset_id": None,
                "aspect_ratio": STUDIO_DEFAULT_PROJECT_DEFAULTS["aspect_ratio"],
                "duration_target_sec": STUDIO_DEFAULT_PROJECT_DEFAULTS["duration_target_sec"],
                "subtitle_style_profile": normalize_subtitle_style_profile(
                    STUDIO_DEFAULT_PROJECT_DEFAULTS["subtitle_style_profile"]
                ),
                "export_profile": normalize_export_profile(STUDIO_DEFAULT_PROJECT_DEFAULTS["export_profile"]),
                "audio_mix_profile": normalize_audio_mix_profile(STUDIO_DEFAULT_PROJECT_DEFAULTS["audio_mix_profile"]),
                "starter_context": {
                    "starter_name": "Studio Default",
                    "starter_description": "Balanced short-form starter with reusable defaults.",
                    "aspect_ratio": STUDIO_DEFAULT_PROJECT_DEFAULTS["aspect_ratio"],
                    "duration_target_sec": STUDIO_DEFAULT_PROJECT_DEFAULTS["duration_target_sec"],
                },
            }

        if not payload.template_id:
            raise ApiError(400, "template_required", "A template must be selected for template-backed quick start.")

        template_service = TemplateService(self.db)
        template = template_service._get_template(auth.workspace_id, payload.template_id)
        if template.is_archived:
            raise ApiError(400, "template_archived", "Archived templates cannot be used for quick start.")
        version = template_service._latest_version(template.id)
        if not version:
            raise ApiError(400, "template_missing_version", "Template does not have a version snapshot.")

        snapshot = dict(version.snapshot_payload or {})
        project_defaults = dict(snapshot.get("project_defaults") or {})
        transferable = self._transferable_snapshot_ids(UUID(auth.workspace_id), version)
        return {
            "starter_name": template.name,
            "starter_description": template.description,
            "source_template_version_id": version.id,
            "brand_kit_id": transferable["brand_kit_id"],
            "default_visual_preset_id": transferable["default_visual_preset_id"],
            "default_voice_preset_id": transferable["default_voice_preset_id"],
            "aspect_ratio": str(project_defaults.get("aspect_ratio") or "9:16"),
            "duration_target_sec": int(project_defaults.get("duration_target_sec") or 90),
            "subtitle_style_profile": normalize_subtitle_style_profile(project_defaults.get("subtitle_style_profile")),
            "export_profile": normalize_export_profile(project_defaults.get("export_profile")),
            "audio_mix_profile": normalize_audio_mix_profile(project_defaults.get("audio_mix_profile")),
            "starter_context": {
                "starter_name": template.name,
                "starter_description": template.description,
                "aspect_ratio": str(project_defaults.get("aspect_ratio") or "9:16"),
                "duration_target_sec": int(project_defaults.get("duration_target_sec") or 90),
            },
        }

    def _ensure_default_visual_preset(self, workspace_id: UUID, user_id: UUID) -> VisualPreset:
        preset = self.db.scalar(
            select(VisualPreset).where(
                VisualPreset.workspace_id == workspace_id,
                VisualPreset.name == STUDIO_DEFAULT_VISUAL_PRESET["name"],
            )
        )
        if preset:
            if preset.is_archived:
                preset.is_archived = False
                preset.version += 1
                self.db.flush()
            return preset

        preset = VisualPreset(
            workspace_id=workspace_id,
            created_by_user_id=user_id,
            **STUDIO_DEFAULT_VISUAL_PRESET,
        )
        self.db.add(preset)
        self.db.flush()
        record_audit_event(
            self.db,
            workspace_id=workspace_id,
            user_id=user_id,
            event_type="presets.visual_created",
            target_type="visual_preset",
            target_id=str(preset.id),
            payload={"name": preset.name, "source": "quick_start_default"},
        )
        return preset

    def _ensure_default_voice_preset(self, workspace_id: UUID, user_id: UUID) -> VoicePreset:
        preset = self.db.scalar(
            select(VoicePreset).where(
                VoicePreset.workspace_id == workspace_id,
                VoicePreset.name == STUDIO_DEFAULT_VOICE_PRESET["name"],
            )
        )
        if preset:
            if preset.is_archived:
                preset.is_archived = False
                preset.version += 1
                self.db.flush()
            return preset

        preset = VoicePreset(
            workspace_id=workspace_id,
            created_by_user_id=user_id,
            **STUDIO_DEFAULT_VOICE_PRESET,
        )
        self.db.add(preset)
        self.db.flush()
        record_audit_event(
            self.db,
            workspace_id=workspace_id,
            user_id=user_id,
            event_type="presets.voice_created",
            target_type="voice_preset",
            target_id=str(preset.id),
            payload={"name": preset.name, "source": "quick_start_default"},
        )
        return preset

    def _recovery_path(self, project_id: str | UUID, failed_step: str | None) -> str:
        if failed_step == StepKind.idea_generation.value:
            return f"/app/projects/{project_id}/ideas"
        if failed_step == StepKind.script_generation.value:
            return f"/app/projects/{project_id}/script"
        if failed_step in {StepKind.scene_plan_generation.value, StepKind.prompt_pair_generation.value}:
            return f"/app/projects/{project_id}/scenes"
        return f"/app/projects/{project_id}/brief"

    def _bootstrap_status_payload(self, job: RenderJob) -> dict[str, object]:
        project = self.db.get(Project, job.project_id)
        if not project:
            raise ApiError(404, "project_not_found", "Project not found.")
        steps = self.db.scalars(
            select(RenderStep)
            .where(RenderStep.render_job_id == job.id)
            .order_by(RenderStep.step_index.asc())
        ).all()
        current = next(
            (
                step.step_kind.value
                for step in steps
                if step.status in {JobStatus.running, JobStatus.queued}
            ),
            None,
        )
        failed = next((step.step_kind.value for step in steps if step.status == JobStatus.failed), None)
        return {
            "project": project_to_dict(project),
            "job": self._job_summary(job),
            "steps": [self._step_summary(step) for step in steps],
            "current_step": failed or current,
            "completed_steps": [step.step_kind.value for step in steps if step.status == JobStatus.completed],
            "redirect_path": self._project_completion_path(project.id),
            "recovery_path": self._recovery_path(project.id, failed or current),
        }

    def _existing_quick_start_job(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        idempotency_key: str,
        request_hash: str,
    ) -> RenderJob | None:
        window_start = datetime.now(UTC) - timedelta(hours=self.settings.idempotency_retention_hours)
        existing = self.db.scalar(
            select(RenderJob)
            .where(
                RenderJob.workspace_id == workspace_id,
                RenderJob.created_by_user_id == user_id,
                RenderJob.job_kind == JobKind.project_bootstrap,
                RenderJob.idempotency_key == idempotency_key,
                RenderJob.created_at >= window_start,
            )
            .order_by(RenderJob.created_at.desc())
        )
        if existing:
            if existing.request_hash != request_hash:
                raise ApiError(
                    409,
                    "idempotency_conflict",
                    "This Idempotency-Key was already used for a different quick-start request.",
                )
            return existing
        return None

    def queue_quick_start(
        self,
        auth: AuthContext,
        payload: QuickStartCreateRequest,
        *,
        idempotency_key: str,
    ) -> dict[str, object]:
        if not idempotency_key:
            raise ApiError(400, "missing_idempotency_key", "Idempotency-Key header is required.")
        require_workspace_edit(auth, message="Only workspace members or admins can create quick-start projects.")

        request_hash = self._hash_request(payload.model_dump())
        workspace_id = UUID(auth.workspace_id)
        user_id = UUID(auth.user_id)
        existing = self._existing_quick_start_job(
            workspace_id=workspace_id,
            user_id=user_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if existing:
            return {
                "project": project_to_dict(self._get_project(str(existing.project_id), auth.workspace_id)),
                "job": self._job_summary(existing),
                "redirect_path": self._project_progress_path(existing.project_id),
            }

        starter_state = self._resolve_starter_state(auth, payload)
        project = Project(
            workspace_id=workspace_id,
            owner_user_id=user_id,
            source_template_version_id=starter_state["source_template_version_id"],
            brand_kit_id=starter_state["brand_kit_id"],
            title=self._fallback_project_title(payload.idea_prompt),
            client=None,
            aspect_ratio=str(starter_state["aspect_ratio"]),
            duration_target_sec=int(starter_state["duration_target_sec"]),
            subtitle_style_profile=normalize_subtitle_style_profile(starter_state["subtitle_style_profile"]),
            export_profile=normalize_export_profile(starter_state["export_profile"]),
            audio_mix_profile=normalize_audio_mix_profile(starter_state["audio_mix_profile"]),
            stage=ProjectStage.brief,
            default_visual_preset_id=starter_state["default_visual_preset_id"],
            default_voice_preset_id=starter_state["default_voice_preset_id"],
        )
        self.db.add(project)
        self.db.flush()

        brand_kit_service = BrandKitService(self.db)
        active_brand_kit = (
            brand_kit_service.get_brand_kit(auth.workspace_id, str(project.brand_kit_id))
            if project.brand_kit_id
            else None
        )
        brand_kit_service.apply_brand_kit_defaults(project, active_brand_kit)

        if not project.default_visual_preset_id:
            project.default_visual_preset_id = self._ensure_default_visual_preset(workspace_id, user_id).id
        if not project.default_voice_preset_id:
            project.default_voice_preset_id = self._ensure_default_voice_preset(workspace_id, user_id).id

        progress_path = self._project_progress_path(project.id)
        completion_path = self._project_completion_path(project.id)
        request_payload = {
            "idea_prompt": payload.idea_prompt,
            "starter_mode": payload.starter_mode,
            "template_id": payload.template_id,
            "starter_context": starter_state["starter_context"],
            "progress_path": progress_path,
            "completion_path": completion_path,
        }
        job = RenderJob(
            workspace_id=workspace_id,
            project_id=project.id,
            created_by_user_id=user_id,
            job_kind=JobKind.project_bootstrap,
            queue_name="planning",
            status=JobStatus.queued,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            payload=request_payload,
        )
        self.db.add(job)
        self.db.flush()
        for index, step_kind in enumerate(self._bootstrap_step_order(), start=1):
            self.db.add(
                RenderStep(
                    render_job_id=job.id,
                    project_id=project.id,
                    step_kind=step_kind,
                    step_index=index,
                    status=JobStatus.queued,
                    input_payload=request_payload,
                )
            )

        record_audit_event(
            self.db,
            workspace_id=workspace_id,
            user_id=user_id,
            event_type="projects.quick_start_queued",
            target_type="project",
            target_id=str(project.id),
            payload={"starter_mode": payload.starter_mode},
        )
        self.db.commit()

        from app.workers.tasks import bootstrap_project_task

        bootstrap_project_task.delay(str(job.id))
        return {
            "project": project_to_dict(self._get_project(str(project.id), auth.workspace_id)),
            "job": self._job_summary(self.db.get(RenderJob, job.id)),
            "redirect_path": progress_path,
        }

    def get_quick_start_status(self, auth: AuthContext, project_id: str) -> dict[str, object]:
        project = self._get_project(project_id, auth.workspace_id)
        job = self.db.scalar(
            select(RenderJob)
            .where(
                RenderJob.project_id == project.id,
                RenderJob.job_kind == JobKind.project_bootstrap,
            )
            .order_by(RenderJob.created_at.desc())
        )
        if not job:
            raise ApiError(404, "quick_start_not_found", "No quick-start job exists for this project.")
        return self._bootstrap_status_payload(job)

    def _bootstrap_job_and_steps(self, job_id: str) -> tuple[RenderJob, Project, dict[StepKind, RenderStep]]:
        job = self.db.get(RenderJob, UUID(job_id))
        if not job or job.job_kind != JobKind.project_bootstrap:
            raise ApiError(404, "job_not_found", "Quick-start job not found.")
        project = self.db.get(Project, job.project_id)
        if not project:
            raise AdapterError("internal", "missing_project", "Quick-start job project is missing.")
        steps = {
            step.step_kind: step
            for step in self.db.scalars(
                select(RenderStep)
                .where(RenderStep.render_job_id == job.id)
                .order_by(RenderStep.step_index.asc())
            ).all()
        }
        return job, project, steps

    def _active_bootstrap_step(self, job: RenderJob) -> RenderStep | None:
        running = self.db.scalar(
            select(RenderStep)
            .where(
                RenderStep.render_job_id == job.id,
                RenderStep.status == JobStatus.running,
            )
            .order_by(RenderStep.step_index.asc())
        )
        if running:
            return running
        return self.db.scalar(
            select(RenderStep)
            .where(
                RenderStep.render_job_id == job.id,
                RenderStep.status == JobStatus.queued,
            )
            .order_by(RenderStep.step_index.asc())
        )

    def mark_quick_start_retry(self, job_id: str, error: AdapterError) -> None:
        job = self.db.get(RenderJob, UUID(job_id))
        if not job:
            return
        step = self._active_bootstrap_step(job)
        job.status = JobStatus.queued
        job.retry_count += 1
        job.error_code = error.code
        job.error_message = error.message
        if step:
            step.status = JobStatus.queued
            step.error_code = error.code
            step.error_message = error.message
        self.db.commit()

    def mark_quick_start_failed(self, job_id: str, error: AdapterError) -> None:
        job = self.db.get(RenderJob, UUID(job_id))
        if not job:
            return
        step = self._active_bootstrap_step(job)
        now = datetime.now(UTC)
        job.status = JobStatus.failed
        job.error_code = error.code
        job.error_message = error.message
        job.completed_at = now
        if step:
            step.status = JobStatus.failed
            step.error_code = error.code
            step.error_message = error.message
            step.completed_at = now
        self.db.commit()

    def _run_text_operation(
        self,
        *,
        job: RenderJob,
        step: RenderStep,
        project: Project,
        operation: str,
        request_payload: dict[str, object],
        execute,
    ) -> dict[str, object]:
        text_provider, routing_decision = RoutingService(self.db, self.settings).build_text_provider_for_workspace(
            project.workspace_id
        )
        provider_run = ProviderRun(
            render_job_id=job.id,
            render_step_id=step.id,
            project_id=project.id,
            workspace_id=project.workspace_id,
            execution_mode=self._provider_execution_mode(routing_decision),
            worker_id=routing_decision.worker_id if routing_decision else None,
            provider_credential_id=(routing_decision.provider_credential_id if routing_decision else None),
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
            operation=operation,
            request_hash=job.request_hash,
            status=ProviderRunStatus.running,
            request_payload=request_payload,
            routing_decision_payload=self._provider_run_payload(routing_decision),
        )
        self.db.add(provider_run)
        self.db.commit()

        started = time.perf_counter()
        try:
            output = execute(text_provider)
        except AdapterError as error:
            self._finalize_provider_run(provider_run, started_at=started, error=error)
            self.db.commit()
            raise

        self._finalize_provider_run(provider_run, started_at=started, response_payload=output)
        return output

    def _mark_step_running(self, job: RenderJob, step: RenderStep) -> None:
        now = datetime.now(UTC)
        job.status = JobStatus.running
        job.started_at = job.started_at or now
        job.error_code = None
        job.error_message = None
        step.status = JobStatus.running
        step.started_at = step.started_at or now
        step.error_code = None
        step.error_message = None
        self.db.commit()

    def _complete_step(self, step: RenderStep, payload: dict[str, object]) -> None:
        step.status = JobStatus.completed
        step.completed_at = datetime.now(UTC)
        step.output_payload = payload
        self._set_step_checkpoint(step, payload)

    def _approve_script_version(self, project: Project, script: ScriptVersion, approved_by_user_id: UUID) -> None:
        script_text = "\n".join(
            f"{line.get('beat', '')}\n{line.get('narration', '')}\n{line.get('caption', '')}"
            for line in (script.lines or [])
        )
        BrandKitService(self.db).validate_text_against_brand_kit(project, script_text)
        script.approval_state = "approved"
        script.approved_at = datetime.now(UTC)
        script.approved_by_user_id = approved_by_user_id
        script.version += 1
        project.active_script_version_id = script.id
        project.active_scene_plan_id = None
        project.stage = ProjectStage.scenes
        record_audit_event(
            self.db,
            workspace_id=project.workspace_id,
            user_id=approved_by_user_id,
            event_type="scripts.approved",
            target_type="script_version",
            target_id=str(script.id),
            payload={"version_number": script.version_number},
        )

    def _approve_scene_plan_version(self, project: Project, scene_plan: ScenePlan, approved_by_user_id: UUID) -> None:
        segments = self._list_scene_segments(scene_plan.id)
        if not segments:
            raise AdapterError("internal", "invalid_scene_plan", "Scene plan approval requires scene segments.")
        if any(not segment.start_image_prompt.strip() or not segment.end_image_prompt.strip() for segment in segments):
            raise AdapterError(
                "internal",
                "prompt_pairs_incomplete",
                "Every scene segment needs both start and end image prompts before approval.",
            )

        visual_preset = self.preset_service.get_visual_preset(str(project.workspace_id), str(scene_plan.visual_preset_id))
        voice_preset = self.preset_service.get_voice_preset(str(project.workspace_id), str(scene_plan.voice_preset_id))
        for existing_pack in self.db.scalars(
            select(ConsistencyPack).where(
                ConsistencyPack.project_id == project.id,
                ConsistencyPack.is_active.is_(True),
            )
        ).all():
            existing_pack.is_active = False

        next_pack_version = (
            self.db.scalar(select(func.max(ConsistencyPack.version_number)).where(ConsistencyPack.project_id == project.id))
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
        scene_plan.approved_by_user_id = approved_by_user_id
        scene_plan.version += 1
        project.active_scene_plan_id = scene_plan.id
        project.stage = ProjectStage.frames
        record_audit_event(
            self.db,
            workspace_id=project.workspace_id,
            user_id=approved_by_user_id,
            event_type="scene_plans.approved",
            target_type="scene_plan",
            target_id=str(scene_plan.id),
            payload={"consistency_pack_id": str(consistency_pack.id)},
        )

    def _execute_brief_generation_step(self, job: RenderJob, step: RenderStep, project: Project) -> None:
        idea_prompt = str(job.payload.get("idea_prompt") or "").strip()
        if not idea_prompt:
            raise AdapterError("deterministic_input", "missing_idea_prompt", "A quick-start idea prompt is required.")

        moderation_provider, _ = RoutingService(self.db, self.settings).build_moderation_provider_for_workspace(
            project.workspace_id
        )
        moderate_text_or_raise(
            self.db,
            provider=moderation_provider,
            text=idea_prompt,
            target_type="quick_start_input",
            user_id=job.created_by_user_id,
            project_id=project.id,
            workspace_id=project.workspace_id,
            target_id=str(project.id),
        )
        starter_context = dict(job.payload.get("starter_context") or {})
        output = self._run_text_operation(
            job=job,
            step=step,
            project=project,
            operation="brief_generation",
            request_payload={"idea_prompt": idea_prompt, "starter_context": starter_context},
            execute=lambda provider: provider.synthesize_brief(
                idea_prompt=idea_prompt,
                starter_context=starter_context,
            ),
        )
        brief_payload = self._normalize_brief_output(output, idea_prompt=idea_prompt)
        moderation_text = "\n".join(
            [
                brief_payload["objective"],
                brief_payload["hook"],
                brief_payload["target_audience"],
                brief_payload["call_to_action"],
                brief_payload["brand_north_star"],
                *brief_payload["guardrails"],
                *brief_payload["must_include"],
                *brief_payload["approval_steps"],
            ]
        )
        moderate_text_or_raise(
            self.db,
            provider=moderation_provider,
            text=moderation_text,
            target_type="brief_input",
            user_id=job.created_by_user_id,
            project_id=project.id,
            workspace_id=project.workspace_id,
            target_id=str(project.id),
        )
        BrandKitService(self.db).validate_text_against_brand_kit(project, moderation_text)

        next_version = (
            self.db.scalar(select(func.max(ProjectBrief.version_number)).where(ProjectBrief.project_id == project.id))
            or 0
        ) + 1
        brief = ProjectBrief(
            project_id=project.id,
            version_number=next_version,
            created_by_user_id=job.created_by_user_id,
            objective=str(brief_payload["objective"]),
            hook=str(brief_payload["hook"]),
            target_audience=str(brief_payload["target_audience"]),
            call_to_action=str(brief_payload["call_to_action"]),
            brand_north_star=str(brief_payload["brand_north_star"]),
            guardrails=list(brief_payload["guardrails"]),
            must_include=list(brief_payload["must_include"]),
            approval_steps=list(brief_payload["approval_steps"]),
        )
        self.db.add(brief)
        self.db.flush()
        project.title = str(brief_payload["title"])[:255]
        project.active_brief_id = brief.id
        project.selected_idea_id = None
        project.active_script_version_id = None
        project.active_scene_plan_id = None
        project.stage = ProjectStage.brief
        record_audit_event(
            self.db,
            workspace_id=project.workspace_id,
            user_id=job.created_by_user_id,
            event_type="project.brief_version_created",
            target_type="project_brief",
            target_id=str(brief.id),
            payload={"version_number": next_version, "source": "quick_start"},
        )
        self._complete_step(
            step,
            {
                "brief_id": str(brief.id),
                "title": project.title,
            },
        )
        self.db.commit()

    def _execute_idea_generation_step(self, job: RenderJob, step: RenderStep, project: Project) -> None:
        brief = self.db.get(ProjectBrief, project.active_brief_id) if project.active_brief_id else None
        if not brief:
            raise AdapterError("internal", "missing_brief", "Quick-start brief is missing.")

        output = self._run_text_operation(
            job=job,
            step=step,
            project=project,
            operation="idea_generation",
            request_payload=self._brief_payload(brief),
            execute=lambda provider: provider.generate_ideas(self._brief_payload(brief)),
        )
        ideas = output.get("ideas") or []
        if len(ideas) != 5:
            raise AdapterError("internal", "invalid_idea_count", "Provider returned an invalid idea count.")

        idea_set = IdeaSet(
            project_id=project.id,
            source_brief_id=brief.id,
            created_by_user_id=job.created_by_user_id,
            prompt_input=self._brief_payload(brief),
        )
        self.db.add(idea_set)
        self.db.flush()
        candidates: list[IdeaCandidate] = []
        for index, raw_idea in enumerate(ideas, start=1):
            candidate = IdeaCandidate(
                idea_set_id=idea_set.id,
                project_id=project.id,
                title=str(raw_idea["title"]),
                hook=str(raw_idea["hook"]),
                summary=str(raw_idea["summary"]),
                tags=list(raw_idea.get("tags", [])),
                order_index=index,
                status=IdeaCandidateStatus.generated,
            )
            self.db.add(candidate)
            candidates.append(candidate)
        self.db.flush()
        selected = candidates[0]
        selected.status = IdeaCandidateStatus.selected
        project.selected_idea_id = selected.id
        project.stage = ProjectStage.script
        record_audit_event(
            self.db,
            workspace_id=project.workspace_id,
            user_id=job.created_by_user_id,
            event_type="ideas.generated",
            target_type="idea_set",
            target_id=str(idea_set.id),
            payload={"source": "quick_start"},
        )
        record_audit_event(
            self.db,
            workspace_id=project.workspace_id,
            user_id=job.created_by_user_id,
            event_type="ideas.selected",
            target_type="idea_candidate",
            target_id=str(selected.id),
            payload={"source": "quick_start", "selection_rule": "top_ranked"},
        )
        self._complete_step(
            step,
            {
                "idea_set_id": str(idea_set.id),
                "selected_idea_id": str(selected.id),
            },
        )
        self.db.commit()

    def _execute_script_generation_step(self, job: RenderJob, step: RenderStep, project: Project) -> None:
        brief = self.db.get(ProjectBrief, project.active_brief_id) if project.active_brief_id else None
        idea = self.db.get(IdeaCandidate, project.selected_idea_id) if project.selected_idea_id else None
        if not brief or not idea:
            raise AdapterError("internal", "missing_job_input", "Quick-start script inputs are missing.")

        output = self._run_text_operation(
            job=job,
            step=step,
            project=project,
            operation="script_generation",
            request_payload={"brief": self._brief_payload(brief), "idea": self._idea_payload(idea)},
            execute=lambda provider: provider.generate_script(
                brief_payload=self._brief_payload(brief),
                selected_idea=self._idea_payload(idea),
            ),
        )
        lines = output.get("lines") or []
        if not lines:
            raise AdapterError("internal", "empty_script_output", "Provider returned an empty script.")

        next_version = (
            self.db.scalar(select(func.max(ScriptVersion.version_number)).where(ScriptVersion.project_id == project.id))
            or 0
        ) + 1
        estimated_duration = int(output.get("estimated_duration_seconds") or sum(int(line["duration_sec"]) for line in lines))
        total_words = sum(len(str(line["narration"]).split()) for line in lines)
        script = ScriptVersion(
            project_id=project.id,
            based_on_idea_id=idea.id,
            created_by_user_id=job.created_by_user_id,
            version_number=next_version,
            version=1,
            source_type=ScriptSource.generated,
            approval_state="draft",
            total_words=total_words,
            estimated_duration_seconds=estimated_duration,
            reading_time_label=output.get("reading_time_label") or f"{estimated_duration}s draft narration",
            lines=lines,
        )
        self.db.add(script)
        self.db.flush()
        project.active_script_version_id = script.id
        project.active_scene_plan_id = None
        project.stage = ProjectStage.script
        record_audit_event(
            self.db,
            workspace_id=project.workspace_id,
            user_id=job.created_by_user_id,
            event_type="scripts.generated",
            target_type="script_version",
            target_id=str(script.id),
            payload={"source": "quick_start"},
        )
        self._approve_script_version(project, script, UUID(str(job.created_by_user_id)))
        self._complete_step(step, {"script_version_id": str(script.id)})
        self.db.commit()

    def _execute_scene_plan_generation_step(self, job: RenderJob, step: RenderStep, project: Project) -> None:
        brief = self.db.get(ProjectBrief, project.active_brief_id) if project.active_brief_id else None
        script = self.db.get(ScriptVersion, project.active_script_version_id) if project.active_script_version_id else None
        idea = self.db.get(IdeaCandidate, project.selected_idea_id) if project.selected_idea_id else None
        visual_preset = self.db.get(VisualPreset, project.default_visual_preset_id) if project.default_visual_preset_id else None
        voice_preset = self.db.get(VoicePreset, project.default_voice_preset_id) if project.default_voice_preset_id else None
        if not brief or not script or not idea:
            raise AdapterError("internal", "missing_job_input", "Quick-start scene plan inputs are missing.")
        if not visual_preset or not voice_preset:
            raise AdapterError("deterministic_input", "missing_project_presets", "Project presets are required.")

        output = self._run_text_operation(
            job=job,
            step=step,
            project=project,
            operation="scene_plan_generation",
            request_payload={
                "brief": self._brief_payload(brief),
                "selected_idea": self._idea_payload(idea),
                "script": self._script_payload(script),
                "visual_preset": self._visual_preset_payload(visual_preset),
                "voice_preset": self._voice_preset_payload(voice_preset),
            },
            execute=lambda provider: provider.generate_scene_plan(
                brief_payload=self._brief_payload(brief),
                selected_idea=self._idea_payload(idea),
                script_payload=self._script_payload(script),
                visual_preset=self._visual_preset_payload(visual_preset),
                voice_preset=self._voice_preset_payload(voice_preset),
            ),
        )
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
        record_audit_event(
            self.db,
            workspace_id=project.workspace_id,
            user_id=job.created_by_user_id,
            event_type="scene_plans.generated",
            target_type="scene_plan",
            target_id=str(scene_plan.id),
            payload={"scene_count": len(segments), "source": "quick_start"},
        )
        self._complete_step(step, {"scene_plan_id": str(scene_plan.id)})
        self.db.commit()

    def _execute_prompt_pair_generation_step(self, job: RenderJob, step: RenderStep, project: Project) -> None:
        scene_plan = self.db.get(ScenePlan, project.active_scene_plan_id) if project.active_scene_plan_id else None
        if not scene_plan:
            raise AdapterError("internal", "missing_job_input", "Quick-start scene plan is missing.")
        segments = self._list_scene_segments(scene_plan.id)
        if not segments:
            raise AdapterError("internal", "missing_job_input", "Quick-start scene segments are missing.")
        visual_preset = self.db.get(VisualPreset, scene_plan.visual_preset_id) if scene_plan.visual_preset_id else None
        if not visual_preset:
            raise AdapterError("deterministic_input", "missing_visual_preset", "Visual preset is required.")

        output = self._run_text_operation(
            job=job,
            step=step,
            project=project,
            operation="prompt_pair_generation",
            request_payload={
                "scene_plan": self._scene_plan_provider_payload(scene_plan, segments),
                "visual_preset": self._visual_preset_payload(visual_preset),
            },
            execute=lambda provider: provider.generate_prompt_pairs(
                scene_plan_payload=self._scene_plan_provider_payload(scene_plan, segments),
                visual_preset=self._visual_preset_payload(visual_preset),
            ),
        )
        prompts_by_index = {int(item["scene_index"]): item for item in (output.get("segments") or [])}
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
        self._approve_scene_plan_version(project, scene_plan, UUID(str(job.created_by_user_id)))
        self._complete_step(
            step,
            {
                "scene_plan_id": str(scene_plan.id),
                "consistency_pack_id": str(scene_plan.consistency_pack_id),
            },
        )
        self.db.commit()

    def execute_quick_start_job(self, job_id: str) -> None:
        job, project, steps = self._bootstrap_job_and_steps(job_id)
        if job.status == JobStatus.completed:
            return
        for step_kind in self._bootstrap_step_order():
            step = steps[step_kind]
            if step.status == JobStatus.completed:
                continue
            self._mark_step_running(job, step)
            if step_kind == StepKind.brief_generation:
                self._execute_brief_generation_step(job, step, project)
            elif step_kind == StepKind.idea_generation:
                self._execute_idea_generation_step(job, step, project)
            elif step_kind == StepKind.script_generation:
                self._execute_script_generation_step(job, step, project)
            elif step_kind == StepKind.scene_plan_generation:
                self._execute_scene_plan_generation_step(job, step, project)
            elif step_kind == StepKind.prompt_pair_generation:
                self._execute_prompt_pair_generation_step(job, step, project)

        job.status = JobStatus.completed
        job.error_code = None
        job.error_message = None
        job.completed_at = datetime.now(UTC)
        self.db.commit()
