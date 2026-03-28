from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.models.entities import Project, RenderJob, User
from app.services.audit_service import record_audit_event


class NotificationService:
    def __init__(self, db, settings) -> None:
        self.db = db
        self.settings = settings

    def notify_render_failed(self, render_job: RenderJob, *, reason: str) -> None:
        user = self.db.get(User, render_job.created_by_user_id)
        project = self.db.get(Project, render_job.project_id)
        if not user:
            return

        delivery_status = "recorded"
        error_message = None
        if self.settings.environment != "test":
            message = EmailMessage()
            message["From"] = self.settings.mail_from
            message["To"] = user.email
            message["Subject"] = f"Render failed for {project.title if project else 'your project'}"
            message.set_content(
                "A render failed permanently.\n\n"
                f"Project: {project.title if project else render_job.project_id}\n"
                f"Render job: {render_job.id}\n"
                f"Reason: {reason}\n"
            )
            try:
                with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=10) as smtp:
                    if self.settings.smtp_username and self.settings.smtp_password:
                        smtp.login(self.settings.smtp_username, self.settings.smtp_password)
                    smtp.send_message(message)
                delivery_status = "sent"
            except Exception as exc:  # pragma: no cover - external I/O
                delivery_status = "failed"
                error_message = str(exc)

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

