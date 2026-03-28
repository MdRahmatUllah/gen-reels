from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import Settings

logger = logging.getLogger(__name__)


class EmailSender:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send_password_reset(self, *, recipient: str, token: str) -> None:
        reset_url = f"{self.settings.frontend_base_url.rstrip('/')}/reset-password?token={token}"
        message = EmailMessage()
        message["Subject"] = "Reset your Reels Generation password"
        message["From"] = self.settings.mail_from
        message["To"] = recipient
        message.set_content(
            "Use the following link to reset your password:\n\n"
            f"{reset_url}\n\n"
            f"This link expires in {self.settings.password_reset_ttl_minutes} minutes."
        )

        try:
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=10) as smtp:
                if self.settings.smtp_username and self.settings.smtp_password:
                    smtp.login(self.settings.smtp_username, self.settings.smtp_password)
                smtp.send_message(message)
        except OSError:
            logger.warning("password_reset_email_delivery_failed recipient=%s", recipient)
