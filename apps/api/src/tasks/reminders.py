"""
Celery Tasks for Deadline Reminders

Scheduled tasks to check for upcoming deadlines and send reminders.
"""

import logging
from datetime import datetime, timezone
from typing import List

from celery import shared_task
from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.services.reminder_service import ReminderService, ReminderChannel, ReminderType
from src.services.email import EmailService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def check_upcoming_deadlines(self):
    """
    Check for upcoming deadlines and queue reminder tasks.

    Runs daily to find obligations with deadlines approaching
    and creates individual reminder tasks.
    """
    logger.info("Starting daily deadline check")

    db = SessionLocal()
    try:
        service = ReminderService(db)

        # Get upcoming deadlines (next 35 days to catch 30-day reminders)
        upcoming = service.get_upcoming_deadlines(days_window=35)

        logger.info(f"Found {len(upcoming)} upcoming deadlines requiring reminders")

        # Queue individual reminder tasks
        for deadline in upcoming:
            send_reminder.delay(
                obligation_id=deadline.obligation_id,
                reminder_type=deadline.reminder_type.value,
                days_remaining=deadline.days_remaining,
            )

        return {
            "status": "success",
            "deadlines_found": len(upcoming),
            "reminders_queued": len(upcoming),
        }

    except Exception as exc:
        logger.error(f"Error checking deadlines: {exc}")
        self.retry(exc=exc, countdown=300)  # Retry in 5 minutes
    finally:
        db.close()


@shared_task(bind=True, max_retries=3)
def send_reminder(self, obligation_id: int, reminder_type: str, days_remaining: int):
    """
    Send a reminder for a specific obligation.

    Args:
        obligation_id: ID of the obligation
        reminder_type: Type of reminder (30_days, 14_days, etc.)
        days_remaining: Days until deadline
    """
    logger.info(f"Sending {reminder_type} reminder for obligation {obligation_id}")

    db = SessionLocal()
    try:
        service = ReminderService(db)
        reminder_enum = ReminderType(reminder_type)

        # Check if we should send this reminder
        if not service.should_send_reminder(obligation_id, reminder_enum):
            logger.info(f"Reminder already sent recently for obligation {obligation_id}")
            return {"status": "skipped", "reason": "already_sent"}

        # Get obligation details
        from src.models.compliance_workflow import RegulatoryObligation

        obligation = db.query(RegulatoryObligation).get(obligation_id)

        if not obligation:
            logger.error(f"Obligation {obligation_id} not found")
            return {"status": "failed", "reason": "obligation_not_found"}

        # Get users to notify
        users = service.get_users_to_notify(obligation_id=obligation_id)

        if not users:
            logger.warning(f"No users to notify for obligation {obligation_id}")
            return {"status": "skipped", "reason": "no_recipients"}

        # Send reminders to each user
        results = []
        for user in users:
            # Send email notification
            if user.get("email_enabled"):
                result = _send_email_reminder(
                    user_email=user["email"],
                    user_name=user["full_name"],
                    obligation=obligation,
                    reminder_type=reminder_enum,
                    days_remaining=days_remaining,
                )

                # Log the reminder
                service.log_reminder(
                    obligation_id=obligation_id,
                    reminder_type=reminder_enum,
                    channel=ReminderChannel.EMAIL,
                    user_id=user["id"],
                    status="sent" if result else "failed",
                )

                results.append(
                    {
                        "user_id": user["id"],
                        "channel": "email",
                        "status": "sent" if result else "failed",
                    }
                )

            # Send Slack notification (if enabled)
            if user.get("slack_enabled"):
                result = _send_slack_reminder(
                    user=user,
                    obligation=obligation,
                    reminder_type=reminder_enum,
                    days_remaining=days_remaining,
                )

                if result:
                    service.log_reminder(
                        obligation_id=obligation_id,
                        reminder_type=reminder_enum,
                        channel=ReminderChannel.SLACK,
                        user_id=user["id"],
                        status="sent",
                    )

                results.append(
                    {
                        "user_id": user["id"],
                        "channel": "slack",
                        "status": "sent" if result else "failed",
                    }
                )

        return {
            "status": "success",
            "obligation_id": obligation_id,
            "recipients": len(users),
            "results": results,
        }

    except Exception as exc:
        logger.error(f"Error sending reminder for obligation {obligation_id}: {exc}")
        self.retry(exc=exc, countdown=60)
    finally:
        db.close()


def _send_email_reminder(
    user_email: str, user_name: str, obligation, reminder_type: ReminderType, days_remaining: int
) -> bool:
    """Send email reminder."""
    try:
        subject = _get_email_subject(reminder_type, days_remaining)
        body = _get_email_body(
            user_name=user_name,
            obligation=obligation,
            reminder_type=reminder_type,
            days_remaining=days_remaining,
        )

        # Use existing email service
        EmailService.send_email(to=user_email, subject=subject, html_body=body)

        logger.info(f"Email reminder sent to {user_email}")
        return True

    except Exception as exc:
        logger.error(f"Failed to send email to {user_email}: {exc}")
        return False


def _send_slack_reminder(
    user: dict, obligation, reminder_type: ReminderType, days_remaining: int
) -> bool:
    """Send Slack reminder."""
    # Placeholder - would integrate with Slack API
    logger.info(f"Slack reminder would be sent to user {user['id']}")
    return True


def _get_email_subject(reminder_type: ReminderType, days_remaining: int) -> str:
    """Generate email subject line."""
    if reminder_type == ReminderType.OVERDUE:
        return "🔴 URGENT: Compliance Deadline Overdue"
    elif reminder_type == ReminderType.ONE_DAY:
        return "⏰ Final Reminder: Compliance Deadline Tomorrow"
    elif reminder_type == ReminderType.SEVEN_DAYS:
        return f"📅 Reminder: Compliance Deadline in {days_remaining} Days"
    elif reminder_type == ReminderType.FOURTEEN_DAYS:
        return "📅 Compliance Deadline in 2 Weeks"
    else:
        return "📅 Compliance Deadline in 30 Days"


def _get_email_body(
    user_name: str, obligation, reminder_type: ReminderType, days_remaining: int
) -> str:
    """Generate HTML email body."""
    urgency_emoji = "🔴" if days_remaining <= 1 else "⏰" if days_remaining <= 7 else "📅"
    urgency_text = "OVERDUE" if days_remaining <= 0 else f"in {days_remaining} days"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
            .urgent {{ color: #d32f2f; font-weight: bold; }}
            .warning {{ color: #f57c00; font-weight: bold; }}
            .info {{ color: #1976d2; font-weight: bold; }}
            .obligation {{ background: #fff3e0; padding: 15px; border-left: 4px solid #ff9800; margin: 15px 0; }}
            .button {{ display: inline-block; padding: 12px 24px; background: #1976d2; color: white;
                      text-decoration: none; border-radius: 4px; margin-top: 20px; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;
                      font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>{urgency_emoji} Compliance Deadline Reminder</h2>
            </div>

            <p>Hello {user_name or 'Compliance Team'},</p>

            <p>This is a reminder that the following compliance obligation is due <strong class="{'urgent' if days_remaining <= 1 else 'warning' if days_remaining <= 7 else 'info'}">{urgency_text}</strong>.</p>

            <div class="obligation">
                <h3>Obligation Details</h3>
                <p><strong>Document:</strong> {obligation.celex or 'N/A'}</p>
                <p><strong>Article:</strong> {obligation.article_ref or 'N/A'}</p>
                <p><strong>Deadline:</strong> {obligation.effective_date.strftime('%B %d, %Y') if obligation.effective_date else 'N/A'}</p>
                <p><strong>Status:</strong> {obligation.status}</p>
                <hr>
                <p><strong>Requirement:</strong></p>
                <p>{obligation.obligation_text[:500]}{'...' if len(obligation.obligation_text) > 500 else ''}</p>
            </div>

            <a href="https://yufeed.app/obligations/{obligation.id}" class="button">
                View Obligation in Yufeed
            </a>

            <div class="footer">
                <p>This is an automated reminder from Yufeed Compliance Platform.</p>
                <p>To manage your notification preferences, <a href="https://yufeed.app/settings/notifications">click here</a>.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html


@shared_task
def send_weekly_digest():
    """
    Send weekly summary of upcoming deadlines.

    Runs every Monday morning.
    """
    logger.info("Generating weekly deadline digest")

    db = SessionLocal()
    try:
        service = ReminderService(db)

        # Get all upcoming deadlines for next 30 days
        upcoming = service.get_upcoming_deadlines(days_window=30)

        if not upcoming:
            logger.info("No upcoming deadlines for weekly digest")
            return {"status": "success", "message": "No upcoming deadlines"}

        # Group by user and send digest
        users = service.get_users_to_notify()

        for user in users:
            if not user.get("email_enabled"):
                continue

            # Filter deadlines relevant to this user
            user_deadlines = upcoming  # Could filter by scope/user preferences

            if user_deadlines:
                _send_digest_email(user, user_deadlines)

        return {
            "status": "success",
            "deadlines_included": len(upcoming),
            "digests_sent": len(users),
        }

    except Exception as exc:
        logger.error(f"Error sending weekly digest: {exc}")
    finally:
        db.close()


def _send_digest_email(user: dict, deadlines: list):
    """Send weekly digest email."""
    subject = f"📅 Weekly Compliance Digest - {len(deadlines)} Upcoming Deadlines"

    # Build digest HTML
    deadline_rows = ""
    for d in deadlines[:10]:  # Top 10
        urgency_color = (
            "#d32f2f"
            if d.days_remaining <= 7
            else "#f57c00" if d.days_remaining <= 14 else "#1976d2"
        )
        deadline_rows += f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #ddd;">{d.doc_title}</td>
            <td style="padding: 10px; border-bottom: 1px solid #ddd;">{d.article_ref or 'N/A'}</td>
            <td style="padding: 10px; border-bottom: 1px solid #ddd; color: {urgency_color}; font-weight: bold;">
                {d.days_remaining} days
            </td>
        </tr>
        """

    body = f"""
    <h2>📅 Your Weekly Compliance Digest</h2>
    <p>Hello {user.get('full_name', 'Compliance Team')},</p>
    <p>You have <strong>{len(deadlines)}</strong> compliance deadlines approaching in the next 30 days.</p>

    <h3>Top Priorities</h3>
    <table style="width: 100%; border-collapse: collapse;">
        <thead>
            <tr style="background: #f5f5f5;">
                <th style="padding: 10px; text-align: left;">Document</th>
                <th style="padding: 10px; text-align: left;">Article</th>
                <th style="padding: 10px; text-align: left;">Days Remaining</th>
            </tr>
        </thead>
        <tbody>
            {deadline_rows}
        </tbody>
    </table>

    <p><a href="https://yufeed.app/dashboard" style="display: inline-block; padding: 12px 24px;
       background: #1976d2; color: white; text-decoration: none; border-radius: 4px; margin-top: 20px;">
       View All Deadlines
    </a></p>
    """

    try:
        EmailService.send_email(to=user["email"], subject=subject, html_body=body)
        logger.info(f"Weekly digest sent to {user['email']}")
    except Exception as exc:
        logger.error(f"Failed to send digest to {user['email']}: {exc}")


# Task schedule configuration (for celery beat)
reminder_schedule = {
    "check-upcoming-deadlines": {
        "task": "src.tasks.reminders.check_upcoming_deadlines",
        "schedule": "cron(hour=9, minute=0)",  # Daily at 9 AM
    },
    "send-weekly-digest": {
        "task": "src.tasks.reminders.send_weekly_digest",
        "schedule": "cron(day_of_week=1, hour=8, minute=0)",  # Monday 8 AM
    },
}
