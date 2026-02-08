"""
Email Service

Sends transactional emails (password resets, notifications) via SMTP.
Uses stdlib smtplib + email.mime for zero extra dependencies.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Sends emails using the SMTP configuration from application settings."""

    @staticmethod
    def send_email(to: str, subject: str, html_body: str) -> bool:
        """
        Send an HTML email via SMTP.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            html_body: HTML content of the email body.

        Returns:
            True if the email was sent successfully, False otherwise.
        """
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        try:
            if settings.SMTP_TLS:
                server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
            else:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
                # Attempt STARTTLS if the server supports it
                try:
                    server.starttls()
                except smtplib.SMTPNotSupportedError:
                    pass  # Server does not support STARTTLS; continue unencrypted

            with server:
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.EMAILS_FROM_EMAIL, [to], msg.as_string())

            logger.info(f"Email sent successfully to {to}: {subject}")
            return True

        except Exception as exc:
            logger.error(f"Failed to send email to {to}: {exc}")
            return False

    @staticmethod
    def send_password_reset_email(email: str, reset_token: str, reset_url: str) -> bool:
        """
        Send a password-reset email containing a one-time reset link.

        Args:
            email: Recipient email address.
            reset_token: Short-lived JWT for password reset.
            reset_url: Full URL the user should visit to reset their password.

        Returns:
            True if the email was sent successfully, False otherwise.
        """
        subject = "Reset your password - Yufeed Sentinel"
        html_body = f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; \
max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
  <h2 style="color: #1a1a2e;">Password Reset Request</h2>
  <p>We received a request to reset the password for your Yufeed Sentinel account.</p>
  <p>Click the button below to choose a new password. This link expires in \
<strong>15 minutes</strong>.</p>
  <p style="text-align: center; margin: 30px 0;">
    <a href="{reset_url}"
       style="background-color: #4f46e5; color: #ffffff; padding: 12px 24px; \
text-decoration: none; border-radius: 6px; font-weight: 600; display: inline-block;">
      Reset Password
    </a>
  </p>
  <p style="font-size: 13px; color: #666;">
    If the button does not work, copy and paste this link into your browser:<br>
    <a href="{reset_url}" style="color: #4f46e5; word-break: break-all;">{reset_url}</a>
  </p>
  <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
  <p style="font-size: 12px; color: #999;">
    If you did not request a password reset, you can safely ignore this email.
    Your password will not be changed.
  </p>
</body>
</html>"""

        return EmailService.send_email(email, subject, html_body)
