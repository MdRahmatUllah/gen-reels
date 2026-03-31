from __future__ import annotations

import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import redis
from sqlalchemy import func, select

from app.api.deps import AuthContext
from app.core.errors import AdapterError, ApiError
from app.integrations.azure import ModerationProvider
from app.integrations.media_ops import (
    compose_reel_export,
    create_slide_clip_from_images,
    probe_media_bytes,
    retime_video_to_target,
    strip_audio_from_video,
)
from app.integrations.media import (
    GeneratedMedia,
    ImageProvider,
    ImageReference,
    MusicProvider,
    SpeechProvider,
    StubImageProvider,
    StubSpeechProvider,
    StubVideoProvider,
    VideoProvider,
    build_image_provider,
    build_music_provider,
    build_speech_provider,
    build_video_provider,
    compose_frame_generation_prompt,
)
from app.integrations.storage import StorageClient, build_storage_client
from app.models.entities import (
    Asset,
    AssetRole,
    AssetType,
    AssetVariant,
    AuditEvent,
    ConsistencyPack,
    ExecutionMode,
    ExportRecord,
    JobKind,
    JobStatus,
    LocalWorker,
    ModerationDecision,
    ModerationEvent,
    ModerationReport,
    ModerationReportStatus,
    ModerationReviewStatus,
    Project,
    ProjectStage,
    PromptHistoryEntry,
    ProviderErrorCategory,
    ProviderRun,
    ProviderRunStatus,
    RenderJob,
    RenderEvent,
    RenderStep,
    ScenePlan,
    SceneSegment,
    ScriptVersion,
    StepKind,
    VoicePreset,
    WorkspaceRole,
)
from app.schemas.execution import LocalWorkerJobResultRequest
from app.schemas.renders import RenderCreateRequest
from app.services.audit_service import record_audit_event
from app.services.billing_service import BillingService
from app.services.execution_policy_service import ExecutionPolicyService
from app.services.generation_service import GenerationService
from app.services.notification_service import NotificationService
from app.services.project_profiles import (
    normalize_audio_mix_profile,
    normalize_export_profile,
    normalize_subtitle_style_profile,
)
from app.services.presenters import asset_to_dict, export_to_dict, job_to_dict, render_step_to_dict
from app.services.routing_service import RoutingDecision, RoutingService


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

    @staticmethod
    def _render_event_channel(render_job_id: UUID) -> str:
        return f"render-events:{render_job_id}"

    def _append_render_event(
        self,
        *,
        render_job: RenderJob,
        event_type: str,
        target_type: str,
        target_id: str | None,
        payload: dict[str, object] | None = None,
        render_step_id: UUID | None = None,
    ) -> RenderEvent:
        next_sequence = (
            self.db.scalar(
                select(func.max(RenderEvent.sequence_number)).where(
                    RenderEvent.render_job_id == render_job.id
                )
            )
            or 0
        ) + 1
        event = RenderEvent(
            workspace_id=render_job.workspace_id,
            project_id=render_job.project_id,
            render_job_id=render_job.id,
            render_step_id=render_step_id,
            sequence_number=next_sequence,
            event_type=event_type,
            target_type=target_type,
            target_id=target_id,
            payload=payload or {},
        )
        self.db.add(event)
        self.db.flush()
        try:
            redis.Redis.from_url(self.settings.redis_url, decode_responses=True).publish(
                self._render_event_channel(render_job.id),
                json.dumps(
                    {
                        "sequence_number": event.sequence_number,
                        "at": event.created_at.isoformat() if event.created_at else None,
                        "render_job_id": str(render_job.id),
                        "render_step_id": str(render_step_id) if render_step_id else None,
                        "event_type": event.event_type,
                        "target_type": event.target_type,
                        "target_id": event.target_id,
                        "payload": event.payload,
                    },
                    default=str,
                ),
            )
        except Exception:
            pass
        return event

    def _latest_provider_run_for_step(
        self,
        render_step_id: UUID,
        *,
        execution_mode: ExecutionMode | None = None,
    ) -> ProviderRun | None:
        query = select(ProviderRun).where(ProviderRun.render_step_id == render_step_id)
        if execution_mode is not None:
            query = query.where(ProviderRun.execution_mode == execution_mode)
        return self.db.scalar(query.order_by(ProviderRun.started_at.desc()))

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

    def _export_download_url(self, export: ExportRecord) -> str | None:
        if export.availability_status not in {"available", "released"}:
            return None
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
        execution_mode: ExecutionMode = ExecutionMode.hosted,
        worker_id: UUID | None = None,
        provider_credential_id: UUID | None = None,
        routing_decision_payload: dict[str, object] | None = None,
        status: ProviderRunStatus = ProviderRunStatus.running,
    ) -> ProviderRun:
        provider_run = ProviderRun(
            render_job_id=render_job.id,
            render_step_id=render_step.id,
            project_id=render_job.project_id,
            workspace_id=render_job.workspace_id,
            execution_mode=execution_mode,
            worker_id=worker_id,
            provider_credential_id=provider_credential_id,
            provider_name=provider_name,
            provider_model=provider_model,
            operation=operation,
            request_hash=self._hash_request(request_payload),
            status=status,
            request_payload=request_payload,
            routing_decision_payload=routing_decision_payload or {},
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
        self._append_render_event(
            render_job=render_job,
            event_type="render.blocked",
            target_type="render_step",
            target_id=str(step.id),
            render_step_id=step.id,
            payload={"error_code": error_code, "error_message": error_message},
        )

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

    def _register_uploaded_asset(
        self,
        *,
        render_job: RenderJob,
        render_step: RenderStep,
        scene_segment: SceneSegment | None,
        bucket_name: str,
        object_name: str,
        file_name: str,
        content_type: str,
        asset_type: AssetType,
        asset_role: AssetRole,
        metadata_payload: dict[str, object] | None = None,
        parent_asset_id: UUID | None = None,
        provider_run_id: UUID | None = None,
        has_audio_stream: bool = False,
        source_audio_policy: str = "request_silent",
        timing_alignment_strategy: str = "none",
    ) -> Asset:
        payload_bytes = self.storage.read_bytes(bucket_name, object_name)
        metadata = dict(metadata_payload or {})
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
            object_name=object_name,
            file_name=file_name,
            content_type=content_type,
            size_bytes=len(payload_bytes),
            duration_ms=metadata.get("duration_ms"),
            width=metadata.get("width"),
            height=metadata.get("height"),
            frame_rate=metadata.get("frame_rate"),
            has_audio_stream=has_audio_stream,
            source_audio_policy=source_audio_policy,
            timing_alignment_strategy=timing_alignment_strategy,
            metadata_payload=metadata,
        )
        self.db.add(asset)
        self.db.flush()
        return asset

    @staticmethod
    def _fallback_hosted_decision(modality: str) -> RoutingDecision:
        defaults = {
            "image": ("azure_openai_image", "azure_openai_image", "azure-openai-image"),
            "video": ("veo_video", "veo_video", "veo-video"),
            "speech": ("azure_openai_speech", "azure_openai_speech", "azure-openai-speech"),
        }
        provider_key, provider_name, provider_model = defaults[modality]
        return RoutingDecision(
            modality=modality,
            execution_mode=ExecutionMode.hosted,
            provider_key=provider_key,
            provider_name=provider_name,
            provider_model=provider_model,
            reason="capability_mismatch_fallback",
        )

    @staticmethod
    def _output_spec(
        *,
        role: str,
        bucket_name: str,
        object_name: str,
        upload_url: str,
        content_type: str,
        file_name: str,
    ) -> dict[str, object]:
        return {
            "role": role,
            "bucket_name": bucket_name,
            "object_name": object_name,
            "upload_url": upload_url,
            "content_type": content_type,
            "file_name": file_name,
        }

    def _image_provider_and_decision(
        self,
        step: RenderStep,
        workspace_id: UUID,
    ) -> tuple[ImageProvider | None, RoutingDecision]:
        if step.input_payload.get("force_hosted"):
            return build_image_provider(self.settings), self._fallback_hosted_decision("image")
        return RoutingService(self.db, self.settings).build_image_provider_for_workspace(workspace_id)

    def _video_provider_and_decision(self, step: RenderStep, workspace_id: UUID) -> tuple[VideoProvider | None, RoutingDecision]:
        if step.input_payload.get("force_hosted"):
            return build_video_provider(self.settings), self._fallback_hosted_decision("video")
        return RoutingService(self.db, self.settings).build_video_provider_for_workspace(workspace_id)

    def _speech_provider_and_decision(self, step: RenderStep, workspace_id: UUID) -> tuple[SpeechProvider | None, RoutingDecision]:
        if step.input_payload.get("force_hosted"):
            return build_speech_provider(self.settings), self._fallback_hosted_decision("speech")
        return RoutingService(self.db, self.settings).build_speech_provider_for_workspace(workspace_id)

    def _queue_render_resume(self, render_job_id: UUID) -> None:
        from app.workers.tasks import execute_render_job_task

        execute_render_job_task.delay(str(render_job_id))

    def _complete_local_provider_run(
        self,
        provider_run: ProviderRun,
        *,
        response_payload: dict[str, object],
        duration_seconds: float | None,
    ) -> None:
        provider_run.status = ProviderRunStatus.completed
        provider_run.response_payload = response_payload
        provider_run.completed_at = datetime.now(UTC)
        if duration_seconds is not None:
            provider_run.latency_ms = int(duration_seconds * 1000)
        elif provider_run.started_at:
            provider_run.latency_ms = int(
                max(
                    0.0,
                    (datetime.now(UTC) - provider_run.started_at).total_seconds(),
                )
                * 1000
            )
        BillingService(self.db, self.settings).capture_provider_run_usage(provider_run)

    def _dispatch_local_provider_run(
        self,
        *,
        render_job: RenderJob,
        render_step: RenderStep,
        routing_decision: RoutingDecision,
        operation: str,
        request_payload: dict[str, object],
    ) -> ProviderRun:
        existing = self._latest_provider_run_for_step(render_step.id, execution_mode=ExecutionMode.local)
        if existing and existing.status in {ProviderRunStatus.queued, ProviderRunStatus.running}:
            return existing
        provider_run = self._create_provider_run(
            render_job=render_job,
            render_step=render_step,
            operation=operation,
            request_payload=request_payload,
            provider_name=routing_decision.provider_name,
            provider_model=routing_decision.provider_model,
            execution_mode=routing_decision.execution_mode,
            worker_id=routing_decision.worker_id,
            provider_credential_id=routing_decision.provider_credential_id,
            routing_decision_payload=routing_decision.to_payload(),
            status=ProviderRunStatus.queued,
        )
        render_step.output_payload = {
            "local_dispatch": True,
            "provider_run_id": str(provider_run.id),
            "worker_id": str(routing_decision.worker_id) if routing_decision.worker_id else None,
        }
        self._set_step_checkpoint(render_step, render_step.output_payload)
        record_audit_event(
            self.db,
            workspace_id=render_job.workspace_id,
            user_id=render_job.created_by_user_id,
            event_type="render.local_worker_dispatched",
            target_type="render_step",
            target_id=str(render_step.id),
            payload={"render_job_id": str(render_job.id), "provider_run_id": str(provider_run.id)},
        )
        self._append_render_event(
            render_job=render_job,
            event_type="render.local_worker_dispatched",
            target_type="render_step",
            target_id=str(render_step.id),
            render_step_id=render_step.id,
            payload={"provider_run_id": str(provider_run.id)},
        )
        return provider_run

    def handle_local_worker_result(
        self,
        worker: LocalWorker,
        provider_run: ProviderRun,
        payload: LocalWorkerJobResultRequest,
    ) -> dict[str, object]:
        render_job = self.db.get(RenderJob, provider_run.render_job_id)
        step = self.db.get(RenderStep, provider_run.render_step_id)
        project = self.db.get(Project, render_job.project_id if render_job else None) if render_job else None
        segment = self.db.get(SceneSegment, step.scene_segment_id) if step and step.scene_segment_id else None
        if not render_job or not step or not project:
            raise ApiError(404, "local_worker_job_not_found", "Local worker job inputs are missing.")

        worker.last_polled_at = datetime.now(UTC)
        worker.last_error_at = None
        worker.last_error_code = None
        worker.last_error_message = None
        provider_run.response_payload = {"provider_metadata": payload.provider_metadata}

        if payload.status == "failed":
            provider_run.status = ProviderRunStatus.failed
            provider_run.completed_at = datetime.now(UTC)
            if payload.error_code == "capability_mismatch":
                provider_run.error_category = ProviderErrorCategory.deterministic_input
                provider_run.error_code = payload.error_code
                provider_run.error_message = payload.error_message or "Worker capability mismatch."
                step.status = JobStatus.queued
                step.error_code = None
                step.error_message = None
                step.input_payload = {
                    **dict(step.input_payload or {}),
                    "force_hosted": True,
                }
                render_job.status = JobStatus.queued
                render_job.error_code = None
                render_job.error_message = None
                self._append_render_event(
                    render_job=render_job,
                    event_type="render.local_worker_rerouted",
                    target_type="render_step",
                    target_id=str(step.id),
                    render_step_id=step.id,
                    payload={"provider_run_id": str(provider_run.id)},
                )
                self.db.commit()
                self._queue_render_resume(render_job.id)
                return {
                    "render_job_id": render_job.id,
                    "render_step_id": step.id,
                    "provider_run_id": provider_run.id,
                    "status": "rerouted",
                }
            worker.last_error_at = datetime.now(UTC)
            worker.last_error_code = payload.error_code
            worker.last_error_message = payload.error_message
            error = AdapterError(
                "transient" if payload.is_retryable else "internal",
                payload.error_code or "local_worker_failed",
                payload.error_message or "Local worker execution failed.",
            )
            self._fail_step(step, error)
            render_job.status = JobStatus.failed
            render_job.error_code = error.code
            render_job.error_message = error.message
            render_job.completed_at = datetime.now(UTC)
            BillingService(self.db, self.settings).release_render_reservation(render_job, reason="failed")
            self._append_render_event(
                render_job=render_job,
                event_type="render.local_worker_failed",
                target_type="render_step",
                target_id=str(step.id),
                render_step_id=step.id,
                payload={"error_code": error.code, "error_message": error.message},
            )
            self.db.commit()
            return {
                "render_job_id": render_job.id,
                "render_step_id": step.id,
                "provider_run_id": provider_run.id,
                "status": "failed",
            }

        moderation_provider, _moderation_decision = RoutingService(
            self.db,
            self.settings,
        ).build_moderation_provider_for_workspace(project.workspace_id)
        request_payload = dict(provider_run.request_payload or {})
        outputs_by_role = {item.role: item for item in payload.outputs}

        if step.step_kind == StepKind.frame_pair_generation and segment:
            start_output = outputs_by_role.get("start_frame")
            end_output = outputs_by_role.get("end_frame")
            if not start_output or not end_output:
                raise ApiError(
                    400,
                    "local_worker_output_incomplete",
                    "Frame pair jobs must return both start_frame and end_frame outputs.",
                )
            start_asset = self._register_uploaded_asset(
                render_job=render_job,
                render_step=step,
                scene_segment=segment,
                bucket_name=start_output.bucket_name,
                object_name=start_output.object_name,
                file_name=start_output.file_name,
                content_type=start_output.content_type,
                asset_type=AssetType.image,
                asset_role=AssetRole.scene_start_frame,
                metadata_payload=start_output.metadata_payload,
                parent_asset_id=segment.chained_from_asset_id,
                provider_run_id=provider_run.id,
            )
            end_asset = self._register_uploaded_asset(
                render_job=render_job,
                render_step=step,
                scene_segment=segment,
                bucket_name=end_output.bucket_name,
                object_name=end_output.object_name,
                file_name=end_output.file_name,
                content_type=end_output.content_type,
                asset_type=AssetType.image,
                asset_role=AssetRole.scene_end_frame,
                metadata_payload=end_output.metadata_payload,
                parent_asset_id=start_asset.id,
                provider_run_id=provider_run.id,
            )
            segment.start_image_asset_id = start_asset.id
            segment.end_image_asset_id = end_asset.id
            segment.chained_from_asset_id = (
                UUID(str(request_payload.get("provider_metadata", {}).get("previous_end_asset_id")))
                if request_payload.get("provider_metadata", {}).get("previous_end_asset_id")
                else None
            )
            self._record_prompt_history(
                render_job=render_job,
                render_step=step,
                scene_segment=segment,
                provider_run=provider_run,
                asset=start_asset,
                prompt_role="scene_start_frame",
                prompt_text=str(request_payload.get("start_prompt") or ""),
                source_asset_id=segment.chained_from_asset_id,
                metadata_payload={"scene_index": segment.scene_index, "frame_kind": "start"},
            )
            self._record_prompt_history(
                render_job=render_job,
                render_step=step,
                scene_segment=segment,
                provider_run=provider_run,
                asset=end_asset,
                prompt_role="scene_end_frame",
                prompt_text=str(request_payload.get("end_prompt") or ""),
                source_asset_id=start_asset.id,
                metadata_payload={"scene_index": segment.scene_index, "frame_kind": "end"},
            )
            start_blocked = self._moderate_generated_asset(
                moderation_provider=moderation_provider,
                project=project,
                scene_segment=segment,
                target_type="generated_frame_output_proxy",
                asset=start_asset,
                input_text=str(request_payload.get("start_prompt") or ""),
            )
            end_blocked = self._moderate_generated_asset(
                moderation_provider=moderation_provider,
                project=project,
                scene_segment=segment,
                target_type="generated_frame_output_proxy",
                asset=end_asset,
                input_text=str(request_payload.get("end_prompt") or ""),
            )
            self._complete_local_provider_run(
                provider_run,
                response_payload={
                    "start_image_asset_id": str(start_asset.id),
                    "end_image_asset_id": str(end_asset.id),
                    "provider_metadata": payload.provider_metadata,
                },
                duration_seconds=payload.duration_seconds,
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
            else:
                step.status = JobStatus.review
                step.completed_at = datetime.now(UTC)
                self._set_step_checkpoint(step, step.output_payload)
                render_job.status = JobStatus.review
                render_job.error_code = None
                render_job.error_message = None
            self.db.commit()
            return {
                "render_job_id": render_job.id,
                "render_step_id": step.id,
                "provider_run_id": provider_run.id,
                "status": render_job.status.value,
            }

        if step.step_kind == StepKind.video_generation and segment:
            video_output = outputs_by_role.get("video_clip")
            if not video_output:
                raise ApiError(
                    400,
                    "local_worker_output_incomplete",
                    "Video jobs must return one video_clip output.",
                )
            raw_asset = self._register_uploaded_asset(
                render_job=render_job,
                render_step=step,
                scene_segment=segment,
                bucket_name=video_output.bucket_name,
                object_name=video_output.object_name,
                file_name=video_output.file_name,
                content_type=video_output.content_type,
                asset_type=AssetType.video_clip,
                asset_role=AssetRole.raw_video_clip,
                metadata_payload={
                    **dict(video_output.metadata_payload or {}),
                    **dict(payload.provider_metadata or {}),
                    "duration_ms": int((payload.duration_seconds or segment.target_duration_seconds) * 1000),
                },
                parent_asset_id=segment.end_image_asset_id,
                provider_run_id=provider_run.id,
                has_audio_stream=bool(payload.has_audio_stream),
                source_audio_policy="strip_after_generation",
            )
            self._record_prompt_history(
                render_job=render_job,
                render_step=step,
                scene_segment=segment,
                provider_run=provider_run,
                asset=raw_asset,
                prompt_role="scene_video",
                prompt_text=str(request_payload.get("prompt") or ""),
                source_asset_id=segment.end_image_asset_id,
                metadata_payload={"scene_index": segment.scene_index},
            )
            self._complete_local_provider_run(
                provider_run,
                response_payload={"asset_id": str(raw_asset.id), "provider_metadata": payload.provider_metadata},
                duration_seconds=payload.duration_seconds,
            )
            if self._moderate_generated_asset(
                moderation_provider=moderation_provider,
                project=project,
                scene_segment=segment,
                target_type="generated_video_output_proxy",
                asset=raw_asset,
                input_text=str(request_payload.get("prompt") or ""),
            ):
                self._set_render_blocked(
                    render_job,
                    step,
                    error_code="moderation_review_required",
                    error_message="Generated video output requires operator moderation review.",
                    checkpoint_payload={"asset_id": str(raw_asset.id)},
                )
                self.db.commit()
                return {
                    "render_job_id": render_job.id,
                    "render_step_id": step.id,
                    "provider_run_id": provider_run.id,
                    "status": render_job.status.value,
                }
            self._complete_step(step, output_payload={"asset_id": str(raw_asset.id)})
            render_job.status = JobStatus.queued
            render_job.error_code = None
            render_job.error_message = None
            self.db.commit()
            self._queue_render_resume(render_job.id)
            return {
                "render_job_id": render_job.id,
                "render_step_id": step.id,
                "provider_run_id": provider_run.id,
                "status": "queued",
            }

        if step.step_kind == StepKind.narration_generation and segment:
            narration_output = outputs_by_role.get("narration")
            if not narration_output:
                raise ApiError(
                    400,
                    "local_worker_output_incomplete",
                    "Narration jobs must return one narration output.",
                )
            narration_content_type = narration_output.content_type
            narration_file_name = narration_output.file_name
            narration_metadata = {
                **dict(narration_output.metadata_payload or {}),
                **dict(payload.provider_metadata or {}),
                "duration_ms": int((payload.duration_seconds or 1) * 1000),
            }
            uploaded_narration_bytes = self.storage.read_bytes(
                narration_output.bucket_name,
                narration_output.object_name,
            )
            narration_probe = probe_media_bytes(
                self.settings,
                file_name=narration_output.file_name,
                bytes_payload=uploaded_narration_bytes,
            )
            narration_stream = next(
                (
                    item
                    for item in narration_probe.get("streams", [])
                    if item.get("codec_type") == "audio"
                ),
                {},
            )
            if not narration_stream:
                fallback_audio = StubSpeechProvider(
                    provider_name="local_worker_audio_fallback",
                    provider_model="stub-speech-v1",
                ).synthesize(
                    text=str(request_payload.get("narration_text") or segment.narration_text),
                    scene_index=segment.scene_index,
                    voice_preset=request_payload.get("voice_preset") if isinstance(request_payload, dict) else None,
                )
                self.storage.put_bytes(
                    narration_output.bucket_name,
                    narration_output.object_name,
                    fallback_audio.bytes_payload,
                    content_type=fallback_audio.content_type,
                )
                narration_content_type = fallback_audio.content_type
                narration_file_name = f"scene-{segment.scene_index:02d}-narration.wav"
                narration_metadata = {
                    **narration_metadata,
                    **fallback_audio.metadata,
                    "fallback_mode": "local_worker_audio_validation",
                }
            narration_asset = self._register_uploaded_asset(
                render_job=render_job,
                render_step=step,
                scene_segment=segment,
                bucket_name=narration_output.bucket_name,
                object_name=narration_output.object_name,
                file_name=narration_file_name,
                content_type=narration_content_type,
                asset_type=AssetType.narration,
                asset_role=AssetRole.narration_track,
                metadata_payload=narration_metadata,
                provider_run_id=provider_run.id,
                has_audio_stream=True,
            )
            segment.actual_voice_duration_seconds = max(1, int((narration_asset.duration_ms or 0) / 1000))
            self._record_prompt_history(
                render_job=render_job,
                render_step=step,
                scene_segment=segment,
                provider_run=provider_run,
                asset=narration_asset,
                prompt_role="narration_generation",
                prompt_text=str(request_payload.get("narration_text") or ""),
                metadata_payload={"scene_index": segment.scene_index},
            )
            self._complete_local_provider_run(
                provider_run,
                response_payload={
                    "asset_id": str(narration_asset.id),
                    "provider_metadata": payload.provider_metadata,
                },
                duration_seconds=payload.duration_seconds,
            )
            self._complete_step(step, output_payload={"asset_id": str(narration_asset.id)})
            render_job.status = JobStatus.queued
            render_job.error_code = None
            render_job.error_message = None
            self.db.commit()
            self._queue_render_resume(render_job.id)
            return {
                "render_job_id": render_job.id,
                "render_step_id": step.id,
                "provider_run_id": provider_run.id,
                "status": "queued",
            }

        raise ApiError(400, "local_worker_step_unsupported", "That render step does not support local worker results.")

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
        policy = ExecutionPolicyService(self.db).get_effective_policy(project.workspace_id)
        if policy.get("pause_render_generation"):
            raise ApiError(
                423,
                "render_generation_paused",
                str(policy.get("pause_reason") or "Render generation is currently paused for this workspace."),
            )
        billing = BillingService(self.db, self.settings)
        billing.ensure_render_credits_available(
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
        billing.reserve_render_credits(
            render_job,
            scene_count=scene_plan.scene_count or len(self._scene_segments(scene_plan.id)),
        )
        record_audit_event(
            self.db,
            workspace_id=project.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="render.created",
            target_type="render_job",
            target_id=str(render_job.id),
            payload=request_payload,
        )
        self._append_render_event(
            render_job=render_job,
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

    def list_renders(self, auth: AuthContext, project_id: str) -> list[dict[str, object]]:
        project = self._get_project(project_id, auth.workspace_id)
        render_jobs = self.db.scalars(
            select(RenderJob)
            .where(
                RenderJob.project_id == project.id,
                RenderJob.job_kind == JobKind.render_generation,
            )
            .order_by(RenderJob.created_at.desc())
        ).all()
        return [self._render_detail_dict(render_job) for render_job in render_jobs]

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
        BillingService(self.db, self.settings).release_render_reservation(render_job, reason="cancelled")
        record_audit_event(
            self.db,
            workspace_id=render_job.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="render.cancelled",
            target_type="render_job",
            target_id=str(render_job.id),
            payload={},
        )
        self._append_render_event(
            render_job=render_job,
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

    def generate_scene_narration(
        self,
        auth: AuthContext,
        render_job_id: str,
        scene_segment_id: str,
        *,
        voice: str | None = None,
    ) -> dict[str, object]:
        render_job = self._get_render_job_for_auth(auth, render_job_id)
        segment = self.db.get(SceneSegment, UUID(scene_segment_id))
        if not segment:
            raise ApiError(404, "scene_segment_not_found", "Scene segment not found.")

        voice_preset: dict[str, object] = {}
        if voice:
            voice_preset["provider_voice"] = voice

        speech_provider, routing_decision = (
            RoutingService(self.db, self.settings)
            .build_speech_provider_for_workspace(render_job.workspace_id)
        )
        if speech_provider is None:
            raise ApiError(
                400,
                "speech_provider_not_available",
                "No speech provider is configured. Set up an audio generation provider in Settings.",
            )

        step = self._get_or_create_step(
            render_job,
            step_kind=StepKind.narration_generation,
            step_index=3000 + segment.scene_index,
            scene_segment_id=segment.id,
            input_payload={
                "scene_index": segment.scene_index,
                "narration_text": segment.narration_text,
                "voice": voice or "",
            },
        )
        step.status = JobStatus.queued
        step.error_code = None
        step.error_message = None
        self._set_step_running(step)
        self.db.commit()

        provider_run = self._create_provider_run(
            render_job=render_job,
            render_step=step,
            operation="narration_generation",
            request_payload={"text": segment.narration_text, "voice_preset": voice_preset},
            provider_name=routing_decision.provider_name,
            provider_model=routing_decision.provider_model,
            execution_mode=routing_decision.execution_mode,
            worker_id=routing_decision.worker_id,
            provider_credential_id=routing_decision.provider_credential_id,
            routing_decision_payload=routing_decision.to_payload(),
        )
        started = time.perf_counter()
        try:
            generated = speech_provider.synthesize(
                text=segment.narration_text,
                scene_index=segment.scene_index,
                voice_preset=voice_preset or None,
            )
            narration_probe = probe_media_bytes(
                self.settings,
                file_name=f"scene-{segment.scene_index:02d}-narration.{generated.file_extension}",
                bytes_payload=generated.bytes_payload,
            )
            audio_stream = next(
                (s for s in narration_probe.get("streams", []) if s.get("codec_type") == "audio"),
                {},
            )
            narration_duration_ms = int(
                float((narration_probe.get("format") or {}).get("duration") or 0) * 1000
            ) or int(generated.metadata.get("duration_ms") or 0)
            generated.metadata = {
                **generated.metadata,
                "duration_ms": narration_duration_ms,
                "sample_rate": audio_stream.get("sample_rate"),
            }
            narration_asset = self._store_generated_asset(
                render_job=render_job,
                render_step=step,
                scene_segment=segment,
                generated_media=generated,
                bucket_name=self.settings.minio_bucket_assets,
                object_name=(
                    f"{self._scene_object_prefix(render_job, segment.scene_index)}/audio/"
                    f"narration.{generated.file_extension}"
                ),
                file_name=f"scene-{segment.scene_index:02d}-narration.{generated.file_extension}",
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
        self._complete_step(step, output_payload={"asset_id": str(narration_asset.id)})
        segment.actual_voice_duration_seconds = max(1, int((narration_asset.duration_ms or 0) / 1000))
        self.db.commit()
        return {
            "asset_id": str(narration_asset.id),
            "download_url": self._asset_download_url(narration_asset),
            "duration_ms": narration_asset.duration_ms,
            "voice": voice or "",
        }

    def list_render_events(
        self,
        auth: AuthContext,
        render_job_id: str,
        *,
        after_sequence: int | None = None,
    ) -> list[dict[str, object]]:
        render_job = self._get_render_job_for_auth(auth, render_job_id)
        query = (
            select(RenderEvent)
            .where(RenderEvent.render_job_id == render_job.id)
            .order_by(RenderEvent.sequence_number.asc())
        )
        if after_sequence:
            query = query.where(RenderEvent.sequence_number > after_sequence)
        events = self.db.scalars(query).all()
        return [
            {
                "sequence_number": event.sequence_number,
                "at": event.created_at,
                "render_job_id": event.render_job_id,
                "render_step_id": event.render_step_id,
                "event_type": event.event_type,
                "target_type": event.target_type,
                "target_id": event.target_id,
                "payload": event.payload,
            }
            for event in events
        ]

    def mark_job_retry(self, job_id: str, error: AdapterError) -> None:
        self.db.rollback()
        render_job = self.db.get(RenderJob, UUID(job_id))
        if not render_job:
            return
        running_step = self.db.scalar(
            select(RenderStep)
            .where(RenderStep.render_job_id == render_job.id, RenderStep.status == JobStatus.running)
            .order_by(RenderStep.step_index.asc())
        )
        if not running_step:
            running_step = self.db.scalar(
                select(RenderStep)
                .where(RenderStep.render_job_id == render_job.id, RenderStep.status == JobStatus.queued)
                .order_by(RenderStep.step_index.asc())
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
            self._append_render_event(
                render_job=render_job,
                event_type="render.step_retry_scheduled",
                target_type="render_step",
                target_id=str(running_step.id),
                render_step_id=running_step.id,
                payload={"error_code": error.code, "error_message": error.message},
            )
        self.db.commit()

    def mark_job_failed(self, job_id: str, error: AdapterError) -> None:
        self.db.rollback()
        render_job = self.db.get(RenderJob, UUID(job_id))
        if not render_job:
            return
        # After rollback the step may have reverted from running → queued (uncommitted status),
        # so fall back to the first queued step when no running step exists.
        running_step = self.db.scalar(
            select(RenderStep)
            .where(RenderStep.render_job_id == render_job.id, RenderStep.status == JobStatus.running)
            .order_by(RenderStep.step_index.asc())
        )
        if not running_step:
            running_step = self.db.scalar(
                select(RenderStep)
                .where(RenderStep.render_job_id == render_job.id, RenderStep.status == JobStatus.queued)
                .order_by(RenderStep.step_index.asc())
            )
        render_job.status = JobStatus.failed
        render_job.error_code = error.code
        render_job.error_message = error.message
        render_job.completed_at = datetime.now(UTC)
        if running_step:
            self._fail_step(running_step, error)
            self._append_render_event(
                render_job=render_job,
                event_type="render.step_failed",
                target_type="render_step",
                target_id=str(running_step.id),
                render_step_id=running_step.id,
                payload={"error_code": error.code, "error_message": error.message},
            )
        BillingService(self.db, self.settings).release_render_reservation(render_job, reason="failed")
        NotificationService(self.db, self.settings).notify_render_failed(render_job, reason=error.message)
        self._append_render_event(
            render_job=render_job,
            event_type="render.failed",
            target_type="render_job",
            target_id=str(render_job.id),
            payload={"error_code": error.code, "error_message": error.message},
        )
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
        self._append_render_event(
            render_job=render_job,
            event_type="render.frame_pair_approved",
            target_type="render_step",
            target_id=str(step.id),
            render_step_id=step.id,
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
            if project:
                project.stage = ProjectStage.renders
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
        if step.status == JobStatus.review and step.step_kind == StepKind.frame_pair_generation:
            return self.regenerate_frame_pair(auth, render_job_id, step_id)
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
        self._append_render_event(
            render_job=render_job,
            event_type="render.step_retry_requested",
            target_type="render_step",
            target_id=str(step.id),
            render_step_id=step.id,
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
        image_provider: ImageProvider | None,
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
            pending_local = self._latest_provider_run_for_step(step.id, execution_mode=ExecutionMode.local)
            if step.status == JobStatus.running and pending_local and pending_local.status in {
                ProviderRunStatus.queued,
                ProviderRunStatus.running,
            }:
                render_job.status = JobStatus.running
                self.db.commit()
                return True

            self._set_step_running(step)
            self.db.commit()
            start_source_asset_id = UUID(previous_end_asset_id) if previous_end_asset_id else None
            resolved_image_provider, routing_decision = self._image_provider_and_decision(
                step,
                render_job.workspace_id,
            )
            previous_asset = self.db.get(Asset, UUID(previous_end_asset_id)) if previous_end_asset_id else None
            ordered_reference_images: list[ImageReference] = []
            if previous_asset:
                ordered_reference_images.append(
                    ImageReference(
                        asset_id=str(previous_asset.id),
                        content_type=previous_asset.content_type,
                        bytes_payload=self.storage.read_bytes(
                            previous_asset.bucket_name,
                            previous_asset.object_name,
                        ),
                        role="chain_anchor",
                    )
                )
            scene_context = {
                "title": segment.title or "",
                "beat": segment.beat or "",
                "narration_text": segment.narration_text or "",
                "visual_direction": segment.visual_direction or "",
                "shot_type": segment.shot_type or "",
                "motion": segment.motion or "",
            }
            composed_start = compose_frame_generation_prompt(
                user_prompt=segment.start_image_prompt,
                frame_kind="start",
                scene_index=segment.scene_index,
                consistency_pack_state=consistency_pack_state,
                scene_context=scene_context,
                uses_prior_scene_anchor=bool(previous_asset),
            )
            composed_end = compose_frame_generation_prompt(
                user_prompt=segment.end_image_prompt,
                frame_kind="end",
                scene_index=segment.scene_index,
                consistency_pack_state=consistency_pack_state,
                scene_context=scene_context,
                uses_prior_scene_anchor=False,
            )
            provider_request = {
                "scene_index": segment.scene_index,
                "start_prompt": composed_start,
                "end_prompt": composed_end,
                "start_prompt_user": segment.start_image_prompt,
                "end_prompt_user": segment.end_image_prompt,
                "previous_end_asset_id": previous_end_asset_id,
                "ordered_reference_asset_ids": [
                    reference.asset_id for reference in ordered_reference_images if reference.asset_id
                ],
                "consistency_pack_id": str(render_job.consistency_pack_id),
                "routing": routing_decision.to_payload(),
            }
            if routing_decision.execution_mode == ExecutionMode.local:
                start_object_name = f"{self._scene_object_prefix(render_job, segment.scene_index)}/images/start.png"
                end_object_name = f"{self._scene_object_prefix(render_job, segment.scene_index)}/images/end.png"
                local_payload = {
                    "step_kind": StepKind.frame_pair_generation.value,
                    "modality": "image",
                    "scene_index": segment.scene_index,
                    "start_prompt": composed_start,
                    "end_prompt": composed_end,
                    "start_frame_url": self._asset_download_url(previous_asset),
                    "reference_image_urls": (
                        [self._asset_download_url(previous_asset)] if previous_asset else []
                    ),
                    "outputs": [
                        self._output_spec(
                            role="start_frame",
                            bucket_name=self.settings.minio_bucket_assets,
                            object_name=start_object_name,
                            upload_url=self.storage.presigned_put_url(
                                self.settings.minio_bucket_assets,
                                start_object_name,
                            ),
                            content_type="image/png",
                            file_name=f"scene-{segment.scene_index:02d}-start.png",
                        ),
                        self._output_spec(
                            role="end_frame",
                            bucket_name=self.settings.minio_bucket_assets,
                            object_name=end_object_name,
                            upload_url=self.storage.presigned_put_url(
                                self.settings.minio_bucket_assets,
                                end_object_name,
                            ),
                            content_type="image/png",
                            file_name=f"scene-{segment.scene_index:02d}-end.png",
                        ),
                    ],
                    "provider_metadata": {
                        "previous_end_asset_id": previous_end_asset_id,
                        "consistency_pack_id": str(render_job.consistency_pack_id)
                        if render_job.consistency_pack_id
                        else None,
                    },
                }
                self._dispatch_local_provider_run(
                    render_job=render_job,
                    render_step=step,
                    routing_decision=routing_decision,
                    operation="frame_pair_generation",
                    request_payload=local_payload,
                )
                render_job.status = JobStatus.running
                render_job.error_code = None
                render_job.error_message = None
                self.db.commit()
                return True
            provider_run = self._create_provider_run(
                render_job=render_job,
                render_step=step,
                operation="frame_pair_generation",
                request_payload=provider_request,
                provider_name=routing_decision.provider_name,
                provider_model=routing_decision.provider_model,
                execution_mode=routing_decision.execution_mode,
                worker_id=routing_decision.worker_id,
                provider_credential_id=routing_decision.provider_credential_id,
                routing_decision_payload=routing_decision.to_payload(),
            )
            started = time.perf_counter()
            try:
                assert resolved_image_provider is not None
                start_frame = resolved_image_provider.generate_frame(
                    prompt=composed_start,
                    scene_index=segment.scene_index,
                    frame_kind="start",
                    reference_images=ordered_reference_images,
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
                end_frame = resolved_image_provider.generate_frame(
                    prompt=composed_end,
                    scene_index=segment.scene_index,
                    frame_kind="end",
                    reference_images=[
                        ImageReference(
                            asset_id=str(start_asset.id),
                            content_type=start_frame.content_type,
                            bytes_payload=start_frame.bytes_payload,
                            role="scene_start_frame",
                        ),
                        *ordered_reference_images,
                    ],
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
                input_text=composed_start,
            )
            end_blocked = self._moderate_generated_asset(
                moderation_provider=moderation_provider,
                project=project,
                scene_segment=segment,
                target_type="generated_frame_output_proxy",
                asset=end_asset,
                input_text=composed_end,
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
                self._append_render_event(
                    render_job=render_job,
                    event_type="render.frame_pair_quarantined",
                    target_type="render_step",
                    target_id=str(step.id),
                    render_step_id=step.id,
                    payload={"scene_index": segment.scene_index},
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
            self._append_render_event(
                render_job=render_job,
                event_type="render.frame_pair_ready",
                target_type="render_step",
                target_id=str(step.id),
                render_step_id=step.id,
                payload={"scene_index": segment.scene_index},
            )
            render_job.status = JobStatus.review
            render_job.error_code = None
            render_job.error_message = None
            self.db.commit()

        if awaiting_review:
            return True
        return False

    def _run_video_stage(
        self,
        *,
        render_job: RenderJob,
        project: Project,
        segment: SceneSegment,
        video_provider: VideoProvider | None,
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
        pending_local = self._latest_provider_run_for_step(step.id, execution_mode=ExecutionMode.local)
        if step.status == JobStatus.running and pending_local and pending_local.status in {
            ProviderRunStatus.queued,
            ProviderRunStatus.running,
        }:
            render_job.status = JobStatus.running
            self.db.commit()
            return None

        self._set_step_running(step)
        resolved_video_provider, routing_decision = self._video_provider_and_decision(
            step,
            render_job.workspace_id,
        )
        start_asset = self.db.get(Asset, segment.start_image_asset_id) if segment.start_image_asset_id else None
        end_asset = self.db.get(Asset, segment.end_image_asset_id) if segment.end_image_asset_id else None
        if not start_asset or not end_asset:
            error = AdapterError(
                "deterministic_input",
                "frame_pair_assets_missing",
                "Scene start and end frames are required before video generation.",
            )
            self._fail_step(step, error)
            raise error
        provider_request = {
            "scene_index": segment.scene_index,
            "visual_prompt": segment.visual_prompt,
            "start_image_asset_id": str(segment.start_image_asset_id),
            "end_image_asset_id": str(segment.end_image_asset_id),
            "duration_seconds": segment.target_duration_seconds,
            "request_silent_output": True,
            "continuity_mode": "first_last_frame",
            "routing": routing_decision.to_payload(),
        }
        if routing_decision.execution_mode == ExecutionMode.local:
            raw_object_name = f"{self._scene_object_prefix(render_job, segment.scene_index)}/videos/raw.mp4"
            local_payload = {
                "step_kind": StepKind.video_generation.value,
                "modality": "video",
                "scene_index": segment.scene_index,
                "prompt": segment.visual_prompt,
                "duration_seconds": segment.target_duration_seconds,
                "start_frame_url": self._asset_download_url(start_asset),
                "end_frame_url": self._asset_download_url(end_asset),
                "outputs": [
                    self._output_spec(
                        role="video_clip",
                        bucket_name=self.settings.minio_bucket_assets,
                        object_name=raw_object_name,
                        upload_url=self.storage.presigned_put_url(
                            self.settings.minio_bucket_assets,
                            raw_object_name,
                        ),
                        content_type="video/mp4",
                        file_name=f"scene-{segment.scene_index:02d}-raw.mp4",
                    )
                ],
                "provider_metadata": {
                    "start_image_asset_id": str(segment.start_image_asset_id)
                    if segment.start_image_asset_id
                    else None,
                    "end_image_asset_id": str(segment.end_image_asset_id)
                    if segment.end_image_asset_id
                    else None,
                },
            }
            self._dispatch_local_provider_run(
                render_job=render_job,
                render_step=step,
                routing_decision=routing_decision,
                operation="video_generation",
                request_payload=local_payload,
            )
            render_job.status = JobStatus.running
            render_job.error_code = None
            render_job.error_message = None
            self.db.commit()
            return None
        provider_run = self._create_provider_run(
            render_job=render_job,
            render_step=step,
            operation="video_generation",
            request_payload=provider_request,
            provider_name=routing_decision.provider_name,
            provider_model=routing_decision.provider_model,
            execution_mode=routing_decision.execution_mode,
            worker_id=routing_decision.worker_id,
            provider_credential_id=routing_decision.provider_credential_id,
            routing_decision_payload=routing_decision.to_payload(),
        )
        started = time.perf_counter()
        try:
            assert resolved_video_provider is not None
            generated = resolved_video_provider.generate_clip(
                prompt=segment.visual_prompt,
                scene_index=segment.scene_index,
                duration_seconds=segment.target_duration_seconds,
                start_frame_bytes=self.storage.read_bytes(start_asset.bucket_name, start_asset.object_name),
                start_frame_content_type=start_asset.content_type,
                end_frame_bytes=self.storage.read_bytes(end_asset.bucket_name, end_asset.object_name),
                end_frame_content_type=end_asset.content_type,
            )
            provider_run.continuity_mode = str(
                generated.metadata.get("continuity_mode") or "first_last_frame"
            )
            raw_asset = self._store_generated_asset(
                render_job=render_job,
                render_step=step,
                scene_segment=segment,
                generated_media=generated,
                bucket_name=self.settings.minio_bucket_assets,
                object_name=(
                    f"{self._scene_object_prefix(render_job, segment.scene_index)}/videos/raw."
                    f"{generated.file_extension}"
                ),
                file_name=f"scene-{segment.scene_index:02d}-raw.{generated.file_extension}",
                asset_type=AssetType.video_clip,
                asset_role=AssetRole.raw_video_clip,
                parent_asset_id=segment.end_image_asset_id,
                provider_run_id=provider_run.id,
                has_audio_stream=bool(generated.metadata.get("has_audio_stream", False)),
                source_audio_policy="request_silent",
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
            self._append_render_event(
                render_job=render_job,
                event_type="render.video_quarantined",
                target_type="render_step",
                target_id=str(step.id),
                render_step_id=step.id,
                payload={"scene_index": segment.scene_index},
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
        self._append_render_event(
            render_job=render_job,
            event_type="render.scene_video_completed",
            target_type="render_step",
            target_id=str(step.id),
            render_step_id=step.id,
            payload={"scene_index": segment.scene_index},
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
        normalized_bytes, normalized_metadata = strip_audio_from_video(
            self.settings,
            source_bytes=source_bytes,
            source_file_name=raw_asset.file_name,
        )
        normalized = GeneratedMedia(
            provider_name="internal_audio_normalizer",
            provider_model="ffmpeg-strip-audio-v1",
            content_type="video/mp4" if raw_asset.content_type.startswith("video/") else raw_asset.content_type,
            file_extension="mp4" if raw_asset.content_type.startswith("video/") else raw_asset.object_name.split(".")[-1],
            bytes_payload=normalized_bytes,
            metadata={
                **raw_asset.metadata_payload,
                **normalized_metadata,
                "normalized": True,
                "source_audio_removed": True,
                "duration_ms": normalized_metadata.get("duration_ms")
                or raw_asset.duration_ms
                or (segment.target_duration_seconds * 1000),
            },
        )
        silent_asset = self._store_generated_asset(
            render_job=render_job,
            render_step=step,
            scene_segment=segment,
            generated_media=normalized,
            bucket_name=self.settings.minio_bucket_assets,
            object_name=f"{self._scene_object_prefix(render_job, segment.scene_index)}/videos/silent.mp4",
            file_name=f"scene-{segment.scene_index:02d}-silent.mp4",
            asset_type=AssetType.video_clip,
            asset_role=AssetRole.silent_video_clip,
            parent_asset_id=raw_asset.id,
            has_audio_stream=False,
            source_audio_policy="request_silent",
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
        speech_provider: SpeechProvider | None,
        voice_preset_snapshot: dict[str, object] | None,
    ) -> Asset | None:
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
        pending_local = self._latest_provider_run_for_step(step.id, execution_mode=ExecutionMode.local)
        if step.status == JobStatus.running and pending_local and pending_local.status in {
            ProviderRunStatus.queued,
            ProviderRunStatus.running,
        }:
            render_job.status = JobStatus.running
            self.db.commit()
            return None

        self._set_step_running(step)
        resolved_speech_provider, routing_decision = self._speech_provider_and_decision(
            step,
            render_job.workspace_id,
        )
        if routing_decision.execution_mode == ExecutionMode.local:
            narration_object_name = (
                f"{self._scene_object_prefix(render_job, segment.scene_index)}/audio/narration.wav"
            )
            local_payload = {
                "step_kind": StepKind.narration_generation.value,
                "modality": "speech",
                "scene_index": segment.scene_index,
                "narration_text": segment.narration_text,
                "voice_preset": voice_preset_snapshot or {},
                "outputs": [
                    self._output_spec(
                        role="narration",
                        bucket_name=self.settings.minio_bucket_assets,
                        object_name=narration_object_name,
                        upload_url=self.storage.presigned_put_url(
                            self.settings.minio_bucket_assets,
                            narration_object_name,
                        ),
                        content_type="audio/wav",
                        file_name=f"scene-{segment.scene_index:02d}-narration.wav",
                    )
                ],
                "provider_metadata": {},
            }
            self._dispatch_local_provider_run(
                render_job=render_job,
                render_step=step,
                routing_decision=routing_decision,
                operation="narration_generation",
                request_payload=local_payload,
            )
            render_job.status = JobStatus.running
            render_job.error_code = None
            render_job.error_message = None
            self.db.commit()
            return None
        provider_run = self._create_provider_run(
            render_job=render_job,
            render_step=step,
            operation="narration_generation",
            request_payload={"text": segment.narration_text, "voice_preset": voice_preset_snapshot or {}},
            provider_name=routing_decision.provider_name,
            provider_model=routing_decision.provider_model,
            execution_mode=routing_decision.execution_mode,
            worker_id=routing_decision.worker_id,
            provider_credential_id=routing_decision.provider_credential_id,
            routing_decision_payload=routing_decision.to_payload(),
        )
        started = time.perf_counter()
        try:
            assert resolved_speech_provider is not None
            generated = resolved_speech_provider.synthesize(
                text=segment.narration_text,
                scene_index=segment.scene_index,
                voice_preset=voice_preset_snapshot,
            )
            narration_probe = probe_media_bytes(
                self.settings,
                file_name=f"scene-{segment.scene_index:02d}-narration.{generated.file_extension}",
                bytes_payload=generated.bytes_payload,
            )
            audio_stream = next(
                (
                    item
                    for item in narration_probe.get("streams", [])
                    if item.get("codec_type") == "audio"
                ),
                {},
            )
            narration_duration_ms = int(
                float((narration_probe.get("format") or {}).get("duration") or 0) * 1000
            ) or int(generated.metadata.get("duration_ms") or 0)
            generated.metadata = {
                **generated.metadata,
                "duration_ms": narration_duration_ms,
                "sample_rate": audio_stream.get("sample_rate"),
            }
            narration_asset = self._store_generated_asset(
                render_job=render_job,
                render_step=step,
                scene_segment=segment,
                generated_media=generated,
                bucket_name=self.settings.minio_bucket_assets,
                object_name=(
                    f"{self._scene_object_prefix(render_job, segment.scene_index)}/audio/"
                    f"narration.{generated.file_extension}"
                ),
                file_name=f"scene-{segment.scene_index:02d}-narration.{generated.file_extension}",
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
        retimed_bytes, retimed_metadata = retime_video_to_target(
            self.settings,
            source_bytes=self.storage.read_bytes(silent_asset.bucket_name, silent_asset.object_name),
            source_file_name=silent_asset.file_name,
            target_duration_ms=narration_duration_ms,
        )
        retimed = GeneratedMedia(
            provider_name="internal_retimer",
            provider_model="ffmpeg-retime-v1",
            content_type="video/mp4" if silent_asset.content_type.startswith("video/") else silent_asset.content_type,
            file_extension="mp4" if silent_asset.content_type.startswith("video/") else silent_asset.object_name.split(".")[-1],
            bytes_payload=retimed_bytes,
            metadata={
                **silent_asset.metadata_payload,
                **retimed_metadata,
                "duration_ms": retimed_metadata.get("duration_ms") or narration_duration_ms,
                "timing_alignment_strategy": retimed_metadata.get("timing_alignment_strategy")
                or strategy,
            },
        )
        retimed_asset = self._store_generated_asset(
            render_job=render_job,
            render_step=step,
            scene_segment=segment,
            generated_media=retimed,
            bucket_name=self.settings.minio_bucket_assets,
            object_name=f"{self._scene_object_prefix(render_job, segment.scene_index)}/videos/retimed.mp4",
            file_name=f"scene-{segment.scene_index:02d}-retimed.mp4",
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

    def _run_slide_generation_stage(
        self,
        *,
        render_job: RenderJob,
        segment: SceneSegment,
        narration_asset: Asset,
        animation_effect: str,
    ) -> Asset:
        step = self._get_or_create_step(
            render_job,
            step_kind=StepKind.video_generation,
            step_index=1000 + segment.scene_index,
            scene_segment_id=segment.id,
            input_payload={
                "scene_index": segment.scene_index,
                "mode": "slide",
                "animation_effect": animation_effect,
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

        start_asset = self.db.get(Asset, segment.start_image_asset_id) if segment.start_image_asset_id else None
        end_asset = self.db.get(Asset, segment.end_image_asset_id) if segment.end_image_asset_id else None
        if not start_asset or not end_asset:
            error = AdapterError(
                "deterministic_input",
                "frame_pair_assets_missing",
                "Scene start and end frames are required for slide generation.",
            )
            self._fail_step(step, error)
            raise error

        target_duration_ms = int(narration_asset.duration_ms or 0) or int(segment.target_duration_seconds * 1000)

        start_bytes = self.storage.read_bytes(start_asset.bucket_name, start_asset.object_name)
        end_bytes = self.storage.read_bytes(end_asset.bucket_name, end_asset.object_name)

        slide_bytes, slide_metadata = create_slide_clip_from_images(
            self.settings,
            start_frame_bytes=start_bytes,
            end_frame_bytes=end_bytes,
            target_duration_ms=target_duration_ms,
            animation_effect=animation_effect,
        )

        is_fallback = slide_metadata.get("fallback_format") == "json"
        content_type = "application/json" if is_fallback else "video/mp4"
        file_ext = "json" if is_fallback else "mp4"

        generated = GeneratedMedia(
            provider_name="internal_slide_generator",
            provider_model="ffmpeg-slide-v1",
            content_type=content_type,
            file_extension=file_ext,
            bytes_payload=slide_bytes,
            metadata={
                **slide_metadata,
                "scene_index": segment.scene_index,
                "start_image_asset_id": str(start_asset.id),
                "end_image_asset_id": str(end_asset.id),
                "target_duration_ms": target_duration_ms,
            },
        )

        slide_asset = self._store_generated_asset(
            render_job=render_job,
            render_step=step,
            scene_segment=segment,
            generated_media=generated,
            bucket_name=self.settings.minio_bucket_assets,
            object_name=(
                f"{self._scene_object_prefix(render_job, segment.scene_index)}/videos/slide.{file_ext}"
            ),
            file_name=f"scene-{segment.scene_index:02d}-slide.{file_ext}",
            asset_type=AssetType.video_clip,
            asset_role=AssetRole.retimed_video_clip,
            has_audio_stream=False,
            source_audio_policy="request_silent",
        )

        self._complete_step(step, output_payload={"asset_id": str(slide_asset.id), "mode": "slide"})
        self._append_render_event(
            render_job=render_job,
            event_type="render.scene_slide_completed",
            target_type="render_step",
            target_id=str(step.id),
            render_step_id=step.id,
            payload={"scene_index": segment.scene_index, "animation_effect": animation_effect},
        )
        return slide_asset

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
            provider_name="curated_music_library",
            provider_model="royalty-free-pack-1",
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

    def _should_hold_export_for_moderation(self, render_job: RenderJob) -> tuple[bool, int, str]:
        lookback = datetime.now(UTC) - timedelta(days=self.settings.export_moderation_lookback_days)
        blocked_count = int(
            self.db.scalar(
                select(func.count())
                .select_from(ModerationEvent)
                .where(
                    ModerationEvent.workspace_id == render_job.workspace_id,
                    ModerationEvent.decision == ModerationDecision.blocked,
                    ModerationEvent.created_at >= lookback,
                )
            )
            or 0
        )
        if blocked_count > 0:
            return True, blocked_count, "recent_workspace_block"
        threshold = int(self.settings.export_moderation_sample_rate * 100)
        sample_bucket = int(str(render_job.id).replace("-", "")[-2:], 16) % 100
        return sample_bucket < threshold, blocked_count, "sampled_export"

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
        subtitle_text = (
            self.storage.read_bytes(subtitle_asset.bucket_name, subtitle_asset.object_name).decode("utf-8")
            if subtitle_asset
            else None
        )
        export_bytes, manifest_bytes, export_metadata = compose_reel_export(
            self.settings,
            clip_files=[
                (video_asset.file_name, self.storage.read_bytes(video_asset.bucket_name, video_asset.object_name))
                for video_asset in retimed_assets
            ],
            narration_files=[
                (audio_asset.file_name, self.storage.read_bytes(audio_asset.bucket_name, audio_asset.object_name))
                for audio_asset in narration_assets
            ],
            music_file=(
                (
                    music_asset.file_name,
                    self.storage.read_bytes(music_asset.bucket_name, music_asset.object_name),
                )
                if music_asset
                else None
            ),
            subtitle_text=subtitle_text,
        )
        export_generated = GeneratedMedia(
            provider_name="internal_ffmpeg_composer",
            provider_model="ffmpeg-export-v1",
            content_type="video/mp4",
            file_extension="mp4",
            bytes_payload=export_bytes,
            metadata={
                **export_metadata,
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
            generated_media=export_generated,
            bucket_name=self.settings.minio_bucket_assets,
            object_name=(
                f"workspace/{render_job.workspace_id}/project/{render_job.project_id}/"
                f"render/{render_job.id}/exports/final-export.mp4"
            ),
            file_name="final-export.mp4",
            asset_type=AssetType.export,
            asset_role=AssetRole.final_export,
            has_audio_stream=True,
        )
        manifest_generated = GeneratedMedia(
            provider_name="internal_ffmpeg_composer",
            provider_model="ffmpeg-export-manifest-v1",
            content_type="application/json",
            file_extension="json",
            bytes_payload=manifest_bytes,
            metadata={
                "sidecar": True,
                "render_job_id": str(render_job.id),
                "scene_plan_id": str(scene_plan.id),
            },
        )
        manifest_asset = self._store_generated_asset(
            render_job=render_job,
            render_step=step,
            scene_segment=None,
            generated_media=manifest_generated,
            bucket_name=self.settings.minio_bucket_assets,
            object_name=(
                f"workspace/{render_job.workspace_id}/project/{render_job.project_id}/"
                f"render/{render_job.id}/exports/final-export-manifest.json"
            ),
            file_name="final-export-manifest.json",
            asset_type=AssetType.export,
            asset_role=AssetRole.final_export,
        )
        hold_export, blocked_count_30d, sample_reason = self._should_hold_export_for_moderation(render_job)
        export_record = ExportRecord(
            workspace_id=render_job.workspace_id,
            project_id=render_job.project_id,
            render_job_id=render_job.id,
            asset_id=export_asset.id,
            status="completed",
            file_name=export_asset.file_name,
            format=str(export_profile.get("format") or "mp4"),
            bucket_name=export_asset.bucket_name,
            object_name=export_asset.object_name,
            duration_ms=export_generated.metadata.get("duration_ms"),
            availability_status="moderation_hold" if hold_export else "available",
            held_at=datetime.now(UTC) if hold_export else None,
            available_at=None if hold_export else datetime.now(UTC),
            subtitle_style_profile=subtitle_style_profile,
            export_profile=export_profile,
            audio_mix_profile=audio_mix_profile,
            metadata_payload={
                **export_generated.metadata,
                "manifest_asset_id": str(manifest_asset.id),
            },
            completed_at=datetime.now(UTC),
        )
        self.db.add(export_record)
        self.db.flush()
        if hold_export:
            export_asset.status = "moderation_hold"
            moderation_report = ModerationReport(
                workspace_id=render_job.workspace_id,
                project_id=render_job.project_id,
                render_job_id=render_job.id,
                export_id=export_record.id,
                related_asset_id=export_asset.id,
                status=ModerationReportStatus.pending,
                sample_reason=sample_reason,
                blocked_event_count_30d=blocked_count_30d,
                findings_payload={"scene_count": len(segments)},
            )
            self.db.add(moderation_report)
        else:
            export_asset.status = "available"
        self._record_prompt_history(
            render_job=render_job,
            render_step=step,
            scene_segment=None,
            provider_run=None,
            asset=manifest_asset,
            export_id=export_record.id,
            prompt_role="final_composition_manifest",
            prompt_text=manifest_bytes.decode("utf-8"),
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
        self._append_render_event(
            render_job=render_job,
            event_type="render.completed",
            target_type="export",
            target_id=str(export_record.id),
            render_step_id=step.id,
            payload={
                "export_id": str(export_record.id),
                "availability_status": export_record.availability_status,
            },
        )
        return export_record

    def execute_render_job(
        self,
        job_id: str,
        *,
        image_provider: ImageProvider | None = None,
        video_provider: VideoProvider | None = None,
        speech_provider: SpeechProvider | None = None,
        music_provider: MusicProvider | None = None,
        moderation_provider: ModerationProvider | None = None,
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
        resolved_moderation_provider = moderation_provider or RoutingService(
            self.db,
            self.settings,
        ).build_moderation_provider_for_workspace(project.workspace_id)[0]
        resolved_music_provider = music_provider or build_music_provider(self.settings)

        voice_preset_snapshot = dict(render_job.payload.get("voice_preset_snapshot", {}) or {})
        subtitle_style_profile, export_profile, audio_mix_profile = self._resolved_project_profiles(
            render_job=render_job,
            project=project,
        )
        segments = self._scene_segments(scene_plan.id)
        render_job.status = JobStatus.running
        render_job.started_at = render_job.started_at or datetime.now(UTC)
        self._append_render_event(
            render_job=render_job,
            event_type="render.started",
            target_type="render_job",
            target_id=str(render_job.id),
            payload={"scene_count": len(segments)},
        )
        self.db.commit()

        if self._run_frame_pair_stage(
            render_job=render_job,
            project=project,
            scene_plan=scene_plan,
            segments=segments,
            consistency_pack_state=consistency_pack_state,
            image_provider=image_provider,
            moderation_provider=resolved_moderation_provider,
        ):
            return

        render_mode = str((render_job.payload or {}).get("render_mode") or "slide")
        animation_profile = dict((render_job.payload or {}).get("animation_profile") or {})
        animation_effect = str(animation_profile.get("effect") or "ken_burns")

        retimed_assets: list[Asset] = []
        narration_assets: list[Asset] = []

        if render_mode == "slide":
            for segment in segments:
                narration_asset = self._run_narration_stage(
                    render_job=render_job,
                    segment=segment,
                    speech_provider=speech_provider,
                    voice_preset_snapshot=voice_preset_snapshot,
                )
                if narration_asset is None:
                    return
                slide_asset = self._run_slide_generation_stage(
                    render_job=render_job,
                    segment=segment,
                    narration_asset=narration_asset,
                    animation_effect=animation_effect,
                )
                retimed_assets.append(slide_asset)
                narration_assets.append(narration_asset)
        else:
            for segment in segments:
                raw_asset = self._run_video_stage(
                    render_job=render_job,
                    project=project,
                    segment=segment,
                    video_provider=video_provider,
                    moderation_provider=resolved_moderation_provider,
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
                if narration_asset is None:
                    return
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
            music_provider=resolved_music_provider,
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
        BillingService(self.db, self.settings).release_render_reservation(render_job, reason="completed")
        NotificationService(self.db, self.settings).notify_render_completed(render_job)
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
            BillingService(self.db, self.settings).release_render_reservation(
                render_job,
                reason="expired",
            )
            self._append_render_event(
                render_job=render_job,
                event_type="render.expired",
                target_type="render_job",
                target_id=str(render_job.id),
                payload={"error_code": "job_timeout"},
            )
            NotificationService(self.db, self.settings).notify_render_failed(
                render_job,
                reason=render_job.error_message,
            )
        self.db.commit()
        return len(stale_jobs)

    def process_frame_pair_review_timeouts(self) -> int:
        threshold = datetime.now(UTC) - timedelta(minutes=max(60, self.settings.render_job_timeout_minutes // 2))
        steps = self.db.scalars(
            select(RenderStep).where(
                RenderStep.step_kind == StepKind.frame_pair_generation,
                RenderStep.status == JobStatus.review,
                RenderStep.last_checkpoint_at < threshold,
            )
        ).all()
        updated = 0
        for step in steps:
            render_job = self.db.get(RenderJob, step.render_job_id)
            if not render_job:
                continue
            step.status = JobStatus.failed
            step.error_code = "frame_pair_review_timeout"
            step.error_message = "Frame-pair review expired before approval."
            step.completed_at = datetime.now(UTC)
            render_job.status = JobStatus.failed
            render_job.error_code = step.error_code
            render_job.error_message = step.error_message
            render_job.completed_at = datetime.now(UTC)
            BillingService(self.db, self.settings).release_render_reservation(
                render_job,
                reason="frame_pair_review_timeout",
            )
            self._append_render_event(
                render_job=render_job,
                event_type="render.review_timeout",
                target_type="render_step",
                target_id=str(step.id),
                render_step_id=step.id,
                payload={"error_code": step.error_code},
            )
            updated += 1
        if updated:
            self.db.commit()
        return updated

    def cleanup_expired_assets(self) -> int:
        now = datetime.now(UTC)
        assets = self.db.scalars(
            select(Asset).where(Asset.expires_at.is_not(None), Asset.expires_at < now, Asset.deleted_at.is_(None))
        ).all()
        deleted = 0
        for asset in assets:
            try:
                self.storage.delete_object(asset.bucket_name, asset.object_name)
            except Exception:
                pass
            asset.deleted_at = now
            asset.status = "deleted"
            deleted += 1
        if deleted:
            self.db.commit()
        return deleted

    def archive_old_quarantine_records(self) -> int:
        threshold = datetime.now(UTC) - timedelta(days=7)
        assets = self.db.scalars(
            select(Asset).where(
                Asset.quarantined_at.is_not(None),
                Asset.quarantined_at < threshold,
                Asset.status == "quarantined",
            )
        ).all()
        archived = 0
        for asset in assets:
            asset.status = "archived_quarantine"
            asset.metadata_payload = {**dict(asset.metadata_payload or {}), "archived_quarantine": True}
            archived += 1
        if archived:
            self.db.commit()
        return archived

    def refresh_provider_health(self) -> int:
        return 1 if build_video_provider(self.settings) else 0

    @staticmethod
    def _format_srt_timestamp(total_ms: int) -> str:
        hours = total_ms // 3_600_000
        minutes = (total_ms % 3_600_000) // 60_000
        seconds = (total_ms % 60_000) // 1_000
        milliseconds = total_ms % 1_000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
