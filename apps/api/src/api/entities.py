"""Entity profile aggregation API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.auth.dependencies import CurrentUser, require_any_role
from src.database import get_db
from src.models.compliance import ComplianceProfile
from src.models.transaction_models import Alert, Case, Transaction, UserRiskProfile

router = APIRouter(prefix="/api/entities", tags=["entities"])


def _tenant_filter(query, model, current_user: CurrentUser):
    if current_user.tenant_id and hasattr(model, "tenant_id"):
        return query.filter(model.tenant_id == current_user.tenant_id)
    return query


def _resolve_triggered_rule(alert: Alert) -> tuple[str | None, str | None]:
    rule_id = getattr(alert, "rule_id", None)
    matched = alert.matched_rules_data if isinstance(alert.matched_rules_data, dict) else None
    if matched and not rule_id:
        first_key = next(iter(matched.keys()), None)
        if isinstance(first_key, str):
            rule_id = first_key
    rule_name = None
    if matched and rule_id and isinstance(matched.get(rule_id), str):
        rule_name = matched.get(rule_id)
    elif matched:
        first_val = next(iter(matched.values()), None)
        if isinstance(first_val, str):
            rule_name = first_val
    return rule_id, rule_name


def _serialize_alert(alert: Alert) -> dict:
    triggered_rule_id, triggered_rule_name = _resolve_triggered_rule(alert)
    return {
        "id": alert.id,
        "alert_id": alert.alert_id,
        "alert_type": alert.alert_type,
        "severity": alert.severity,
        "status": alert.status,
        "priority": alert.priority,
        "risk_score": float(alert.risk_score or 0),
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
        "assigned_to": alert.assigned_to,
        "triggered_rule_id": triggered_rule_id,
        "triggered_rule_name": triggered_rule_name,
    }


def _serialize_case(case: Case) -> dict:
    return {
        "id": case.id,
        "case_id": case.case_id,
        "case_type": case.case_type,
        "status": case.status,
        "priority": case.priority,
        "subject_id": case.subject_id,
        "assigned_to": case.assigned_to,
        "opened_at": case.opened_at.isoformat() if case.opened_at else None,
        "updated_at": case.updated_at.isoformat() if case.updated_at else None,
        "outcome": case.outcome,
    }


def _serialize_transaction(transaction: Transaction) -> dict:
    return {
        "id": transaction.id,
        "transaction_id": transaction.transaction_id,
        "amount": float(transaction.amount or 0),
        "currency": transaction.currency,
        "transaction_type": transaction.transaction_type,
        "timestamp": transaction.timestamp.isoformat() if transaction.timestamp else None,
        "status": transaction.status,
        "country_code": transaction.country_code,
        "risk_score": float(transaction.risk_score or 0),
    }


@router.get("/{entity_type}/{entity_id}")
def get_entity_profile(
    entity_type: str,
    entity_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "auditor", "user"])
    ),
):
    """Return a consolidated entity profile across risk, alerts, cases, and transactions."""
    normalized_type = entity_type.lower()
    allowed = {"user", "entity", "kyc_profile", "transaction"}
    if normalized_type not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported entity type: {entity_type}")

    user_id: str | None = None
    transaction_ref: str | None = None

    if normalized_type == "transaction":
        tx_query = _tenant_filter(db.query(Transaction), Transaction, current_user)
        transaction = tx_query.filter(Transaction.transaction_id == entity_id).first()
        if not transaction and entity_id.isdigit():
            transaction = tx_query.filter(Transaction.id == int(entity_id)).first()
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        transaction_ref = transaction.transaction_id
        user_id = transaction.user_id
    elif normalized_type == "kyc_profile":
        profile_query = _tenant_filter(db.query(ComplianceProfile), ComplianceProfile, current_user)
        profile = (
            profile_query.filter(ComplianceProfile.id == int(entity_id)).first()
            if entity_id.isdigit()
            else None
        )
        if not profile:
            raise HTTPException(status_code=404, detail="Compliance profile not found")
        user_id = profile.user_id
    else:
        user_id = entity_id

    risk_profile = None
    if user_id:
        risk_query = _tenant_filter(db.query(UserRiskProfile), UserRiskProfile, current_user)
        risk_profile = risk_query.filter(UserRiskProfile.user_id == user_id).first()

    compliance_profile = None
    if user_id:
        compliance_query = _tenant_filter(
            db.query(ComplianceProfile), ComplianceProfile, current_user
        )
        compliance_profile = (
            compliance_query.filter(ComplianceProfile.user_id == user_id)
            .order_by(ComplianceProfile.updated_at.desc())
            .first()
        )

    alert_query = _tenant_filter(db.query(Alert), Alert, current_user)
    if user_id:
        alert_query = alert_query.filter(Alert.user_id == user_id)
    elif transaction_ref:
        alert_query = alert_query.filter(Alert.alert_id == transaction_ref)
    alerts = alert_query.order_by(Alert.created_at.desc()).limit(200).all()

    case_query = _tenant_filter(db.query(Case), Case, current_user)
    if user_id:
        case_query = case_query.filter(Case.subject_id == user_id)
    cases = case_query.order_by(Case.updated_at.desc(), Case.opened_at.desc()).limit(200).all()

    transaction_query = _tenant_filter(db.query(Transaction), Transaction, current_user)
    if user_id:
        transaction_query = transaction_query.filter(Transaction.user_id == user_id)
    elif transaction_ref:
        transaction_query = transaction_query.filter(Transaction.transaction_id == transaction_ref)
    transactions = transaction_query.order_by(Transaction.timestamp.desc()).limit(200).all()

    if not user_id and not transactions:
        raise HTTPException(status_code=404, detail="Entity not found")

    return {
        "type": normalized_type,
        "id": entity_id,
        "user_id": user_id,
        "risk": (
            {
                "overall_score": float(risk_profile.overall_risk_score or 0),
                "risk_level": risk_profile.risk_level,
                "kyc_status": risk_profile.kyc_status,
                "enhanced_due_diligence": bool(risk_profile.enhanced_due_diligence),
                "last_updated": (
                    risk_profile.updated_at.isoformat() if risk_profile.updated_at else None
                ),
            }
            if risk_profile
            else None
        ),
        "compliance": (
            {
                "id": compliance_profile.id,
                "status": compliance_profile.status,
                "risk_level": compliance_profile.risk_level,
                "type": compliance_profile.type,
                "updated_at": (
                    compliance_profile.updated_at.isoformat()
                    if compliance_profile.updated_at
                    else None
                ),
            }
            if compliance_profile
            else None
        ),
        "alerts": [_serialize_alert(alert) for alert in alerts],
        "cases": [_serialize_case(case) for case in cases],
        "transactions": [_serialize_transaction(transaction) for transaction in transactions],
        "network": {
            "seed_user_id": user_id,
            "alerts_count": len(alerts),
            "cases_count": len(cases),
            "transactions_count": len(transactions),
        },
    }
