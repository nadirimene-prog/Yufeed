"""
WebSocket event types and notification models.
"""
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime


class EventType(str, Enum):
    """WebSocket event types."""
    # Alert events
    ALERT_CREATED = "alert.created"
    ALERT_UPDATED = "alert.updated"
    ALERT_ASSIGNED = "alert.assigned"
    ALERT_RESOLVED = "alert.resolved"
    ALERT_ESCALATED = "alert.escalated"

    # Transaction events
    TRANSACTION_FLAGGED = "transaction.flagged"
    TRANSACTION_BLOCKED = "transaction.blocked"
    HIGH_RISK_TRANSACTION = "transaction.high_risk"

    # Case events
    CASE_CREATED = "case.created"
    CASE_UPDATED = "case.updated"
    CASE_CLOSED = "case.closed"

    # Rule events
    RULE_TRIGGERED = "rule.triggered"
    RULE_UPDATED = "rule.updated"

    # System events
    SYSTEM_ALERT = "system.alert"
    SYSTEM_STATUS = "system.status"

    # User events
    USER_MENTION = "user.mention"
    USER_ASSIGNED = "user.assigned"


class NotificationEvent(BaseModel):
    """
    WebSocket notification event model.
    """
    event_type: EventType
    title: str
    message: str
    data: Dict[str, Any]
    timestamp: datetime = datetime.utcnow()
    priority: str = "normal"  # low, normal, high, critical
    user_id: Optional[str] = None
    link: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


def create_alert_notification(
    event_type: EventType,
    alert_id: str,
    alert_type: str,
    severity: str,
    user_id: Optional[str] = None,
    assigned_to: Optional[str] = None
) -> NotificationEvent:
    """Create notification for alert events."""

    messages = {
        EventType.ALERT_CREATED: f"New {severity} alert: {alert_type}",
        EventType.ALERT_UPDATED: f"Alert {alert_id} updated",
        EventType.ALERT_ASSIGNED: f"Alert assigned to you",
        EventType.ALERT_RESOLVED: f"Alert {alert_id} resolved",
        EventType.ALERT_ESCALATED: f"Alert {alert_id} escalated"
    }

    priority_map = {
        "low": "low",
        "medium": "normal",
        "high": "high",
        "critical": "critical"
    }

    return NotificationEvent(
        event_type=event_type,
        title="Alert Notification",
        message=messages.get(event_type, f"Alert event: {event_type}"),
        data={
            "alert_id": alert_id,
            "alert_type": alert_type,
            "severity": severity,
            "user_id": user_id,
            "assigned_to": assigned_to
        },
        priority=priority_map.get(severity, "normal"),
        user_id=assigned_to,
        link=f"/alerts/{alert_id}"
    )


def create_transaction_notification(
    event_type: EventType,
    transaction_id: str,
    amount: float,
    currency: str,
    risk_score: float,
    user_id: Optional[str] = None
) -> NotificationEvent:
    """Create notification for transaction events."""

    messages = {
        EventType.TRANSACTION_FLAGGED: f"Transaction flagged: {currency} {amount:,.2f}",
        EventType.TRANSACTION_BLOCKED: f"Transaction blocked: {currency} {amount:,.2f}",
        EventType.HIGH_RISK_TRANSACTION: f"High-risk transaction detected"
    }

    priority = "critical" if risk_score > 80 else "high" if risk_score > 60 else "normal"

    return NotificationEvent(
        event_type=event_type,
        title="Transaction Alert",
        message=messages.get(event_type, f"Transaction event: {event_type}"),
        data={
            "transaction_id": transaction_id,
            "amount": amount,
            "currency": currency,
            "risk_score": risk_score,
            "user_id": user_id
        },
        priority=priority,
        link=f"/transactions/{transaction_id}"
    )


def create_case_notification(
    event_type: EventType,
    case_id: str,
    case_type: str,
    priority: str,
    assigned_to: Optional[str] = None
) -> NotificationEvent:
    """Create notification for case events."""

    messages = {
        EventType.CASE_CREATED: f"New {priority} priority case created",
        EventType.CASE_UPDATED: f"Case {case_id} updated",
        EventType.CASE_CLOSED: f"Case {case_id} closed"
    }

    return NotificationEvent(
        event_type=event_type,
        title="Case Notification",
        message=messages.get(event_type, f"Case event: {event_type}"),
        data={
            "case_id": case_id,
            "case_type": case_type,
            "priority": priority,
            "assigned_to": assigned_to
        },
        priority=priority,
        user_id=assigned_to,
        link=f"/cases/{case_id}"
    )
