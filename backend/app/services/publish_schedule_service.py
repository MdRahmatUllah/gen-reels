from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext
from app.core.config import Settings
from app.core.errors import ApiError
from app.integrations.youtube.scheduler import YouTubePublishScheduler
from app.models.youtube import PublishJob, PublishJobStatus, PublishSchedule
from app.schemas.youtube import PublishScheduleUpsertRequest
from app.services.audit_service import record_structured_audit_log
from app.services.publishing_presenters import publish_schedule_to_dict
from app.services.youtube_account_service import YouTubeAccountService

UuidLike = str | uuid.UUID


def _coerce_uuid(value: UuidLike) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


class PublishScheduleService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.scheduler = YouTubePublishScheduler()

    def list_schedules(self, auth: AuthContext) -> list[dict[str, object]]:
        schedules = self.db.scalars(
            select(PublishSchedule).where(
                PublishSchedule.workspace_id == uuid.UUID(auth.workspace_id),
                PublishSchedule.owner_user_id == uuid.UUID(auth.user_id),
            )
        ).all()
        return [self._schedule_to_response(schedule) for schedule in schedules]

    def create_schedule(self, auth: AuthContext, payload: PublishScheduleUpsertRequest) -> dict[str, object]:
        account = YouTubeAccountService(self.db, self.settings).get_owned_account(
            workspace_id=auth.workspace_id,
            owner_user_id=auth.user_id,
            youtube_account_id=str(payload.youtube_account_id),
        )
        existing = self.db.scalar(
            select(PublishSchedule).where(PublishSchedule.youtube_account_id == account.id)
        )
        if existing is not None:
            raise ApiError(409, "publish_schedule_exists", "A publish schedule already exists for this account.")
        schedule = PublishSchedule(
            workspace_id=uuid.UUID(auth.workspace_id),
            owner_user_id=uuid.UUID(auth.user_id),
            youtube_account_id=account.id,
            timezone_name=payload.timezone_name,
            slots_local=self.scheduler.normalize_slots(payload.slots_local),
            is_active=payload.is_active,
        )
        self.scheduler.validate_timezone(schedule.timezone_name)
        self.db.add(schedule)
        self.db.flush()
        record_structured_audit_log(
            self.db,
            workspace_id=uuid.UUID(auth.workspace_id),
            user_id=uuid.UUID(auth.user_id),
            action="publish_schedule_created",
            target_type="publish_schedule",
            target_id=str(schedule.id),
            payload={
                "youtube_account_id": str(schedule.youtube_account_id),
                "timezone_name": schedule.timezone_name,
                "slots_local": list(schedule.slots_local),
            },
        )
        self.db.commit()
        self.db.refresh(schedule)
        return self._schedule_to_response(schedule)

    def update_schedule(
        self,
        auth: AuthContext,
        schedule_id: str,
        payload: PublishScheduleUpsertRequest,
    ) -> dict[str, object]:
        schedule = self.db.scalar(
            select(PublishSchedule).where(
                PublishSchedule.id == uuid.UUID(schedule_id),
                PublishSchedule.workspace_id == uuid.UUID(auth.workspace_id),
                PublishSchedule.owner_user_id == uuid.UUID(auth.user_id),
            )
        )
        if schedule is None:
            raise ApiError(404, "publish_schedule_not_found", "Publish schedule not found.")
        if schedule.youtube_account_id != payload.youtube_account_id:
            raise ApiError(422, "publish_schedule_account_mismatch", "Schedules cannot be moved to another account.")
        YouTubeAccountService(self.db, self.settings).get_owned_account(
            workspace_id=auth.workspace_id,
            owner_user_id=auth.user_id,
            youtube_account_id=str(payload.youtube_account_id),
        )
        schedule.timezone_name = payload.timezone_name
        schedule.slots_local = self.scheduler.normalize_slots(payload.slots_local)
        schedule.is_active = payload.is_active
        self.scheduler.validate_timezone(schedule.timezone_name)
        record_structured_audit_log(
            self.db,
            workspace_id=uuid.UUID(auth.workspace_id),
            user_id=uuid.UUID(auth.user_id),
            action="publish_schedule_updated",
            target_type="publish_schedule",
            target_id=str(schedule.id),
            payload={
                "youtube_account_id": str(schedule.youtube_account_id),
                "timezone_name": schedule.timezone_name,
                "slots_local": list(schedule.slots_local),
                "is_active": schedule.is_active,
            },
        )
        self.db.commit()
        self.db.refresh(schedule)
        return self._schedule_to_response(schedule)

    def get_active_schedule_for_account(
        self,
        *,
        workspace_id: UuidLike,
        owner_user_id: UuidLike,
        youtube_account_id: UuidLike,
    ) -> PublishSchedule:
        schedule = self.db.scalar(
            select(PublishSchedule).where(
                PublishSchedule.workspace_id == _coerce_uuid(workspace_id),
                PublishSchedule.owner_user_id == _coerce_uuid(owner_user_id),
                PublishSchedule.youtube_account_id == _coerce_uuid(youtube_account_id),
                PublishSchedule.is_active.is_(True),
            )
        )
        if schedule is None:
            raise ApiError(
                422,
                "publish_schedule_missing",
                "Create an active daily publishing schedule for this YouTube account first.",
            )
        return schedule

    def _schedule_to_response(self, schedule: PublishSchedule) -> dict[str, object]:
        future_slots = self.db.scalars(
            select(PublishJob.scheduled_publish_at).where(
                PublishJob.youtube_account_id == schedule.youtube_account_id,
                PublishJob.status.in_(
                    [PublishJobStatus.scheduled, PublishJobStatus.queued, PublishJobStatus.publishing]
                ),
                PublishJob.cancelled_at.is_(None),
                PublishJob.scheduled_publish_at.is_not(None),
                PublishJob.scheduled_publish_at >= datetime.now(UTC),
            )
        ).all()
        next_slots = []
        if schedule.slots_local:
            next_slots = [
                item.publish_at_utc
                for item in self.scheduler.next_slots(
                    timezone_name=schedule.timezone_name,
                    slots_local=list(schedule.slots_local),
                    occupied_utc=[slot for slot in future_slots if slot is not None],
                    count=min(5, max(1, len(schedule.slots_local))),
                )
            ]
        return publish_schedule_to_dict(schedule, next_available_slots_utc=next_slots)
