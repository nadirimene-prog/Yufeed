"""
Helpers for recording immutable events and decisions.
"""
import uuid
from typing import Any, Dict, Optional, List
from sqlalchemy.orm import Session

from src.audit.models import EventRecord, DecisionRecord


def record_event(
    db: Session,
    event_type: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    source: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    event_id: Optional[str] = None,
) -> EventRecord:
    record = EventRecord(
        event_id=event_id or uuid.uuid4().hex,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        source=source,
        payload=payload,
        metadata=metadata,
    )
    db.add(record)
    return record


def record_decision(
    db: Session,
    decision: str,
    event_id: Optional[str] = None,
    reason_codes: Optional[List[str]] = None,
    rule_version: Optional[str] = None,
    model_version: Optional[str] = None,
    evidence: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    decision_id: Optional[str] = None,
) -> DecisionRecord:
    record = DecisionRecord(
        decision_id=decision_id or uuid.uuid4().hex,
        event_id=event_id,
        decision=decision,
        reason_codes=reason_codes,
        rule_version=rule_version,
        model_version=model_version,
        evidence=evidence,
        metadata=metadata,
    )
    db.add(record)
    return record
