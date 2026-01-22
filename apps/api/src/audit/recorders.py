"""
Helpers for recording immutable events and decisions.
"""
import uuid
from typing import Any, Dict, Optional, List
from sqlalchemy.orm import Session

from src.audit.models import EventRecord, DecisionRecord
from src.utils.event_bus import publish_event_safe


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
        metadata_json=metadata,
    )
    db.add(record)

    bus_payload = {
        "event_id": record.event_id,
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "source": source,
        "payload": payload,
        "metadata": metadata,
    }
    publish_event_safe("events.raw", bus_payload)

    if event_type.startswith("alert.created"):
        publish_event_safe("alerts.created", bus_payload)
    elif event_type.startswith("alert.updated"):
        publish_event_safe("alerts.updated", bus_payload)
    elif event_type.startswith("case."):
        publish_event_safe("cases.updated", bus_payload)
    elif event_type in {"txn_fiat", "txn_crypto"}:
        publish_event_safe("events.normalized", bus_payload)

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
        metadata_json=metadata,
    )
    db.add(record)

    publish_event_safe(
        "decisions.made",
        {
            "decision_id": record.decision_id,
            "event_id": event_id,
            "decision": decision,
            "reason_codes": reason_codes,
            "rule_version": rule_version,
            "model_version": model_version,
            "evidence": evidence,
            "metadata": metadata,
        },
    )
    return record
