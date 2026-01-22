"""
Audit, Event, and Decision APIs (append-only).
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from src.database import get_db
from src.audit.models import AuditLog, EventRecord, DecisionRecord
from src.schemas.audit_schemas import (
    AuditLogResponse,
    EventCreate,
    EventResponse,
    DecisionCreate,
    DecisionResponse,
)
from src.auth.dependencies import require_any_role, CurrentUser

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/logs", response_model=List[AuditLogResponse])
def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    actor_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    action: Optional[str] = None,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "auditor", "user"]))
):
    query = db.query(AuditLog)

    if actor_id:
        query = query.filter(AuditLog.actor_id == actor_id)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(AuditLog.entity_id == entity_id)
    if action:
        query = query.filter(AuditLog.action == action)

    logs = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()
    return logs


@router.get("/logs/{audit_id}", response_model=AuditLogResponse)
def get_audit_log(
    audit_id: str,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "auditor", "user"]))
):
    log = db.query(AuditLog).filter(AuditLog.audit_id == audit_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return log


@router.post("/events", response_model=EventResponse, status_code=201)
def create_event(
    event: EventCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "auditor", "user"]))
):
    event_id = event.event_id or uuid.uuid4().hex
    record = EventRecord(
        event_id=event_id,
        event_type=event.event_type,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        source=event.source,
        payload=event.payload,
        metadata_json=event.metadata,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/events/{event_id}", response_model=EventResponse)
def get_event(
    event_id: str,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "auditor", "user"]))
):
    record = db.query(EventRecord).filter(EventRecord.event_id == event_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Event not found")
    return record


@router.post("/decisions", response_model=DecisionResponse, status_code=201)
def create_decision(
    decision: DecisionCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "auditor", "user"]))
):
    decision_id = decision.decision_id or uuid.uuid4().hex
    record = DecisionRecord(
        decision_id=decision_id,
        event_id=decision.event_id,
        decision=decision.decision,
        reason_codes=decision.reason_codes,
        rule_version=decision.rule_version,
        model_version=decision.model_version,
        evidence=decision.evidence,
        metadata_json=decision.metadata,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/decisions/{decision_id}", response_model=DecisionResponse)
def get_decision(
    decision_id: str,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "auditor", "user"]))
):
    record = db.query(DecisionRecord).filter(
        DecisionRecord.decision_id == decision_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Decision not found")
    return record
