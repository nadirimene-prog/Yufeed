"""
Deadline Reminder Service

Manages automated reminders for compliance deadlines.
Sends notifications at 30, 14, 7, and 1 day before deadlines.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from src.models.compliance_workflow import RegulatoryObligation, PolicyDocument
from src.models.models import LegalDocument
from src.models.user import User

logger = logging.getLogger(__name__)


class ReminderType(str, Enum):
    """Types of reminders."""

    THIRTY_DAYS = "30_days"
    FOURTEEN_DAYS = "14_days"
    SEVEN_DAYS = "7_days"
    ONE_DAY = "1_day"
    OVERDUE = "overdue"


class ReminderChannel(str, Enum):
    """Channels for sending reminders."""

    EMAIL = "email"
    SLACK = "slack"
    IN_APP = "in_app"


@dataclass
class ReminderConfig:
    """Configuration for reminder scheduling."""

    days_before: List[int] = None
    channels: List[ReminderChannel] = None

    def __post_init__(self):
        if self.days_before is None:
            self.days_before = [30, 14, 7, 1]
        if self.channels is None:
            self.channels = [ReminderChannel.EMAIL]


@dataclass
class UpcomingDeadline:
    """Represents an upcoming deadline."""

    obligation_id: int
    obligation_text: str
    celex: str
    doc_title: str
    deadline: datetime
    days_remaining: int
    reminder_type: ReminderType
    linked_policy_id: Optional[int] = None
    linked_policy_title: Optional[str] = None


class ReminderService:
    """
    Service for managing deadline reminders.

    Features:
    - Calculate upcoming deadlines
    - Determine which reminders to send
    - Track reminder history
    - Support multiple notification channels
    """

    DEFAULT_REMINDER_DAYS = [30, 14, 7, 1]

    def __init__(self, db: Session):
        self.db = db

    def get_upcoming_deadlines(
        self, days_window: int = 35, scope_filter: Optional[List[str]] = None
    ) -> List[UpcomingDeadline]:
        """
        Get all upcoming deadlines within the specified window.

        Args:
            days_window: Number of days to look ahead (default 35 for 30+day reminders)
            scope_filter: Optional list of scope tags to filter by

        Returns:
            List of UpcomingDeadline objects
        """
        now = datetime.now(timezone.utc)
        future_cutoff = now + timedelta(days=days_window)

        # Query obligations with upcoming effective dates
        query = (
            self.db.query(
                RegulatoryObligation,
                LegalDocument.celex,
                LegalDocument.title,
                PolicyDocument.id.label("policy_id"),
                PolicyDocument.title.label("policy_title"),
            )
            .join(LegalDocument, RegulatoryObligation.doc_id == LegalDocument.id)
            .outerjoin(PolicyDocument, RegulatoryObligation.linked_policy_id == PolicyDocument.id)
            .filter(
                RegulatoryObligation.effective_date.isnot(None),
                RegulatoryObligation.effective_date >= now,
                RegulatoryObligation.effective_date <= future_cutoff,
                RegulatoryObligation.status.in_(["draft", "in_review"]),  # Not yet approved
            )
        )

        if scope_filter:
            # Apply scope filter if provided
            query = query.filter(LegalDocument.scope_tags.overlap(scope_filter))

        results = query.all()

        upcoming = []
        for row in results:
            obl = row[0]
            celex = row[1]
            doc_title = row[2]
            policy_id = row[3]
            policy_title = row[4]

            days_remaining = (obl.effective_date - now).days
            reminder_type = self._get_reminder_type(days_remaining)

            if reminder_type:  # Only include if it's a reminder day
                upcoming.append(
                    UpcomingDeadline(
                        obligation_id=obl.id,
                        obligation_text=(
                            obl.obligation_text[:200] + "..."
                            if len(obl.obligation_text) > 200
                            else obl.obligation_text
                        ),
                        celex=celex,
                        doc_title=doc_title,
                        deadline=obl.effective_date,
                        days_remaining=days_remaining,
                        reminder_type=reminder_type,
                        linked_policy_id=policy_id,
                        linked_policy_title=policy_title,
                    )
                )

        # Sort by deadline
        upcoming.sort(key=lambda x: x.deadline)
        return upcoming

    def _get_reminder_type(self, days_remaining: int) -> Optional[ReminderType]:
        """Determine the reminder type based on days remaining."""
        if days_remaining <= 0:
            return ReminderType.OVERDUE
        elif days_remaining == 1:
            return ReminderType.ONE_DAY
        elif days_remaining <= 7:
            return ReminderType.SEVEN_DAYS
        elif days_remaining <= 14:
            return ReminderType.FOURTEEN_DAYS
        elif days_remaining <= 30:
            return ReminderType.THIRTY_DAYS
        return None

    def should_send_reminder(
        self, obligation_id: int, reminder_type: ReminderType, user_id: Optional[int] = None
    ) -> bool:
        """
        Check if a reminder should be sent for this obligation.

        Prevents duplicate reminders by checking reminder_logs.
        """
        # Check if reminder already sent in the last 24 hours
        yesterday = datetime.now(timezone.utc) - timedelta(hours=24)

        from src.database import Base

        # Query reminder_logs
        existing = self.db.execute(
            text(
                """
                SELECT COUNT(*) FROM reminder_logs
                WHERE obligation_id = :obl_id
                AND reminder_type = :rem_type
                AND sent_at > :yesterday
                AND status = 'sent'
            """
            ),
            {"obl_id": obligation_id, "rem_type": reminder_type.value, "yesterday": yesterday},
        ).scalar()

        return existing == 0

    def get_users_to_notify(
        self, obligation_id: Optional[int] = None, doc_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Get list of users who should be notified.

        Returns users who have subscriptions or have relevant roles.
        """
        users = []

        # First, check explicit subscriptions
        from sqlalchemy import text

        subs = self.db.execute(
            text(
                """
                SELECT u.id, u.email, u.full_name, u.default_role,
                       s.email_enabled, s.slack_enabled, s.reminder_days
                FROM user_deadline_subscriptions s
                JOIN users u ON s.user_id = u.id
                WHERE (s.obligation_id = :obl_id OR s.doc_id = :doc_id)
                AND u.is_active = 1
            """
            ),
            {"obl_id": obligation_id, "doc_id": doc_id},
        ).fetchall()

        for row in subs:
            users.append(
                {
                    "id": row[0],
                    "email": row[1],
                    "full_name": row[2],
                    "role": row[3],
                    "email_enabled": row[4],
                    "slack_enabled": row[5],
                    "reminder_days": row[6],
                    "subscribed": True,
                }
            )

        # If no explicit subscriptions, notify compliance team
        if not users:
            compliance_users = (
                self.db.query(User)
                .filter(
                    User.default_role.in_(["compliance", "admin", "aml_officer"]),
                    User.is_active == True,
                )
                .all()
            )

            for user in compliance_users:
                users.append(
                    {
                        "id": user.id,
                        "email": user.email,
                        "full_name": user.full_name,
                        "role": user.default_role,
                        "email_enabled": True,
                        "slack_enabled": False,
                        "reminder_days": self.DEFAULT_REMINDER_DAYS,
                        "subscribed": False,
                    }
                )

        return users

    def log_reminder(
        self,
        obligation_id: int,
        reminder_type: ReminderType,
        channel: ReminderChannel,
        user_id: Optional[int] = None,
        status: str = "sent",
        error_message: Optional[str] = None,
    ):
        """Log a reminder that was sent."""
        from sqlalchemy import text

        self.db.execute(
            text(
                """
                INSERT INTO reminder_logs
                (obligation_id, user_id, reminder_type, channel, status, error_message)
                VALUES (:obl_id, :user_id, :rem_type, :channel, :status, :error)
            """
            ),
            {
                "obl_id": obligation_id,
                "user_id": user_id,
                "rem_type": reminder_type.value,
                "channel": channel.value,
                "status": status,
                "error": error_message,
            },
        )

        # Update obligation reminder tracking
        self.db.execute(
            text(
                """
                UPDATE regulatory_obligations
                SET reminder_count = COALESCE(reminder_count, 0) + 1,
                    last_reminder_at = CURRENT_TIMESTAMP,
                    next_reminder_at = :next_reminder
                WHERE id = :obl_id
            """
            ),
            {
                "obl_id": obligation_id,
                "next_reminder": self._calculate_next_reminder(obligation_id),
            },
        )

        self.db.commit()

    def _calculate_next_reminder(self, obligation_id: int) -> Optional[datetime]:
        """Calculate when the next reminder should be sent."""
        obl = self.db.query(RegulatoryObligation).get(obligation_id)
        if not obl or not obl.effective_date:
            return None

        now = datetime.now(timezone.utc)
        days_remaining = (obl.effective_date - now).days

        # Find the next reminder day
        for days in self.DEFAULT_REMINDER_DAYS:
            if days < days_remaining:
                return obl.effective_date - timedelta(days=days)

        return None

    def get_reminder_statistics(self, days: int = 30) -> Dict:
        """Get statistics about reminders sent."""
        from sqlalchemy import text

        since = datetime.now(timezone.utc) - timedelta(days=days)

        stats = self.db.execute(
            text(
                """
                SELECT
                    COUNT(*) as total_sent,
                    SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN opened_at IS NOT NULL THEN 1 ELSE 0 END) as opened,
                    COUNT(DISTINCT obligation_id) as unique_obligations
                FROM reminder_logs
                WHERE sent_at > :since
            """
            ),
            {"since": since},
        ).fetchone()

        return {
            "total_sent": stats[0] or 0,
            "successful": stats[1] or 0,
            "failed": stats[2] or 0,
            "opened": stats[3] or 0,
            "unique_obligations": stats[4] or 0,
            "open_rate": round((stats[3] or 0) / max(stats[0] or 1, 1) * 100, 1),
        }

    def snooze_reminder(self, obligation_id: int, snooze_days: int = 3):
        """Snooze reminders for an obligation."""
        from sqlalchemy import text

        snooze_until = datetime.now(timezone.utc) + timedelta(days=snooze_days)

        self.db.execute(
            text(
                """
                UPDATE regulatory_obligations
                SET next_reminder_at = :snooze_until
                WHERE id = :obl_id
            """
            ),
            {"obl_id": obligation_id, "snooze_until": snooze_until},
        )
        self.db.commit()

        logger.info(f"Snoozed reminders for obligation {obligation_id} until {snooze_until}")


# Import text for raw queries
from sqlalchemy import text


# Global service instance
def get_reminder_service(db: Session) -> ReminderService:
    """Get reminder service instance."""
    return ReminderService(db)
