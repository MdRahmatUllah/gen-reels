from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext
from app.core.config import Settings
from app.core.errors import AdapterError, ApiError
from app.integrations.azure import ModerationProvider, TextProvider
from app.models.entities import (
    Asset,
    ExportRecord,
    JobStatus,
    Project,
    ProviderErrorCategory,
    ProviderRun,
    ProviderRunStatus,
    RenderJob,
    SceneSegment,
    Series,
    SeriesRun,
    SeriesRunStep,
    SeriesScript,
    SeriesScriptRevision,
    SeriesVideoRun,
    SeriesVideoRunStep,
)
from app.schemas.series import SeriesRunCreateRequest
from app.services.audit_service import record_audit_event
from app.services.generation_service import GenerationService
from app.services.moderation_service import moderate_text_or_raise
from app.services.permissions import require_workspace_edit
from app.services.presenters import (
    series_published_video_to_dict,
    series_revision_to_dict,
    series_run_to_dict,
    series_script_to_dict,
)
from app.services.render_service import RenderService
from app.services.routing_service import RoutingService
from app.services.series_catalog import get_catalog_option


class SeriesGenerationService(GenerationService):
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

    def _get_series_run(self, run_id: str | UUID) -> SeriesRun:
        record = self.db.get(SeriesRun, UUID(str(run_id)))
        if not record:
            raise ApiError(404, "series_run_not_found", "Series run not found.")
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

    def _get_revision(self, revision_id: UUID | None) -> SeriesScriptRevision | None:
        return self.db.get(SeriesScriptRevision, revision_id) if revision_id else None

    def _assert_mutation_rights(self, auth: AuthContext) -> None:
        require_workspace_edit(auth, message="Only workspace members or admins can perform this action.")

    def _active_run(self, series_id: UUID) -> SeriesRun | None:
        return self.db.scalar(
            select(SeriesRun)
            .where(
                SeriesRun.series_id == series_id,
                SeriesRun.status.in_([JobStatus.queued, JobStatus.running]),
            )
            .order_by(SeriesRun.created_at.desc())
        )

    def _active_video_run(self, series_id: UUID) -> SeriesVideoRun | None:
        return self.db.scalar(
            select(SeriesVideoRun)
            .where(
                SeriesVideoRun.series_id == series_id,
                SeriesVideoRun.status.in_([JobStatus.queued, JobStatus.running]),
            )
            .order_by(SeriesVideoRun.created_at.desc())
        )

    def _latest_sequence_number(self, series_id: UUID) -> int:
        return int(
            self.db.scalar(
                select(func.max(SeriesScript.sequence_number)).where(SeriesScript.series_id == series_id)
            )
            or 0
        )

    def _next_revision_number(self, series_script_id: UUID) -> int:
        return int(
            self.db.scalar(
                select(func.max(SeriesScriptRevision.revision_number)).where(
                    SeriesScriptRevision.series_script_id == series_script_id
                )
            )
            or 0
        ) + 1

    def _get_idempotent_run(
        self,
        *,
        series_id: UUID,
        user_id: UUID,
        idempotency_key: str,
        request_hash: str,
    ) -> SeriesRun | None:
        window_start = datetime.now(timezone.utc) - timedelta(hours=self.settings.idempotency_retention_hours)
        existing = self.db.scalar(
            select(SeriesRun).where(
                SeriesRun.series_id == series_id,
                SeriesRun.created_by_user_id == user_id,
                SeriesRun.idempotency_key == idempotency_key,
                SeriesRun.created_at >= window_start,
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

    def _get_run_with_steps(
        self,
        run_id: str | UUID,
        *,
        series_id: UUID | None = None,
    ) -> tuple[SeriesRun, list[SeriesRunStep]]:
        run = self._get_series_run(run_id)
        if series_id and run.series_id != series_id:
            raise ApiError(404, "series_run_not_found", "Series run not found.")
        steps = self.db.scalars(
            select(SeriesRunStep)
            .where(SeriesRunStep.series_run_id == run.id)
            .order_by(SeriesRunStep.step_index.asc())
        ).all()
        return run, steps

    def _snapshot_from_series(self, series: Series) -> dict[str, object]:
        preset = (
            get_catalog_option("content_presets", series.preset_key)
            if series.content_mode == "preset" and series.preset_key
            else None
        )
        return {
            "series_id": str(series.id),
            "title": series.title,
            "description": series.description,
            "content_mode": series.content_mode,
            "preset_key": series.preset_key,
            "content_preset": preset,
            "custom_topic": series.custom_topic,
            "custom_example_script": series.custom_example_script,
            "language_key": series.language_key,
            "language": get_catalog_option("languages", series.language_key),
            "voice_key": series.voice_key,
            "voice": get_catalog_option("voices", series.voice_key),
            "music_mode": series.music_mode,
            "music_keys": list(series.music_keys or []),
            "music": [get_catalog_option("music", key) for key in list(series.music_keys or [])],
            "art_style_key": series.art_style_key,
            "art_style": get_catalog_option("art_styles", series.art_style_key),
            "caption_style_key": series.caption_style_key,
            "caption_style": get_catalog_option("caption_styles", series.caption_style_key),
            "effect_keys": list(series.effect_keys or []),
            "effects": [get_catalog_option("effects", key) for key in list(series.effect_keys or [])],
        }

    def _series_input_text(self, payload: dict[str, object]) -> str:
        parts: list[str] = []
        for value in [
            payload.get("title"),
            payload.get("description"),
            payload.get("preset_key"),
            payload.get("custom_topic"),
            payload.get("custom_example_script"),
            payload.get("voice_key"),
            payload.get("art_style_key"),
            payload.get("caption_style_key"),
        ]:
            if isinstance(value, str) and value.strip():
                parts.append(value.strip())
        for collection_key in ["music_keys", "effect_keys"]:
            value = payload.get(collection_key)
            if isinstance(value, list):
                parts.extend(str(item).strip() for item in value if str(item).strip())
        return "\n".join(parts)

    def _load_scripts(self, series_id: UUID) -> list[SeriesScript]:
        return self.db.scalars(
            select(SeriesScript)
            .where(SeriesScript.series_id == series_id)
            .order_by(SeriesScript.sequence_number.asc())
        ).all()

    def _active_video_step_map(self, series_id: UUID) -> dict[UUID, SeriesVideoRunStep]:
        steps = self.db.scalars(
            select(SeriesVideoRunStep)
            .join(SeriesVideoRun, SeriesVideoRun.id == SeriesVideoRunStep.series_video_run_id)
            .where(
                SeriesVideoRun.series_id == series_id,
                SeriesVideoRun.status.in_([JobStatus.queued, JobStatus.running]),
                SeriesVideoRunStep.status.in_([JobStatus.queued, JobStatus.running, JobStatus.review]),
            )
            .order_by(SeriesVideoRunStep.created_at.desc())
        ).all()
        return {step.series_script_id: step for step in steps}

    def _latest_video_step(self, series_id: UUID, script_id: UUID) -> SeriesVideoRunStep | None:
        return self.db.scalar(
            select(SeriesVideoRunStep)
            .join(SeriesVideoRun, SeriesVideoRun.id == SeriesVideoRunStep.series_video_run_id)
            .where(
                SeriesVideoRun.series_id == series_id,
                SeriesVideoRunStep.series_script_id == script_id,
            )
            .order_by(SeriesVideoRunStep.created_at.desc())
        )

    def _approved_other_scripts_context(
        self,
        series_id: UUID,
        *,
        exclude_script_id: UUID | None = None,
        before_sequence_number: int | None = None,
    ) -> list[dict[str, object]]:
        scripts = self._load_scripts(series_id)
        context: list[dict[str, object]] = []
        detailed_candidates: list[tuple[SeriesScript, SeriesScriptRevision]] = []
        for script in scripts:
            if exclude_script_id and script.id == exclude_script_id:
                continue
            if before_sequence_number is not None and script.sequence_number >= before_sequence_number:
                continue
            revision = self._get_revision(script.approved_revision_id) or self._get_revision(script.current_revision_id)
            if not revision:
                continue
            detailed_candidates.append((script, revision))
        detailed_ids = {script.id for script, _revision in detailed_candidates[-10:]}
        for script, revision in detailed_candidates:
            context.append(
                {
                    "sequence_number": script.sequence_number,
                    "title": revision.title,
                    "summary": revision.summary if script.id in detailed_ids else "",
                }
            )
        return context

    def _regeneration_context(self, slot: SeriesScript) -> list[dict[str, object]]:
        history = self.db.scalars(
            select(SeriesScriptRevision)
            .where(SeriesScriptRevision.series_script_id == slot.id)
            .order_by(SeriesScriptRevision.revision_number.asc())
        ).all()
        prior = self._approved_other_scripts_context(slot.series_id, exclude_script_id=slot.id)
        for revision in history:
            prior.append(
                {
                    "sequence_number": slot.sequence_number,
                    "title": revision.title,
                    "summary": revision.summary,
                }
            )
        return prior

    def _provider_name(self, routing_decision) -> str:
        if routing_decision:
            return routing_decision.provider_name
        if self.settings.use_stub_providers or self.settings.environment == "test":
            return "stub_text_provider"
        return "azure_openai"

    def _provider_model(self, routing_decision) -> str:
        if routing_decision:
            return routing_decision.provider_model
        return self.settings.azure_openai_chat_deployment or "stub"

    def _published_video_payload(
        self,
        slot: SeriesScript,
        published_revision: SeriesScriptRevision | None,
    ) -> dict[str, object] | None:
        if not slot.published_export_id:
            return None
        export = self.db.get(ExportRecord, slot.published_export_id)
        if not export:
            return None
        render_service = RenderService(self.db, self.settings)
        return series_published_video_to_dict(
            project_id=slot.published_project_id,
            render_job_id=slot.published_render_job_id,
            export_id=slot.published_export_id,
            download_url=render_service._export_download_url(export),
            title=(published_revision.video_title if published_revision else "") or slot.title,
            description=(published_revision.video_description if published_revision else "") or slot.summary,
            completed_at=export.completed_at,
        )

    def _script_card_dict(
        self,
        slot: SeriesScript,
        active_video_step_map: dict[UUID, SeriesVideoRunStep],
    ) -> dict[str, object]:
        current_revision = self._get_revision(slot.current_revision_id)
        approved_revision = self._get_revision(slot.approved_revision_id)
        published_revision = self._get_revision(slot.published_revision_id)
        active_video_step = active_video_step_map.get(slot.id)
        published_video = self._published_video_payload(slot, published_revision)
        approved_ready_for_video = bool(
            approved_revision and slot.approved_revision_id and slot.approved_revision_id != slot.published_revision_id
        )
        if slot.published_revision_id and slot.approved_revision_id == slot.published_revision_id:
            approved_ready_for_video = False
        return series_script_to_dict(
            slot,
            current_revision=current_revision,
            approved_revision=approved_revision,
            published_revision=published_revision,
            published_video=published_video,
            active_video_step=active_video_step,
            can_approve=bool(current_revision and current_revision.approval_state != "approved" and not active_video_step),
            can_reject=bool(current_revision and current_revision.approval_state != "rejected" and not active_video_step),
            can_regenerate=bool(not active_video_step),
            can_create_video=bool(approved_ready_for_video and not active_video_step),
        )

    def list_series_scripts(self, auth: AuthContext, series_id: str) -> list[dict[str, object]]:
        series = self._get_series(series_id, auth.workspace_id)
        active_video_step_map = self._active_video_step_map(series.id)
        scripts = self._load_scripts(series.id)
        return [self._script_card_dict(script, active_video_step_map) for script in scripts]

    def get_series_script_detail(self, auth: AuthContext, series_id: str, script_id: str) -> dict[str, object]:
        series = self._get_series(series_id, auth.workspace_id)
        slot = self._get_series_script(series, script_id)
        active_video_step = self._active_video_step_map(series.id).get(slot.id)
        card = self._script_card_dict(slot, {slot.id: active_video_step} if active_video_step else {})
        latest_video_step = active_video_step or self._latest_video_step(series.id, slot.id)
        revisions = self.db.scalars(
            select(SeriesScriptRevision)
            .where(SeriesScriptRevision.series_script_id == slot.id)
            .order_by(SeriesScriptRevision.revision_number.desc())
        ).all()

        project = self.db.scalar(select(Project).where(Project.series_script_id == slot.id))
        render_job_id = (
            latest_video_step.render_job_id
            if latest_video_step and latest_video_step.render_job_id
            else slot.published_render_job_id
        )
        scene_plan_id = None
        latest_render_status = None
        scenes: list[dict[str, object]] = []
        render_service = RenderService(self.db, self.settings)
        if render_job_id:
            render_job = self.db.get(RenderJob, render_job_id)
            if render_job:
                scene_plan_id = render_job.scene_plan_id
                latest_render_status = (
                    render_job.status.value if isinstance(render_job.status, JobStatus) else str(render_job.status)
                )
        if not scene_plan_id and project and project.active_scene_plan_id:
            scene_plan_id = project.active_scene_plan_id
        if scene_plan_id:
            segments = self.db.scalars(
                select(SceneSegment)
                .where(SceneSegment.scene_plan_id == scene_plan_id)
                .order_by(SceneSegment.scene_index.asc())
            ).all()
            for segment in segments:
                asset_rows = self.db.scalars(
                    select(Asset).where(Asset.scene_segment_id == segment.id)
                ).all()
                by_role = {asset.asset_role.value: asset for asset in asset_rows}
                preferred_slide = (
                    by_role.get("retimed_video_clip")
                    or by_role.get("silent_video_clip")
                    or by_role.get("raw_video_clip")
                )
                scenes.append(
                    {
                        "scene_segment_id": segment.id,
                        "scene_index": segment.scene_index,
                        "title": segment.title,
                        "beat": segment.beat,
                        "narration_text": segment.narration_text,
                        "caption_text": segment.caption_text,
                        "target_duration_seconds": segment.target_duration_seconds,
                        "visual_prompt": segment.visual_prompt,
                        "start_image_prompt": segment.start_image_prompt,
                        "end_image_prompt": segment.end_image_prompt,
                        "start_frame_asset": (
                            {
                                "asset_id": by_role["scene_start_frame"].id,
                                "download_url": render_service._asset_download_url(by_role["scene_start_frame"]),
                            }
                            if "scene_start_frame" in by_role
                            else None
                        ),
                        "end_frame_asset": (
                            {
                                "asset_id": by_role["scene_end_frame"].id,
                                "download_url": render_service._asset_download_url(by_role["scene_end_frame"]),
                            }
                            if "scene_end_frame" in by_role
                            else None
                        ),
                        "narration_asset": (
                            {
                                "asset_id": by_role["narration_track"].id,
                                "download_url": render_service._asset_download_url(by_role["narration_track"]),
                            }
                            if "narration_track" in by_role
                            else None
                        ),
                        "slide_asset": (
                            {
                                "asset_id": preferred_slide.id,
                                "download_url": render_service._asset_download_url(preferred_slide),
                            }
                            if preferred_slide
                            else None
                        ),
                    }
                )

        return {
            "script": card,
            "revisions": [series_revision_to_dict(revision) for revision in revisions],
            "scenes": scenes,
            "latest_render_job_id": render_job_id,
            "latest_render_status": latest_render_status,
            "latest_scene_plan_id": scene_plan_id,
        }

    def approve_series_script(self, auth: AuthContext, series_id: str, script_id: str) -> dict[str, object]:
        self._assert_mutation_rights(auth)
        series = self._get_series(series_id, auth.workspace_id)
        slot = self._get_series_script(series, script_id)
        if self._active_video_step_map(series.id).get(slot.id):
            raise ApiError(409, "series_script_video_active", "This script is currently generating a video.")
        current_revision = self._get_revision(slot.current_revision_id)
        if not current_revision:
            raise ApiError(400, "series_script_missing_revision", "Series script has no current revision.")
        current_revision.approval_state = "approved"
        if slot.approved_revision_id and slot.approved_revision_id != current_revision.id:
            previous = self._get_revision(slot.approved_revision_id)
            if previous and slot.published_revision_id != previous.id:
                previous.approval_state = "superseded"
        slot.approved_revision_id = current_revision.id
        record_audit_event(
            self.db,
            workspace_id=series.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="series.script_approved",
            target_type="series_script_revision",
            target_id=str(current_revision.id),
            payload={"series_script_id": str(slot.id)},
        )
        self.db.commit()
        self.db.refresh(slot)
        return self._script_card_dict(slot, self._active_video_step_map(series.id))

    def reject_series_script(self, auth: AuthContext, series_id: str, script_id: str) -> dict[str, object]:
        self._assert_mutation_rights(auth)
        series = self._get_series(series_id, auth.workspace_id)
        slot = self._get_series_script(series, script_id)
        if self._active_video_step_map(series.id).get(slot.id):
            raise ApiError(409, "series_script_video_active", "This script is currently generating a video.")
        current_revision = self._get_revision(slot.current_revision_id)
        if not current_revision:
            raise ApiError(400, "series_script_missing_revision", "Series script has no current revision.")
        current_revision.approval_state = "rejected"
        if slot.approved_revision_id == current_revision.id:
            slot.approved_revision_id = None
        record_audit_event(
            self.db,
            workspace_id=series.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="series.script_rejected",
            target_type="series_script_revision",
            target_id=str(current_revision.id),
            payload={"series_script_id": str(slot.id)},
        )
        self.db.commit()
        self.db.refresh(slot)
        return self._script_card_dict(slot, self._active_video_step_map(series.id))

    def regenerate_series_script(
        self,
        auth: AuthContext,
        series_id: str,
        script_id: str,
        *,
        idempotency_key: str,
        moderation_provider: ModerationProvider,
    ) -> dict[str, object]:
        if not idempotency_key:
            raise ApiError(400, "missing_idempotency_key", "Idempotency-Key header is required.")
        self._assert_mutation_rights(auth)
        series = self._get_series(series_id, auth.workspace_id)
        slot = self._get_series_script(series, script_id)
        if self._active_video_step_map(series.id).get(slot.id):
            raise ApiError(409, "series_script_video_active", "This script is currently generating a video.")
        request_payload = {"series_id": series_id, "mode": "regenerate", "series_script_id": script_id}
        request_hash = self._hash_request(request_payload)
        existing = self._get_idempotent_run(
            series_id=series.id,
            user_id=UUID(auth.user_id),
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if existing:
            return self.get_series_run(auth, series_id, str(existing.id))
        active_run = self._active_run(series.id)
        if active_run:
            raise ApiError(409, "series_run_active", "This series already has a queued or running generation run.")

        snapshot = self._snapshot_from_series(series)
        input_text = self._series_input_text(snapshot)
        if input_text:
            moderate_text_or_raise(
                self.db,
                provider=moderation_provider,
                text=input_text,
                target_type="series_generation_input",
                user_id=UUID(auth.user_id),
                workspace_id=series.workspace_id,
                target_id=series_id,
            )
        run = SeriesRun(
            series_id=series.id,
            workspace_id=series.workspace_id,
            created_by_user_id=UUID(auth.user_id),
            status=JobStatus.queued,
            requested_script_count=1,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            payload={
                "series_id": series_id,
                "mode": "regenerate",
                "series_snapshot": snapshot,
                "series_script_id": script_id,
            },
        )
        self.db.add(run)
        self.db.flush()
        self.db.add(
            SeriesRunStep(
                series_run_id=run.id,
                series_id=series.id,
                series_script_id=slot.id,
                step_index=1,
                sequence_number=slot.sequence_number,
                status=JobStatus.queued,
                input_payload={
                    "series_script_id": str(slot.id),
                    "sequence_number": slot.sequence_number,
                    "mode": "regenerate",
                },
            )
        )
        self.db.commit()
        from app.workers.tasks import generate_series_run_task

        generate_series_run_task.delay(str(run.id))
        self.db.expire_all()
        return self.get_series_run(auth, series_id, str(run.id))

    def get_series_run(self, auth: AuthContext, series_id: str, run_id: str) -> dict[str, object]:
        series = self._get_series(series_id, auth.workspace_id)
        run, steps = self._get_run_with_steps(run_id, series_id=series.id)
        return series_run_to_dict(run, steps)

    def queue_series_run(
        self,
        auth: AuthContext,
        series_id: str,
        payload: SeriesRunCreateRequest,
        *,
        idempotency_key: str,
        moderation_provider: ModerationProvider,
    ) -> dict[str, object]:
        if not idempotency_key:
            raise ApiError(400, "missing_idempotency_key", "Idempotency-Key header is required.")
        series = self._get_series(series_id, auth.workspace_id)
        self._assert_mutation_rights(auth)

        request_payload = {
            "series_id": series_id,
            "requested_script_count": payload.requested_script_count,
            "mode": "append",
        }
        request_hash = self._hash_request(request_payload)
        existing = self._get_idempotent_run(
            series_id=series.id,
            user_id=UUID(auth.user_id),
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if existing:
            return self.get_series_run(auth, series_id, str(existing.id))

        active_run = self._active_run(series.id)
        if active_run:
            raise ApiError(
                409,
                "series_run_active",
                "This series already has a queued or running generation run.",
            )

        snapshot = self._snapshot_from_series(series)
        input_text = self._series_input_text(snapshot)
        if input_text:
            moderate_text_or_raise(
                self.db,
                provider=moderation_provider,
                text=input_text,
                target_type="series_generation_input",
                user_id=UUID(auth.user_id),
                workspace_id=series.workspace_id,
                target_id=series_id,
            )

        run_payload = {
            **request_payload,
            "series_snapshot": snapshot,
        }
        next_sequence_number = self._latest_sequence_number(series.id)
        run = SeriesRun(
            series_id=series.id,
            workspace_id=series.workspace_id,
            created_by_user_id=UUID(auth.user_id),
            status=JobStatus.queued,
            requested_script_count=payload.requested_script_count,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            payload=run_payload,
        )
        self.db.add(run)
        self.db.flush()
        for step_index in range(1, payload.requested_script_count + 1):
            self.db.add(
                SeriesRunStep(
                    series_run_id=run.id,
                    series_id=series.id,
                    step_index=step_index,
                    sequence_number=next_sequence_number + step_index,
                    status=JobStatus.queued,
                    input_payload={
                        "sequence_number": next_sequence_number + step_index,
                        "mode": "append",
                    },
                )
            )
        record_audit_event(
            self.db,
            workspace_id=series.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="series.run_queued",
            target_type="series_run",
            target_id=str(run.id),
            payload=request_payload,
        )
        self.db.commit()

        from app.workers.tasks import generate_series_run_task

        generate_series_run_task.delay(str(run.id))
        self.db.expire_all()
        return self.get_series_run(auth, series_id, str(run.id))

    def _create_slot(
        self,
        *,
        run: SeriesRun,
        step: SeriesRunStep,
        output: dict[str, object],
    ) -> SeriesScript:
        lines = list(output.get("lines") or [])
        estimated_duration = int(
            output.get("estimated_duration_seconds")
            or sum(int(line.get("duration_sec") or 0) for line in lines)
        )
        total_words = sum(len(str(line.get("narration") or "").split()) for line in lines)
        slot = SeriesScript(
            series_id=run.series_id,
            series_run_id=run.id,
            created_by_user_id=run.created_by_user_id,
            sequence_number=step.sequence_number,
            title=str(output.get("title") or "").strip(),
            summary=str(output.get("summary") or "").strip(),
            estimated_duration_seconds=estimated_duration,
            reading_time_label=str(output.get("reading_time_label") or f"{estimated_duration}s draft narration"),
            total_words=total_words,
            lines=lines,
        )
        self.db.add(slot)
        self.db.flush()
        return slot

    def _create_revision(
        self,
        *,
        slot: SeriesScript,
        run: SeriesRun,
        output: dict[str, object],
        approval_state: str = "needs_review",
    ) -> SeriesScriptRevision:
        lines = list(output.get("lines") or [])
        estimated_duration = int(
            output.get("estimated_duration_seconds")
            or sum(int(line.get("duration_sec") or 0) for line in lines)
        )
        total_words = sum(len(str(line.get("narration") or "").split()) for line in lines)
        revision = SeriesScriptRevision(
            series_script_id=slot.id,
            series_id=slot.series_id,
            created_by_user_id=run.created_by_user_id,
            source_series_run_id=run.id,
            revision_number=self._next_revision_number(slot.id),
            approval_state=approval_state,
            moderation_summary={},
            title=str(output.get("title") or "").strip(),
            summary=str(output.get("summary") or "").strip(),
            estimated_duration_seconds=estimated_duration,
            reading_time_label=str(output.get("reading_time_label") or f"{estimated_duration}s draft narration"),
            total_words=total_words,
            lines=lines,
            video_title="",
            video_description="",
        )
        self.db.add(revision)
        self.db.flush()
        slot.current_revision_id = revision.id
        slot.title = revision.title
        slot.summary = revision.summary
        slot.estimated_duration_seconds = revision.estimated_duration_seconds
        slot.reading_time_label = revision.reading_time_label
        slot.total_words = revision.total_words
        slot.lines = revision.lines
        return revision

    def execute_series_run(self, run_id: str, text_provider: TextProvider | None = None) -> None:
        run, steps = self._get_run_with_steps(run_id)
        series = self.db.get(Series, run.series_id)
        if not series:
            raise AdapterError("internal", "series_not_found", "Series not found.")

        snapshot = dict(run.payload or {}).get("series_snapshot") or self._snapshot_from_series(series)
        pending_steps = [step for step in steps if step.status != JobStatus.completed]
        if not pending_steps:
            run.status = JobStatus.completed
            run.completed_at = run.completed_at or datetime.now(timezone.utc)
            self.db.commit()
            return

        resolved_text_provider, routing_decision = (
            (text_provider, None)
            if text_provider is not None
            else RoutingService(self.db, self.settings).build_text_provider_for_workspace(run.workspace_id)
        )
        run.status = JobStatus.running
        run.started_at = run.started_at or datetime.now(timezone.utc)
        run.completed_at = None
        run.error_code = None
        run.error_message = None
        self.db.commit()

        for step in pending_steps:
            step.status = JobStatus.running
            step.started_at = datetime.now(timezone.utc)
            step.completed_at = None
            step.error_code = None
            step.error_message = None
            is_regeneration = str((run.payload or {}).get("mode") or "append") == "regenerate"
            target_slot = self.db.get(SeriesScript, step.series_script_id) if step.series_script_id else None
            if is_regeneration and not target_slot:
                raise AdapterError("internal", "series_script_not_found", "Series script not found.")
            request_payload = {
                "series": snapshot,
                "sequence_number": step.sequence_number,
                "prior_scripts": (
                    self._regeneration_context(target_slot)
                    if is_regeneration and target_slot
                    else self._approved_other_scripts_context(
                        run.series_id,
                        before_sequence_number=step.sequence_number,
                    )
                ),
            }
            provider_run = ProviderRun(
                project_id=None,
                render_job_id=None,
                render_step_id=None,
                workspace_id=run.workspace_id,
                execution_mode=self._provider_execution_mode(routing_decision),
                worker_id=routing_decision.worker_id if routing_decision else None,
                provider_credential_id=(
                    routing_decision.provider_credential_id if routing_decision else None
                ),
                provider_name=self._provider_name(routing_decision),
                provider_model=self._provider_model(routing_decision),
                operation="series_script_generation",
                request_hash=run.request_hash,
                status=ProviderRunStatus.running,
                request_payload=request_payload,
                routing_decision_payload=self._provider_run_payload(routing_decision),
            )
            self.db.add(provider_run)
            self.db.commit()

            started = time.perf_counter()
            try:
                output = resolved_text_provider.generate_series_script(
                    series_payload=snapshot,
                    sequence_number=step.sequence_number,
                    prior_scripts=request_payload["prior_scripts"],
                )
                title = str(output.get("title") or "").strip()
                lines = output.get("lines") or []
                if not title:
                    raise AdapterError("internal", "empty_series_script_title", "Provider returned an empty title.")
                if not lines:
                    raise AdapterError("internal", "empty_series_script", "Provider returned an empty script.")
            except AdapterError as error:
                self._finalize_provider_run(provider_run, started_at=started, error=error)
                self.db.commit()
                raise

            if is_regeneration and target_slot:
                current_revision = self._get_revision(target_slot.current_revision_id)
                if current_revision and current_revision.approval_state == "needs_review":
                    current_revision.approval_state = "superseded"
                slot = target_slot
            else:
                slot = self._create_slot(run=run, step=step, output=output)
            revision = self._create_revision(slot=slot, run=run, output=output)

            step.series_script_id = slot.id
            step.status = JobStatus.completed
            step.output_payload = {
                "series_script_id": str(slot.id),
                "series_script_revision_id": str(revision.id),
                "sequence_number": slot.sequence_number,
                "title": revision.title,
            }
            step.completed_at = datetime.now(timezone.utc)
            run.completed_script_count += 1
            self._finalize_provider_run(provider_run, started_at=started, response_payload=output)
            record_audit_event(
                self.db,
                workspace_id=run.workspace_id,
                user_id=run.created_by_user_id,
                event_type=(
                    "series.script_regenerated"
                    if is_regeneration and target_slot
                    else "series.script_generated"
                ),
                target_type="series_script_revision",
                target_id=str(revision.id),
                payload={"series_run_id": str(run.id), "sequence_number": slot.sequence_number},
            )
            self.db.commit()

        run.status = JobStatus.completed
        run.completed_at = datetime.now(timezone.utc)
        run.error_code = None
        run.error_message = None
        record_audit_event(
            self.db,
            workspace_id=run.workspace_id,
            user_id=run.created_by_user_id,
            event_type="series.run_completed",
            target_type="series_run",
            target_id=str(run.id),
            payload={"completed_script_count": run.completed_script_count},
        )
        self.db.commit()

    def mark_series_run_retry(self, run_id: str, error: AdapterError) -> None:
        run = self.db.get(SeriesRun, UUID(run_id))
        if not run:
            return
        step = self.db.scalar(
            select(SeriesRunStep)
            .where(
                SeriesRunStep.series_run_id == run.id,
                SeriesRunStep.status.in_([JobStatus.running, JobStatus.failed]),
            )
            .order_by(SeriesRunStep.step_index.asc())
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

    def mark_series_run_failed(self, run_id: str, error: AdapterError) -> None:
        run = self.db.get(SeriesRun, UUID(run_id))
        if not run:
            return
        step = self.db.scalar(
            select(SeriesRunStep)
            .where(
                SeriesRunStep.series_run_id == run.id,
                SeriesRunStep.status.in_([JobStatus.running, JobStatus.queued]),
            )
            .order_by(SeriesRunStep.step_index.asc())
        )
        run.status = JobStatus.failed
        run.error_code = error.code
        run.error_message = error.message
        run.failed_script_count = max(
            int(
                self.db.scalar(
                    select(func.count())
                    .select_from(SeriesRunStep)
                    .where(
                        SeriesRunStep.series_run_id == run.id,
                        SeriesRunStep.status == JobStatus.failed,
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
        provider_run = self.db.scalar(
            select(ProviderRun)
            .where(
                ProviderRun.workspace_id == run.workspace_id,
                ProviderRun.operation == "series_script_generation",
                ProviderRun.request_hash == run.request_hash,
                ProviderRun.status == ProviderRunStatus.running,
            )
            .order_by(ProviderRun.started_at.desc())
        )
        if provider_run:
            provider_run.status = ProviderRunStatus.failed
            provider_run.error_category = ProviderErrorCategory(error.category)
            provider_run.error_code = error.code
            provider_run.error_message = error.message
            provider_run.completed_at = datetime.now(timezone.utc)
        self.db.commit()
