"""
Audit Trails API
Audit trails and detailed monitoring summaries.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import Optional
from datetime import datetime, timedelta, timezone

from src.database import get_db
from src.models.transaction_models import Transaction, Alert, Case
from src.auth.dependencies import require_any_role, CurrentUser


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


router = APIRouter(prefix="/api/reporting", tags=["audit-trails"])


@router.get("/alerts/summary")
def get_alerts_summary_report(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Detailed alert summary report for compliance review.
    """
    if not date_from:
        date_from = utc_now() - timedelta(days=30)
    if not date_to:
        date_to = utc_now()

    alerts = db.query(Alert).filter(
        and_(
            Alert.created_at >= date_from,
            Alert.created_at <= date_to
        )
    ).all()

    # Group by status
    by_status = {}
    for alert in alerts:
        by_status[alert.status] = by_status.get(alert.status, 0) + 1

    # False positive analysis
    false_positives = [a for a in alerts if a.resolution_status == 'false_positive']
    fp_rate = len(false_positives) / len(alerts) * 100 if alerts else 0

    # Top triggered rules
    rule_counts = {}
    for alert in alerts:
        matched = getattr(alert, "matched_rules_data", None)
        if isinstance(matched, dict):
            for rule_id in matched.keys():
                rule_counts[rule_id] = rule_counts.get(rule_id, 0) + 1
        elif isinstance(matched, list):
            for rule_id in matched:
                rule_counts[rule_id] = rule_counts.get(rule_id, 0) + 1
        else:
            rule_hits = getattr(alert, "rule_hits", []) or []
            for hit in rule_hits:
                rule = getattr(hit, "rule", None)
                if rule and getattr(rule, "rule_id", None):
                    rule_counts[rule.rule_id] = rule_counts.get(rule.rule_id, 0) + 1

    top_rules = sorted(rule_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "period": {
            "from": date_from.isoformat(),
            "to": date_to.isoformat()
        },
        "total_alerts": len(alerts),
        "by_status": by_status,
        "false_positive_rate": round(fp_rate, 2),
        "false_positive_count": len(false_positives),
        "top_triggered_rules": [
            {"rule_id": rule_id, "count": count}
            for rule_id, count in top_rules
        ],
        "severity_distribution": {
            "critical": sum(1 for a in alerts if a.severity == 'critical'),
            "high": sum(1 for a in alerts if a.severity == 'high'),
            "medium": sum(1 for a in alerts if a.severity == 'medium'),
            "low": sum(1 for a in alerts if a.severity == 'low')
        }
    }


@router.get("/transactions/summary")
def get_transactions_summary_report(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Detailed transaction summary report.
    """
    if not date_from:
        date_from = utc_now() - timedelta(days=30)
    if not date_to:
        date_to = utc_now()

    transactions = db.query(Transaction).filter(
        and_(
            Transaction.timestamp >= date_from,
            Transaction.timestamp <= date_to
        )
    ).all()

    # Calculate statistics
    total_volume = sum(tx.amount for tx in transactions)
    avg_amount = total_volume / len(transactions) if transactions else 0

    # By currency
    by_currency = {}
    for tx in transactions:
        by_currency[tx.currency] = by_currency.get(tx.currency, 0) + float(tx.amount)

    # By country
    by_country = {}
    for tx in transactions:
        if tx.country_code:
            by_country[tx.country_code] = by_country.get(tx.country_code, 0) + 1

    # Risk distribution
    by_risk = {}
    for tx in transactions:
        if tx.risk_level:
            by_risk[tx.risk_level] = by_risk.get(tx.risk_level, 0) + 1

    return {
        "period": {
            "from": date_from.isoformat(),
            "to": date_to.isoformat()
        },
        "total_transactions": len(transactions),
        "total_volume_by_currency": by_currency,
        "average_amount": round(float(avg_amount), 2),
        "by_country": dict(sorted(by_country.items(), key=lambda x: x[1], reverse=True)[:10]),
        "risk_distribution": by_risk,
        "flagged_transactions": sum(1 for tx in transactions if tx.status == 'flagged'),
        "high_risk_transactions": by_risk.get('high', 0) + by_risk.get('critical', 0)
    }


@router.get("/audit/alerts")
def get_alert_audit_trail(
    alert_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get audit trail for alert actions.

    Returns history of status changes, assignments, resolutions.
    """
    query = db.query(Alert)

    if alert_id:
        query = query.filter(Alert.alert_id == alert_id)

    if date_from:
        query = query.filter(Alert.created_at >= date_from)

    alerts = query.order_by(Alert.updated_at.desc()).limit(limit).all()

    audit_trail = []
    for alert in alerts:
        audit_trail.append({
            "alert_id": alert.alert_id,
            "created_at": alert.created_at.isoformat(),
            "updated_at": alert.updated_at.isoformat(),
            "status": alert.status,
            "assigned_to": alert.assigned_to,
            "resolved_by": alert.resolved_by,
            "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
            "resolution_status": alert.resolution_status,
            "sar_filed": alert.sar_filed,
            "changes": alert.resolution_notes  # Contains AI triage and manual notes
        })

    return {
        "audit_trail": audit_trail,
        "count": len(audit_trail)
    }


@router.get("/audit/cases")
def get_case_audit_trail(
    case_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get audit trail for case actions.
    """
    query = db.query(Case)

    if case_id:
        query = query.filter(Case.case_id == case_id)

    if date_from:
        query = query.filter(Case.opened_at >= date_from)

    cases = query.order_by(Case.updated_at.desc()).limit(limit).all()

    audit_trail = []
    for case in cases:
        audit_trail.append({
            "case_id": case.case_id,
            "opened_at": case.opened_at.isoformat(),
            "updated_at": case.updated_at.isoformat(),
            "closed_at": case.closed_at.isoformat() if case.closed_at else None,
            "status": case.status,
            "assigned_to": case.assigned_to,
            "outcome": case.outcome,
            "related_alerts": case.related_alert_ids or [],
            "related_transactions": case.related_transaction_ids or []
        })

    return {
        "audit_trail": audit_trail,
        "count": len(audit_trail)
    }
