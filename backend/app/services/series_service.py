from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext
from app.core.errors import ApiError
from app.integrations.azure import ModerationProvider
from app.models.entities import (
    JobStatus,
    Series,
    SeriesRun,
    SeriesScript,
    SeriesScriptRevision,
    SeriesVideoRun,
)
from app.schemas.series import SeriesCreateRequest, SeriesUpdateRequest
from app.services.audit_service import record_audit_event
from app.services.moderation_service import moderate_text_or_raise
from app.services.permissions import require_workspace_edit
from app.services.presenters import series_to_dict
from app.services.series_catalog import get_catalog_keys, get_series_catalog


class SeriesService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_series_catalog(self) -> dict[str, list[dict[str, object]]]:
        return get_series_catalog()

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

    def _assert_mutation_rights(self, auth: AuthContext) -> None:
        require_workspace_edit(auth, message="Only workspace members or admins can modify a series.")

    def _validate_catalog_keys(self, payload: SeriesCreateRequest | SeriesUpdateRequest) -> None:
        if payload.content_mode == "preset" and payload.preset_key not in get_catalog_keys("content_presets"):
            raise ApiError(400, "invalid_series_preset", "Invalid series preset key.")
        if payload.language_key not in get_catalog_keys("languages"):
            raise ApiError(400, "invalid_series_language", "Invalid language key.")
        if payload.voice_key not in get_catalog_keys("voices"):
            raise ApiError(400, "invalid_series_voice", "Invalid voice key.")
        if payload.music_mode == "preset":
            invalid_music = set(payload.music_keys) - get_catalog_keys("music")
            if invalid_music:
                raise ApiError(400, "invalid_series_music", "Invalid music key.")
        if payload.art_style_key not in get_catalog_keys("art_styles"):
            raise ApiError(400, "invalid_series_art_style", "Invalid art style key.")
        if payload.caption_style_key not in get_catalog_keys("caption_styles"):
            raise ApiError(400, "invalid_series_caption_style", "Invalid caption style key.")
        invalid_effects = set(payload.effect_keys) - get_catalog_keys("effects")
        if invalid_effects:
            raise ApiError(400, "invalid_series_effect", "Invalid effect key.")

    def _series_input_text(self, payload: SeriesCreateRequest | SeriesUpdateRequest) -> str:
        return "\n".join(
            part
            for part in [
                payload.title.strip(),
                payload.description.strip(),
                payload.custom_topic.strip(),
                payload.custom_example_script.strip(),
            ]
            if part
        )

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

    def _latest_run(self, series_id: UUID) -> SeriesRun | None:
        return self.db.scalar(
            select(SeriesRun).where(SeriesRun.series_id == series_id).order_by(SeriesRun.created_at.desc())
        )

    def _latest_video_activity_at(self, series_id: UUID):
        return self.db.scalar(
            select(func.max(SeriesVideoRun.updated_at)).where(SeriesVideoRun.series_id == series_id)
        )

    def _script_stats(self, series_id: UUID) -> dict[str, int]:
        scripts = self.db.scalars(
            select(SeriesScript).where(SeriesScript.series_id == series_id)
        ).all()
        awaiting_review = 0
        approved = 0
        completed_video = 0
        for script in scripts:
            current_revision = (
                self.db.get(SeriesScriptRevision, script.current_revision_id) if script.current_revision_id else None
            )
            if current_revision and current_revision.approval_state == "needs_review":
                awaiting_review += 1
            if script.approved_revision_id:
                approved += 1
            if script.published_export_id:
                completed_video += 1
        return {
            "total_script_count": len(scripts),
            "scripts_awaiting_review_count": awaiting_review,
            "approved_script_count": approved,
            "completed_video_count": completed_video,
        }

    def _last_activity_at(self, series: Series, latest_run: SeriesRun | None) -> object:
        latest_script_created_at = self.db.scalar(
            select(func.max(SeriesScript.created_at)).where(SeriesScript.series_id == series.id)
        )
        timestamps = [series.updated_at]
        if latest_run and latest_run.updated_at:
            timestamps.append(latest_run.updated_at)
        latest_video_activity = self._latest_video_activity_at(series.id)
        if latest_video_activity:
            timestamps.append(latest_video_activity)
        if latest_script_created_at:
            timestamps.append(latest_script_created_at)
        return max(timestamps)

    def list_series(self, auth: AuthContext) -> list[dict[str, object]]:
        rows = self.db.scalars(
            select(Series).where(Series.workspace_id == UUID(auth.workspace_id)).order_by(Series.updated_at.desc())
        ).all()
        response: list[dict[str, object]] = []
        for row in rows:
            stats = self._script_stats(row.id)
            latest_run = self._latest_run(row.id)
            active_run = self._active_run(row.id)
            active_video_run = self._active_video_run(row.id)
            response.append(
                series_to_dict(
                    row,
                    total_script_count=stats["total_script_count"],
                    scripts_awaiting_review_count=stats["scripts_awaiting_review_count"],
                    approved_script_count=stats["approved_script_count"],
                    completed_video_count=stats["completed_video_count"],
                    latest_run=latest_run,
                    active_run=active_run,
                    active_video_run=active_video_run,
                    primary_cta="create_video" if stats["total_script_count"] > 0 else "start_series",
                    last_activity_at=self._last_activity_at(row, latest_run),
                    can_edit=active_run is None and active_video_run is None,
                )
            )
        return response

    def create_series(
        self,
        auth: AuthContext,
        payload: SeriesCreateRequest,
        moderation_provider: ModerationProvider,
    ) -> dict[str, object]:
        self._assert_mutation_rights(auth)
        self._validate_catalog_keys(payload)
        input_text = self._series_input_text(payload)
        if input_text:
            moderate_text_or_raise(
                self.db,
                provider=moderation_provider,
                text=input_text,
                target_type="series_input",
                user_id=UUID(auth.user_id),
                workspace_id=UUID(auth.workspace_id),
                target_id=None,
            )
        record = Series(
            workspace_id=UUID(auth.workspace_id),
            owner_user_id=UUID(auth.user_id),
            title=payload.title.strip(),
            description=payload.description.strip(),
            content_mode=payload.content_mode,
            preset_key=payload.preset_key if payload.content_mode == "preset" else None,
            custom_topic=payload.custom_topic.strip() if payload.content_mode == "custom" else "",
            custom_example_script=payload.custom_example_script.strip(),
            language_key=payload.language_key,
            voice_key=payload.voice_key,
            music_mode=payload.music_mode,
            music_keys=list(payload.music_keys) if payload.music_mode == "preset" else [],
            art_style_key=payload.art_style_key,
            caption_style_key=payload.caption_style_key,
            effect_keys=list(payload.effect_keys),
        )
        self.db.add(record)
        self.db.flush()
        record_audit_event(
            self.db,
            workspace_id=record.workspace_id,
            user_id=record.owner_user_id,
            event_type="series.created",
            target_type="series",
            target_id=str(record.id),
            payload={"title": record.title},
        )
        self.db.commit()
        self.db.refresh(record)
        return series_to_dict(
            record,
            total_script_count=0,
            scripts_awaiting_review_count=0,
            approved_script_count=0,
            completed_video_count=0,
            latest_run=None,
            active_run=None,
            active_video_run=None,
            primary_cta="start_series",
            last_activity_at=record.updated_at,
            can_edit=True,
        )

    def get_series_detail(self, auth: AuthContext, series_id: str) -> dict[str, object]:
        record = self._get_series(series_id, auth.workspace_id)
        stats = self._script_stats(record.id)
        latest_run = self._latest_run(record.id)
        active_run = self._active_run(record.id)
        active_video_run = self._active_video_run(record.id)
        return series_to_dict(
            record,
            total_script_count=stats["total_script_count"],
            scripts_awaiting_review_count=stats["scripts_awaiting_review_count"],
            approved_script_count=stats["approved_script_count"],
            completed_video_count=stats["completed_video_count"],
            latest_run=latest_run,
            active_run=active_run,
            active_video_run=active_video_run,
            primary_cta="create_video" if stats["total_script_count"] > 0 else "start_series",
            last_activity_at=self._last_activity_at(record, latest_run),
            can_edit=active_run is None and active_video_run is None,
        )

    def update_series(
        self,
        auth: AuthContext,
        series_id: str,
        payload: SeriesUpdateRequest,
        moderation_provider: ModerationProvider,
    ) -> dict[str, object]:
        self._assert_mutation_rights(auth)
        record = self._get_series(series_id, auth.workspace_id)
        active_run = self._active_run(record.id)
        active_video_run = self._active_video_run(record.id)
        if active_run or active_video_run:
            raise ApiError(
                409,
                "series_locked",
                "Series cannot be edited while a run is queued or running.",
            )
        self._validate_catalog_keys(payload)
        input_text = self._series_input_text(payload)
        if input_text:
            moderate_text_or_raise(
                self.db,
                provider=moderation_provider,
                text=input_text,
                target_type="series_input",
                user_id=UUID(auth.user_id),
                workspace_id=UUID(auth.workspace_id),
                target_id=series_id,
            )
        record.title = payload.title.strip()
        record.description = payload.description.strip()
        record.content_mode = payload.content_mode
        record.preset_key = payload.preset_key if payload.content_mode == "preset" else None
        record.custom_topic = payload.custom_topic.strip() if payload.content_mode == "custom" else ""
        record.custom_example_script = payload.custom_example_script.strip()
        record.language_key = payload.language_key
        record.voice_key = payload.voice_key
        record.music_mode = payload.music_mode
        record.music_keys = list(payload.music_keys) if payload.music_mode == "preset" else []
        record.art_style_key = payload.art_style_key
        record.caption_style_key = payload.caption_style_key
        record.effect_keys = list(payload.effect_keys)
        record_audit_event(
            self.db,
            workspace_id=record.workspace_id,
            user_id=UUID(auth.user_id),
            event_type="series.updated",
            target_type="series",
            target_id=str(record.id),
            payload={},
        )
        self.db.commit()
        self.db.refresh(record)
        latest_run = self._latest_run(record.id)
        stats = self._script_stats(record.id)
        return series_to_dict(
            record,
            total_script_count=stats["total_script_count"],
            scripts_awaiting_review_count=stats["scripts_awaiting_review_count"],
            approved_script_count=stats["approved_script_count"],
            completed_video_count=stats["completed_video_count"],
            latest_run=latest_run,
            active_run=None,
            active_video_run=None,
            primary_cta="create_video" if stats["total_script_count"] > 0 else "start_series",
            last_activity_at=self._last_activity_at(record, latest_run),
            can_edit=True,
        )
