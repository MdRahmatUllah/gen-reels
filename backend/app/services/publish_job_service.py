from __future__ import annotations

import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext
from app.core.config import Settings
from app.core.errors import AdapterError, ApiError
from app.integrations.storage import StorageClient, build_storage_client
from app.integrations.youtube.scheduler import YouTubePublishScheduler
from app.integrations.youtube.service import YouTubeIntegrationService
from app.models.youtube import (
    PublishJob,
    PublishJobStatus,
    PublishMode,
    PublishVisibility,
    Video,
    VideoLifecycleStatus,
    VideoMetadataVersion,
    YouTubeAccount,
)
from app.schemas.videos import BatchScheduleRequest, ScheduleVideoRequest
from app.services.audit_service import record_structured_audit_log
from app.services.publishing_presenters import publish_job_to_dict
from app.services.publish_schedule_service import PublishScheduleService
from app.services.youtube_account_service import YouTubeAccountService


class PublishJobService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self._storage: StorageClient | None = None
        self.scheduler = YouTubePublishScheduler()
        self.youtube_integration = YouTubeIntegrationService(settings)

    @property
    def storage(self) -> StorageClient:
        if self._storage is None:
            self._storage = build_storage_client(self.settings)
        return self._storage

    def list_jobs(self, auth: AuthContext) -> list[dict[str, object]]:
        jobs = self.db.scalars(
            select(PublishJob)
            .where(
                PublishJob.workspace_id == uuid.UUID(auth.workspace_id),
                PublishJob.owner_user_id == uuid.UUID(auth.user_id),
            )
            .order_by(PublishJob.created_at.desc())
        ).all()
        return self._serialize_jobs(jobs)

    def schedule_video(self, auth: AuthContext, video_id: str, payload: ScheduleVideoRequest) -> dict[str, object]:
        video = self._get_owned_video(auth, video_id)
        self._assert_schedulable(video)
        metadata = self._get_approved_metadata(video)
        account = self._resolve_target_account(auth, payload.youtube_account_id)
        self._cancel_pending_jobs_for_video(video.id)

        now = datetime.now(UTC)
        publish_mode = PublishMode(payload.publish_mode)
        if publish_mode == PublishMode.immediate:
            job = PublishJob(
                workspace_id=uuid.UUID(auth.workspace_id),
                owner_user_id=uuid.UUID(auth.user_id),
                video_id=video.id,
                youtube_account_id=account.id,
                metadata_version_id=metadata.id,
                publish_mode=PublishMode.immediate,
                visibility=PublishVisibility(payload.visibility),
                status=PublishJobStatus.queued,
                queued_at=now,
            )
            video.youtube_account_id = account.id
            video.status = VideoLifecycleStatus.publishing
            video.scheduled_publish_at = None
            self.db.add(job)
            self.db.commit()
            self.db.refresh(job)
            self._dispatch_publish_job(job.id)
            return self._serialize_jobs([job])[0]

        if payload.visibility != "public":
            raise ApiError(
                422,
                "scheduled_visibility_invalid",
                "Scheduled YouTube publishes must use the account schedule and publish publicly at the release time.",
            )
        scheduled_at = self._resolve_scheduled_publish_at(
            auth=auth,
            account=account,
            explicit_publish_at=payload.scheduled_publish_at_utc,
            use_next_available_slot=payload.use_next_available_slot or payload.scheduled_publish_at_utc is None,
            slot_count=1,
        )[0]
        job = PublishJob(
            workspace_id=uuid.UUID(auth.workspace_id),
            owner_user_id=uuid.UUID(auth.user_id),
            video_id=video.id,
            youtube_account_id=account.id,
            metadata_version_id=metadata.id,
            publish_mode=PublishMode.scheduled,
            visibility=PublishVisibility.public,
            scheduled_publish_at=scheduled_at,
            status=PublishJobStatus.scheduled,
            queued_at=now,
        )
        video.youtube_account_id = account.id
        video.status = VideoLifecycleStatus.scheduled
        video.scheduled_publish_at = scheduled_at
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        self._dispatch_publish_job(job.id)
        return self._serialize_jobs([job])[0]

    def batch_schedule(self, auth: AuthContext, payload: BatchScheduleRequest) -> dict[str, object]:
        account = self._resolve_target_account(auth, str(payload.youtube_account_id))
        schedule = PublishScheduleService(self.db, self.settings).get_active_schedule_for_account(
            workspace_id=auth.workspace_id,
            owner_user_id=auth.user_id,
            youtube_account_id=str(account.id),
        )
        requested_ids = [uuid.UUID(str(video_id)) for video_id in payload.video_ids]
        if not requested_ids:
            raise ApiError(422, "batch_schedule_empty", "Select at least one video to batch schedule.")
        if len(requested_ids) != len(set(requested_ids)):
            raise ApiError(422, "batch_schedule_duplicate_video", "Batch scheduling cannot include the same video twice.")

        videos = self.db.scalars(
            select(Video).where(
                Video.id.in_(requested_ids),
                Video.workspace_id == uuid.UUID(auth.workspace_id),
                Video.owner_user_id == uuid.UUID(auth.user_id),
                Video.deleted_at.is_(None),
            )
        ).all()
        by_id = {video.id: video for video in videos}
        if len(by_id) != len(set(requested_ids)):
            raise ApiError(404, "video_not_found", "One or more selected videos were not found.")

        ordered_videos = [by_id[item_id] for item_id in requested_ids]
        for video in ordered_videos:
            self._assert_schedulable(video)

        assignments = self.scheduler.next_slots(
            timezone_name=schedule.timezone_name,
            slots_local=list(schedule.slots_local or []),
            occupied_utc=self._future_occupied_slots(account.id),
            count=len(ordered_videos),
        )
        assignment_payloads = [
            {
                "video_id": video.id,
                "original_file_name": video.original_file_name,
                "publish_at_utc": assignment.publish_at_utc,
                "publish_at_local_label": assignment.publish_at_local_label,
            }
            for video, assignment in zip(ordered_videos, assignments, strict=True)
        ]
        if payload.preview_only:
            return {
                "preview_only": True,
                "assignments": assignment_payloads,
                "created_job_ids": [],
            }

        created_job_ids: list[uuid.UUID] = []
        for video, assignment in zip(ordered_videos, assignments, strict=True):
            self._cancel_pending_jobs_for_video(video.id)
            metadata = self._get_approved_metadata(video)
            job = PublishJob(
                workspace_id=uuid.UUID(auth.workspace_id),
                owner_user_id=uuid.UUID(auth.user_id),
                video_id=video.id,
                youtube_account_id=account.id,
                metadata_version_id=metadata.id,
                schedule_id=schedule.id,
                publish_mode=PublishMode.scheduled,
                visibility=PublishVisibility.public,
                scheduled_publish_at=assignment.publish_at_utc,
                status=PublishJobStatus.scheduled,
                queued_at=datetime.now(UTC),
            )
            video.youtube_account_id = account.id
            video.status = VideoLifecycleStatus.scheduled
            video.scheduled_publish_at = assignment.publish_at_utc
            self.db.add(job)
            self.db.flush()
            created_job_ids.append(job.id)
        self.db.commit()
        for job_id in created_job_ids:
            self._dispatch_publish_job(job_id)
        return {
            "preview_only": False,
            "assignments": assignment_payloads,
            "created_job_ids": created_job_ids,
        }

    def enqueue_due_jobs(self) -> int:
        now = datetime.now(UTC)
        jobs = self.db.scalars(
            select(PublishJob)
            .where(
                PublishJob.status == PublishJobStatus.scheduled,
                PublishJob.cancelled_at.is_(None),
                PublishJob.queued_at.is_(None),
                PublishJob.youtube_video_id.is_(None),
                PublishJob.scheduled_publish_at.is_not(None),
            )
            .order_by(PublishJob.scheduled_publish_at.asc())
        ).all()
        for job in jobs:
            job.status = PublishJobStatus.queued
            job.queued_at = now
        self.db.commit()
        for job in jobs:
            self._dispatch_publish_job(job.id)
        return len(jobs)

    def execute_publish_job(self, job_id: str) -> None:
        job = self.db.scalar(select(PublishJob).where(PublishJob.id == uuid.UUID(job_id)))
        if job is None or job.status in {PublishJobStatus.cancelled, PublishJobStatus.published}:
            return
        video = self.db.scalar(select(Video).where(Video.id == job.video_id))
        account = self.db.scalar(select(YouTubeAccount).where(YouTubeAccount.id == job.youtube_account_id))
        metadata = self.db.scalar(
            select(VideoMetadataVersion).where(VideoMetadataVersion.id == job.metadata_version_id)
        )
        if video is None or account is None or metadata is None:
            raise AdapterError(
                "deterministic_input",
                "publish_job_invalid",
                "The publish job no longer has a valid video, YouTube account, or approved metadata version.",
            )
        if account.disconnected_at is not None:
            raise AdapterError(
                "deterministic_input",
                "youtube_account_disconnected",
                "Reconnect the YouTube account before publishing this video.",
            )

        now = datetime.now(UTC)
        job.status = PublishJobStatus.publishing
        job.started_at = now
        job.error_code = None
        job.error_message = None
        job.last_progress_percent = 0
        video.status = VideoLifecycleStatus.publishing
        video.processing_error_code = None
        video.processing_error_message = None
        record_structured_audit_log(
            self.db,
            workspace_id=job.workspace_id,
            user_id=job.owner_user_id,
            action="youtube_upload_started",
            target_type="publish_job",
            target_id=str(job.id),
            payload={"video_id": str(video.id), "youtube_account_id": str(account.id)},
        )
        self.db.commit()

        token_bundle = YouTubeAccountService(self.db, self.settings).ensure_runtime_token_bundle(account)
        source_bytes = self.storage.read_bytes(video.storage_bucket, video.storage_object_name)

        with tempfile.TemporaryDirectory() as temp_dir:
            workdir = Path(temp_dir)
            upload_path = workdir / video.original_file_name
            upload_path.write_bytes(source_bytes)
            publish_at = self._youtube_publish_at(job)

            def progress_callback(percent: int) -> None:
                if percent > (job.last_progress_percent or 0):
                    job.last_progress_percent = percent
                    self.db.flush()

            try:
                upload_request = self.youtube_integration.prepare_upload_request(
                    file_path=str(upload_path),
                    content_type=video.content_type,
                    title=metadata.title,
                    description=metadata.description,
                    tags=list(metadata.tags or []),
                    visibility=job.visibility.value,
                    publish_at=publish_at,
                )
            except ApiError as exc:
                raise AdapterError("deterministic_input", exc.code, exc.message) from exc
            result = self.youtube_integration.client.upload_video(
                token_bundle,
                upload_request,
                progress_callback=progress_callback,
            )

        completed_at = datetime.now(UTC)
        is_future_scheduled_upload = publish_at is not None
        job.status = PublishJobStatus.scheduled if is_future_scheduled_upload else PublishJobStatus.published
        job.published_at = None if is_future_scheduled_upload else completed_at
        job.youtube_video_id = result.youtube_video_id
        job.youtube_video_url = result.video_url
        job.youtube_response_payload = result.raw_response
        job.last_progress_percent = 100
        video.status = VideoLifecycleStatus.scheduled if is_future_scheduled_upload else VideoLifecycleStatus.published
        video.scheduled_publish_at = job.scheduled_publish_at if is_future_scheduled_upload else None
        video.published_at = None if is_future_scheduled_upload else completed_at
        video.youtube_video_id = result.youtube_video_id
        video.processing_error_code = None
        video.processing_error_message = None
        record_structured_audit_log(
            self.db,
            workspace_id=job.workspace_id,
            user_id=job.owner_user_id,
            action="youtube_upload_scheduled" if is_future_scheduled_upload else "youtube_upload_succeeded",
            target_type="publish_job",
            target_id=str(job.id),
            payload={
                "youtube_video_id": result.youtube_video_id,
                "youtube_video_url": result.video_url,
                "scheduled_publish_at": job.scheduled_publish_at.isoformat() if job.scheduled_publish_at else None,
            },
        )
        self.db.commit()

    def mark_job_retry(self, job_id: str, error: AdapterError, attempt_count: int) -> None:
        job = self.db.scalar(select(PublishJob).where(PublishJob.id == uuid.UUID(job_id)))
        if job is None:
            return
        video = self.db.scalar(select(Video).where(Video.id == job.video_id))
        job.status = PublishJobStatus.queued
        job.attempt_count = attempt_count
        job.error_code = error.code
        job.error_message = error.message
        if video is not None:
            video.status = VideoLifecycleStatus.publishing
        self.db.commit()

    def mark_job_failed(self, job_id: str, error: AdapterError, attempt_count: int) -> None:
        job = self.db.scalar(select(PublishJob).where(PublishJob.id == uuid.UUID(job_id)))
        if job is None:
            return
        video = self.db.scalar(select(Video).where(Video.id == job.video_id))
        job.status = PublishJobStatus.failed
        job.failed_at = datetime.now(UTC)
        job.attempt_count = attempt_count
        job.error_code = error.code
        job.error_message = error.message
        if video is not None:
            video.status = VideoLifecycleStatus.failed
            video.processing_error_code = error.code
            video.processing_error_message = error.message
        record_structured_audit_log(
            self.db,
            workspace_id=job.workspace_id,
            user_id=job.owner_user_id,
            action="youtube_upload_failed",
            target_type="publish_job",
            target_id=str(job.id),
            status="failed",
            message=error.message,
            payload={"error_code": error.code},
        )
        self.db.commit()

    def _serialize_jobs(self, jobs: list[PublishJob]) -> list[dict[str, object]]:
        if not jobs:
            return []
        video_ids = [job.video_id for job in jobs]
        account_ids = [job.youtube_account_id for job in jobs]
        videos = self.db.scalars(select(Video).where(Video.id.in_(video_ids))).all()
        accounts = self.db.scalars(select(YouTubeAccount).where(YouTubeAccount.id.in_(account_ids))).all()
        videos_by_id = {video.id: video for video in videos}
        accounts_by_id = {account.id: account for account in accounts}
        return [
            publish_job_to_dict(
                job,
                original_file_name=videos_by_id.get(job.video_id).original_file_name if videos_by_id.get(job.video_id) else None,
                channel_title=accounts_by_id.get(job.youtube_account_id).channel_title if accounts_by_id.get(job.youtube_account_id) else None,
            )
            for job in jobs
        ]

    def _get_owned_video(self, auth: AuthContext, video_id: str) -> Video:
        video = self.db.scalar(
            select(Video).where(
                Video.id == uuid.UUID(video_id),
                Video.workspace_id == uuid.UUID(auth.workspace_id),
                Video.owner_user_id == uuid.UUID(auth.user_id),
                Video.deleted_at.is_(None),
            )
        )
        if video is None:
            raise ApiError(404, "video_not_found", "Video not found.")
        return video

    def _assert_schedulable(self, video: Video) -> None:
        if video.status in {VideoLifecycleStatus.transcribing, VideoLifecycleStatus.uploaded}:
            raise ApiError(
                409,
                "video_processing_incomplete",
                "Wait until transcription and metadata generation finish before scheduling this video.",
            )
        if video.status == VideoLifecycleStatus.scheduled and video.youtube_video_id:
            raise ApiError(
                409,
                "video_already_scheduled_on_youtube",
                "This video is already scheduled on YouTube. Adjust or remove the scheduled upload in YouTube Studio before scheduling it again here.",
            )
        if video.status in {VideoLifecycleStatus.publishing, VideoLifecycleStatus.published}:
            raise ApiError(409, "video_already_publishing", "This video is already publishing or has been published.")
        if not video.approved_metadata_version_id:
            raise ApiError(422, "video_metadata_not_approved", "Approve metadata before scheduling this video.")

    def _get_approved_metadata(self, video: Video) -> VideoMetadataVersion:
        metadata = self.db.scalar(
            select(VideoMetadataVersion).where(VideoMetadataVersion.id == video.approved_metadata_version_id)
        )
        if metadata is None:
            raise ApiError(422, "video_metadata_not_approved", "Approve metadata before scheduling this video.")
        return metadata

    def _resolve_target_account(self, auth: AuthContext, youtube_account_id: str | uuid.UUID | None) -> YouTubeAccount:
        account_service = YouTubeAccountService(self.db, self.settings)
        if youtube_account_id:
            return account_service.get_owned_account(
                workspace_id=auth.workspace_id,
                owner_user_id=auth.user_id,
                youtube_account_id=youtube_account_id,
            )
        account = account_service.get_default_account(
            workspace_id=auth.workspace_id,
            owner_user_id=auth.user_id,
        )
        if account is None:
            raise ApiError(
                422,
                "youtube_account_required",
                "Connect a YouTube account before scheduling or publishing videos.",
            )
        return account

    def _resolve_scheduled_publish_at(
        self,
        *,
        auth: AuthContext,
        account: YouTubeAccount,
        explicit_publish_at,
        use_next_available_slot: bool,
        slot_count: int,
    ) -> list[datetime]:
        if explicit_publish_at is not None and not use_next_available_slot:
            scheduled_at = explicit_publish_at if explicit_publish_at.tzinfo else explicit_publish_at.replace(tzinfo=UTC)
            scheduled_at = scheduled_at.astimezone(UTC)
            if scheduled_at <= datetime.now(UTC):
                raise ApiError(422, "scheduled_publish_in_past", "Scheduled publish times must be in the future.")
            return [scheduled_at]

        schedule = PublishScheduleService(self.db, self.settings).get_active_schedule_for_account(
            workspace_id=auth.workspace_id,
            owner_user_id=auth.user_id,
            youtube_account_id=str(account.id),
        )
        assignments = self.scheduler.next_slots(
            timezone_name=schedule.timezone_name,
            slots_local=list(schedule.slots_local or []),
            occupied_utc=self._future_occupied_slots(account.id),
            count=slot_count,
        )
        return [item.publish_at_utc for item in assignments]

    def _future_occupied_slots(self, youtube_account_id: uuid.UUID) -> list[datetime]:
        values = self.db.scalars(
            select(PublishJob.scheduled_publish_at).where(
                PublishJob.youtube_account_id == youtube_account_id,
                PublishJob.status.in_(
                    [PublishJobStatus.scheduled, PublishJobStatus.queued, PublishJobStatus.publishing]
                ),
                PublishJob.cancelled_at.is_(None),
                PublishJob.scheduled_publish_at.is_not(None),
                PublishJob.scheduled_publish_at >= datetime.now(UTC),
            )
        ).all()
        return [value for value in values if value is not None]

    def _cancel_pending_jobs_for_video(self, video_id: uuid.UUID) -> None:
        pending_jobs = self.db.scalars(
            select(PublishJob).where(
                PublishJob.video_id == video_id,
                PublishJob.status.in_([PublishJobStatus.scheduled, PublishJobStatus.queued]),
                PublishJob.cancelled_at.is_(None),
            )
        ).all()
        now = datetime.now(UTC)
        for job in pending_jobs:
            job.status = PublishJobStatus.cancelled
            job.cancelled_at = now

    def _dispatch_publish_job(self, job_id: uuid.UUID) -> None:
        from app.workers.youtube_publish import publish_job_task

        publish_job_task.delay(str(job_id))

    def _youtube_publish_at(self, job: PublishJob) -> datetime | None:
        if job.publish_mode != PublishMode.scheduled or job.scheduled_publish_at is None:
            return None
        scheduled_at = job.scheduled_publish_at
        normalized = scheduled_at if scheduled_at.tzinfo else scheduled_at.replace(tzinfo=UTC)
        if normalized <= datetime.now(UTC):
            return None
        return normalized
