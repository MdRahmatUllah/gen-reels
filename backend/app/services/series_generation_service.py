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
    JobStatus,
    ProviderErrorCategory,
    ProviderRun,
    ProviderRunStatus,
    Series,
    SeriesRun,
    SeriesRunStep,
    SeriesScript,
)
from app.schemas.series import SeriesRunCreateRequest
from app.services.audit_service import record_audit_event
from app.services.generation_service import GenerationService
from app.services.moderation_service import moderate_text_or_raise
from app.services.permissions import require_workspace_edit
from app.services.presenters import series_run_to_dict, series_script_to_dict
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

    def _latest_sequence_number(self, series_id: UUID) -> int:
        return int(
            self.db.scalar(
                select(func.max(SeriesScript.sequence_number)).where(SeriesScript.series_id == series_id)
            )
            or 0
        )

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

    def _get_run_with_steps(self, run_id: str | UUID, *, series_id: UUID | None = None) -> tuple[SeriesRun, list[SeriesRunStep]]:
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

    def _prior_scripts_context(self, series_id: UUID, *, before_sequence_number: int) -> list[dict[str, object]]:
        scripts = self.db.scalars(
            select(SeriesScript)
            .where(
                SeriesScript.series_id == series_id,
                SeriesScript.sequence_number < before_sequence_number,
            )
            .order_by(SeriesScript.sequence_number.asc())
        ).all()
        detailed_ids = {script.id for script in scripts[-10:]}
        return [
            {
                "sequence_number": script.sequence_number,
                "title": script.title,
                "summary": script.summary if script.id in detailed_ids else "",
            }
            for script in scripts
        ]

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

    def list_series_scripts(self, auth: AuthContext, series_id: str) -> list[dict[str, object]]:
        series = self._get_series(series_id, auth.workspace_id)
        scripts = self.db.scalars(
            select(SeriesScript)
            .where(SeriesScript.series_id == series.id)
            .order_by(SeriesScript.sequence_number.asc())
        ).all()
        return [series_script_to_dict(script) for script in scripts]

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
            request_payload = {
                "series": snapshot,
                "sequence_number": step.sequence_number,
                "prior_scripts": self._prior_scripts_context(
                    run.series_id,
                    before_sequence_number=step.sequence_number,
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
                estimated_duration = int(
                    output.get("estimated_duration_seconds")
                    or sum(int(line.get("duration_sec") or 0) for line in lines)
                )
                total_words = sum(len(str(line.get("narration") or "").split()) for line in lines)
            except AdapterError as error:
                self._finalize_provider_run(provider_run, started_at=started, error=error)
                self.db.commit()
                raise

            script = SeriesScript(
                series_id=run.series_id,
                series_run_id=run.id,
                created_by_user_id=run.created_by_user_id,
                sequence_number=step.sequence_number,
                title=title,
                summary=str(output.get("summary") or "").strip(),
                estimated_duration_seconds=estimated_duration,
                reading_time_label=str(output.get("reading_time_label") or f"{estimated_duration}s draft narration"),
                total_words=total_words,
                lines=list(lines),
            )
            self.db.add(script)
            self.db.flush()

            step.series_script_id = script.id
            step.status = JobStatus.completed
            step.output_payload = {
                "series_script_id": str(script.id),
                "sequence_number": script.sequence_number,
                "title": script.title,
            }
            step.completed_at = datetime.now(timezone.utc)
            run.completed_script_count += 1
            self._finalize_provider_run(provider_run, started_at=started, response_payload=output)
            record_audit_event(
                self.db,
                workspace_id=run.workspace_id,
                user_id=run.created_by_user_id,
                event_type="series.script_generated",
                target_type="series_script",
                target_id=str(script.id),
                payload={"series_run_id": str(run.id), "sequence_number": script.sequence_number},
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
