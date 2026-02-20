"""
WebSocket event types and notification models.
"""

from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


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

    # Compliance events
    OBLIGATION_APPROVED = "obligation.approved"
    OBLIGATION_REJECTED = "obligation.rejected"
    OBLIGATION_UPDATED = "obligation.updated"
    OBLIGATION_EXTRACTED = "obligation.extracted"
    POLICY_CREATED = "policy.created"
    POLICY_APPROVED = "policy.approved"
    POLICY_UPDATED = "policy.updated"
    RISK_ENTRY_CREATED = "risk.entry_created"
    RISK_ENTRY_UPDATED = "risk.entry_updated"
    INTERNAL_RULE_CREATED = "internal_rule.created"


class NotificationEvent(BaseModel):
    """
    WebSocket notification event model.
    """

    event_type: EventType
    title: str
    message: str
    data: Dict[str, Any]
    timestamp: datetime = None  # Will be set to utc_now() in __init__
    priority: str = "normal"  # low, normal, high, critical

    def __init__(self, **data):
        if "timestamp" not in data or data["timestamp"] is None:
            data["timestamp"] = utc_now()
        super().__init__(**data)

    user_id: Optional[str] = None
    link: Optional[str] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


def create_alert_notification(
    event_type: EventType,
    alert_id: str,
    alert_type: str,
    severity: str,
    user_id: Optional[str] = None,
    assigned_to: Optional[str] = None,
) -> NotificationEvent:
    """Create notification for alert events."""

    messages = {
        EventType.ALERT_CREATED: f"New {severity} alert: {alert_type}",
        EventType.ALERT_UPDATED: f"Alert {alert_id} updated",
        EventType.ALERT_ASSIGNED: "Alert assigned to you",
        EventType.ALERT_RESOLVED: f"Alert {alert_id} resolved",
        EventType.ALERT_ESCALATED: f"Alert {alert_id} escalated",
    }

    priority_map = {"low": "low", "medium": "normal", "high": "high", "critical": "critical"}

    return NotificationEvent(
        event_type=event_type,
        title="Alert Notification",
        message=messages.get(event_type, f"Alert event: {event_type}"),
        data={
            "alert_id": alert_id,
            "alert_type": alert_type,
            "severity": severity,
            "user_id": user_id,
            "assigned_to": assigned_to,
        },
        priority=priority_map.get(severity, "normal"),
        user_id=assigned_to,
        link=f"/alerts/{alert_id}",
    )


def create_transaction_notification(
    event_type: EventType,
    transaction_id: str,
    amount: float,
    currency: str,
    risk_score: float,
    user_id: Optional[str] = None,
) -> NotificationEvent:
    """Create notification for transaction events."""

    messages = {
        EventType.TRANSACTION_FLAGGED: f"Transaction flagged: {currency} {amount:,.2f}",
        EventType.TRANSACTION_BLOCKED: f"Transaction blocked: {currency} {amount:,.2f}",
        EventType.HIGH_RISK_TRANSACTION: "High-risk transaction detected",
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
            "user_id": user_id,
        },
        priority=priority,
        link=f"/transactions/{transaction_id}",
    )


def create_case_notification(
    event_type: EventType,
    case_id: str,
    case_type: str,
    priority: str,
    assigned_to: Optional[str] = None,
) -> NotificationEvent:
    """Create notification for case events."""

    messages = {
        EventType.CASE_CREATED: f"New {priority} priority case created",
        EventType.CASE_UPDATED: f"Case {case_id} updated",
        EventType.CASE_CLOSED: f"Case {case_id} closed",
    }

    return NotificationEvent(
        event_type=event_type,
        title="Case Notification",
        message=messages.get(event_type, f"Case event: {event_type}"),
        data={
            "case_id": case_id,
            "case_type": case_type,
            "priority": priority,
            "assigned_to": assigned_to,
        },
        priority=priority,
        user_id=assigned_to,
        link=f"/cases/{case_id}",
    )


def create_obligation_notification(
    event_type: EventType,
    obligation_id: str,
    obligation_text: str,
    status: str,
    approved_by: Optional[str] = None,
    internal_rule_id: Optional[str] = None,
) -> NotificationEvent:
    """Create notification for obligation events."""

    messages = {
        EventType.OBLIGATION_APPROVED: f"Obligation approved: {obligation_text[:50]}...",
        EventType.OBLIGATION_REJECTED: f"Obligation rejected: {obligation_text[:50]}...",
        EventType.OBLIGATION_UPDATED: f"Obligation updated: {obligation_text[:50]}...",
    }

    priority_map = {
        "approved": "normal",
        "rejected": "high",
    }

    return NotificationEvent(
        event_type=event_type,
        title="Obligation Notification",
        message=messages.get(event_type, f"Obligation event: {event_type}"),
        data={
            "obligation_id": obligation_id,
            "status": status,
            "approved_by": approved_by,
            "internal_rule_id": internal_rule_id,
        },
        priority=priority_map.get(status, "normal"),
        link=f"/compliance/obligations/{obligation_id}",
    )


def create_policy_notification(
    event_type: EventType,
    policy_id: str,
    policy_name: str,
    status: str,
    user_id: Optional[str] = None,
) -> NotificationEvent:
    """Create notification for policy events."""

    messages = {
        EventType.POLICY_CREATED: f"New policy created: {policy_name}",
        EventType.POLICY_APPROVED: f"Policy approved: {policy_name}",
        EventType.POLICY_UPDATED: f"Policy updated: {policy_name}",
    }

    return NotificationEvent(
        event_type=event_type,
        title="Policy Notification",
        message=messages.get(event_type, f"Policy event: {event_type}"),
        data={
            "policy_id": policy_id,
            "policy_name": policy_name,
            "status": status,
        },
        priority="normal",
        user_id=user_id,
        link=f"/compliance/policies/{policy_id}",
    )


def create_risk_notification(
    event_type: EventType,
    risk_id: str,
    risk_name: str,
    category_name: str,
    risk_level: str,
    user_id: Optional[str] = None,
) -> NotificationEvent:
    """Create notification for risk events."""

    messages = {
        EventType.RISK_ENTRY_CREATED: f"New risk entry: {risk_name}",
        EventType.RISK_ENTRY_UPDATED: f"Risk updated: {risk_name}",
    }

    priority_map = {
        "critical": "critical",
        "high": "high",
        "medium": "normal",
        "low": "low",
    }

    return NotificationEvent(
        event_type=event_type,
        title="Risk Notification",
        message=messages.get(event_type, f"Risk event: {event_type}"),
        data={
            "risk_id": risk_id,
            "risk_name": risk_name,
            "category": category_name,
            "risk_level": risk_level,
        },
        priority=priority_map.get(risk_level, "normal"),
        user_id=user_id,
        link=f"/compliance/risk-map?risk={risk_id}",
    )


def create_internal_rule_notification(
    event_type: EventType,
    internal_rule_id: str,
    rule_name: str,
    obligation_id: str,
    user_id: Optional[str] = None,
) -> NotificationEvent:
    """Create notification for internal rule events."""

    messages = {
        EventType.INTERNAL_RULE_CREATED: f"Internal rule created: {rule_name}",
    }

    return NotificationEvent(
        event_type=event_type,
        title="Internal Rule Notification",
        message=messages.get(event_type, f"Internal rule event: {event_type}"),
        data={
            "internal_rule_id": internal_rule_id,
            "rule_name": rule_name,
            "obligation_id": obligation_id,
        },
        priority="normal",
        user_id=user_id,
        link=f"/compliance/obligations/{obligation_id}",
    )
