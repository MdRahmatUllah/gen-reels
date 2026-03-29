from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.models.entities import ReviewRequest, Workspace, WorkspaceMember
from app.models.entities import Project, RenderJob, User
from app.services.audit_service import record_audit_event

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, db, settings) -> None:
        self.db = db
        self.settings = settings

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

    def notify_render_failed(self, render_job: RenderJob, *, reason: str) -> None:
        user = self.db.get(User, render_job.created_by_user_id)
        project = self.db.get(Project, render_job.project_id)
        if not user:
            return

        delivery_status, error_message = self._deliver_email(
            recipient=user.email,
            subject=f"Render failed for {project.title if project else 'your project'}",
            body=(
                "A render failed permanently.\n\n"
                f"Project: {project.title if project else render_job.project_id}\n"
                f"Render job: {render_job.id}\n"
                f"Reason: {reason}\n"
            ),
        )

        record_audit_event(
            self.db,
            workspace_id=render_job.workspace_id,
            user_id=render_job.created_by_user_id,
            event_type="notifications.render_failed",
            target_type="render_job",
            target_id=str(render_job.id),
            payload={
                "delivery_status": delivery_status,
                "email": user.email,
                "reason": reason,
                "error_message": error_message,
            },
        )

    def notify_membership_added(self, member: WorkspaceMember, user: User) -> None:
        workspace = self.db.get(Workspace, member.workspace_id)
        delivery_status, error_message = self._deliver_email(
            recipient=user.email,
            subject=f"You were added to {workspace.name if workspace else 'a workspace'}",
            body=(
                f"You now have {member.role.value} access in "
                f"{workspace.name if workspace else member.workspace_id}.\n\n"
                "An existing admin can help you sign in if you do not already have credentials."
            ),
        )
        record_audit_event(
            self.db,
            workspace_id=member.workspace_id,
            user_id=member.user_id,
            event_type="notifications.membership_added",
            target_type="workspace_member",
            target_id=str(member.id),
            payload={
                "delivery_status": delivery_status,
                "email": user.email,
                "error_message": error_message,
            },
        )

    def notify_review_requested(self, review: ReviewRequest) -> None:
        recipient = self.db.get(User, review.assigned_to_user_id) if review.assigned_to_user_id else None
        if not recipient:
            record_audit_event(
                self.db,
                workspace_id=review.workspace_id,
                user_id=review.requested_by_user_id,
                event_type="notifications.review_requested",
                target_type="review_request",
                target_id=str(review.id),
                payload={"delivery_status": "skipped", "reason": "no_assignee"},
            )
            return

        delivery_status, error_message = self._deliver_email(
            recipient=recipient.email,
            subject=f"Review requested for {review.target_type.value}",
            body=(
                "A review was assigned to you.\n\n"
                f"Target type: {review.target_type.value}\n"
                f"Target id: {review.target_id}\n"
                f"Requested version: {review.requested_version or 'latest'}\n"
                f"Notes: {review.request_notes or 'None'}\n"
            ),
        )
        record_audit_event(
            self.db,
            workspace_id=review.workspace_id,
            user_id=review.requested_by_user_id,
            event_type="notifications.review_requested",
            target_type="review_request",
            target_id=str(review.id),
            payload={
                "delivery_status": delivery_status,
                "email": recipient.email,
                "error_message": error_message,
            },
        )
