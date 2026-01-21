"""
WebSocket Event Types and Schemas

Defines all real-time event types for the Yufeed platform.
"""

from enum import Enum
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class EventType(str, Enum):
    """All supported WebSocket event types."""
    # Transaction events
    TRANSACTION_NEW = "transaction.new"
    TRANSACTION_UPDATED = "transaction.updated"
    TRANSACTION_RISK_CHANGED = "transaction.risk_changed"

    # Alert events
    ALERT_CREATED = "alert.created"
    ALERT_UPDATED = "alert.updated"
    ALERT_ASSIGNED = "alert.assigned"
    ALERT_RESOLVED = "alert.resolved"
    ALERT_ESCALATED = "alert.escalated"

    # Case events
    CASE_CREATED = "case.created"
    CASE_UPDATED = "case.updated"
    CASE_CLOSED = "case.closed"

    # System events
    SYSTEM_HEALTH = "system.health"
    METRICS_UPDATE = "metrics.update"

    # SAR events
    SAR_FILED = "sar.filed"
    SAR_ACKNOWLEDGED = "sar.acknowledged"


class WebSocketEvent(BaseModel):
    """Base class for all WebSocket events."""
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def to_json(self) -> dict:
        """Convert event to JSON-serializable dict."""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data
        }


class TransactionEvent(WebSocketEvent):
    """Event for transaction-related updates."""
    event_type: EventType = EventType.TRANSACTION_NEW

    @classmethod
    def new_transaction(
        cls,
        transaction_id: str,
        user_id: str,
        amount: float,
        currency: str,
        risk_score: int,
        risk_level: str,
        country_code: Optional[str] = None
    ) -> "TransactionEvent":
        return cls(
            event_type=EventType.TRANSACTION_NEW,
            data={
                "transaction_id": transaction_id,
                "user_id": user_id,
                "amount": amount,
                "currency": currency,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "country_code": country_code
            }
        )

    @classmethod
    def risk_changed(
        cls,
        transaction_id: str,
        old_risk_score: int,
        new_risk_score: int,
        old_risk_level: str,
        new_risk_level: str
    ) -> "TransactionEvent":
        return cls(
            event_type=EventType.TRANSACTION_RISK_CHANGED,
            data={
                "transaction_id": transaction_id,
                "old_risk_score": old_risk_score,
                "new_risk_score": new_risk_score,
                "old_risk_level": old_risk_level,
                "new_risk_level": new_risk_level
            }
        )


class AlertEvent(WebSocketEvent):
    """Event for alert-related updates."""
    event_type: EventType = EventType.ALERT_CREATED

    @classmethod
    def created(
        cls,
        alert_id: str,
        alert_type: str,
        severity: str,
        user_id: str,
        description: str,
        ai_confidence: Optional[float] = None
    ) -> "AlertEvent":
        return cls(
            event_type=EventType.ALERT_CREATED,
            data={
                "alert_id": alert_id,
                "alert_type": alert_type,
                "severity": severity,
                "user_id": user_id,
                "description": description,
                "ai_confidence": ai_confidence
            }
        )

    @classmethod
    def updated(
        cls,
        alert_id: str,
        status: str,
        changes: Dict[str, Any]
    ) -> "AlertEvent":
        return cls(
            event_type=EventType.ALERT_UPDATED,
            data={
                "alert_id": alert_id,
                "status": status,
                "changes": changes
            }
        )

    @classmethod
    def assigned(
        cls,
        alert_id: str,
        assigned_to: str,
        assigned_by: Optional[str] = None
    ) -> "AlertEvent":
        return cls(
            event_type=EventType.ALERT_ASSIGNED,
            data={
                "alert_id": alert_id,
                "assigned_to": assigned_to,
                "assigned_by": assigned_by
            }
        )

    @classmethod
    def resolved(
        cls,
        alert_id: str,
        resolution_status: str,
        resolved_by: str
    ) -> "AlertEvent":
        return cls(
            event_type=EventType.ALERT_RESOLVED,
            data={
                "alert_id": alert_id,
                "resolution_status": resolution_status,
                "resolved_by": resolved_by
            }
        )

    @classmethod
    def escalated(
        cls,
        alert_id: str,
        new_priority: int,
        escalated_by: Optional[str] = None
    ) -> "AlertEvent":
        return cls(
            event_type=EventType.ALERT_ESCALATED,
            data={
                "alert_id": alert_id,
                "new_priority": new_priority,
                "escalated_by": escalated_by
            }
        )


class SystemHealthEvent(WebSocketEvent):
    """Event for system health status updates."""
    event_type: EventType = EventType.SYSTEM_HEALTH

    @classmethod
    def update(
        cls,
        services: Dict[str, str],
        uptime_percentage: float,
        latency_p50: float,
        latency_p95: float,
        latency_p99: float,
        queue_depth: int
    ) -> "SystemHealthEvent":
        return cls(
            event_type=EventType.SYSTEM_HEALTH,
            data={
                "services": services,
                "uptime_percentage": uptime_percentage,
                "latency": {
                    "p50": latency_p50,
                    "p95": latency_p95,
                    "p99": latency_p99
                },
                "queue_depth": queue_depth
            }
        )


class MetricsEvent(WebSocketEvent):
    """Event for real-time metrics updates."""
    event_type: EventType = EventType.METRICS_UPDATE

    @classmethod
    def update(
        cls,
        transactions_per_minute: int,
        active_alerts: int,
        critical_alerts: int,
        pending_reviews: int,
        sars_this_month: int,
        false_positive_rate: float,
        geographic_distribution: Optional[List[Dict[str, Any]]] = None
    ) -> "MetricsEvent":
        return cls(
            event_type=EventType.METRICS_UPDATE,
            data={
                "transactions_per_minute": transactions_per_minute,
                "active_alerts": active_alerts,
                "critical_alerts": critical_alerts,
                "pending_reviews": pending_reviews,
                "sars_this_month": sars_this_month,
                "false_positive_rate": false_positive_rate,
                "geographic_distribution": geographic_distribution or []
            }
        )
