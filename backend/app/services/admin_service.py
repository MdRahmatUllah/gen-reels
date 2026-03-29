from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.api.deps import AuthContext
from app.core.errors import ApiError
from app.integrations.storage import StorageClient, build_storage_client
from app.models.entities import (
    Asset,
    JobStatus,
    ModerationDecision,
    ModerationEvent,
    ModerationReviewStatus,
    ProviderRun,
    RenderJob,
    RenderStep,
    StepKind,
    WorkspaceRole,
)
from app.services.audit_service import record_audit_event
from app.services.notification_service import NotificationService


class AdminService:
    def __init__(self, db, settings, storage: StorageClient | None = None) -> None:
        self.db = db
        self.settings = settings
        self.storage = storage or build_storage_client(settings)
        self.notifications = NotificationService(db, settings)

    def _assert_admin(self, auth: AuthContext) -> None:
        if auth.workspace_role != WorkspaceRole.admin:
            raise ApiError(403, "forbidden", "Only workspace admins can access admin operations.")

    def _get_moderation_event(self, auth: AuthContext, moderation_event_id: str) -> ModerationEvent:
        self._assert_admin(auth)
        event = self.db.get(ModerationEvent, UUID(moderation_event_id))
        if not event or str(event.workspace_id) != auth.workspace_id:
            raise ApiError(404, "moderation_event_not_found", "Moderation event not found.")
        return event

    def _asset_url(self, asset: Asset | None) -> str | None:
        if not asset:
            return None
        return self.storage.presigned_get_url(asset.bucket_name, asset.object_name)

    def _moderation_to_dict(self, event: ModerationEvent) -> dict[str, object]:
        asset = self.db.get(Asset, event.related_asset_id) if event.related_asset_id else None
        render_step = self.db.get(RenderStep, asset.render_step_id) if asset and asset.render_step_id else None
        render_job = self.db.get(RenderJob, asset.render_job_id) if asset and asset.render_job_id else None
        return {
            "id": event.id,
            "project_id": event.project_id,
            "workspace_id": event.workspace_id,
            "user_id": event.user_id,
            "related_asset_id": event.related_asset_id,
            "render_job_id": render_job.id if render_job else None,
            "render_step_id": render_step.id if render_step else None,
            "target_type": event.target_type,
            "target_id": event.target_id,
            "input_text": event.input_text,
            "decision": event.decision.value,
            "review_status": event.review_status.value,
            "reviewed_by_user_id": event.reviewed_by_user_id,
            "reviewed_at": event.reviewed_at,
            "review_notes": event.review_notes,
            "provider_name": event.provider_name,
            "severity_summary": event.severity_summary,
            "blocked_message": event.blocked_message,
            "asset_status": asset.status if asset else None,
            "asset_download_url": self._asset_url(asset),
            "created_at": event.created_at,
        }

    def list_moderation(self, auth: AuthContext, *, review_status: str | None = None) -> list[dict[str, object]]:
        self._assert_admin(auth)
        query = select(ModerationEvent).where(
            ModerationEvent.workspace_id == UUID(auth.workspace_id),
            ModerationEvent.decision == ModerationDecision.blocked,
        )
        if review_status:
            query = query.where(ModerationEvent.review_status == ModerationReviewStatus(review_status))
        events = self.db.scalars(query.order_by(ModerationEvent.created_at.desc())).all()
        return [self._moderation_to_dict(event) for event in events]

    def _pending_blocked_events_for_job(self, render_job_id: UUID) -> int:
        return len(
            self.db.scalars(
                select(ModerationEvent)
                .join(Asset, ModerationEvent.related_asset_id == Asset.id)
                .where(
                    Asset.render_job_id == render_job_id,
                    ModerationEvent.decision == ModerationDecision.blocked,
                    ModerationEvent.review_status == ModerationReviewStatus.pending,
                )
            ).all()
        )

    def release_moderation(self, auth: AuthContext, moderation_event_id: str, *, notes: str | None) -> dict[str, object]:
        event = self._get_moderation_event(auth, moderation_event_id)
        if event.review_status != ModerationReviewStatus.pending:
            raise ApiError(400, "moderation_event_not_pending", "This moderation event is not pending review.")
        asset = self.db.get(Asset, event.related_asset_id) if event.related_asset_id else None
        if not asset:
            raise ApiError(400, "moderation_asset_missing", "This moderation event cannot be released.")

        source_bucket = asset.bucket_name
        source_object = asset.object_name
        target_bucket = str(asset.metadata_payload.get("release_target_bucket_name") or self.settings.minio_bucket_assets)
        target_object = str(asset.metadata_payload.get("release_target_object_name") or asset.object_name)
        if source_bucket != target_bucket or source_object != target_object:
            self.storage.copy_object(source_bucket, source_object, target_bucket, target_object)
            self.storage.delete_object(source_bucket, source_object)

        asset.quarantine_bucket_name = source_bucket
        asset.quarantine_object_name = source_object
        asset.bucket_name = target_bucket
        asset.object_name = target_object
        asset.status = "completed"
        asset.released_at = datetime.now(UTC)
        event.review_status = ModerationReviewStatus.released
        event.reviewed_by_user_id = UUID(auth.user_id)
        event.reviewed_at = datetime.now(UTC)
        event.review_notes = notes

        render_step = self.db.get(RenderStep, asset.render_step_id) if asset.render_step_id else None
        render_job = self.db.get(RenderJob, asset.render_job_id) if asset.render_job_id else None
        if render_step and render_job:
            render_step.error_code = None
            render_step.error_message = None
            if render_step.step_kind == StepKind.frame_pair_generation:
                render_step.status = JobStatus.review
                render_job.status = JobStatus.review
            else:
                render_step.status = JobStatus.completed
                render_job.status = JobStatus.queued
                render_job.error_code = None
                render_job.error_message = None

        record_audit_event(
            self.db,
            workspace_id=UUID(auth.workspace_id),
            user_id=UUID(auth.user_id),
            event_type="admin.moderation_released",
            target_type="moderation_event",
            target_id=str(event.id),
            payload={"asset_id": str(asset.id)},
        )
        self.db.commit()

        if render_job and render_step and render_step.step_kind != StepKind.frame_pair_generation:
            if self._pending_blocked_events_for_job(render_job.id) == 0:
                from app.workers.tasks import execute_render_job_task

                execute_render_job_task.delay(str(render_job.id))

        return self._moderation_to_dict(event)

    def reject_moderation(self, auth: AuthContext, moderation_event_id: str, *, notes: str | None) -> dict[str, object]:
        event = self._get_moderation_event(auth, moderation_event_id)
        if event.review_status != ModerationReviewStatus.pending:
            raise ApiError(400, "moderation_event_not_pending", "This moderation event is not pending review.")
        asset = self.db.get(Asset, event.related_asset_id) if event.related_asset_id else None
        if asset:
            asset.status = "rejected"

        event.review_status = ModerationReviewStatus.rejected
        event.reviewed_by_user_id = UUID(auth.user_id)
        event.reviewed_at = datetime.now(UTC)
        event.review_notes = notes

        render_step = self.db.get(RenderStep, asset.render_step_id) if asset and asset.render_step_id else None
        render_job = self.db.get(RenderJob, asset.render_job_id) if asset and asset.render_job_id else None
        if render_step and render_job:
            render_step.status = JobStatus.failed
            render_step.error_code = "moderation_rejected"
            render_step.error_message = "An operator rejected a quarantined asset."
            render_step.completed_at = datetime.now(UTC)
            render_job.status = JobStatus.failed
            render_job.error_code = "moderation_rejected"
            render_job.error_message = "An operator rejected a quarantined asset."
            render_job.completed_at = datetime.now(UTC)
            self.notifications.notify_render_failed(
                render_job,
                reason=render_job.error_message or "An operator rejected a quarantined asset.",
            )

        record_audit_event(
            self.db,
            workspace_id=UUID(auth.workspace_id),
            user_id=UUID(auth.user_id),
            event_type="admin.moderation_rejected",
            target_type="moderation_event",
            target_id=str(event.id),
            payload={"asset_id": str(asset.id) if asset else None},
        )
        self.db.commit()
        return self._moderation_to_dict(event)

    def list_renders(self, auth: AuthContext, *, status: str | None = None) -> list[dict[str, object]]:
        self._assert_admin(auth)
        query = select(RenderJob).where(RenderJob.workspace_id == UUID(auth.workspace_id))
        if status:
            query = query.where(RenderJob.status == JobStatus(status))
        jobs = self.db.scalars(query.order_by(RenderJob.created_at.desc())).all()
        summaries: list[dict[str, object]] = []
        for job in jobs:
            steps = self.db.scalars(
                select(RenderStep)
                .where(RenderStep.render_job_id == job.id)
                .order_by(RenderStep.step_index.desc(), RenderStep.created_at.desc())
            ).all()
            provider_runs = self.db.scalars(select(ProviderRun).where(ProviderRun.render_job_id == job.id)).all()
            latest_step = steps[0] if steps else None
            summaries.append(
                {
                    "id": job.id,
                    "workspace_id": job.workspace_id,
                    "project_id": job.project_id,
                    "created_by_user_id": job.created_by_user_id,
                    "status": job.status.value,
                    "queue_name": job.queue_name,
                    "retry_count": job.retry_count,
                    "error_code": job.error_code,
                    "error_message": job.error_message,
                    "created_at": job.created_at,
                    "started_at": job.started_at,
                    "completed_at": job.completed_at,
                    "step_count": len(steps),
                    "failed_step_count": sum(1 for step in steps if step.status == JobStatus.failed),
                    "blocked_step_count": sum(1 for step in steps if step.status == JobStatus.blocked),
                    "latest_step_kind": latest_step.step_kind.value if latest_step else None,
                    "latest_provider_cost_cents": sum(run.normalized_cost_cents for run in provider_runs),
                    "provider_run_count": len(provider_runs),
                }
            )
        return summaries
