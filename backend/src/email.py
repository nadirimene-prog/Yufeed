import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from src.config import settings
import logging

logger = logging.getLogger(__name__)

def send_email(
    to_email: str | List[str],
    subject: str,
    html_content: str,
    plain_text: Optional[str] = None,
    from_email: Optional[str] = None
):
    """
    Send an email with HTML content and optional plain text fallback.

    Args:
        to_email: Single email address or list of addresses
        subject: Email subject line
        html_content: HTML body of the email
        plain_text: Optional plain text version (auto-generated if not provided)
        from_email: Optional sender email (uses settings default if not provided)
    """
    try:
        # Convert single email to list
        recipients = [to_email] if isinstance(to_email, str) else to_email

        # Use configured sender or default
        sender = from_email or settings.EMAILS_FROM_EMAIL

        msg = MIMEMultipart('alternative')
        msg['From'] = sender
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = subject

        # Add plain text version (fallback for non-HTML clients)
        if plain_text:
            msg.attach(MIMEText(plain_text, 'plain'))
        else:
            # Basic HTML stripping for plain text fallback
            import re
            plain_fallback = re.sub('<[^<]+?>', '', html_content)
            msg.attach(MIMEText(plain_fallback, 'plain'))

        # Add HTML version
        msg.attach(MIMEText(html_content, 'html'))

        # Send email
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            # Enable TLS if configured
            if hasattr(settings, 'SMTP_TLS') and settings.SMTP_TLS:
                server.starttls()

            # Authenticate if credentials provided
            if hasattr(settings, 'SMTP_USER') and settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

            server.send_message(msg)

        logger.info(f"Email sent successfully to {', '.join(recipients)}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def send_daily_digest(to_emails: List[str], documents: list):
    """Send daily digest email to a list of recipients."""
    from src.email_templates import daily_digest_template

    html = daily_digest_template(documents)
    subject = f"Daily EU Legal Digest - {len(documents)} New Document(s)"

    success_count = 0
    for email in to_emails:
        if send_email(email, subject, html):
            success_count += 1

    logger.info(f"Daily digest sent to {success_count}/{len(to_emails)} recipients")
    return success_count


def send_watchlist_alert(to_emails: List[str], watchlist_name: str, documents: list):
    """Send watchlist-specific alert."""
    from src.email_templates import watchlist_alert_template

    html = watchlist_alert_template(watchlist_name, documents)
    subject = f"Watchlist Alert: {watchlist_name} - {len(documents)} New Match(es)"

    success_count = 0
    for email in to_emails:
        if send_email(email, subject, html):
            success_count += 1

    return success_count


def send_compliance_alert(to_emails: List[str], high_risk_docs: list, upcoming_deadlines: list):
    """Send compliance-focused alert."""
    from src.email_templates import compliance_alert_template

    html = compliance_alert_template(high_risk_docs, upcoming_deadlines)
    subject = "⚠️ Compliance Alert: High Priority Updates"

    success_count = 0
    for email in to_emails:
        if send_email(email, subject, html):
            success_count += 1

    return success_count


def send_test_email(to_email: str):
    """Send test email to verify configuration."""
    from src.email_templates import test_email_template

    html = test_email_template()
    return send_email(to_email, "Yufeed Test Email", html)
