from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from uuid import UUID

from sqlalchemy import select

from app.api.deps import AuthContext
from app.core.errors import ApiError
from app.models.entities import (
    NotificationEvent,
    NotificationPreference,
    Project,
    RenderJob,
    ReviewRequest,
    User,
    Workspace,
    WorkspaceMember,
)
from app.services.audit_service import record_audit_event

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, db, settings) -> None:
        self.db = db
        self.settings = settings

    def _preference(self, workspace_id: UUID, user_id: UUID) -> NotificationPreference:
        preference = self.db.scalar(
            select(NotificationPreference).where(
                NotificationPreference.workspace_id == workspace_id,
                NotificationPreference.user_id == user_id,
            )
        )
        if preference:
            return preference
        preference = NotificationPreference(workspace_id=workspace_id, user_id=user_id)
        self.db.add(preference)
        self.db.flush()
        return preference

    @staticmethod
    def _preference_key(event_type: str) -> str:
        if event_type.startswith("render."):
            return "render_email_enabled"
        if event_type.startswith("review."):
            return "review_email_enabled"
        if event_type.startswith("workspace.membership"):
            return "membership_email_enabled"
        if event_type.startswith("moderation."):
            return "moderation_email_enabled"
        return "planning_email_enabled"

    @staticmethod
    def _to_dict(notification: NotificationEvent) -> dict[str, object]:
        return {
            "id": notification.id,
            "workspace_id": notification.workspace_id,
            "user_id": notification.user_id,
            "project_id": notification.project_id,
            "render_job_id": notification.render_job_id,
            "review_request_id": notification.review_request_id,
            "event_type": notification.event_type,
            "title": notification.title,
            "body": notification.body,
            "payload": notification.payload,
            "email_delivery_status": notification.email_delivery_status,
            "email_error_message": notification.email_error_message,
            "read_at": notification.read_at,
            "created_at": notification.created_at,
        }

    @staticmethod
    def _preference_to_dict(preference: NotificationPreference) -> dict[str, object]:
        return {
            "workspace_id": preference.workspace_id,
            "user_id": preference.user_id,
            "render_email_enabled": preference.render_email_enabled,
            "review_email_enabled": preference.review_email_enabled,
            "membership_email_enabled": preference.membership_email_enabled,
            "moderation_email_enabled": preference.moderation_email_enabled,
            "planning_email_enabled": preference.planning_email_enabled,
            "created_at": preference.created_at,
            "updated_at": preference.updated_at,
        }

    def list_notifications(self, auth: AuthContext, *, limit: int = 100) -> list[dict[str, object]]:
        notifications = self.db.scalars(
            select(NotificationEvent)
            .where(
                NotificationEvent.workspace_id == UUID(auth.workspace_id),
                NotificationEvent.user_id == UUID(auth.user_id),
            )
            .order_by(NotificationEvent.created_at.desc())
            .limit(limit)
        ).all()
        return [self._to_dict(notification) for notification in notifications]

    def mark_read(self, auth: AuthContext, notification_id: str) -> dict[str, object]:
        notification = self.db.scalar(
            select(NotificationEvent).where(
                NotificationEvent.id == UUID(notification_id),
                NotificationEvent.workspace_id == UUID(auth.workspace_id),
                NotificationEvent.user_id == UUID(auth.user_id),
            )
        )
        if not notification:
            raise ApiError(404, "notification_not_found", "Notification not found.")
        if notification.read_at is None:
            from datetime import UTC, datetime

            notification.read_at = datetime.now(UTC)
            self.db.commit()
        return self._to_dict(notification)

    def get_preferences(self, auth: AuthContext) -> dict[str, object]:
        preference = self._preference(UUID(auth.workspace_id), UUID(auth.user_id))
        self.db.commit()
        return self._preference_to_dict(preference)

    def update_preferences(self, auth: AuthContext, payload) -> dict[str, object]:
        preference = self._preference(UUID(auth.workspace_id), UUID(auth.user_id))
        for field_name in payload.model_fields_set:
            setattr(preference, field_name, getattr(payload, field_name))
        self.db.commit()
        self.db.refresh(preference)
        return self._preference_to_dict(preference)

    def _queue_email(self, notification: NotificationEvent) -> None:
        if self.settings.celery_task_always_eager or self.settings.environment == "test":
            notification.email_delivery_status = "recorded"
            notification.email_error_message = None
            return
        from app.workers.tasks import deliver_notification_email_task

        deliver_notification_email_task.apply_async(args=[str(notification.id)], countdown=5)

    def create_notification(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        event_type: str,
        title: str,
        body: str,
        project_id: UUID | None = None,
        render_job_id: UUID | None = None,
        review_request_id: UUID | None = None,
        payload: dict[str, object] | None = None,
        queue_email: bool = True,
    ) -> NotificationEvent:
        notification = NotificationEvent(
            workspace_id=workspace_id,
            user_id=user_id,
            project_id=project_id,
            render_job_id=render_job_id,
            review_request_id=review_request_id,
            event_type=event_type,
            title=title,
            body=body,
            payload=payload or {},
        )
        self.db.add(notification)
        self.db.flush()
        preference = self._preference(workspace_id, user_id)
        if queue_email and getattr(preference, self._preference_key(event_type)):
            self._queue_email(notification)
        return notification

    def _deliver_email(self, *, recipient: str, subject: str, body: str) -> tuple[str, str | None]:
        if self.settings.environment == "test":
            return "recorded", None

        message = EmailMessage()
        message["From"] = self.settings.mail_from
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        try:
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=10) as smtp:
                if self.settings.smtp_username and self.settings.smtp_password:
                    smtp.login(self.settings.smtp_username, self.settings.smtp_password)
                smtp.send_message(message)
            return "sent", None
        except Exception as exc:  # pragma: no cover - external I/O
            logger.warning("notification_delivery_failed recipient=%s subject=%s", recipient, subject)
            return "failed", str(exc)

    def deliver_notification_email(self, notification_id: str) -> None:
        notification = self.db.get(NotificationEvent, UUID(notification_id))
        if not notification:
            return
        user = self.db.get(User, notification.user_id)
        if not user:
            notification.email_delivery_status = "skipped"
            notification.email_error_message = "recipient_not_found"
            self.db.commit()
            return
        status, error_message = self._deliver_email(
            recipient=user.email,
            subject=notification.title,
            body=notification.body,
        )
        notification.email_delivery_status = status
        notification.email_error_message = error_message
        record_audit_event(
            self.db,
            workspace_id=notification.workspace_id,
            user_id=notification.user_id,
            event_type=f"notifications.{notification.event_type}",
            target_type="notification_event",
            target_id=str(notification.id),
            payload={"delivery_status": status, "error_message": error_message},
        )
        self.db.commit()

    def notify_render_failed(self, render_job: RenderJob, *, reason: str) -> None:
        user = self.db.get(User, render_job.created_by_user_id)
        project = self.db.get(Project, render_job.project_id)
        if not user:
            return
        self.create_notification(
            workspace_id=render_job.workspace_id,
            user_id=user.id,
            project_id=render_job.project_id,
            render_job_id=render_job.id,
            event_type="render.failed",
            title=f"Render failed for {project.title if project else 'your project'}",
            body=(
                "A render failed permanently.\n\n"
                f"Project: {project.title if project else render_job.project_id}\n"
                f"Render job: {render_job.id}\n"
                f"Reason: {reason}\n"
            ),
            payload={"reason": reason},
        )

    def notify_render_completed(self, render_job: RenderJob) -> None:
        user = self.db.get(User, render_job.created_by_user_id)
        project = self.db.get(Project, render_job.project_id)
        if not user:
            return
        self.create_notification(
            workspace_id=render_job.workspace_id,
            user_id=user.id,
            project_id=render_job.project_id,
            render_job_id=render_job.id,
            event_type="render.completed",
            title=f"Render completed for {project.title if project else 'your project'}",
            body=(
                "Your render completed.\n\n"
                f"Project: {project.title if project else render_job.project_id}\n"
                f"Render job: {render_job.id}\n"
            ),
            payload={},
        )

    def notify_membership_added(self, member: WorkspaceMember, user: User) -> None:
        workspace = self.db.get(Workspace, member.workspace_id)
        self.create_notification(
            workspace_id=member.workspace_id,
            user_id=member.user_id,
            event_type="workspace.membership_created",
            title=f"You were added to {workspace.name if workspace else 'a workspace'}",
            body=(
                f"You now have {member.role.value} access in "
                f"{workspace.name if workspace else member.workspace_id}.\n\n"
                "An existing admin can help you sign in if you do not already have credentials."
            ),
            payload={"member_id": str(member.id), "role": member.role.value},
        )

    def notify_review_requested(self, review: ReviewRequest) -> None:
        recipient = self.db.get(User, review.assigned_to_user_id) if review.assigned_to_user_id else None
        if not recipient:
            return
        self.create_notification(
            workspace_id=review.workspace_id,
            user_id=recipient.id,
            project_id=review.project_id,
            review_request_id=review.id,
            event_type="review.requested",
            title=f"Review requested for {review.target_type.value}",
            body=(
                "A review was assigned to you.\n\n"
                f"Target type: {review.target_type.value}\n"
                f"Target id: {review.target_id}\n"
                f"Requested version: {review.requested_version or 'latest'}\n"
                f"Notes: {review.request_notes or 'None'}\n"
            ),
            payload={"target_id": review.target_id, "target_type": review.target_type.value},
        )
