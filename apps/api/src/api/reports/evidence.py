"""
Evidence Exports API
Export evidence bundles for cases, decisions, and travel rule requests.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from sqlalchemy.inspection import inspect as sa_inspect
from typing import Optional
from datetime import datetime, timezone
from decimal import Decimal

from src.database import get_db
from src.models.transaction_models import Transaction, Alert, Case
from src.models.travel_rule import TravelRuleRequestRecord
from src.audit.models import AuditLog, EventRecord, DecisionRecord
from src.auth.dependencies import require_any_role, CurrentUser


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


router = APIRouter(prefix="/reporting", tags=["evidence"])


def _model_to_dict(obj):
    """Convert SQLAlchemy model instance to dictionary."""
    data = {}
    for attr in sa_inspect(obj).mapper.column_attrs:
        key = attr.key
        value = getattr(obj, key)
        if isinstance(value, datetime):
            value = value.isoformat()
        elif isinstance(value, Decimal):
            value = float(value)
        data[key] = value
    if "metadata_json" in data:
        data["metadata"] = data.pop("metadata_json")
    return data


@router.get("/evidence/case/{case_id}")
def export_case_evidence(
    case_id: str,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "auditor"])),
):
    """
    Export an evidence bundle for a case.

    Includes case, related alerts/transactions, events, decisions, and audit logs.
    """
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    related_alert_ids = case.related_alert_ids or []
    related_tx_ids = case.related_transaction_ids or []

    alerts = (
        db.query(Alert).filter(Alert.id.in_(related_alert_ids)).all() if related_alert_ids else []
    )
    transactions = (
        db.query(Transaction).filter(Transaction.id.in_(related_tx_ids)).all()
        if related_tx_ids
        else []
    )

    # Collect entity IDs for event lookup
    alert_entity_ids = [a.alert_id for a in alerts]
    tx_entity_ids = [t.transaction_id for t in transactions]

    events = (
        db.query(EventRecord)
        .filter(
            or_(
                and_(EventRecord.entity_type == "case", EventRecord.entity_id == case.case_id),
                and_(
                    EventRecord.entity_type == "alert",
                    EventRecord.entity_id.in_(alert_entity_ids or ["__none__"]),
                ),
                and_(
                    EventRecord.entity_type == "transaction",
                    EventRecord.entity_id.in_(tx_entity_ids or ["__none__"]),
                ),
            )
        )
        .all()
    )

    event_ids = [e.event_id for e in events]
    decisions = (
        db.query(DecisionRecord)
        .filter(DecisionRecord.event_id.in_(event_ids or ["__none__"]))
        .all()
    )

    audit_logs = (
        db.query(AuditLog)
        .filter(
            or_(
                and_(AuditLog.entity_type == "case", AuditLog.entity_id == case.case_id),
                and_(
                    AuditLog.entity_type == "alert",
                    AuditLog.entity_id.in_(alert_entity_ids or ["__none__"]),
                ),
                and_(
                    AuditLog.entity_type == "transaction",
                    AuditLog.entity_id.in_(tx_entity_ids or ["__none__"]),
                ),
            )
        )
        .order_by(AuditLog.created_at.desc())
        .all()
    )

    return {
        "export_id": f"EVID-{utc_now().strftime('%Y%m%d')}-{case.case_id}",
        "exported_at": utc_now().isoformat(),
        "case": _model_to_dict(case),
        "alerts": [_model_to_dict(a) for a in alerts],
        "transactions": [_model_to_dict(t) for t in transactions],
        "events": [_model_to_dict(e) for e in events],
        "decisions": [_model_to_dict(d) for d in decisions],
        "audit_logs": [_model_to_dict(l) for l in audit_logs],
    }


@router.get("/evidence/decision/{decision_id}")
def export_decision_evidence(
    decision_id: str,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "auditor"])),
):
    """
    Export an evidence bundle for a decision.
    """
    decision = db.query(DecisionRecord).filter(DecisionRecord.decision_id == decision_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    event = db.query(EventRecord).filter(EventRecord.event_id == decision.event_id).first()

    transaction = None
    alerts = []
    if event and event.entity_type == "transaction":
        transaction = (
            db.query(Transaction).filter(Transaction.transaction_id == event.entity_id).first()
        )
        if transaction:
            alerts = db.query(Alert).filter(Alert.transaction_id == transaction.id).all()

    audit_logs = (
        db.query(AuditLog)
        .filter(
            or_(
                and_(
                    AuditLog.entity_type == "decision", AuditLog.entity_id == decision.decision_id
                ),
                and_(AuditLog.entity_type == "event", AuditLog.entity_id == decision.event_id),
            )
        )
        .order_by(AuditLog.created_at.desc())
        .all()
    )

    return {
        "export_id": f"EVID-{utc_now().strftime('%Y%m%d')}-{decision.decision_id}",
        "exported_at": utc_now().isoformat(),
        "decision": _model_to_dict(decision),
        "event": _model_to_dict(event) if event else None,
        "transaction": _model_to_dict(transaction) if transaction else None,
        "alerts": [_model_to_dict(a) for a in alerts],
        "audit_logs": [_model_to_dict(l) for l in audit_logs],
    }


@router.get("/evidence/travel-rule/{request_id}")
def export_travel_rule_evidence(
    request_id: str,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "auditor"])),
):
    """
    Export an evidence bundle for a travel rule request.
    """
    request = (
        db.query(TravelRuleRequestRecord)
        .filter(TravelRuleRequestRecord.request_id == request_id)
        .first()
    )
    if not request:
        raise HTTPException(status_code=404, detail="Travel rule request not found")

    audit_logs = (
        db.query(AuditLog)
        .filter(
            and_(AuditLog.entity_type == "travel_rule_request", AuditLog.entity_id == request_id)
        )
        .order_by(AuditLog.created_at.desc())
        .all()
    )

    return {
        "export_id": f"EVID-{utc_now().strftime('%Y%m%d')}-{request.request_id}",
        "exported_at": utc_now().isoformat(),
        "travel_rule_request": _model_to_dict(request),
        "audit_logs": [_model_to_dict(l) for l in audit_logs],
    }
