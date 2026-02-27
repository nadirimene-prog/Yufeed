"""
Dashboard telemetry ingestion API.

Accepts frontend UX telemetry events from the AMLCO dashboard for KPI baselining
and rollout monitoring. The endpoint is intentionally lightweight and additive.
"""

from datetime import datetime
from typing import Any, Literal
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from src.audit.recorders import record_event
from src.auth.dependencies import CurrentUser, require_any_role
from src.database import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard/telemetry", tags=["dashboard-telemetry"])

DashboardTelemetryEventName = Literal[
    "dashboard_filter_apply",
    "dashboard_row_select",
    "dashboard_action_submit",
    "dashboard_action_next",
    "dashboard_shortcut_used",
    "dashboard_autosave_result",
    "dashboard_ui_timing",
]


class DashboardTelemetryEvent(BaseModel):
    event: DashboardTelemetryEventName
    payload: dict[str, Any] = Field(default_factory=dict)
    at: datetime


class DashboardTelemetryBatchRequest(BaseModel):
    events: list[DashboardTelemetryEvent] = Field(default_factory=list)

    @field_validator("events")
    @classmethod
    def validate_events(cls, value: list[DashboardTelemetryEvent]) -> list[DashboardTelemetryEvent]:
        if not value:
            raise ValueError("events must not be empty")
        if len(value) > 100:
            raise ValueError("events batch exceeds limit (100)")
        return value


class DashboardTelemetryBatchResponse(BaseModel):
    accepted: int
    dropped: int = 0


@router.post(
    "/events",
    response_model=DashboardTelemetryBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def ingest_dashboard_telemetry_events(
    payload: DashboardTelemetryBatchRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_role(
            [
                "admin",
                "compliance",
                "auditor",
                "user",
                "viewer",
                "analyst",
                "reviewer",
                "manager",
                "qa_audit",
            ]
        )
    ),
):
    accepted = len(payload.events)
    if accepted == 0:
        raise HTTPException(status_code=400, detail="No telemetry events provided")

    event_names = [event.event for event in payload.events]
    for event in payload.events:
        record_event(
            db,
            event_type=f"dashboard.telemetry.{event.event}",
            tenant_id=current_user.tenant_id,
            entity_type="dashboard_telemetry",
            entity_id=current_user.user_id,
            source="dashboard_frontend",
            payload={
                "event": event.event,
                "at": event.at.isoformat(),
                "payload": event.payload,
                "role": current_user.role,
            },
        )
    db.commit()
    logger.info(
        "dashboard.telemetry.ingested",
        extra={
            "user_id": current_user.user_id,
            "tenant_id": current_user.tenant_id,
            "role": current_user.role,
            "accepted": accepted,
            "event_names": event_names,
        },
    )

    return DashboardTelemetryBatchResponse(accepted=accepted, dropped=0)
