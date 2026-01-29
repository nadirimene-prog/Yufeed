"""
Audit, Event, and Decision APIs (append-only).
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from src.database import get_db
from src.audit.models import AuditLog, EventRecord, DecisionRecord
from src.schemas.audit_schemas import (
    AuditLogResponse,
    EventCreate,
    EventResponse,
    DecisionCreate,
    DecisionResponse,
    DecisionListItem,
    DecisionListResponse,
)
from src.auth.dependencies import require_any_role, CurrentUser
from sqlalchemy import func

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/", response_model=List[AuditLogResponse])
def list_audit_logs_compat(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    actor_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    action: Optional[str] = None,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "auditor", "user"]))
):
    """
    Backwards-compatible audit log listing endpoint.

    Alias for /api/audit/logs.
    """
    return list_audit_logs(
        skip=skip,
        limit=limit,
        actor_id=actor_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        db=db,
        _=_
    )


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


@router.get("/decisions", response_model=DecisionListResponse)
def list_decisions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    decision: Optional[str] = None,
    event_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    event_id: Optional[str] = None,
    decision_id: Optional[str] = None,
    created_from: Optional[datetime] = None,
    created_to: Optional[datetime] = None,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "auditor", "user"]))
):
    query = db.query(DecisionRecord, EventRecord).outerjoin(
        EventRecord, DecisionRecord.event_id == EventRecord.event_id
    )

    if decision:
        query = query.filter(DecisionRecord.decision == decision)
    if event_id:
        query = query.filter(DecisionRecord.event_id == event_id)
    if decision_id:
        query = query.filter(DecisionRecord.decision_id == decision_id)
    if created_from:
        query = query.filter(DecisionRecord.created_at >= created_from)
    if created_to:
        query = query.filter(DecisionRecord.created_at <= created_to)
    if event_type:
        query = query.filter(EventRecord.event_type == event_type)
    if entity_type:
        query = query.filter(EventRecord.entity_type == entity_type)
    if entity_id:
        query = query.filter(EventRecord.entity_id == entity_id)

    count_query = db.query(func.count(DecisionRecord.id))
    if event_type or entity_type or entity_id:
        count_query = count_query.outerjoin(
            EventRecord, DecisionRecord.event_id == EventRecord.event_id
        )

    if decision:
        count_query = count_query.filter(DecisionRecord.decision == decision)
    if event_id:
        count_query = count_query.filter(DecisionRecord.event_id == event_id)
    if decision_id:
        count_query = count_query.filter(DecisionRecord.decision_id == decision_id)
    if created_from:
        count_query = count_query.filter(DecisionRecord.created_at >= created_from)
    if created_to:
        count_query = count_query.filter(DecisionRecord.created_at <= created_to)
    if event_type:
        count_query = count_query.filter(EventRecord.event_type == event_type)
    if entity_type:
        count_query = count_query.filter(EventRecord.entity_type == entity_type)
    if entity_id:
        count_query = count_query.filter(EventRecord.entity_id == entity_id)

    total = count_query.scalar() or 0
    rows = query.order_by(DecisionRecord.created_at.desc()).offset(skip).limit(limit).all()
    items: List[DecisionListItem] = []
    for decision_record, event_record in rows:
        items.append(
            DecisionListItem(
                decision_id=decision_record.decision_id,
                event_id=decision_record.event_id,
                decision=decision_record.decision,
                reason_codes=decision_record.reason_codes,
                rule_version=decision_record.rule_version,
                model_version=decision_record.model_version,
                created_at=decision_record.created_at,
                event_type=getattr(event_record, "event_type", None) if event_record else None,
                entity_type=getattr(event_record, "entity_type", None) if event_record else None,
                entity_id=getattr(event_record, "entity_id", None) if event_record else None,
                source=getattr(event_record, "source", None) if event_record else None,
            )
        )

    return DecisionListResponse(total=total, items=items)
