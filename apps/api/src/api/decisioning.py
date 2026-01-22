"""
Risk OS Decisioning API
Unified event normalization and low-latency decision endpoint.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.auth.dependencies import require_any_role, CurrentUser
from src.audit.recorders import record_event, record_decision
from src.services.event_normalizer import normalize_event
from src.services.rules_engine import RulesEngine
from src.services.risk_scoring import RiskScoringService
from src.models.transaction_models import Transaction

router = APIRouter(prefix="/api/decisioning", tags=["decisioning"])


class EventIngestRequest(BaseModel):
    event_type: str = Field(..., description="Incoming event type (any variant)")
    payload: Dict[str, Any] = Field(default_factory=dict)
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    source: Optional[str] = None


class EventIngestResponse(BaseModel):
    event_id: str
    event_type: str
    entity_type: Optional[str]
    entity_id: Optional[str]
    metadata: Dict[str, Any]


class DecisionRequest(BaseModel):
    event_type: str = Field("txn_fiat", description="Canonical event type")
    transaction_id: Optional[int] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    source: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class DecisionResponse(BaseModel):
    event_id: str
    decision_id: str
    decision: str
    risk_score: Optional[float]
    risk_level: Optional[str]
    alerts: List[str]
    reason_codes: List[str]
    evidence: Dict[str, Any]


@router.post(
    "/events",
    response_model=EventIngestResponse,
)
def ingest_event(
    request: EventIngestRequest,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "analyst", "aml_officer", "user"])),
):
    normalized = normalize_event(
        request.event_type,
        request.payload,
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        source=request.source or "decisioning",
    )

    event_record = record_event(
        db,
        event_type=normalized.event_type,
        entity_type=normalized.entity_type,
        entity_id=normalized.entity_id,
        source=normalized.source,
        payload=normalized.payload,
        metadata=normalized.metadata,
    )
    db.commit()

    return EventIngestResponse(
        event_id=event_record.event_id,
        event_type=normalized.event_type,
        entity_type=normalized.entity_type,
        entity_id=normalized.entity_id,
        metadata=normalized.metadata,
    )


@router.post(
    "/decide",
    response_model=DecisionResponse,
)
def decide(
    request: DecisionRequest,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "analyst", "aml_officer", "user"])),
):
    normalized = normalize_event(
        request.event_type,
        request.payload,
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        source=request.source or "decisioning",
    )

    event_record = record_event(
        db,
        event_type=normalized.event_type,
        entity_type=normalized.entity_type,
        entity_id=normalized.entity_id,
        source=normalized.source,
        payload=normalized.payload,
        metadata={"context": request.context, **normalized.metadata},
    )

    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    alerts: List[str] = []
    reason_codes: List[str] = []

    transaction: Optional[Transaction] = None
    if request.transaction_id is not None:
        transaction = db.query(Transaction).filter(
            Transaction.id == request.transaction_id
        ).first()
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")

        risk_service = RiskScoringService(db)
        score = risk_service.score_transaction(request.transaction_id)
        risk_score = float(score)
        risk_level = risk_service.get_risk_level(score)

        transaction.risk_score = score
        transaction.risk_level = risk_level

        rules_engine = RulesEngine(db)
        generated_alerts = rules_engine.evaluate_transaction(request.transaction_id)
        alerts = [alert.alert_id for alert in generated_alerts]
        reason_codes = [alert.rule_id for alert in generated_alerts if alert.rule_id]

        risk_service.update_user_risk_profile(transaction.user_id)

    decision = "allow"
    if alerts:
        decision = "alert"
    elif risk_level in {"high", "critical"}:
        decision = "step-up"

    evidence = {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "alerts": alerts,
    }

    decision_record = record_decision(
        db,
        decision=decision,
        event_id=event_record.event_id,
        reason_codes=reason_codes,
        evidence=evidence,
        metadata={"context": request.context},
    )
    db.commit()

    return DecisionResponse(
        event_id=event_record.event_id,
        decision_id=decision_record.decision_id,
        decision=decision,
        risk_score=risk_score,
        risk_level=risk_level,
        alerts=alerts,
        reason_codes=reason_codes,
        evidence=evidence,
    )
