"""Compliance calendar API."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.auth.dependencies import CurrentUser, require_any_role
from src.database import get_db
from src.schemas.compliance_calendar import (
    CalendarEventListResponse,
    CalendarEventRead,
    CalendarEventStatusUpdate,
    CalendarSeedRequest,
    CalendarSeedResponse,
    RegulatoryChangeResponse,
)
from src.services.compliance_calendar import ComplianceCalendarService
from src.tenancy.context import get_current_tenant

router = APIRouter(prefix="/api/compliance-calendar", tags=["compliance-calendar"])


def _resolve_tenant_id(current_user: Optional[CurrentUser]) -> str:
    if current_user and current_user.tenant_id:
        return current_user.tenant_id
    return get_current_tenant() or "default"


@router.get("/events", response_model=CalendarEventListResponse)
def list_calendar_events(
    status: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    due_before: Optional[datetime] = Query(None),
    due_after: Optional[datetime] = Query(None),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])
    ),
):
    tenant_id = _resolve_tenant_id(current_user)
    service = ComplianceCalendarService(db)
    items = service.list_events(
        tenant_id=tenant_id,
        status=status,
        event_type=event_type,
        due_before=due_before,
        due_after=due_after,
        limit=limit,
    )
    return {"total": len(items), "items": items}


@router.post("/seed", response_model=CalendarSeedResponse)
def seed_calendar_events(
    payload: CalendarSeedRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    tenant_id = _resolve_tenant_id(current_user)
    service = ComplianceCalendarService(db)

    created = {"obligations": 0, "policy_reviews": 0, "kyc_reviews": 0}
    if payload.include_obligations:
        created["obligations"] = service.seed_events_from_obligations(tenant_id)
    if payload.include_policy_reviews:
        created["policy_reviews"] = service.seed_events_from_policy_reviews(tenant_id)
    if payload.include_kyc_reviews:
        created["kyc_reviews"] = service.seed_events_from_kyc_reviews(tenant_id)

    db.commit()
    return {
        "tenant_id": tenant_id,
        "created": created,
        "total_created": sum(created.values()),
    }


@router.post("/regulatory-change/{doc_id}", response_model=RegulatoryChangeResponse)
def propagate_regulatory_change(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    tenant_id = _resolve_tenant_id(current_user)
    service = ComplianceCalendarService(db)
    try:
        created = service.propagate_regulatory_change(tenant_id=tenant_id, doc_id=doc_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    db.commit()
    return {
        "tenant_id": tenant_id,
        "regulation_doc_id": doc_id,
        "created_events": created,
    }


@router.patch("/events/{event_id}", response_model=CalendarEventRead)
def update_calendar_event_status(
    event_id: int,
    payload: CalendarEventStatusUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    tenant_id = _resolve_tenant_id(current_user)
    service = ComplianceCalendarService(db)

    try:
        event = service.update_event_status(
            tenant_id=tenant_id,
            event_id=event_id,
            status=payload.status,
            assigned_to=payload.assigned_to,
            priority=payload.priority,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    db.commit()
    db.refresh(event)
    return event
