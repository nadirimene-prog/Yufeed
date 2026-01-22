"""
Compliance Reporting API
Regulatory reporting, analytics, and audit trails.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from sqlalchemy.inspection import inspect as sa_inspect
from typing import Optional
from datetime import datetime, timedelta
from decimal import Decimal

from src.database import get_db
from src.models.transaction_models import (
    Transaction, Alert, Case, MonitoringRule, UserRiskProfile
)
from src.models.travel_rule import TravelRuleRequestRecord
from src.models.models import LegalDocument
from src.audit.models import AuditLog, EventRecord, DecisionRecord
from src.compliance.sar_filing import SARFilingSystem, UARFilingSystem
from src.auth.dependencies import require_any_role, CurrentUser
from src.utils.event_bus import publish_event_safe
from src.models.travel_rule import TravelRuleRequestRecord

router = APIRouter(prefix="/api/reporting", tags=["reporting"])


# ============================================================================
# SAR/UAR FILING
# ============================================================================

@router.post("/sar/prepare/{case_id}")
def prepare_sar(
    case_id: str,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "analyst", "aml_officer"]))
):
    """
    Prepare Suspicious Activity Report from a case.

    Returns complete SAR structure ready for filing.
    """
    sar_system = SARFilingSystem(db)

    try:
        sar = sar_system.prepare_sar(case_id)
        publish_event_safe(
            "events.raw",
            {
                "event_type": "sar.prepared",
                "entity_type": "case",
                "entity_id": case_id,
                "source": "reporting",
                "payload": {
                    "case_id": case_id,
                },
            },
        )
        return sar

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SAR preparation failed: {str(e)}")


@router.post("/sar/file/{case_id}")
def file_sar(
    case_id: str,
    jurisdiction: str = Query("EU", regex="^(US|EU|INTL)$"),
    dry_run: bool = Query(True),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"]))
):
    """
    File SAR with regulatory authority.

    jurisdiction: US (FinCEN), EU (National FIU), INTL (goAML)
    dry_run: If True, validates but doesn't submit
    """
    sar_system = SARFilingSystem(db)

    try:
        # Prepare SAR
        sar = sar_system.prepare_sar(case_id)

        # File SAR
        result = sar_system.file_sar(sar, jurisdiction, dry_run)

        # Update case if actually filed
        if not dry_run:
            case = db.query(Case).filter(Case.case_id == case_id).first()
            if case:
                case.outcome = 'sar_filed'
                case.outcome_notes = f"SAR filed: {result['filing_reference']}"
                db.commit()

        publish_event_safe(
            "events.raw",
            {
                "event_type": "sar.filed",
                "entity_type": "case",
                "entity_id": case_id,
                "source": "reporting",
                "payload": {
                    "case_id": case_id,
                    "jurisdiction": jurisdiction,
                    "dry_run": dry_run,
                    "filing_reference": result.get("filing_reference"),
                },
            },
        )
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SAR filing failed: {str(e)}")


@router.post("/uar/prepare/{alert_id}")
def prepare_uar(
    alert_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "analyst", "aml_officer"]))
):
    """
    Prepare Unusual Activity Report from an alert.
    """
    uar_system = UARFilingSystem(db)

    try:
        uar = uar_system.prepare_uar(alert_id)
        publish_event_safe(
            "events.raw",
            {
                "event_type": "uar.prepared",
                "entity_type": "alert",
                "entity_id": str(alert_id),
                "source": "reporting",
                "payload": {
                    "alert_id": alert_id,
                },
            },
        )
        return uar

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"UAR preparation failed: {str(e)}")


# ============================================================================
# COMPLIANCE DASHBOARD
# ============================================================================

@router.get("/dashboard")
def get_compliance_dashboard(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Comprehensive compliance reporting dashboard.

    Includes alert metrics, case metrics, regulatory coverage, and risk metrics.
    """
    if not date_from:
        date_from = datetime.utcnow() - timedelta(days=30)
    if not date_to:
        date_to = datetime.utcnow()

    # Alert metrics
    total_alerts = db.query(func.count(Alert.id)).filter(
        and_(
            Alert.created_at >= date_from,
            Alert.created_at <= date_to
        )
    ).scalar() or 0

    alerts_by_severity = db.query(
        Alert.severity,
        func.count(Alert.id).label('count')
    ).filter(
        and_(
            Alert.created_at >= date_from,
            Alert.created_at <= date_to
        )
    ).group_by(Alert.severity).all()

    alerts_by_type = db.query(
        Alert.alert_type,
        func.count(Alert.id).label('count')
    ).filter(
        and_(
            Alert.created_at >= date_from,
            Alert.created_at <= date_to
        )
    ).group_by(Alert.alert_type).all()

    # Resolution time average
    resolved_alerts = db.query(Alert).filter(
        and_(
            Alert.created_at >= date_from,
            Alert.resolved_at.isnot(None)
        )
    ).all()

    avg_resolution_hours = 0
    if resolved_alerts:
        total_hours = sum(
            (alert.resolved_at - alert.created_at).total_seconds() / 3600
            for alert in resolved_alerts
        )
        avg_resolution_hours = total_hours / len(resolved_alerts)

    # Case metrics
    open_cases = db.query(func.count(Case.id)).filter(
        Case.status.in_(['open', 'in_progress'])
    ).scalar() or 0

    closed_cases = db.query(func.count(Case.id)).filter(
        and_(
            Case.status == 'closed',
            Case.closed_at >= date_from,
            Case.closed_at <= date_to
        )
    ).scalar() or 0

    sar_filed = db.query(func.count(Case.id)).filter(
        and_(
            Case.outcome == 'sar_filed',
            Case.closed_at >= date_from,
            Case.closed_at <= date_to
        )
    ).scalar() or 0

    # Regulatory coverage
    monitored_regulations = db.query(func.count(LegalDocument.id)).scalar() or 0

    rules_with_regs = db.query(func.count(MonitoringRule.id)).filter(
        MonitoringRule.regulatory_source_id.isnot(None)
    ).scalar() or 0

    total_rules = db.query(func.count(MonitoringRule.id)).scalar() or 1  # Avoid division by zero

    recent_updates = db.query(LegalDocument).filter(
        LegalDocument.created_at >= date_from
    ).count()

    # Risk metrics
    high_risk_users = db.query(func.count(UserRiskProfile.id)).filter(
        UserRiskProfile.risk_level.in_(['high', 'critical'])
    ).scalar() or 0


# ============================================================================
# EVIDENCE EXPORTS (RISK OS)
# ============================================================================

@router.get("/evidence/case/{case_id}")
def export_case_evidence(
    case_id: str,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "auditor"]))
):
    """
    Export an evidence bundle for a case.

    Includes case, related alerts/transactions, events, decisions, and audit logs.
    """
    def _model_to_dict(obj):
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

    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    related_alert_ids = case.related_alert_ids or []
    related_tx_ids = case.related_transaction_ids or []

    alerts = db.query(Alert).filter(Alert.id.in_(related_alert_ids)).all() if related_alert_ids else []
    transactions = db.query(Transaction).filter(Transaction.id.in_(related_tx_ids)).all() if related_tx_ids else []

    # Collect entity IDs for event lookup
    alert_entity_ids = [a.alert_id for a in alerts]
    tx_entity_ids = [t.transaction_id for t in transactions]

    events = db.query(EventRecord).filter(
        or_(
            and_(EventRecord.entity_type == "case", EventRecord.entity_id == case.case_id),
            and_(EventRecord.entity_type == "alert", EventRecord.entity_id.in_(alert_entity_ids or ["__none__"])),
            and_(EventRecord.entity_type == "transaction", EventRecord.entity_id.in_(tx_entity_ids or ["__none__"])),
        )
    ).all()

    event_ids = [e.event_id for e in events]
    decisions = db.query(DecisionRecord).filter(
        DecisionRecord.event_id.in_(event_ids or ["__none__"])
    ).all()

    audit_logs = db.query(AuditLog).filter(
        or_(
            and_(AuditLog.entity_type == "case", AuditLog.entity_id == case.case_id),
            and_(AuditLog.entity_type == "alert", AuditLog.entity_id.in_(alert_entity_ids or ["__none__"])),
            and_(AuditLog.entity_type == "transaction", AuditLog.entity_id.in_(tx_entity_ids or ["__none__"])),
        )
    ).order_by(AuditLog.created_at.desc()).all()

    return {
        "export_id": f"EVID-{datetime.utcnow().strftime('%Y%m%d')}-{case.case_id}",
        "exported_at": datetime.utcnow().isoformat(),
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
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "auditor"]))
):
    """
    Export an evidence bundle for a decision.
    """
    def _model_to_dict(obj):
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

    decision = db.query(DecisionRecord).filter(
        DecisionRecord.decision_id == decision_id
    ).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    event = db.query(EventRecord).filter(
        EventRecord.event_id == decision.event_id
    ).first()

    transaction = None
    alerts = []
    if event and event.entity_type == "transaction":
        transaction = db.query(Transaction).filter(
            Transaction.transaction_id == event.entity_id
        ).first()
        if transaction:
            alerts = db.query(Alert).filter(Alert.transaction_id == transaction.id).all()

    audit_logs = db.query(AuditLog).filter(
        or_(
            and_(AuditLog.entity_type == "decision", AuditLog.entity_id == decision.decision_id),
            and_(AuditLog.entity_type == "event", AuditLog.entity_id == decision.event_id),
        )
    ).order_by(AuditLog.created_at.desc()).all()

    return {
        "export_id": f"EVID-{datetime.utcnow().strftime('%Y%m%d')}-{decision.decision_id}",
        "exported_at": datetime.utcnow().isoformat(),
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
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "auditor"]))
):
    """
    Export an evidence bundle for a travel rule request.
    """
    def _model_to_dict(obj):
        data = {}
        for attr in sa_inspect(obj).mapper.column_attrs:
            key = attr.key
            value = getattr(obj, key)
            if isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, Decimal):
                value = float(value)
            data[key] = value
        return data

    request = db.query(TravelRuleRequestRecord).filter(
        TravelRuleRequestRecord.request_id == request_id
    ).first()
    if not request:
        raise HTTPException(status_code=404, detail="Travel rule request not found")

    audit_logs = db.query(AuditLog).filter(
        and_(AuditLog.entity_type == "travel_rule_request", AuditLog.entity_id == request_id)
    ).order_by(AuditLog.created_at.desc()).all()

    return {
        "export_id": f"EVID-{datetime.utcnow().strftime('%Y%m%d')}-{request.request_id}",
        "exported_at": datetime.utcnow().isoformat(),
        "travel_rule_request": _model_to_dict(request),
        "audit_logs": [_model_to_dict(l) for l in audit_logs],
    }


# ============================================================================
# COMPLIANCE OFFICER HOME DASHBOARD
# ============================================================================

@router.get("/dashboard/home")
def compliance_home_dashboard(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "auditor", "user"]))
):
    """
    Aggregated home dashboard metrics for Compliance Officer.
    """
    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)
    last_30d = now - timedelta(days=30)

    total_docs = db.query(func.count(LegalDocument.id)).scalar() or 0
    rules_total = db.query(func.count(MonitoringRule.id)).scalar() or 0
    rules_with_celex = db.query(func.count(MonitoringRule.id)).filter(
        MonitoringRule.regulatory_source_id.isnot(None)
    ).scalar() or 0
    celex_covered = db.query(func.count(func.distinct(MonitoringRule.regulatory_source_id))).filter(
        MonitoringRule.regulatory_source_id.isnot(None)
    ).scalar() or 0

    celex_coverage_pct = round((celex_covered / total_docs * 100), 2) if total_docs > 0 else 0
    rules_coverage_pct = round((rules_with_celex / rules_total * 100), 2) if rules_total > 0 else 0

    mapped_ids_subq = db.query(MonitoringRule.regulatory_source_id).filter(
        MonitoringRule.regulatory_source_id.isnot(None)
    ).subquery()

    uncovered_docs = db.query(LegalDocument).filter(
        ~LegalDocument.id.in_(mapped_ids_subq)
    ).order_by(LegalDocument.publication_date.desc()).limit(5).all()

    rules_without_celex = db.query(MonitoringRule).filter(
        MonitoringRule.regulatory_source_id.is_(None)
    ).order_by(MonitoringRule.updated_at.desc()).limit(5).all()

    pending_alerts = db.query(func.count(Alert.id)).filter(Alert.status == "pending").scalar() or 0
    critical_alerts = db.query(func.count(Alert.id)).filter(Alert.severity == "critical").scalar() or 0
    open_cases = db.query(func.count(Case.id)).filter(Case.status.in_(["open", "in_progress"])).scalar() or 0

    decisions_24h = db.query(func.count(DecisionRecord.id)).filter(
        DecisionRecord.created_at >= last_24h
    ).scalar() or 0
    decision_breakdown_rows = db.query(
        DecisionRecord.decision,
        func.count(DecisionRecord.id).label("count")
    ).filter(DecisionRecord.created_at >= last_24h).group_by(DecisionRecord.decision).all()
    decision_breakdown = {row.decision: row.count for row in decision_breakdown_rows}

    sar_filed_30d = db.query(func.count(Case.id)).filter(
        Case.outcome == "sar_filed",
        Case.closed_at >= last_30d
    ).scalar() or 0

    travel_pending = db.query(func.count(TravelRuleRequestRecord.id)).filter(
        TravelRuleRequestRecord.status == "pending"
    ).scalar() or 0
    travel_submitted = db.query(func.count(TravelRuleRequestRecord.id)).filter(
        TravelRuleRequestRecord.status == "submitted"
    ).scalar() or 0

    onchain_checks = db.query(func.count(EventRecord.id)).filter(
        EventRecord.event_type == "onchain_risk_check",
        EventRecord.created_at >= last_24h
    ).scalar() or 0

    def _doc_to_dict(doc):
        return {
            "id": doc.id,
            "celex": doc.celex,
            "title": doc.title,
            "risk_level": doc.risk_level,
            "compliance_domain": doc.compliance_domain,
        }

    def _rule_to_dict(rule):
        return {
            "rule_id": rule.rule_id,
            "name": rule.name,
            "severity": rule.severity,
            "category": rule.category,
        }

    return {
        "coverage": {
            "total_documents": total_docs,
            "celex_covered": celex_covered,
            "celex_coverage_pct": celex_coverage_pct,
            "rules_total": rules_total,
            "rules_with_celex": rules_with_celex,
            "rules_coverage_pct": rules_coverage_pct,
        },
        "coverage_gaps": {
            "celex_without_rules": [_doc_to_dict(doc) for doc in uncovered_docs],
            "rules_without_celex": [_rule_to_dict(rule) for rule in rules_without_celex],
        },
        "risk_ops": {
            "pending_alerts": pending_alerts,
            "critical_alerts": critical_alerts,
            "open_cases": open_cases,
        },
        "decisions": {
            "last_24h_total": decisions_24h,
            "breakdown": decision_breakdown,
        },
        "reporting": {
            "sar_filed_30d": sar_filed_30d,
            "travel_pending": travel_pending,
            "travel_submitted": travel_submitted,
            "onchain_checks_24h": onchain_checks,
        },
    }

    transaction_volume = db.query(
        func.sum(Transaction.amount)
    ).filter(
        and_(
            Transaction.timestamp >= date_from,
            Transaction.timestamp <= date_to
        )
    ).scalar() or 0

    avg_risk_score = db.query(
        func.avg(Transaction.risk_score)
    ).filter(
        and_(
            Transaction.timestamp >= date_from,
            Transaction.timestamp <= date_to,
            Transaction.risk_score.isnot(None)
        )
    ).scalar() or 0

    return {
        "reporting_period": {
            "from": date_from.isoformat(),
            "to": date_to.isoformat(),
            "days": (date_to - date_from).days
        },
        "alert_metrics": {
            "total_alerts": total_alerts,
            "by_severity": {row.severity: row.count for row in alerts_by_severity},
            "by_type": {row.alert_type: row.count for row in alerts_by_type},
            "resolution_time_avg_hours": round(avg_resolution_hours, 2)
        },
        "case_metrics": {
            "open_cases": open_cases,
            "closed_cases": closed_cases,
            "sar_filed": sar_filed,
            "sar_rate": round(sar_filed / closed_cases * 100, 2) if closed_cases > 0 else 0
        },
        "regulatory_coverage": {
            "monitored_regulations": monitored_regulations,
            "total_rules": total_rules,
            "rules_derived_from_regs": rules_with_regs,
            "regulatory_coverage_rate": round(rules_with_regs / total_rules * 100, 2),
            "recent_regulatory_updates": recent_updates
        },
        "risk_metrics": {
            "high_risk_users": high_risk_users,
            "transaction_volume": float(transaction_volume),
            "average_risk_score": round(float(avg_risk_score), 2),
            "total_transactions": db.query(func.count(Transaction.id)).filter(
                and_(
                    Transaction.timestamp >= date_from,
                    Transaction.timestamp <= date_to
                )
            ).scalar() or 0
        }
    }


# ============================================================================
# DETAILED REPORTS
# ============================================================================

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
        date_from = datetime.utcnow() - timedelta(days=30)
    if not date_to:
        date_to = datetime.utcnow()

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
        if alert.rule_id:
            rule_counts[alert.rule_id] = rule_counts.get(alert.rule_id, 0) + 1

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
        date_from = datetime.utcnow() - timedelta(days=30)
    if not date_to:
        date_to = datetime.utcnow()

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


@router.get("/regulatory/coverage")
def get_regulatory_coverage_report(
    db: Session = Depends(get_db)
):
    """
    Report on regulatory coverage and compliance monitoring.
    """
    # Total regulations
    total_regulations = db.query(func.count(LegalDocument.id)).scalar() or 0

    # Regulations with monitoring rules
    regs_with_rules = db.query(
        func.count(func.distinct(MonitoringRule.regulatory_source_id))
    ).filter(
        MonitoringRule.regulatory_source_id.isnot(None)
    ).scalar() or 0

    # Coverage by domain
    by_domain = db.query(
        LegalDocument.compliance_domain,
        func.count(LegalDocument.id).label('count')
    ).group_by(LegalDocument.compliance_domain).all()

    # Rules by regulation
    rules_per_reg = db.query(
        MonitoringRule.regulatory_source_id,
        func.count(MonitoringRule.id).label('rule_count')
    ).filter(
        MonitoringRule.regulatory_source_id.isnot(None)
    ).group_by(MonitoringRule.regulatory_source_id).all()

    return {
        "total_regulations_monitored": total_regulations,
        "regulations_with_rules": regs_with_rules,
        "coverage_rate": round(regs_with_rules / total_regulations * 100, 2) if total_regulations > 0 else 0,
        "by_compliance_domain": {row.compliance_domain or 'uncategorized': row.count for row in by_domain},
        "average_rules_per_regulation": round(
            sum(r.rule_count for r in rules_per_reg) / len(rules_per_reg), 2
        ) if rules_per_reg else 0
    }


# ============================================================================
# AUDIT TRAIL
# ============================================================================

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
