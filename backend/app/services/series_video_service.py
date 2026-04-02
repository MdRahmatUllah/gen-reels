from __future__ import annotations

import re
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext
from app.core.config import Settings
from app.core.errors import AdapterError, ApiError
from app.models.entities import (
    ExportRecord,
    IdeaCandidate,
    IdeaCandidateStatus,
    IdeaSet,
    JobKind,
    JobStatus,
    Project,
    ProjectBrief,
    ProjectStage,
    RenderJob,
    RenderStep,
    ScenePlan,
    ScriptSource,
    ScriptVersion,
    Series,
    SeriesRun,
    SeriesScript,
    SeriesScriptRevision,
    SeriesVideoRun,
    SeriesVideoRunStep,
    VisualPreset,
    VoicePreset,
    WorkspaceRole,
)
from app.schemas.renders import RenderCreateRequest
from app.schemas.series import SeriesVideoRunCreateRequest
from app.services.audit_service import record_audit_event
from app.services.content_planning_service import ContentPlanningService
from app.services.permissions import require_workspace_edit
from app.services.presenters import series_video_run_to_dict
from app.services.project_profiles import (
    normalize_audio_mix_profile,
    normalize_export_profile,
    normalize_subtitle_style_profile,
)
from app.services.quick_start_service import QuickStartService
from app.services.render_service import RenderService
from app.services.series_catalog import get_catalog_option


class SeriesVideoService(QuickStartService):
    def __init__(self, db: Session, settings: Settings) -> None:
        super().__init__(db, settings)

    def _get_series(self, series_id: str, workspace_id: str) -> Series:
        record = self.db.scalar(
            select(Series).where(
                Series.id == UUID(series_id),
                Series.workspace_id == UUID(workspace_id),
            )
        )
        if not record:
            raise ApiError(404, "series_not_found", "Series not found.")
        return record

    def _get_series_script(self, series: Series, script_id: str) -> SeriesScript:
        record = self.db.scalar(
            select(SeriesScript).where(
                SeriesScript.id == UUID(script_id),
                SeriesScript.series_id == series.id,
            )
        )
        if not record:
            raise ApiError(404, "series_script_not_found", "Series script not found.")
        return record

    def _get_video_run(self, run_id: str | UUID) -> SeriesVideoRun:
        record = self.db.get(SeriesVideoRun, UUID(str(run_id)))
        if not record:
            raise ApiError(404, "series_video_run_not_found", "Series video run not found.")
        return record

    def _get_run_with_steps(
        self,
        run_id: str | UUID,
        *,
        series_id: UUID | None = None,
    ) -> tuple[SeriesVideoRun, list[SeriesVideoRunStep]]:
        run = self._get_video_run(run_id)
        if series_id and run.series_id != series_id:
            raise ApiError(404, "series_video_run_not_found", "Series video run not found.")
        steps = self.db.scalars(
            select(SeriesVideoRunStep)
            .where(SeriesVideoRunStep.series_video_run_id == run.id)
            .order_by(SeriesVideoRunStep.step_index.asc())
        ).all()
        return run, steps

    def _active_run(self, series_id: UUID) -> SeriesVideoRun | None:
        return self.db.scalar(
            select(SeriesVideoRun)
            .where(
                SeriesVideoRun.series_id == series_id,
                SeriesVideoRun.status.in_([JobStatus.queued, JobStatus.running]),
            )
            .order_by(SeriesVideoRun.created_at.desc())
        )

    def _active_script_run(self, series_id: UUID) -> SeriesRun | None:
        return self.db.scalar(
            select(SeriesRun)
            .where(
                SeriesRun.series_id == series_id,
                SeriesRun.status.in_([JobStatus.queued, JobStatus.running]),
            )
            .order_by(SeriesRun.created_at.desc())
        )

    def _idempotent_run(
        self,
        *,
        series_id: UUID,
        user_id: UUID,
        idempotency_key: str,
        request_hash: str,
    ) -> SeriesVideoRun | None:
        window_start = datetime.now(timezone.utc) - timedelta(hours=self.settings.idempotency_retention_hours)
        existing = self.db.scalar(
            select(SeriesVideoRun).where(
                SeriesVideoRun.series_id == series_id,
                SeriesVideoRun.created_by_user_id == user_id,
                SeriesVideoRun.idempotency_key == idempotency_key,
                SeriesVideoRun.created_at >= window_start,
            )
        )
        if existing:
            if existing.request_hash != request_hash:
                raise ApiError(
                    409,
                    "idempotency_conflict",
                    "This Idempotency-Key was already used for a different request.",
                )
            return existing
        return None

    def _internal_auth(self, workspace_id: UUID, user_id: UUID) -> AuthContext:
        return AuthContext(
            user_id=str(user_id),
            email="series-internal@example.com",
            workspace_id=str(workspace_id),
            workspace_role=WorkspaceRole.admin,
            session_id="series-internal",
        )

    def _slug_hashtag(self, value: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9]+", " ", value).strip()
        bits = [bit.capitalize() for bit in cleaned.split()[:3] if bit]
        return "#" + "".join(bits) if bits else ""

    def _build_viral_metadata(self, series: Series, revision: SeriesScriptRevision) -> tuple[str, str]:
        title = revision.title.strip() or f"{series.title} Episode"
        preset_label = ""
        preset = get_catalog_option("content_presets", series.preset_key or "") if series.preset_key else None
        if isinstance(preset, dict):
            preset_label = str(preset.get("label") or "")
        hashtag_bits = [
            self._slug_hashtag(title),
            self._slug_hashtag(preset_label),
            self._slug_hashtag(series.title),
        ]
        hashtags = " ".join(bit for bit in hashtag_bits if bit).strip()
        summary = revision.summary.strip() or "A fresh short-form story built for repeatable viral pacing."
        description = f"{summary}\n{hashtags}".strip()
        return title[:255], description[:500]

    def _ensure_series_visual_preset(self, series: Series, user_id: UUID) -> VisualPreset:
        option = get_catalog_option("art_styles", series.art_style_key) or {}
        name = f"Series Visual {option.get('label') or series.art_style_key}"
        preset = self.db.scalar(
            select(VisualPreset).where(
                VisualPreset.workspace_id == series.workspace_id,
                VisualPreset.name == name,
            )
        )
        if preset:
            return preset
        preset = VisualPreset(
            workspace_id=series.workspace_id,
            created_by_user_id=user_id,
            name=name[:255],
            description=str(option.get("description") or "Series visual preset."),
            prompt_prefix=f"{option.get('label') or series.art_style_key} storytelling visual.",
            style_descriptor=str(option.get("description") or ""),
            negative_prompt="No text artifacts, no warped hands, no duplicate faces.",
            camera_defaults="Cinematic framing for 9:16 short-form.",
            color_palette="Series-defined palette.",
            reference_notes=f"Derived from series art style key {series.art_style_key}.",
        )
        self.db.add(preset)
        self.db.flush()
        return preset

    def _ensure_series_voice_preset(self, series: Series, user_id: UUID) -> VoicePreset:
        option = get_catalog_option("voices", series.voice_key) or {}
        name = f"Series Voice {option.get('label') or series.voice_key}"
        desired_provider_voice = str(option.get("provider_voice") or self.settings.azure_openai_speech_voice or "alloy")
        desired_tone = str(option.get("description") or "Confident short-form narration.")
        preset = self.db.scalar(
            select(VoicePreset).where(
                VoicePreset.workspace_id == series.workspace_id,
                VoicePreset.name == name,
            )
        )
        if preset:
            if preset.provider_voice != desired_provider_voice:
                preset.provider_voice = desired_provider_voice
            if preset.tone_descriptor != desired_tone:
                preset.tone_descriptor = desired_tone
            if preset.language_code != "en-US":
                preset.language_code = "en-US"
            return preset
        preset = VoicePreset(
            workspace_id=series.workspace_id,
            created_by_user_id=user_id,
            name=name[:255],
            description=str(option.get("description") or "Series voice preset."),
            provider_voice=desired_provider_voice,
            tone_descriptor=desired_tone,
            language_code="en-US",
            pace_multiplier=1.0,
        )
        self.db.add(preset)
        self.db.flush()
        return preset

    def _ensure_hidden_project(self, series: Series, slot: SeriesScript, user_id: UUID) -> Project:
        project = self.db.scalar(select(Project).where(Project.series_script_id == slot.id))
        if project:
            return project
        visual_preset = self._ensure_series_visual_preset(series, user_id)
        voice_preset = self._ensure_series_voice_preset(series, user_id)
        project = Project(
            workspace_id=series.workspace_id,
            owner_user_id=user_id,
            title=f"{series.title} Episode {slot.sequence_number}"[:255],
            client=None,
            aspect_ratio="9:16",
            duration_target_sec=90,
            subtitle_style_profile=normalize_subtitle_style_profile(None),
            export_profile=normalize_export_profile(None),
            audio_mix_profile=normalize_audio_mix_profile(None),
            stage=ProjectStage.brief,
            default_visual_preset_id=visual_preset.id,
            default_voice_preset_id=voice_preset.id,
            is_internal=True,
            series_script_id=slot.id,
        )
        self.db.add(project)
        self.db.flush()
        return project

    def _sync_hidden_project(
        self,
        *,
        series: Series,
        slot: SeriesScript,
        revision: SeriesScriptRevision,
        project: Project,
        user_id: UUID,
    ) -> None:
        visual_preset = self._ensure_series_visual_preset(series, user_id)
        voice_preset = self._ensure_series_voice_preset(series, user_id)
        project.default_visual_preset_id = visual_preset.id
        project.default_voice_preset_id = voice_preset.id
        project.title = (revision.video_title or revision.title or project.title)[:255]

        next_brief_version = (
            self.db.scalar(select(func.max(ProjectBrief.version_number)).where(ProjectBrief.project_id == project.id))
            or 0
        ) + 1
        brief = ProjectBrief(
            project_id=project.id,
            version_number=next_brief_version,
            created_by_user_id=user_id,
            objective=f"Create a viral short-form video for {series.title} episode {slot.sequence_number}.",
            hook=revision.title,
            target_audience="Short-form viewers who respond to fast, visual storytelling.",
            call_to_action="Encourage the viewer to follow for the next episode.",
            brand_north_star=(series.description or revision.summary or "Clear, dramatic short-form storytelling.")[:1000],
            guardrails=["Keep the pacing tight and the payoff explicit."],
            must_include=[revision.title],
            approval_steps=["Series automation"],
        )
        self.db.add(brief)
        self.db.flush()

        idea_set = IdeaSet(
            project_id=project.id,
            source_brief_id=brief.id,
            created_by_user_id=user_id,
            prompt_input={"series_id": str(series.id), "series_script_id": str(slot.id)},
        )
        self.db.add(idea_set)
        self.db.flush()
        candidate = IdeaCandidate(
            idea_set_id=idea_set.id,
            project_id=project.id,
            title=(revision.video_title or revision.title)[:255],
            hook=revision.summary or revision.title,
            summary=revision.summary or revision.title,
            tags=[series.content_mode, series.preset_key or series.art_style_key],
            order_index=1,
            status=IdeaCandidateStatus.selected,
        )
        self.db.add(candidate)
        self.db.flush()

        next_script_version = (
            self.db.scalar(select(func.max(ScriptVersion.version_number)).where(ScriptVersion.project_id == project.id))
            or 0
        ) + 1
        script = ScriptVersion(
            project_id=project.id,
            based_on_idea_id=candidate.id,
            created_by_user_id=user_id,
            version_number=next_script_version,
            version=1,
            source_type=ScriptSource.generated,
            approval_state="draft",
            total_words=revision.total_words,
            estimated_duration_seconds=revision.estimated_duration_seconds,
            reading_time_label=revision.reading_time_label,
            lines=list(revision.lines or []),
        )
        self.db.add(script)
        self.db.flush()

        project.active_brief_id = brief.id
        project.selected_idea_id = candidate.id
        project.active_script_version_id = script.id
        project.active_scene_plan_id = None
        self._approve_script_version(project, script, user_id)
        self.db.commit()

    def _eligible_slots(
        self,
        series_id: UUID,
        selected_ids: set[UUID] | None = None,
    ) -> list[tuple[SeriesScript, SeriesScriptRevision]]:
        scripts = self.db.scalars(
            select(SeriesScript)
            .where(SeriesScript.series_id == series_id)
            .order_by(SeriesScript.sequence_number.asc())
        ).all()
        eligible: list[tuple[SeriesScript, SeriesScriptRevision]] = []
        for script in scripts:
            if selected_ids and script.id not in selected_ids:
                continue
            if not script.approved_revision_id:
                continue
            if script.approved_revision_id == script.published_revision_id and script.published_export_id:
                continue
            revision = self.db.get(SeriesScriptRevision, script.approved_revision_id)
            if not revision:
                continue
            eligible.append((script, revision))
        return eligible

    def _step_job_key(self, step: SeriesVideoRunStep, kind: str) -> str:
        return f"series-video-{kind}-{step.id}"

    def _find_step_job(
        self,
        *,
        project_id: UUID,
        user_id: UUID,
        job_kind: JobKind,
        idempotency_key: str,
    ) -> RenderJob | None:
        return self.db.scalar(
            select(RenderJob).where(
                RenderJob.project_id == project_id,
                RenderJob.created_by_user_id == user_id,
                RenderJob.job_kind == job_kind,
                RenderJob.idempotency_key == idempotency_key,
            )
        )

    def get_video_run(self, auth: AuthContext, series_id: str, run_id: str) -> dict[str, object]:
        series = self._get_series(series_id, auth.workspace_id)
        run, steps = self._get_run_with_steps(run_id, series_id=series.id)
        if run.status in {JobStatus.queued, JobStatus.running}:
            active_step = next(
                (
                    item
                    for item in steps
                    if item.status in {JobStatus.running, JobStatus.review, JobStatus.queued}
                    and item.render_job_id
                ),
                None,
            )
            if active_step and active_step.render_job_id:
                self._sync_render_progress(auth, active_step.render_job_id, active_step)
                run, steps = self._get_run_with_steps(run_id, series_id=series.id)
        return series_video_run_to_dict(run, steps)

    def queue_video_run(
        self,
        auth: AuthContext,
        series_id: str,
        payload: SeriesVideoRunCreateRequest,
        *,
        idempotency_key: str,
    ) -> dict[str, object]:
        if not idempotency_key:
            raise ApiError(400, "missing_idempotency_key", "Idempotency-Key header is required.")
        require_workspace_edit(auth, message="Only workspace members or admins can create series videos.")
        series = self._get_series(series_id, auth.workspace_id)
        if self._active_script_run(series.id):
            raise ApiError(409, "series_run_active", "Wait for the current script generation run to finish first.")
        active_run = self._active_run(series.id)
        if active_run:
            raise ApiError(409, "series_video_run_active", "This series already has an active video batch.")

        selected_ids = {UUID(item) for item in payload.series_script_ids} if payload.series_script_ids else None
        request_payload = {
            "series_id": series_id,
            "series_script_ids": sorted(str(item) for item in selected_ids) if selected_ids else [],
        }
        request_hash = self._hash_request(request_payload)
        existing = self._idempotent_run(
            series_id=series.id,
            user_id=UUID(auth.user_id),
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if existing:
            return self.get_video_run(auth, series_id, str(existing.id))

        eligible = self._eligible_slots(series.id, selected_ids=selected_ids)
        if not eligible:
            raise ApiError(400, "no_series_videos_eligible", "No approved scripts are eligible for video creation.")

        run = SeriesVideoRun(
            series_id=series.id,
            workspace_id=series.workspace_id,
            created_by_user_id=UUID(auth.user_id),
            status=JobStatus.queued,
            requested_video_count=len(eligible),
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            payload=request_payload,
        )
        self.db.add(run)
        self.db.flush()
        for index, (slot, revision) in enumerate(eligible, start=1):
            self.db.add(
                SeriesVideoRunStep(
                    series_video_run_id=run.id,
                    series_id=series.id,
                    series_script_id=slot.id,
                    series_script_revision_id=revision.id,
                    step_index=index,
                    sequence_number=slot.sequence_number,
                    status=JobStatus.queued,
                    phase="queued",
                    input_payload={
                        "series_script_id": str(slot.id),
                        "series_script_revision_id": str(revision.id),
                        "sequence_number": slot.sequence_number,
                    },
                )
            )
        record_audit_event(
            self.db,
            workspace_id=series.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="series.video_run_queued",
            target_type="series_video_run",
            target_id=str(run.id),
            payload=request_payload,
        )
        self.db.commit()

        from app.workers.tasks import generate_series_video_run_task

        generate_series_video_run_task.delay(str(run.id))
        self.db.expire_all()
        return self.get_video_run(auth, series_id, str(run.id))

    def _wait_for_job(self, job_id: UUID, *, timeout_seconds: int = 900) -> RenderJob:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            self.db.expire_all()
            job = self.db.get(RenderJob, job_id)
            if not job:
                raise AdapterError("internal", "job_not_found", "Background job not found.")
            if job.status == JobStatus.completed:
                return job
            if job.status in {JobStatus.failed, JobStatus.cancelled, JobStatus.blocked}:
                raise AdapterError(
                    "internal",
                    job.error_code or "series_video_job_failed",
                    job.error_message or "Series video planning job failed.",
                )
            time.sleep(1)
        raise AdapterError("transient", "series_video_job_timeout", "Timed out while waiting for a planning job.")

    def _sync_render_progress(
        self,
        auth: AuthContext,
        render_job_id: UUID,
        step: SeriesVideoRunStep,
    ) -> RenderJob:
        render_service = RenderService(self.db, self.settings)
        render_job = self.db.get(RenderJob, render_job_id)
        assert render_job is not None
        events = render_service.list_render_events(auth, str(render_job_id), after_sequence=step.last_render_event_sequence)
        if events:
            step.last_render_event_sequence = max(event["sequence_number"] for event in events)
        render_steps = self.db.scalars(
            select(RenderStep)
            .where(RenderStep.render_job_id == render_job_id)
            .order_by(RenderStep.step_index.asc())
        ).all()
        active_step = next(
            (
                item
                for item in render_steps
                if item.status in {JobStatus.running, JobStatus.review, JobStatus.queued}
            ),
            None,
        )
        scene_plan = self.db.get(ScenePlan, render_job.scene_plan_id) if render_job.scene_plan_id else None
        step.current_scene_count = scene_plan.scene_count if scene_plan else step.current_scene_count
        if active_step:
            scene_index = active_step.input_payload.get("scene_index") if active_step.input_payload else None
            if scene_index is not None:
                step.current_scene_index = int(scene_index)
            if active_step.step_kind.value == "frame_pair_generation":
                step.phase = "generating_frames"
            elif active_step.step_kind.value == "narration_generation":
                step.phase = "generating_voiceover"
            else:
                step.phase = "rendering"
        elif render_job.status == JobStatus.completed:
            step.phase = "completed"
        self.db.commit()
        return render_job

    def _wait_for_render(self, auth: AuthContext, render_job_id: UUID, step: SeriesVideoRunStep) -> RenderJob:
        deadline = time.monotonic() + 3600
        render_service = RenderService(self.db, self.settings)
        while time.monotonic() < deadline:
            self.db.expire_all()
            render_job = self.db.get(RenderJob, render_job_id)
            if not render_job:
                raise AdapterError("internal", "render_job_not_found", "Render job not found.")
            render_job = self._sync_render_progress(auth, render_job_id, step)
            if render_job.status == JobStatus.review:
                render_service.auto_approve_frame_pairs(auth, str(render_job_id))
            if render_job.status == JobStatus.completed:
                return render_job
            if render_job.status in {JobStatus.failed, JobStatus.blocked, JobStatus.cancelled}:
                raise AdapterError(
                    "internal",
                    render_job.error_code or "series_render_failed",
                    render_job.error_message or "Series render failed.",
                )
            time.sleep(1)
        raise AdapterError("transient", "series_render_timeout", "Timed out while waiting for render completion.")

    def execute_video_run(self, run_id: str) -> None:
        run, steps = self._get_run_with_steps(run_id)
        series = self.db.get(Series, run.series_id)
        if not series:
            raise AdapterError("internal", "series_not_found", "Series not found.")
        pending_steps = [step for step in steps if step.status != JobStatus.completed]
        if not pending_steps:
            run.status = JobStatus.completed
            run.completed_at = run.completed_at or datetime.now(timezone.utc)
            self.db.commit()
            return

        auth = self._internal_auth(run.workspace_id, run.created_by_user_id)
        planning_service = ContentPlanningService(self.db, self.settings)
        render_service = RenderService(self.db, self.settings)
        run.status = JobStatus.running
        run.started_at = run.started_at or datetime.now(timezone.utc)
        run.error_code = None
        run.error_message = None
        run.failed_video_count = 0
        run.completed_at = None
        self.db.commit()

        for step in pending_steps:
            slot = self.db.get(SeriesScript, step.series_script_id)
            revision = self.db.get(SeriesScriptRevision, step.series_script_revision_id)
            if not slot or not revision:
                raise AdapterError("internal", "series_script_not_found", "Series script inputs are missing.")

            step.status = JobStatus.running
            step.phase = "preparing_project"
            step.error_code = None
            step.error_message = None
            step.started_at = step.started_at or datetime.now(timezone.utc)
            if not revision.video_title.strip() or not revision.video_description.strip():
                revision.video_title, revision.video_description = self._build_viral_metadata(series, revision)
            self.db.commit()

            project = self.db.get(Project, step.hidden_project_id) if step.hidden_project_id else None
            if not project:
                project = self._ensure_hidden_project(series, slot, run.created_by_user_id)
            step.hidden_project_id = project.id

            scene_job_key = self._step_job_key(step, "scene")
            prompt_job_key = self._step_job_key(step, "prompts")
            render_job_key = self._step_job_key(step, "render")
            existing_scene_job = self._find_step_job(
                project_id=project.id,
                user_id=run.created_by_user_id,
                job_kind=JobKind.scene_plan_generation,
                idempotency_key=scene_job_key,
            )
            existing_prompt_job = self._find_step_job(
                project_id=project.id,
                user_id=run.created_by_user_id,
                job_kind=JobKind.prompt_pair_generation,
                idempotency_key=prompt_job_key,
            )
            existing_render_job = self.db.get(RenderJob, step.render_job_id) if step.render_job_id else None
            if not existing_render_job:
                existing_render_job = self._find_step_job(
                    project_id=project.id,
                    user_id=run.created_by_user_id,
                    job_kind=JobKind.render_generation,
                    idempotency_key=render_job_key,
                )
                if existing_render_job:
                    step.render_job_id = existing_render_job.id

            if not existing_scene_job and not existing_prompt_job and not existing_render_job:
                self._sync_hidden_project(
                    series=series,
                    slot=slot,
                    revision=revision,
                    project=project,
                    user_id=run.created_by_user_id,
                )
                self.db.refresh(project)

            if existing_render_job:
                if existing_render_job.script_version_id:
                    project.active_script_version_id = existing_render_job.script_version_id
                if existing_render_job.scene_plan_id:
                    project.active_scene_plan_id = existing_render_job.scene_plan_id
                step.phase = "rendering"
                self.db.commit()
                completed_render = self._wait_for_render(auth, existing_render_job.id, step)
            else:
                step.phase = "generating_scenes"
                self.db.commit()
                scene_job_id: UUID
                if existing_scene_job:
                    scene_job_id = existing_scene_job.id
                else:
                    scene_job = planning_service.queue_scene_plan_generation(
                        auth,
                        str(project.id),
                        idempotency_key=scene_job_key,
                        include_internal=True,
                    )
                    scene_job_id = UUID(str(scene_job["job_id"]))
                self._wait_for_job(scene_job_id)
                scene_plan_id = project.active_scene_plan_id or self.db.scalar(
                    select(ScenePlan.id)
                    .where(ScenePlan.project_id == project.id)
                    .order_by(ScenePlan.created_at.desc())
                )
                if not scene_plan_id:
                    raise AdapterError("internal", "scene_plan_not_found", "Scene plan was not created.")
                scene_plan = self.db.get(ScenePlan, scene_plan_id)
                if scene_plan:
                    step.current_scene_count = scene_plan.scene_count
                self.db.commit()

                if existing_prompt_job:
                    self._wait_for_job(existing_prompt_job.id)
                elif scene_plan and scene_plan.approval_state != "approved":
                    prompt_job = planning_service.queue_prompt_pair_generation(
                        auth,
                        str(project.id),
                        str(scene_plan_id),
                        idempotency_key=prompt_job_key,
                        include_internal=True,
                    )
                    self._wait_for_job(UUID(str(prompt_job["job_id"])))
                if scene_plan and scene_plan.approval_state != "approved":
                    planning_service.approve_scene_plan(
                        auth,
                        str(project.id),
                        str(scene_plan_id),
                        include_internal=True,
                    )

                step.phase = "rendering"
                self.db.commit()
                render_response = render_service.queue_render_job(
                    auth,
                    str(project.id),
                    RenderCreateRequest(
                        scene_plan_id=str(scene_plan_id),
                        allow_export_without_music=True,
                        render_mode="slide",
                        subtitle_style_profile={"burn_in": False, "preset": "off"},
                        audio_mix_profile={"music_enabled": False, "music_track_name": "", "music_ducking": "-12 dB"},
                    ),
                    idempotency_key=render_job_key,
                    include_internal=True,
                )
                render_job_id = UUID(str(render_response["job_id"]))
                step.render_job_id = render_job_id
                self.db.commit()
                completed_render = self._wait_for_render(auth, render_job_id, step)

            export = self.db.scalar(
                select(ExportRecord)
                .where(
                    ExportRecord.render_job_id == completed_render.id,
                    ExportRecord.status == "completed",
                )
                .order_by(ExportRecord.created_at.desc())
            )
            if not export:
                raise AdapterError("internal", "series_export_missing", "Render completed without an export.")

            slot.published_revision_id = revision.id
            slot.approved_revision_id = revision.id
            slot.published_project_id = project.id
            slot.published_render_job_id = completed_render.id
            slot.published_export_id = export.id
            step.status = JobStatus.completed
            step.phase = "completed"
            step.output_payload = {
                "project_id": str(project.id),
                "render_job_id": str(completed_render.id),
                "export_id": str(export.id),
            }
            step.completed_at = datetime.now(timezone.utc)
            run.completed_video_count += 1
            record_audit_event(
                self.db,
                workspace_id=run.workspace_id,
                user_id=run.created_by_user_id,
                event_type="series.video_completed",
                target_type="series_script",
                target_id=str(slot.id),
                payload={"series_video_run_id": str(run.id), "render_job_id": str(completed_render.id)},
            )
            self.db.commit()

        run.status = JobStatus.completed
        run.completed_at = datetime.now(timezone.utc)
        run.error_code = None
        run.error_message = None
        self.db.commit()

    def mark_video_run_retry(self, run_id: str, error: AdapterError) -> None:
        run = self.db.get(SeriesVideoRun, UUID(run_id))
        if not run:
            return
        step = self.db.scalar(
            select(SeriesVideoRunStep)
            .where(
                SeriesVideoRunStep.series_video_run_id == run.id,
                SeriesVideoRunStep.status.in_([JobStatus.running, JobStatus.failed]),
            )
            .order_by(SeriesVideoRunStep.step_index.asc())
        )
        run.status = JobStatus.queued
        run.retry_count += 1
        run.error_code = error.code
        run.error_message = error.message
        run.completed_at = None
        if step:
            step.status = JobStatus.queued
            step.error_code = error.code
            step.error_message = error.message
            step.completed_at = None
        self.db.commit()

    def mark_video_run_failed(self, run_id: str, error: AdapterError) -> None:
        run = self.db.get(SeriesVideoRun, UUID(run_id))
        if not run:
            return
        step = self.db.scalar(
            select(SeriesVideoRunStep)
            .where(
                SeriesVideoRunStep.series_video_run_id == run.id,
                SeriesVideoRunStep.status.in_([JobStatus.running, JobStatus.queued]),
            )
            .order_by(SeriesVideoRunStep.step_index.asc())
        )
        run.status = JobStatus.failed
        run.error_code = error.code
        run.error_message = error.message
        run.failed_video_count = max(
            int(
                self.db.scalar(
                    select(func.count())
                    .select_from(SeriesVideoRunStep)
                    .where(
                        SeriesVideoRunStep.series_video_run_id == run.id,
                        SeriesVideoRunStep.status == JobStatus.failed,
                    )
                )
                or 0
            ),
            1,
        )
        run.completed_at = datetime.now(timezone.utc)
        if step:
            step.status = JobStatus.failed
            step.error_code = error.code
            step.error_message = error.message
            step.completed_at = datetime.now(timezone.utc)
        self.db.commit()
