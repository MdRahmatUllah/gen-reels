from __future__ import annotations

import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from app.api.deps import AuthContext
from app.core.errors import AdapterError, ApiError
from app.integrations.azure import ModerationProvider
from app.integrations.media import GeneratedMedia, ImageProvider, MusicProvider, SpeechProvider, VideoProvider
from app.integrations.storage import StorageClient, build_storage_client
from app.models.entities import (
    Asset,
    AssetRole,
    AssetType,
    AssetVariant,
    AuditEvent,
    ConsistencyPack,
    ExportRecord,
    JobKind,
    JobStatus,
    ModerationDecision,
    ModerationEvent,
    ModerationReviewStatus,
    Project,
    ProjectStage,
    PromptHistoryEntry,
    ProviderRun,
    ProviderRunStatus,
    RenderJob,
    RenderStep,
    ScenePlan,
    SceneSegment,
    ScriptVersion,
    StepKind,
    VoicePreset,
    WorkspaceRole,
)
from app.schemas.renders import RenderCreateRequest
from app.services.audit_service import record_audit_event
from app.services.billing_service import BillingService
from app.services.generation_service import GenerationService
from app.services.notification_service import NotificationService
from app.services.project_profiles import (
    normalize_audio_mix_profile,
    normalize_export_profile,
    normalize_subtitle_style_profile,
)
from app.services.presenters import asset_to_dict, export_to_dict, job_to_dict, render_step_to_dict


class RenderService(GenerationService):
    def __init__(self, db, settings, storage: StorageClient | None = None) -> None:
        super().__init__(db, settings)
        self.storage = storage or build_storage_client(settings)

    def _get_render_job(self, render_job_id: str) -> RenderJob:
        render_job = self.db.get(RenderJob, UUID(render_job_id))
        if not render_job or render_job.job_kind != JobKind.render_generation:
            raise ApiError(404, "render_job_not_found", "Render job not found.")
        return render_job

    def _fresh_render_job(self, render_job_id: str) -> RenderJob:
        render_job = self.db.scalar(
            select(RenderJob)
            .where(RenderJob.id == UUID(render_job_id))
            .execution_options(populate_existing=True)
        )
        if not render_job or render_job.job_kind != JobKind.render_generation:
            raise ApiError(404, "render_job_not_found", "Render job not found.")
        return render_job

    def _get_render_job_for_auth(self, auth: AuthContext, render_job_id: str) -> RenderJob:
        render_job = self._get_render_job(render_job_id)
        if str(render_job.workspace_id) != auth.workspace_id:
            raise ApiError(404, "render_job_not_found", "Render job not found.")
        project = self.db.get(Project, render_job.project_id)
        if not project:
            raise ApiError(404, "project_not_found", "Project not found.")
        self._assert_mutation_rights(project, auth)
        return render_job

    def _get_scene_plan_for_render(self, project: Project, scene_plan_id: str | None) -> ScenePlan:
        resolved_scene_plan_id = scene_plan_id or (str(project.active_scene_plan_id) if project.active_scene_plan_id else None)
        if not resolved_scene_plan_id:
            raise ApiError(400, "scene_plan_required", "An approved scene plan is required before rendering.")
        scene_plan = self.db.scalar(
            select(ScenePlan).where(
                ScenePlan.id == UUID(resolved_scene_plan_id),
                ScenePlan.project_id == project.id,
            )
        )
        if not scene_plan:
            raise ApiError(404, "scene_plan_not_found", "Scene plan not found.")
        if scene_plan.approval_state != "approved":
            raise ApiError(
                400,
                "scene_plan_not_approved",
                "Only an approved scene plan can be used to create a render job.",
            )
        if not scene_plan.consistency_pack_id:
            raise ApiError(
                400,
                "consistency_pack_required",
                "The approved scene plan does not have a resolved consistency pack.",
            )
        return scene_plan

    def _scene_segments(self, scene_plan_id: UUID) -> list[SceneSegment]:
        return self.db.scalars(
            select(SceneSegment)
            .where(SceneSegment.scene_plan_id == scene_plan_id)
            .order_by(SceneSegment.scene_index.asc())
        ).all()

    def _render_steps(self, render_job_id: UUID) -> list[RenderStep]:
        return self.db.scalars(
            select(RenderStep)
            .where(RenderStep.render_job_id == render_job_id)
            .order_by(RenderStep.step_index.asc(), RenderStep.created_at.asc())
        ).all()

    def _render_assets(self, render_job_id: UUID) -> list[Asset]:
        return self.db.scalars(
            select(Asset)
            .where(Asset.render_job_id == render_job_id)
            .order_by(Asset.created_at.asc())
        ).all()

    def _render_exports(self, render_job_id: UUID) -> list[ExportRecord]:
        return self.db.scalars(
            select(ExportRecord)
            .where(ExportRecord.render_job_id == render_job_id)
            .order_by(ExportRecord.created_at.asc())
        ).all()

    def _prompt_history_for_asset(self, asset_id: UUID | None) -> PromptHistoryEntry | None:
        if not asset_id:
            return None
        return self.db.scalar(
            select(PromptHistoryEntry)
            .where(PromptHistoryEntry.asset_id == asset_id)
            .order_by(PromptHistoryEntry.created_at.desc())
        )

    def _step_key(self, step_kind: StepKind, scene_segment_id: UUID | None) -> tuple[str, str | None]:
        return step_kind.value, str(scene_segment_id) if scene_segment_id else None

    def _get_or_create_step(
        self,
        render_job: RenderJob,
        *,
        step_kind: StepKind,
        step_index: int,
        scene_segment_id: UUID | None = None,
        input_payload: dict[str, object] | None = None,
    ) -> RenderStep:
        step = self.db.scalar(
            select(RenderStep).where(
                RenderStep.render_job_id == render_job.id,
                RenderStep.step_kind == step_kind,
                RenderStep.scene_segment_id == scene_segment_id,
            )
        )
        if step:
            return step
        step = RenderStep(
            render_job_id=render_job.id,
            project_id=render_job.project_id,
            scene_segment_id=scene_segment_id,
            step_kind=step_kind,
            step_index=step_index,
            status=JobStatus.queued,
            input_payload=input_payload or {},
        )
        self.db.add(step)
        self.db.flush()
        return step

    def _asset_download_url(self, asset: Asset | None) -> str | None:
        if not asset:
            return None
        return self.storage.presigned_get_url(asset.bucket_name, asset.object_name)

    def _export_download_url(self, export: ExportRecord) -> str:
        return self.storage.presigned_get_url(export.bucket_name, export.object_name)

    def _render_detail_dict(self, render_job: RenderJob) -> dict[str, object]:
        steps = self._render_steps(render_job.id)
        assets = self._render_assets(render_job.id)
        exports = self._render_exports(render_job.id)
        return {
            **job_to_dict(render_job),
            "steps": [render_step_to_dict(step) for step in steps],
            "assets": [asset_to_dict(asset, download_url=self._asset_download_url(asset)) for asset in assets],
            "exports": [
                export_to_dict(export, download_url=self._export_download_url(export))
                for export in exports
            ],
        }

    def _resolved_project_profiles(
        self,
        *,
        render_job: RenderJob,
        project: Project | None = None,
    ) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
        subtitle_profile = normalize_subtitle_style_profile(
            render_job.payload.get("subtitle_style_profile")
            or (project.subtitle_style_profile if project else None)
        )
        export_profile = normalize_export_profile(
            render_job.payload.get("export_profile")
            or (project.export_profile if project else None)
        )
        audio_mix_profile = normalize_audio_mix_profile(
            render_job.payload.get("audio_mix_profile")
            or (project.audio_mix_profile if project else None)
        )
        return subtitle_profile, export_profile, audio_mix_profile

    def _latest_asset(
        self,
        render_job_id: UUID,
        *,
        asset_role: AssetRole,
        scene_segment_id: UUID | None = None,
    ) -> Asset | None:
        query = select(Asset).where(
            Asset.render_job_id == render_job_id,
            Asset.asset_role == asset_role,
        )
        if scene_segment_id is not None:
            query = query.where(Asset.scene_segment_id == scene_segment_id)
        return self.db.scalar(query.order_by(Asset.created_at.desc()))

    def _set_step_running(self, step: RenderStep) -> None:
        step.status = JobStatus.running
        step.error_code = None
        step.error_message = None
        step.started_at = datetime.now(UTC)
        step.completed_at = None
        self._set_step_checkpoint(step, {"status": "running"})

    def _complete_step(self, step: RenderStep, *, output_payload: dict[str, object] | None = None) -> None:
        step.output_payload = output_payload
        step.status = JobStatus.completed
        step.is_stale = False
        step.completed_at = datetime.now(UTC)
        self._set_step_checkpoint(step, output_payload or {"status": "completed"})

    def _fail_step(self, step: RenderStep, error: AdapterError) -> None:
        step.status = JobStatus.failed
        step.error_code = error.code
        step.error_message = error.message
        step.completed_at = datetime.now(UTC)
        self._set_step_checkpoint(
            step,
            {"status": "failed", "error_code": error.code, "error_message": error.message},
        )

    def _create_asset_variant(
        self,
        *,
        source_asset: Asset,
        variant_asset: Asset,
        variant_kind: str,
        metadata_payload: dict[str, object] | None = None,
    ) -> None:
        self.db.add(
            AssetVariant(
                asset_id=source_asset.id,
                variant_asset_id=variant_asset.id,
                variant_kind=variant_kind,
                metadata_payload=metadata_payload or {},
            )
        )
        self.db.flush()

    def _scene_object_prefix(self, render_job: RenderJob, scene_index: int) -> str:
        return (
            f"workspace/{render_job.workspace_id}/project/{render_job.project_id}/"
            f"render/{render_job.id}/scene/{scene_index:02d}"
        )

    def _next_object_name(self, object_name: str) -> str:
        existing = self.db.scalar(select(Asset.id).where(Asset.object_name == object_name))
        if not existing:
            return object_name

        stem, separator, extension = object_name.rpartition(".")
        if not separator:
            stem = object_name
        version = 2
        while True:
            candidate = f"{stem}-v{version}{separator}{extension}" if separator else f"{stem}-v{version}"
            if not self.db.scalar(select(Asset.id).where(Asset.object_name == candidate)):
                return candidate
            version += 1

    def _quarantine_asset(self, asset: Asset) -> None:
        release_target_bucket = asset.bucket_name
        release_target_object = asset.object_name
        quarantine_object_name = f"moderation/{asset.id}/{Path(asset.object_name).name}"
        self.storage.copy_object(
            asset.bucket_name,
            asset.object_name,
            self.settings.minio_bucket_quarantine,
            quarantine_object_name,
        )
        self.storage.delete_object(asset.bucket_name, asset.object_name)
        asset.metadata_payload = {
            **dict(asset.metadata_payload or {}),
            "release_target_bucket_name": release_target_bucket,
            "release_target_object_name": release_target_object,
        }
        asset.bucket_name = self.settings.minio_bucket_quarantine
        asset.object_name = quarantine_object_name
        asset.quarantine_bucket_name = self.settings.minio_bucket_quarantine
        asset.quarantine_object_name = quarantine_object_name
        asset.status = "quarantined"
        asset.quarantined_at = datetime.now(UTC)

    def _moderate_generated_asset(
        self,
        *,
        moderation_provider: ModerationProvider,
        project: Project,
        scene_segment: SceneSegment | None,
        target_type: str,
        asset: Asset,
        input_text: str,
    ) -> bool:
        result = moderation_provider.moderate_text(input_text, target_type=target_type)
        self.db.add(
            AuditEvent(
                workspace_id=project.workspace_id,
                user_id=None,
                event_type=f"{target_type}.moderated",
                target_type="render_job",
                target_id=str(project.id),
                payload={"blocked": result.blocked, "scene_segment_id": str(scene_segment.id) if scene_segment else None},
            )
        )
        moderation_event = ModerationEvent(
            project_id=project.id,
            workspace_id=project.workspace_id,
            user_id=None,
            related_asset_id=asset.id,
            target_type=target_type,
            target_id=str(asset.id),
            input_text=input_text,
            decision=ModerationDecision.blocked if result.blocked else ModerationDecision.allowed,
            review_status=ModerationReviewStatus.pending if result.blocked else ModerationReviewStatus.none,
            provider_name=result.provider_name,
            severity_summary=result.severity_summary,
            response_payload=result.raw_response,
            blocked_message=result.blocked_message,
        )
        self.db.add(moderation_event)
        self.db.flush()
        if result.blocked:
            self._quarantine_asset(asset)
            return True
        return False

    def _create_provider_run(
        self,
        *,
        render_job: RenderJob,
        render_step: RenderStep,
        operation: str,
        request_payload: dict[str, object],
        provider_name: str,
        provider_model: str,
    ) -> ProviderRun:
        provider_run = ProviderRun(
            render_job_id=render_job.id,
            render_step_id=render_step.id,
            project_id=render_job.project_id,
            workspace_id=render_job.workspace_id,
            provider_name=provider_name,
            provider_model=provider_model,
            operation=operation,
            request_hash=self._hash_request(request_payload),
            status=ProviderRunStatus.running,
            request_payload=request_payload,
        )
        self.db.add(provider_run)
        self.db.flush()
        return provider_run

    def _finish_provider_run(
        self,
        provider_run: ProviderRun,
        *,
        started_at: float,
        response_payload: dict[str, object] | None = None,
        error: AdapterError | None = None,
    ) -> None:
        self._finalize_provider_run(
            provider_run,
            started_at=started_at,
            response_payload=response_payload,
            error=error,
        )

    def _set_render_blocked(
        self,
        render_job: RenderJob,
        step: RenderStep,
        *,
        error_code: str,
        error_message: str,
        checkpoint_payload: dict[str, object],
    ) -> None:
        step.status = JobStatus.blocked
        step.error_code = error_code
        step.error_message = error_message
        step.completed_at = datetime.now(UTC)
        step.output_payload = checkpoint_payload
        self._set_step_checkpoint(step, checkpoint_payload)
        render_job.status = JobStatus.blocked
        render_job.error_code = error_code
        render_job.error_message = error_message

    def _recovery_source_step_id(self, render_job: RenderJob, step: RenderStep) -> UUID | None:
        previous_step = self.db.scalar(
            select(RenderStep)
            .where(
                RenderStep.render_job_id == render_job.id,
                RenderStep.step_index < step.step_index,
                RenderStep.status.in_([JobStatus.completed, JobStatus.review, JobStatus.approved]),
            )
            .order_by(RenderStep.step_index.desc())
        )
        return previous_step.id if previous_step else None

    def _reset_step_for_resume(
        self,
        step: RenderStep,
        *,
        is_stale: bool,
        clear_output: bool,
        recovery_source_step_id: UUID | None,
    ) -> None:
        step.status = JobStatus.queued
        step.is_stale = is_stale
        step.error_code = None
        step.error_message = None
        step.started_at = None
        step.completed_at = None
        if clear_output:
            step.output_payload = None
        self._set_step_checkpoint(step, {"status": "queued"})
        step.recovery_source_step_id = recovery_source_step_id

    def _store_generated_asset(
        self,
        *,
        render_job: RenderJob,
        render_step: RenderStep,
        scene_segment: SceneSegment | None,
        generated_media: GeneratedMedia,
        bucket_name: str,
        object_name: str,
        file_name: str,
        asset_type: AssetType,
        asset_role: AssetRole,
        parent_asset_id: UUID | None = None,
        provider_run_id: UUID | None = None,
        has_audio_stream: bool = False,
        source_audio_policy: str = "request_silent",
        timing_alignment_strategy: str = "none",
    ) -> Asset:
        resolved_object_name = self._next_object_name(object_name)
        self.storage.put_bytes(
            bucket_name,
            resolved_object_name,
            generated_media.bytes_payload,
            content_type=generated_media.content_type,
        )
        asset = Asset(
            workspace_id=render_job.workspace_id,
            project_id=render_job.project_id,
            render_job_id=render_job.id,
            render_step_id=render_step.id,
            scene_segment_id=scene_segment.id if scene_segment else None,
            parent_asset_id=parent_asset_id,
            provider_run_id=provider_run_id,
            consistency_pack_snapshot_id=render_job.consistency_pack_id,
            asset_type=asset_type,
            asset_role=asset_role,
            status="completed",
            bucket_name=bucket_name,
            object_name=resolved_object_name,
            file_name=file_name,
            content_type=generated_media.content_type,
            size_bytes=len(generated_media.bytes_payload),
            duration_ms=generated_media.metadata.get("duration_ms"),
            width=generated_media.metadata.get("width"),
            height=generated_media.metadata.get("height"),
            frame_rate=generated_media.metadata.get("frame_rate"),
            has_audio_stream=has_audio_stream,
            source_audio_policy=source_audio_policy,
            timing_alignment_strategy=timing_alignment_strategy,
            metadata_payload=generated_media.metadata,
        )
        self.db.add(asset)
        self.db.flush()
        return asset

    def _record_prompt_history(
        self,
        *,
        render_job: RenderJob,
        render_step: RenderStep,
        scene_segment: SceneSegment | None,
        provider_run: ProviderRun | None,
        asset: Asset | None,
        prompt_role: str,
        prompt_text: str,
        source_asset_id: UUID | None = None,
        export_id: UUID | None = None,
        metadata_payload: dict[str, object] | None = None,
    ) -> PromptHistoryEntry:
        source_prompt = self._prompt_history_for_asset(source_asset_id)
        entry = PromptHistoryEntry(
            workspace_id=render_job.workspace_id,
            project_id=render_job.project_id,
            scene_plan_id=render_job.scene_plan_id,
            scene_segment_id=scene_segment.id if scene_segment else None,
            render_job_id=render_job.id,
            render_step_id=render_step.id,
            provider_run_id=provider_run.id if provider_run else None,
            asset_id=asset.id if asset else None,
            export_id=export_id,
            prompt_role=prompt_role,
            prompt_text=prompt_text,
            source_asset_id=source_asset_id,
            source_prompt_history_id=source_prompt.id if source_prompt else None,
            metadata_payload=metadata_payload or {},
        )
        self.db.add(entry)
        self.db.flush()
        return entry

    @staticmethod
    def _continuity_score(segment: SceneSegment, start_asset: Asset, end_asset: Asset) -> float:
        score = 0.72
        if segment.scene_index == 1:
            score += 0.12
        if segment.chained_from_asset_id:
            score += 0.10
        if start_asset.width and end_asset.width and start_asset.width == end_asset.width:
            score += 0.03
        if start_asset.height and end_asset.height and start_asset.height == end_asset.height:
            score += 0.03
        return round(min(score, 0.99), 2)

    def queue_render_job(
        self,
        auth: AuthContext,
        project_id: str,
        payload: RenderCreateRequest,
        *,
        idempotency_key: str,
    ) -> dict[str, object]:
        if not idempotency_key:
            raise ApiError(400, "missing_idempotency_key", "Idempotency-Key header is required.")
        project = self._get_project(project_id, auth.workspace_id)
        self._assert_mutation_rights(project, auth)
        scene_plan = self._get_scene_plan_for_render(project, payload.scene_plan_id)
        script = self.db.get(ScriptVersion, scene_plan.based_on_script_version_id)
        voice_preset = self.db.get(VoicePreset, scene_plan.voice_preset_id) if scene_plan.voice_preset_id else None
        consistency_pack = self.db.get(ConsistencyPack, scene_plan.consistency_pack_id)
        if not script or script.approval_state != "approved":
            raise ApiError(
                400,
                "script_not_approved",
                "The render requires the approved script bound to the approved scene plan.",
            )
        if not consistency_pack:
            raise ApiError(
                400,
                "consistency_pack_required",
                "The approved scene plan does not have a resolved consistency pack.",
            )
        BillingService(self.db, self.settings).ensure_render_credits_available(
            project.workspace_id,
            scene_plan.scene_count or len(self._scene_segments(scene_plan.id)),
        )
        request_payload = {
            "project_id": project_id,
            "scene_plan_id": str(scene_plan.id),
            "scene_plan_version": scene_plan.version_number,
            "script_version_id": str(script.id),
            "consistency_pack_id": str(scene_plan.consistency_pack_id),
            "allow_export_without_music": payload.allow_export_without_music,
            "subtitle_style_profile": normalize_subtitle_style_profile(project.subtitle_style_profile),
            "export_profile": normalize_export_profile(project.export_profile),
            "audio_mix_profile": normalize_audio_mix_profile(project.audio_mix_profile),
            "voice_preset_snapshot": {
                "id": str(voice_preset.id) if voice_preset else None,
                "name": voice_preset.name if voice_preset else None,
                "provider_voice": voice_preset.provider_voice if voice_preset else "",
                "tone_descriptor": voice_preset.tone_descriptor if voice_preset else "",
                "language_code": voice_preset.language_code if voice_preset else "en-US",
                "pace_multiplier": voice_preset.pace_multiplier if voice_preset else 1.0,
            },
            "consistency_pack_snapshot": consistency_pack.state,
        }
        request_hash = self._hash_request(request_payload)
        existing = self._get_idempotent_job(
            project_id=project.id,
            user_id=UUID(auth.user_id),
            job_kind=JobKind.render_generation,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if existing:
            return {"job_id": existing.id, "job_status": existing.status.value, "project_id": project.id}

        render_job = RenderJob(
            workspace_id=project.workspace_id,
            project_id=project.id,
            created_by_user_id=UUID(auth.user_id),
            script_version_id=script.id,
            scene_plan_id=scene_plan.id,
            consistency_pack_id=scene_plan.consistency_pack_id,
            voice_preset_id=scene_plan.voice_preset_id,
            job_kind=JobKind.render_generation,
            queue_name="render",
            status=JobStatus.queued,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            payload=request_payload,
            allow_export_without_music=payload.allow_export_without_music,
        )
        self.db.add(render_job)
        self.db.flush()
        record_audit_event(
            self.db,
            workspace_id=project.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="render.created",
            target_type="render_job",
            target_id=str(render_job.id),
            payload=request_payload,
        )
        self.db.commit()
        from app.workers.tasks import execute_render_job_task

        execute_render_job_task.delay(str(render_job.id))
        return {"job_id": render_job.id, "job_status": render_job.status.value, "project_id": project.id}

    def get_render_detail(self, auth: AuthContext, render_job_id: str) -> dict[str, object]:
        render_job = self._get_render_job_for_auth(auth, render_job_id)
        return self._render_detail_dict(render_job)

    def list_exports(self, auth: AuthContext, project_id: str) -> list[dict[str, object]]:
        project = self._get_project(project_id, auth.workspace_id)
        exports = self.db.scalars(
            select(ExportRecord)
            .where(ExportRecord.project_id == project.id)
            .order_by(ExportRecord.created_at.desc())
        ).all()
        return [export_to_dict(export, download_url=self._export_download_url(export)) for export in exports]

    def cancel_render(self, auth: AuthContext, render_job_id: str) -> dict[str, object]:
        render_job = self._get_render_job_for_auth(auth, render_job_id)
        if render_job.status in {JobStatus.completed, JobStatus.cancelled}:
            raise ApiError(400, "render_not_cancellable", "This render can no longer be cancelled.")
        render_job.status = JobStatus.cancelled
        render_job.cancelled_at = datetime.now(UTC)
        record_audit_event(
            self.db,
            workspace_id=render_job.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="render.cancelled",
            target_type="render_job",
            target_id=str(render_job.id),
            payload={},
        )
        self.db.commit()
        return self._render_detail_dict(render_job)

    def get_asset_signed_url(self, auth: AuthContext, asset_id: str) -> dict[str, object]:
        asset = self.db.get(Asset, UUID(asset_id))
        if not asset or str(asset.workspace_id) != auth.workspace_id:
            raise ApiError(404, "asset_not_found", "Asset not found.")
        return {"asset_id": asset.id, "url": self._asset_download_url(asset)}

    def list_render_events(self, auth: AuthContext, render_job_id: str) -> list[dict[str, object]]:
        render_job = self._get_render_job_for_auth(auth, render_job_id)
        step_ids = {str(step.id) for step in self._render_steps(render_job.id)}
        events = self.db.scalars(
            select(AuditEvent)
            .where(AuditEvent.workspace_id == render_job.workspace_id)
            .order_by(AuditEvent.created_at.asc())
        ).all()
        return [
            {
                "at": event.created_at,
                "event_type": event.event_type,
                "target_type": event.target_type,
                "target_id": event.target_id,
                "payload": event.payload,
            }
            for event in events
            if (
                (event.target_type == "render_job" and event.target_id == str(render_job.id))
                or (event.target_type == "render_step" and (event.target_id or "") in step_ids)
                or (
                    event.target_type == "export"
                    and str(event.payload.get("render_job_id", "")) == str(render_job.id)
                )
            )
        ]

    def mark_job_retry(self, job_id: str, error: AdapterError) -> None:
        self.db.rollback()
        render_job = self.db.get(RenderJob, UUID(job_id))
        if not render_job:
            return
        running_step = self.db.scalar(
            select(RenderStep)
            .where(RenderStep.render_job_id == render_job.id, RenderStep.status == JobStatus.running)
            .order_by(RenderStep.step_index.desc())
        )
        render_job.status = JobStatus.queued
        render_job.retry_count += 1
        render_job.error_code = error.code
        render_job.error_message = error.message
        if running_step:
            self._record_step_retry(
                running_step,
                requested_by_user_id=render_job.created_by_user_id,
                reason="transient_provider_retry",
                recovery_source_step_id=self._recovery_source_step_id(render_job, running_step),
            )
            running_step.status = JobStatus.queued
            running_step.error_code = error.code
            running_step.error_message = error.message
            running_step.started_at = None
            self._set_step_checkpoint(
                running_step,
                {"status": "queued", "reason": "transient_provider_retry", "error_code": error.code},
            )
        self.db.commit()

    def mark_job_failed(self, job_id: str, error: AdapterError) -> None:
        self.db.rollback()
        render_job = self.db.get(RenderJob, UUID(job_id))
        if not render_job:
            return
        running_step = self.db.scalar(
            select(RenderStep)
            .where(RenderStep.render_job_id == render_job.id, RenderStep.status == JobStatus.running)
            .order_by(RenderStep.step_index.desc())
        )
        render_job.status = JobStatus.failed
        render_job.error_code = error.code
        render_job.error_message = error.message
        render_job.completed_at = datetime.now(UTC)
        if running_step:
            self._fail_step(running_step, error)
        NotificationService(self.db, self.settings).notify_render_failed(render_job, reason=error.message)
        self.db.commit()

    def approve_frame_pair(
        self,
        auth: AuthContext,
        render_job_id: str,
        step_id: str,
    ) -> dict[str, object]:
        render_job = self._get_render_job_for_auth(auth, render_job_id)
        step = self.db.scalar(
            select(RenderStep).where(
                RenderStep.id == UUID(step_id),
                RenderStep.render_job_id == render_job.id,
                RenderStep.step_kind == StepKind.frame_pair_generation,
            )
        )
        if not step:
            raise ApiError(404, "render_step_not_found", "Render step not found.")
        if step.status not in {JobStatus.review, JobStatus.approved}:
            raise ApiError(
                400,
                "frame_pair_not_ready_for_approval",
                "This frame pair is not currently awaiting approval.",
            )

        project = self.db.get(Project, render_job.project_id)
        segment = self.db.get(SceneSegment, step.scene_segment_id) if step.scene_segment_id else None
        start_asset = (
            self.db.get(Asset, UUID(str(step.output_payload.get("start_image_asset_id"))))
            if step.output_payload and step.output_payload.get("start_image_asset_id")
            else None
        )
        end_asset = (
            self.db.get(Asset, UUID(str(step.output_payload.get("end_image_asset_id"))))
            if step.output_payload and step.output_payload.get("end_image_asset_id")
            else None
        )
        if project and segment and start_asset and end_asset:
            continuity_score = self._continuity_score(segment, start_asset, end_asset)
            library_label = f"{project.title} scene {segment.scene_index:02d} approved frame pair"
            for asset in (start_asset, end_asset):
                asset.is_library_asset = True
                asset.is_reusable = True
                asset.library_label = library_label
                asset.continuity_score = continuity_score
                asset.metadata_payload = {
                    **dict(asset.metadata_payload or {}),
                    "approved_for_reuse": True,
                    "approved_scene_plan_id": str(render_job.scene_plan_id) if render_job.scene_plan_id else None,
                }

        step.status = JobStatus.approved
        step.is_stale = False
        record_audit_event(
            self.db,
            workspace_id=render_job.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="render.frame_pair_approved",
            target_type="render_step",
            target_id=str(step.id),
            payload={"render_job_id": str(render_job.id)},
        )
        frame_pair_steps = self.db.scalars(
            select(RenderStep).where(
                RenderStep.render_job_id == render_job.id,
                RenderStep.step_kind == StepKind.frame_pair_generation,
            )
        ).all()
        all_approved = frame_pair_steps and all(
            candidate.status == JobStatus.approved and not candidate.is_stale for candidate in frame_pair_steps
        )
        if all_approved:
            render_job.status = JobStatus.queued
        self.db.commit()
        if all_approved:
            from app.workers.tasks import execute_render_job_task

            execute_render_job_task.delay(str(render_job.id))
        self.db.expire_all()
        return self._render_detail_dict(self._fresh_render_job(str(render_job.id)))

    def regenerate_frame_pair(
        self,
        auth: AuthContext,
        render_job_id: str,
        step_id: str,
    ) -> dict[str, object]:
        render_job = self._get_render_job_for_auth(auth, render_job_id)
        target_step = self.db.scalar(
            select(RenderStep).where(
                RenderStep.id == UUID(step_id),
                RenderStep.render_job_id == render_job.id,
                RenderStep.step_kind == StepKind.frame_pair_generation,
            )
        )
        if not target_step or not target_step.scene_segment_id:
            raise ApiError(404, "render_step_not_found", "Render step not found.")

        target_segment = self.db.get(SceneSegment, target_step.scene_segment_id)
        assert target_segment is not None
        recovery_source_step_id = self._recovery_source_step_id(render_job, target_step)
        self._record_step_retry(
            target_step,
            requested_by_user_id=auth.user_id,
            reason="frame_pair_regeneration_requested",
            recovery_source_step_id=recovery_source_step_id,
        )
        affected_steps = self.db.scalars(
            select(RenderStep)
            .where(RenderStep.render_job_id == render_job.id)
            .order_by(RenderStep.step_index.asc())
        ).all()
        for step in affected_steps:
            segment = self.db.get(SceneSegment, step.scene_segment_id) if step.scene_segment_id else None
            if step.id != target_step.id and step.step_index < target_step.step_index:
                continue
            if segment and segment.scene_index < target_segment.scene_index:
                continue
            self._reset_step_for_resume(
                step,
                is_stale=bool(segment and segment.scene_index > target_segment.scene_index),
                clear_output=True,
                recovery_source_step_id=recovery_source_step_id,
            )
            if segment:
                if step.step_kind == StepKind.frame_pair_generation:
                    segment.start_image_asset_id = None
                    segment.end_image_asset_id = None
                    if segment.scene_index == 1:
                        segment.chained_from_asset_id = None
        render_job.status = JobStatus.queued
        render_job.error_code = None
        render_job.error_message = None
        record_audit_event(
            self.db,
            workspace_id=render_job.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="render.frame_pair_regeneration_requested",
            target_type="render_step",
            target_id=str(target_step.id),
            payload={"render_job_id": str(render_job.id), "from_scene_index": target_segment.scene_index},
        )
        self.db.commit()
        from app.workers.tasks import execute_render_job_task

        execute_render_job_task.delay(str(render_job.id))
        self.db.expire_all()
        return self._render_detail_dict(self._fresh_render_job(str(render_job.id)))

    def retry_step(
        self,
        auth: AuthContext,
        render_job_id: str,
        step_id: str,
    ) -> dict[str, object]:
        render_job = self._get_render_job_for_auth(auth, render_job_id)
        step = self.db.scalar(
            select(RenderStep).where(
                RenderStep.id == UUID(step_id),
                RenderStep.render_job_id == render_job.id,
            )
        )
        if not step:
            raise ApiError(404, "render_step_not_found", "Render step not found.")
        if step.status not in {JobStatus.failed, JobStatus.cancelled}:
            raise ApiError(400, "render_step_not_retryable", "This render step is not retryable.")
        recovery_source_step_id = self._recovery_source_step_id(render_job, step)
        self._record_step_retry(
            step,
            requested_by_user_id=auth.user_id,
            reason="manual_step_retry",
            recovery_source_step_id=recovery_source_step_id,
        )
        reset_candidates = self.db.scalars(
            select(RenderStep)
            .where(
                RenderStep.render_job_id == render_job.id,
                RenderStep.step_index >= step.step_index,
            )
            .order_by(RenderStep.step_index.asc())
        ).all()
        for candidate in reset_candidates:
            self._reset_step_for_resume(
                candidate,
                is_stale=False,
                clear_output=True,
                recovery_source_step_id=recovery_source_step_id,
            )
        render_job.status = JobStatus.queued
        render_job.error_code = None
        render_job.error_message = None
        record_audit_event(
            self.db,
            workspace_id=render_job.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="render.step_retry_requested",
            target_type="render_step",
            target_id=str(step.id),
            payload={"render_job_id": str(render_job.id)},
        )
        self.db.commit()
        from app.workers.tasks import execute_render_job_task

        execute_render_job_task.delay(str(render_job.id))
        self.db.expire_all()
        return self._render_detail_dict(self._fresh_render_job(str(render_job.id)))

    def _run_frame_pair_stage(
        self,
        *,
        render_job: RenderJob,
        project: Project,
        scene_plan: ScenePlan,
        segments: list[SceneSegment],
        consistency_pack_state: dict[str, object],
        image_provider: ImageProvider,
        moderation_provider: ModerationProvider,
    ) -> bool:
        awaiting_review = False
        previous_end_asset_id: str | None = None
        for segment in segments:
            step = self._get_or_create_step(
                render_job,
                step_kind=StepKind.frame_pair_generation,
                step_index=100 + segment.scene_index,
                scene_segment_id=segment.id,
                input_payload={
                    "scene_index": segment.scene_index,
                    "start_image_prompt": segment.start_image_prompt,
                    "end_image_prompt": segment.end_image_prompt,
                },
            )
            if step.status == JobStatus.approved and not step.is_stale:
                previous_end_asset_id = str(segment.end_image_asset_id) if segment.end_image_asset_id else None
                continue
            if step.status == JobStatus.review and not step.is_stale:
                awaiting_review = True
                previous_end_asset_id = str(segment.end_image_asset_id) if segment.end_image_asset_id else None
                continue
            if step.status == JobStatus.blocked and not step.is_stale:
                render_job.status = JobStatus.blocked
                render_job.error_code = step.error_code
                render_job.error_message = step.error_message
                self.db.commit()
                return True

            self._set_step_running(step)
            start_source_asset_id = UUID(previous_end_asset_id) if previous_end_asset_id else None
            provider_request = {
                "scene_index": segment.scene_index,
                "start_prompt": segment.start_image_prompt,
                "end_prompt": segment.end_image_prompt,
                "previous_end_asset_id": previous_end_asset_id,
                "consistency_pack_id": str(render_job.consistency_pack_id),
            }
            provider_run = self._create_provider_run(
                render_job=render_job,
                render_step=step,
                operation="frame_pair_generation",
                request_payload=provider_request,
                provider_name="stub_image_provider",
                provider_model="stub-image-v1",
            )
            started = time.perf_counter()
            try:
                start_frame = image_provider.generate_frame(
                    prompt=segment.start_image_prompt,
                    scene_index=segment.scene_index,
                    frame_kind="start",
                    reference_asset_id=previous_end_asset_id,
                    consistency_pack_state=consistency_pack_state,
                )
                start_asset = self._store_generated_asset(
                    render_job=render_job,
                    render_step=step,
                    scene_segment=segment,
                    generated_media=start_frame,
                    bucket_name=self.settings.minio_bucket_assets,
                    object_name=f"{self._scene_object_prefix(render_job, segment.scene_index)}/images/start.png",
                    file_name=f"scene-{segment.scene_index:02d}-start.png",
                    asset_type=AssetType.image,
                    asset_role=AssetRole.scene_start_frame,
                    parent_asset_id=UUID(previous_end_asset_id) if previous_end_asset_id else None,
                    provider_run_id=provider_run.id,
                )
                end_frame = image_provider.generate_frame(
                    prompt=segment.end_image_prompt,
                    scene_index=segment.scene_index,
                    frame_kind="end",
                    reference_asset_id=str(start_asset.id),
                    consistency_pack_state=consistency_pack_state,
                )
                end_asset = self._store_generated_asset(
                    render_job=render_job,
                    render_step=step,
                    scene_segment=segment,
                    generated_media=end_frame,
                    bucket_name=self.settings.minio_bucket_assets,
                    object_name=f"{self._scene_object_prefix(render_job, segment.scene_index)}/images/end.png",
                    file_name=f"scene-{segment.scene_index:02d}-end.png",
                    asset_type=AssetType.image,
                    asset_role=AssetRole.scene_end_frame,
                    parent_asset_id=start_asset.id,
                    provider_run_id=provider_run.id,
                )
            except AdapterError as error:
                self._finish_provider_run(provider_run, started_at=started, error=error)
                self._fail_step(step, error)
                raise

            segment.chained_from_asset_id = UUID(previous_end_asset_id) if previous_end_asset_id else None
            segment.start_image_asset_id = start_asset.id
            segment.end_image_asset_id = end_asset.id
            start_asset.library_label = f"Scene {segment.scene_index:02d} start frame"
            end_asset.library_label = f"Scene {segment.scene_index:02d} end frame"
            previous_end_asset_id = str(end_asset.id)
            self._record_prompt_history(
                render_job=render_job,
                render_step=step,
                scene_segment=segment,
                provider_run=provider_run,
                asset=start_asset,
                prompt_role="scene_start_frame",
                prompt_text=segment.start_image_prompt,
                source_asset_id=start_source_asset_id,
                metadata_payload={
                    "scene_index": segment.scene_index,
                    "frame_kind": "start",
                    "consistency_pack_id": str(render_job.consistency_pack_id) if render_job.consistency_pack_id else None,
                },
            )
            self._record_prompt_history(
                render_job=render_job,
                render_step=step,
                scene_segment=segment,
                provider_run=provider_run,
                asset=end_asset,
                prompt_role="scene_end_frame",
                prompt_text=segment.end_image_prompt,
                source_asset_id=start_asset.id,
                metadata_payload={
                    "scene_index": segment.scene_index,
                    "frame_kind": "end",
                    "consistency_pack_id": str(render_job.consistency_pack_id) if render_job.consistency_pack_id else None,
                },
            )
            start_blocked = self._moderate_generated_asset(
                moderation_provider=moderation_provider,
                project=project,
                scene_segment=segment,
                target_type="generated_frame_output_proxy",
                asset=start_asset,
                input_text=segment.start_image_prompt,
            )
            end_blocked = self._moderate_generated_asset(
                moderation_provider=moderation_provider,
                project=project,
                scene_segment=segment,
                target_type="generated_frame_output_proxy",
                asset=end_asset,
                input_text=segment.end_image_prompt,
            )
            self._finish_provider_run(
                provider_run,
                started_at=started,
                response_payload={
                    "start_image_asset_id": str(start_asset.id),
                    "end_image_asset_id": str(end_asset.id),
                },
            )
            step.output_payload = {
                "start_image_asset_id": str(start_asset.id),
                "end_image_asset_id": str(end_asset.id),
            }
            if start_blocked or end_blocked:
                self._set_render_blocked(
                    render_job,
                    step,
                    error_code="moderation_review_required",
                    error_message="Generated frame pairs require operator moderation review.",
                    checkpoint_payload=step.output_payload,
                )
                record_audit_event(
                    self.db,
                    workspace_id=render_job.workspace_id,
                    user_id=render_job.created_by_user_id,
                    event_type="render.frame_pair_quarantined",
                    target_type="render_step",
                    target_id=str(step.id),
                    payload={"render_job_id": str(render_job.id), "scene_index": segment.scene_index},
                )
                self.db.commit()
                return True
            step.status = JobStatus.review
            step.is_stale = False
            step.completed_at = datetime.now(UTC)
            self._set_step_checkpoint(step, step.output_payload)
            awaiting_review = True
            record_audit_event(
                self.db,
                workspace_id=render_job.workspace_id,
                user_id=render_job.created_by_user_id,
                event_type="render.frame_pair_ready",
                target_type="render_step",
                target_id=str(step.id),
                payload={"render_job_id": str(render_job.id), "scene_index": segment.scene_index},
            )

        if awaiting_review:
            render_job.status = JobStatus.review
            render_job.error_code = None
            render_job.error_message = None
            self.db.commit()
            return True
        return False

    def _run_video_stage(
        self,
        *,
        render_job: RenderJob,
        project: Project,
        segment: SceneSegment,
        video_provider: VideoProvider,
        moderation_provider: ModerationProvider,
    ) -> Asset | None:
        step = self._get_or_create_step(
            render_job,
            step_kind=StepKind.video_generation,
            step_index=1000 + segment.scene_index,
            scene_segment_id=segment.id,
            input_payload={"scene_index": segment.scene_index, "visual_prompt": segment.visual_prompt},
        )
        if step.status == JobStatus.completed:
            existing_asset = self._latest_asset(
                render_job.id,
                asset_role=AssetRole.raw_video_clip,
                scene_segment_id=segment.id,
            )
            if existing_asset:
                return existing_asset
        if step.status == JobStatus.blocked:
            render_job.status = JobStatus.blocked
            render_job.error_code = step.error_code
            render_job.error_message = step.error_message
            self.db.commit()
            return None

        self._set_step_running(step)
        provider_request = {
            "scene_index": segment.scene_index,
            "visual_prompt": segment.visual_prompt,
            "start_image_asset_id": str(segment.start_image_asset_id),
            "end_image_asset_id": str(segment.end_image_asset_id),
            "duration_seconds": segment.target_duration_seconds,
        }
        provider_run = self._create_provider_run(
            render_job=render_job,
            render_step=step,
            operation="video_generation",
            request_payload=provider_request,
            provider_name="stub_video_provider",
            provider_model="stub-video-v1",
        )
        started = time.perf_counter()
        try:
            generated = video_provider.generate_clip(
                prompt=segment.visual_prompt,
                scene_index=segment.scene_index,
                duration_seconds=segment.target_duration_seconds,
                start_frame_asset_id=str(segment.start_image_asset_id),
                end_frame_asset_id=str(segment.end_image_asset_id),
            )
            raw_asset = self._store_generated_asset(
                render_job=render_job,
                render_step=step,
                scene_segment=segment,
                generated_media=generated,
                bucket_name=self.settings.minio_bucket_assets,
                object_name=f"{self._scene_object_prefix(render_job, segment.scene_index)}/videos/raw.json",
                file_name=f"scene-{segment.scene_index:02d}-raw.json",
                asset_type=AssetType.video_clip,
                asset_role=AssetRole.raw_video_clip,
                parent_asset_id=segment.end_image_asset_id,
                provider_run_id=provider_run.id,
                has_audio_stream=bool(generated.metadata.get("has_audio_stream", True)),
                source_audio_policy="strip_after_generation",
            )
        except AdapterError as error:
            self._finish_provider_run(provider_run, started_at=started, error=error)
            self._fail_step(step, error)
            raise

        self._finish_provider_run(
            provider_run,
            started_at=started,
            response_payload={"asset_id": str(raw_asset.id)},
        )
        self._record_prompt_history(
            render_job=render_job,
            render_step=step,
            scene_segment=segment,
            provider_run=provider_run,
            asset=raw_asset,
            prompt_role="scene_video",
            prompt_text=segment.visual_prompt,
            source_asset_id=segment.end_image_asset_id,
            metadata_payload={
                "scene_index": segment.scene_index,
                "start_image_asset_id": str(segment.start_image_asset_id) if segment.start_image_asset_id else None,
                "end_image_asset_id": str(segment.end_image_asset_id) if segment.end_image_asset_id else None,
            },
        )
        if self._moderate_generated_asset(
            moderation_provider=moderation_provider,
            project=project,
            scene_segment=segment,
            target_type="generated_video_output_proxy",
            asset=raw_asset,
            input_text=segment.visual_prompt,
        ):
            self._set_render_blocked(
                render_job,
                step,
                error_code="moderation_review_required",
                error_message="Generated video output requires operator moderation review.",
                checkpoint_payload={"asset_id": str(raw_asset.id)},
            )
            record_audit_event(
                self.db,
                workspace_id=render_job.workspace_id,
                user_id=render_job.created_by_user_id,
                event_type="render.video_quarantined",
                target_type="render_step",
                target_id=str(step.id),
                payload={"render_job_id": str(render_job.id), "scene_index": segment.scene_index},
            )
            self.db.commit()
            return None
        self._complete_step(step, output_payload={"asset_id": str(raw_asset.id)})
        record_audit_event(
            self.db,
            workspace_id=render_job.workspace_id,
            user_id=render_job.created_by_user_id,
            event_type="render.scene_video_completed",
            target_type="render_step",
            target_id=str(step.id),
            payload={"render_job_id": str(render_job.id), "scene_index": segment.scene_index},
        )
        return raw_asset

    def _run_audio_normalization_stage(self, *, render_job: RenderJob, segment: SceneSegment, raw_asset: Asset) -> Asset:
        step = self._get_or_create_step(
            render_job,
            step_kind=StepKind.audio_normalization,
            step_index=2000 + segment.scene_index,
            scene_segment_id=segment.id,
            input_payload={"source_asset_id": str(raw_asset.id)},
        )
        if step.status == JobStatus.completed:
            existing_asset = self._latest_asset(
                render_job.id,
                asset_role=AssetRole.silent_video_clip,
                scene_segment_id=segment.id,
            )
            if existing_asset:
                return existing_asset

        self._set_step_running(step)
        source_bytes = self.storage.read_bytes(raw_asset.bucket_name, raw_asset.object_name)
        normalized = GeneratedMedia(
            provider_name="internal_audio_normalizer",
            provider_model="copy-strip-v1",
            content_type=raw_asset.content_type,
            file_extension=raw_asset.object_name.split(".")[-1],
            bytes_payload=source_bytes,
            metadata={
                **raw_asset.metadata_payload,
                "normalized": True,
                "source_audio_removed": True,
                "duration_ms": raw_asset.duration_ms or (segment.target_duration_seconds * 1000),
            },
        )
        silent_asset = self._store_generated_asset(
            render_job=render_job,
            render_step=step,
            scene_segment=segment,
            generated_media=normalized,
            bucket_name=self.settings.minio_bucket_assets,
            object_name=f"{self._scene_object_prefix(render_job, segment.scene_index)}/videos/silent.json",
            file_name=f"scene-{segment.scene_index:02d}-silent.json",
            asset_type=AssetType.video_clip,
            asset_role=AssetRole.silent_video_clip,
            parent_asset_id=raw_asset.id,
            has_audio_stream=False,
            source_audio_policy="strip_after_generation",
        )
        self._create_asset_variant(
            source_asset=raw_asset,
            variant_asset=silent_asset,
            variant_kind="silent_video",
        )
        self._complete_step(step, output_payload={"asset_id": str(silent_asset.id)})
        return silent_asset

    def _run_narration_stage(
        self,
        *,
        render_job: RenderJob,
        segment: SceneSegment,
        speech_provider: SpeechProvider,
        voice_preset_snapshot: dict[str, object] | None,
    ) -> Asset:
        step = self._get_or_create_step(
            render_job,
            step_kind=StepKind.narration_generation,
            step_index=3000 + segment.scene_index,
            scene_segment_id=segment.id,
            input_payload={"scene_index": segment.scene_index, "narration_text": segment.narration_text},
        )
        if step.status == JobStatus.completed:
            existing_asset = self._latest_asset(
                render_job.id,
                asset_role=AssetRole.narration_track,
                scene_segment_id=segment.id,
            )
            if existing_asset:
                return existing_asset

        self._set_step_running(step)
        provider_run = self._create_provider_run(
            render_job=render_job,
            render_step=step,
            operation="narration_generation",
            request_payload={"text": segment.narration_text, "voice_preset": voice_preset_snapshot or {}},
            provider_name="stub_speech_provider",
            provider_model="stub-speech-v1",
        )
        started = time.perf_counter()
        try:
            generated = speech_provider.synthesize(
                text=segment.narration_text,
                scene_index=segment.scene_index,
                voice_preset=voice_preset_snapshot,
            )
            narration_asset = self._store_generated_asset(
                render_job=render_job,
                render_step=step,
                scene_segment=segment,
                generated_media=generated,
                bucket_name=self.settings.minio_bucket_assets,
                object_name=f"{self._scene_object_prefix(render_job, segment.scene_index)}/audio/narration.wav",
                file_name=f"scene-{segment.scene_index:02d}-narration.wav",
                asset_type=AssetType.narration,
                asset_role=AssetRole.narration_track,
                provider_run_id=provider_run.id,
                has_audio_stream=True,
            )
        except AdapterError as error:
            self._finish_provider_run(provider_run, started_at=started, error=error)
            self._fail_step(step, error)
            raise

        self._finish_provider_run(
            provider_run,
            started_at=started,
            response_payload={"asset_id": str(narration_asset.id)},
        )
        self._record_prompt_history(
            render_job=render_job,
            render_step=step,
            scene_segment=segment,
            provider_run=provider_run,
            asset=narration_asset,
            prompt_role="narration_generation",
            prompt_text=segment.narration_text,
            metadata_payload={"scene_index": segment.scene_index},
        )
        self._complete_step(step, output_payload={"asset_id": str(narration_asset.id)})
        segment.actual_voice_duration_seconds = max(1, int((narration_asset.duration_ms or 0) / 1000))
        return narration_asset

    def _run_retime_stage(
        self,
        *,
        render_job: RenderJob,
        segment: SceneSegment,
        silent_asset: Asset,
        narration_asset: Asset,
    ) -> Asset:
        step = self._get_or_create_step(
            render_job,
            step_kind=StepKind.clip_retime,
            step_index=4000 + segment.scene_index,
            scene_segment_id=segment.id,
            input_payload={
                "silent_asset_id": str(silent_asset.id),
                "narration_asset_id": str(narration_asset.id),
            },
        )
        if step.status == JobStatus.completed:
            existing_asset = self._latest_asset(
                render_job.id,
                asset_role=AssetRole.retimed_video_clip,
                scene_segment_id=segment.id,
            )
            if existing_asset:
                return existing_asset

        self._set_step_running(step)
        clip_duration_ms = silent_asset.duration_ms or (segment.target_duration_seconds * 1000)
        narration_duration_ms = narration_asset.duration_ms or clip_duration_ms
        ratio = narration_duration_ms / max(clip_duration_ms, 1)
        if 0.92 <= ratio <= 1.08:
            strategy = "speed_adjust"
        elif narration_duration_ms > clip_duration_ms:
            strategy = "freeze_pad"
        else:
            strategy = "trim"
        retimed = GeneratedMedia(
            provider_name="internal_retimer",
            provider_model="timing-align-v1",
            content_type=silent_asset.content_type,
            file_extension=silent_asset.object_name.split(".")[-1],
            bytes_payload=self.storage.read_bytes(silent_asset.bucket_name, silent_asset.object_name),
            metadata={
                **silent_asset.metadata_payload,
                "duration_ms": narration_duration_ms,
                "timing_alignment_strategy": strategy,
            },
        )
        retimed_asset = self._store_generated_asset(
            render_job=render_job,
            render_step=step,
            scene_segment=segment,
            generated_media=retimed,
            bucket_name=self.settings.minio_bucket_assets,
            object_name=f"{self._scene_object_prefix(render_job, segment.scene_index)}/videos/retimed.json",
            file_name=f"scene-{segment.scene_index:02d}-retimed.json",
            asset_type=AssetType.video_clip,
            asset_role=AssetRole.retimed_video_clip,
            parent_asset_id=silent_asset.id,
            has_audio_stream=False,
            source_audio_policy="request_silent",
            timing_alignment_strategy=strategy,
        )
        self._create_asset_variant(
            source_asset=silent_asset,
            variant_asset=retimed_asset,
            variant_kind="retimed_video",
            metadata_payload={"strategy": strategy},
        )
        self._complete_step(
            step,
            output_payload={"asset_id": str(retimed_asset.id), "strategy": strategy},
        )
        return retimed_asset

    def _run_music_stage(
        self,
        *,
        render_job: RenderJob,
        music_provider: MusicProvider,
        total_duration_seconds: int,
        audio_mix_profile: dict[str, object],
    ) -> Asset | None:
        step = self._get_or_create_step(
            render_job,
            step_kind=StepKind.music_preparation,
            step_index=5000,
            input_payload={
                "total_duration_seconds": total_duration_seconds,
                "audio_mix_profile": audio_mix_profile,
            },
        )
        if step.status == JobStatus.completed:
            return self._latest_asset(render_job.id, asset_role=AssetRole.music_bed)

        self._set_step_running(step)
        provider_run = self._create_provider_run(
            render_job=render_job,
            render_step=step,
            operation="music_preparation",
            request_payload={
                "total_duration_seconds": total_duration_seconds,
                "audio_mix_profile": audio_mix_profile,
            },
            provider_name="stub_music_provider",
            provider_model="stub-music-v1",
        )
        started = time.perf_counter()
        try:
            generated = music_provider.prepare_track(total_duration_seconds=total_duration_seconds)
        except AdapterError as error:
            self._finish_provider_run(provider_run, started_at=started, error=error)
            self._fail_step(step, error)
            if render_job.allow_export_without_music:
                return None
            raise

        music_asset = self._store_generated_asset(
            render_job=render_job,
            render_step=step,
            scene_segment=None,
            generated_media=generated,
            bucket_name=self.settings.minio_bucket_assets,
            object_name=(
                f"workspace/{render_job.workspace_id}/project/{render_job.project_id}/"
                f"render/{render_job.id}/audio/music.wav"
            ),
            file_name="music-bed.wav",
            asset_type=AssetType.music,
            asset_role=AssetRole.music_bed,
            provider_run_id=provider_run.id,
            has_audio_stream=True,
        )
        music_asset.metadata_payload = {
            **dict(music_asset.metadata_payload or {}),
            "audio_mix_profile": audio_mix_profile,
        }
        self._finish_provider_run(
            provider_run,
            started_at=started,
            response_payload={"asset_id": str(music_asset.id)},
        )
        self._complete_step(step, output_payload={"asset_id": str(music_asset.id)})
        return music_asset

    def _run_subtitle_stage(
        self,
        *,
        render_job: RenderJob,
        segments: list[SceneSegment],
        subtitle_style_profile: dict[str, object],
    ) -> Asset | None:
        step = self._get_or_create_step(
            render_job,
            step_kind=StepKind.subtitle_generation,
            step_index=6000,
            input_payload={"scene_count": len(segments), "subtitle_style_profile": subtitle_style_profile},
        )
        if step.status == JobStatus.completed:
            return self._latest_asset(render_job.id, asset_role=AssetRole.subtitle_file)

        self._set_step_running(step)
        try:
            current_ms = 0
            lines: list[str] = []
            for index, segment in enumerate(segments, start=1):
                start_ms = current_ms
                duration_ms = (segment.actual_voice_duration_seconds or segment.target_duration_seconds) * 1000
                end_ms = start_ms + duration_ms
                lines.extend(
                    [
                        str(index),
                        f"{self._format_srt_timestamp(start_ms)} --> {self._format_srt_timestamp(end_ms)}",
                        segment.caption_text or segment.narration_text,
                        "",
                    ]
                )
                current_ms = end_ms
            subtitle_bytes = "\n".join(lines).encode("utf-8")
            generated = GeneratedMedia(
                provider_name="internal_subtitle_generator",
                provider_model="subtitle-srt-v1",
                content_type="text/plain",
                file_extension="srt",
                bytes_payload=subtitle_bytes,
                metadata={"scene_count": len(segments)},
            )
            subtitle_asset = self._store_generated_asset(
                render_job=render_job,
                render_step=step,
                scene_segment=None,
                generated_media=generated,
                bucket_name=self.settings.minio_bucket_assets,
                object_name=(
                    f"workspace/{render_job.workspace_id}/project/{render_job.project_id}/"
                    f"render/{render_job.id}/subtitles/reel.srt"
                ),
                file_name="reel.srt",
                asset_type=AssetType.subtitle,
                asset_role=AssetRole.subtitle_file,
            )
            subtitle_asset.metadata_payload = {
                **dict(subtitle_asset.metadata_payload or {}),
                "subtitle_style_profile": subtitle_style_profile,
            }
        except Exception as exc:  # pragma: no cover - defensive guard
            step.status = JobStatus.failed
            step.error_code = "subtitle_generation_failed"
            step.error_message = str(exc)
            step.completed_at = datetime.now(UTC)
            return None

        self._complete_step(step, output_payload={"asset_id": str(subtitle_asset.id)})
        return subtitle_asset

    def _run_composition_stage(
        self,
        *,
        render_job: RenderJob,
        scene_plan: ScenePlan,
        segments: list[SceneSegment],
        retimed_assets: list[Asset],
        narration_assets: list[Asset],
        music_asset: Asset | None,
        subtitle_asset: Asset | None,
        subtitle_style_profile: dict[str, object],
        export_profile: dict[str, object],
        audio_mix_profile: dict[str, object],
    ) -> ExportRecord:
        step = self._get_or_create_step(
            render_job,
            step_kind=StepKind.composition,
            step_index=7000,
            input_payload={
                "scene_count": len(segments),
                "subtitle_style_profile": subtitle_style_profile,
                "export_profile": export_profile,
                "audio_mix_profile": audio_mix_profile,
            },
        )
        if step.status == JobStatus.completed:
            existing_export = self.db.scalar(
                select(ExportRecord).where(ExportRecord.render_job_id == render_job.id)
            )
            if existing_export:
                return existing_export

        self._set_step_running(step)
        manifest = {
            "render_job_id": str(render_job.id),
            "scene_plan_id": str(scene_plan.id),
            "aspect_ratio": "9:16",
            "scene_count": len(segments),
            "scenes": [
                {
                    "scene_index": segment.scene_index,
                    "retimed_video_asset_id": str(video_asset.id),
                    "narration_asset_id": str(audio_asset.id),
                }
                for segment, video_asset, audio_asset in zip(segments, retimed_assets, narration_assets, strict=True)
            ],
            "music_asset_id": str(music_asset.id) if music_asset else None,
            "subtitle_asset_id": str(subtitle_asset.id) if subtitle_asset else None,
            "consistency_pack_id": str(render_job.consistency_pack_id) if render_job.consistency_pack_id else None,
            "subtitle_style_profile": subtitle_style_profile,
            "export_profile": export_profile,
            "audio_mix_profile": audio_mix_profile,
        }
        generated = GeneratedMedia(
            provider_name="internal_stub_composer",
            provider_model="manifest-export-v1",
            content_type="application/json",
            file_extension="json",
            bytes_payload=json.dumps(manifest, indent=2).encode("utf-8"),
            metadata={
                "duration_ms": sum(asset.duration_ms or 0 for asset in narration_assets),
                "scene_count": len(segments),
                "aspect_ratio": "9:16",
                "subtitle_style_profile": subtitle_style_profile,
                "export_profile": export_profile,
                "audio_mix_profile": audio_mix_profile,
            },
        )
        export_asset = self._store_generated_asset(
            render_job=render_job,
            render_step=step,
            scene_segment=None,
            generated_media=generated,
            bucket_name=self.settings.minio_bucket_assets,
            object_name=(
                f"workspace/{render_job.workspace_id}/project/{render_job.project_id}/"
                f"render/{render_job.id}/exports/final-export.json"
            ),
            file_name="final-export.json",
            asset_type=AssetType.export,
            asset_role=AssetRole.final_export,
        )
        export_record = ExportRecord(
            workspace_id=render_job.workspace_id,
            project_id=render_job.project_id,
            render_job_id=render_job.id,
            asset_id=export_asset.id,
            status="completed",
            file_name=export_asset.file_name,
            format=str(export_profile.get("format") or "json"),
            bucket_name=export_asset.bucket_name,
            object_name=export_asset.object_name,
            duration_ms=generated.metadata.get("duration_ms"),
            subtitle_style_profile=subtitle_style_profile,
            export_profile=export_profile,
            audio_mix_profile=audio_mix_profile,
            metadata_payload=generated.metadata,
            completed_at=datetime.now(UTC),
        )
        self.db.add(export_record)
        self.db.flush()
        self._record_prompt_history(
            render_job=render_job,
            render_step=step,
            scene_segment=None,
            provider_run=None,
            asset=export_asset,
            export_id=export_record.id,
            prompt_role="final_composition_manifest",
            prompt_text=json.dumps(manifest, default=str),
            metadata_payload={"scene_count": len(segments)},
        )
        BillingService(self.db, self.settings).capture_export_usage(export_record)
        self._complete_step(step, output_payload={"asset_id": str(export_asset.id), "export_id": str(export_record.id)})
        record_audit_event(
            self.db,
            workspace_id=render_job.workspace_id,
            user_id=render_job.created_by_user_id,
            event_type="render.completed",
            target_type="export",
            target_id=str(export_record.id),
            payload={"render_job_id": str(render_job.id)},
        )
        return export_record

    def execute_render_job(
        self,
        job_id: str,
        *,
        image_provider: ImageProvider,
        video_provider: VideoProvider,
        speech_provider: SpeechProvider,
        music_provider: MusicProvider,
        moderation_provider: ModerationProvider,
    ) -> None:
        render_job = self.db.get(RenderJob, UUID(job_id))
        if not render_job:
            raise AdapterError("internal", "render_job_not_found", "Render job not found.")
        if render_job.status == JobStatus.cancelled:
            return
        project = self.db.get(Project, render_job.project_id)
        scene_plan = self.db.get(ScenePlan, render_job.scene_plan_id if render_job else None)
        script = self.db.get(ScriptVersion, render_job.script_version_id if render_job else None)
        if not project or not scene_plan or not script:
            raise AdapterError("internal", "missing_render_inputs", "Render inputs are incomplete.")
        if not render_job.consistency_pack_id:
            raise AdapterError("deterministic_input", "consistency_pack_required", "Consistency pack is required.")
        consistency_pack_row = self.db.get(ConsistencyPack, render_job.consistency_pack_id)
        consistency_pack_state = dict(render_job.payload.get("consistency_pack_snapshot", {}) or {})
        if not consistency_pack_state and consistency_pack_row:
            consistency_pack_state = dict(consistency_pack_row.state or {})
        if not consistency_pack_state:
            raise AdapterError("deterministic_input", "consistency_pack_required", "Consistency pack is required.")

        voice_preset_snapshot = dict(render_job.payload.get("voice_preset_snapshot", {}) or {})
        subtitle_style_profile, export_profile, audio_mix_profile = self._resolved_project_profiles(
            render_job=render_job,
            project=project,
        )
        segments = self._scene_segments(scene_plan.id)
        render_job.status = JobStatus.running
        render_job.started_at = render_job.started_at or datetime.now(UTC)
        self.db.commit()

        if self._run_frame_pair_stage(
            render_job=render_job,
            project=project,
            scene_plan=scene_plan,
            segments=segments,
            consistency_pack_state=consistency_pack_state,
            image_provider=image_provider,
            moderation_provider=moderation_provider,
        ):
            return

        retimed_assets: list[Asset] = []
        narration_assets: list[Asset] = []
        for segment in segments:
            raw_asset = self._run_video_stage(
                render_job=render_job,
                project=project,
                segment=segment,
                video_provider=video_provider,
                moderation_provider=moderation_provider,
            )
            if raw_asset is None:
                return
            silent_asset = self._run_audio_normalization_stage(
                render_job=render_job,
                segment=segment,
                raw_asset=raw_asset,
            )
            narration_asset = self._run_narration_stage(
                render_job=render_job,
                segment=segment,
                speech_provider=speech_provider,
                voice_preset_snapshot=voice_preset_snapshot,
            )
            retimed_asset = self._run_retime_stage(
                render_job=render_job,
                segment=segment,
                silent_asset=silent_asset,
                narration_asset=narration_asset,
            )
            retimed_assets.append(retimed_asset)
            narration_assets.append(narration_asset)

        total_duration_seconds = max(1, sum((asset.duration_ms or 0) for asset in narration_assets) // 1000)
        music_asset = self._run_music_stage(
            render_job=render_job,
            music_provider=music_provider,
            total_duration_seconds=total_duration_seconds,
            audio_mix_profile=audio_mix_profile,
        )
        subtitle_asset = self._run_subtitle_stage(
            render_job=render_job,
            segments=segments,
            subtitle_style_profile=subtitle_style_profile,
        )
        self._run_composition_stage(
            render_job=render_job,
            scene_plan=scene_plan,
            segments=segments,
            retimed_assets=retimed_assets,
            narration_assets=narration_assets,
            music_asset=music_asset,
            subtitle_asset=subtitle_asset,
            subtitle_style_profile=subtitle_style_profile,
            export_profile=export_profile,
            audio_mix_profile=audio_mix_profile,
        )
        project.stage = ProjectStage.exports
        render_job.status = JobStatus.completed
        render_job.completed_at = datetime.now(UTC)
        render_job.error_code = None
        render_job.error_message = None
        self.db.commit()

    def expire_stale_render_jobs(self) -> int:
        threshold = datetime.now(UTC) - timedelta(minutes=self.settings.render_job_timeout_minutes)
        stale_jobs = self.db.scalars(
            select(RenderJob).where(
                RenderJob.queue_name == "render",
                RenderJob.status.in_([JobStatus.queued, JobStatus.running, JobStatus.blocked]),
                RenderJob.created_at < threshold,
            )
        ).all()
        for render_job in stale_jobs:
            render_job.status = JobStatus.failed
            render_job.error_code = "job_timeout"
            render_job.error_message = "The render expired before completion."
            render_job.completed_at = datetime.now(UTC)
            running_step = self.db.scalar(
                select(RenderStep)
                .where(
                    RenderStep.render_job_id == render_job.id,
                    RenderStep.status.in_([JobStatus.queued, JobStatus.running, JobStatus.blocked]),
                )
                .order_by(RenderStep.step_index.desc())
            )
            if running_step:
                running_step.status = JobStatus.failed
                running_step.error_code = "job_timeout"
                running_step.error_message = "The render expired before completion."
                running_step.completed_at = datetime.now(UTC)
                self._set_step_checkpoint(
                    running_step,
                    {
                        "status": "failed",
                        "error_code": "job_timeout",
                        "error_message": "The render expired before completion.",
                    },
                )
            NotificationService(self.db, self.settings).notify_render_failed(
                render_job,
                reason=render_job.error_message,
            )
        self.db.commit()
        return len(stale_jobs)

    @staticmethod
    def _format_srt_timestamp(total_ms: int) -> str:
        hours = total_ms // 3_600_000
        minutes = (total_ms % 3_600_000) // 60_000
        seconds = (total_ms % 60_000) // 1_000
        milliseconds = total_ms % 1_000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
