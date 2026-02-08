"""
Risk OS Decisioning API
Unified event normalization and low-latency decision endpoint.
"""

from typing import Any, Dict, List, Optional
import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.auth.dependencies import require_any_role, CurrentUser
from src.audit.recorders import record_event, record_decision
from src.audit.models import EventRecord, DecisionRecord
from src.services.event_normalizer import normalize_event
from src.services.rules_engine import RulesEngine
from src.services.risk_scoring import RiskScoringService
from src.models.transaction_models import Transaction
from src.models.transaction_models import Alert
from src.tenancy.queries import set_tenant_on_create
from src.plugins.registry import get_plugin, register_plugin
from src.plugins.onchain import get_default_onchain_plugin
from src.tenancy.context import get_current_tenant

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
    event_id: Optional[str] = None
    event_type: str = Field("txn_fiat", description="Canonical event type")
    transaction_id: Optional[int] = None
    decision_type: Optional[str] = None
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
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "analyst", "aml_officer", "user"])
    ),
):
    tenant_id = current_user.tenant_id or get_current_tenant()
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant context is required")

    normalized = normalize_event(
        request.event_type,
        request.payload,
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        source=request.source or "decisioning",
    )

    event_record = record_event(
        db,
        tenant_id=tenant_id,
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
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "analyst", "aml_officer", "user"])
    ),
):
    tenant_id = current_user.tenant_id or get_current_tenant()
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant context is required")

    event_record: EventRecord | None = None
    if request.event_id:
        event_record = (
            db.query(EventRecord)
            .filter(
                EventRecord.event_id == request.event_id,
                EventRecord.tenant_id == tenant_id,
            )
            .first()
        )
        if not event_record:
            raise HTTPException(status_code=404, detail="Event not found")

    normalized = normalize_event(
        event_record.event_type if event_record else request.event_type,
        event_record.payload if event_record and event_record.payload else request.payload,
        entity_type=event_record.entity_type if event_record else request.entity_type,
        entity_id=event_record.entity_id if event_record else request.entity_id,
        source=(event_record.source if event_record and event_record.source else request.source)
        or "decisioning",
    )

    if event_record is None:
        event_record = record_event(
            db,
            tenant_id=tenant_id,
            event_type=normalized.event_type,
            entity_type=normalized.entity_type,
            entity_id=normalized.entity_id,
            source=normalized.source,
            payload=normalized.payload,
            metadata={"context": request.context, **normalized.metadata},
        )
        db.commit()

    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    alerts: List[str] = []
    reason_codes: List[str] = []
    onchain_evidence: Optional[Dict[str, Any]] = None

    transaction: Optional[Transaction] = None
    if request.transaction_id is not None:
        transaction = (
            db.query(Transaction)
            .filter(
                Transaction.id == request.transaction_id,
                Transaction.tenant_id == tenant_id,
            )
            .first()
        )
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

    # On-chain risk scoring for crypto events / wallet addresses
    wallet_address = None
    if isinstance(request.payload, dict):
        wallet_address = request.payload.get("wallet_address") or request.payload.get("address")
    if normalized.event_type in {"txn_crypto", "onchain_risk_check"} or wallet_address:
        plugin = get_plugin("mock-onchain")
        if not plugin:
            plugin = get_default_onchain_plugin()
            register_plugin("mock-onchain", plugin)
        if wallet_address:
            try:
                onchain_result = asyncio.run(plugin.score_address(wallet_address))
                onchain_evidence = onchain_result
                onchain_level = onchain_result.get("risk_level")
                if onchain_level in {"high", "critical"}:
                    alert_id = f"ALT-ONCHAIN-{uuid.uuid4().hex[:8].upper()}"
                    alert = Alert(
                        alert_id=alert_id,
                        alert_type="onchain_risk",
                        severity=onchain_level,
                        user_id=(
                            request.payload.get("user_id")
                            if isinstance(request.payload, dict)
                            else None
                        ),
                        description="On-chain risk score exceeded threshold",
                        evidence=onchain_result,
                    )
                    set_tenant_on_create(alert, tenant_id=tenant_id)
                    db.add(alert)
                    db.commit()
                    alerts.append(alert_id)
                    reason_codes.append("ONCHAIN-RISK")
            except Exception as exc:
                onchain_evidence = {"error": str(exc)}

    decision = "approve"
    if alerts or risk_level in {"high", "critical"}:
        decision = "review"

    evidence = {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "alerts": alerts,
        "onchain": onchain_evidence,
    }

    decision_record = record_decision(
        db,
        decision=decision,
        tenant_id=tenant_id,
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


@router.get(
    "/decisions/{decision_id}",
    response_model=DecisionResponse,
)
def get_decision(
    decision_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "analyst", "aml_officer", "user"])
    ),
):
    tenant_id = current_user.tenant_id or get_current_tenant()
    if not tenant_id:
        raise HTTPException(status_code=403, detail="Tenant context is required")

    record = (
        db.query(DecisionRecord)
        .filter(
            DecisionRecord.decision_id == decision_id,
            DecisionRecord.tenant_id == tenant_id,
        )
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Decision not found")

    evidence = record.evidence or {}
    alerts = evidence.get("alerts") if isinstance(evidence, dict) else None

    return DecisionResponse(
        event_id=record.event_id,
        decision_id=record.decision_id,
        decision=record.decision,
        risk_score=evidence.get("risk_score") if isinstance(evidence, dict) else None,
        risk_level=evidence.get("risk_level") if isinstance(evidence, dict) else None,
        alerts=alerts if isinstance(alerts, list) else [],
        reason_codes=record.reason_codes or [],
        evidence=evidence if isinstance(evidence, dict) else {},
    )
