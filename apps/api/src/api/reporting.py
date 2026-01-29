"""
Compliance Reporting API
Regulatory reporting, analytics, and audit trails.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case
import sqlalchemy as sa
from sqlalchemy.inspection import inspect as sa_inspect
from typing import Optional
from datetime import datetime, timedelta, timezone


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)
from decimal import Decimal

from src.database import get_db
from src.models.transaction_models import (
    Transaction, Alert, Case, MonitoringRule, UserRiskProfile
)
from src.models.travel_rule import TravelRuleRequestRecord
from src.models.models import LegalDocument
from src.models.compliance_workflow import RegulatoryObligation, PolicyDocument, InternalRule, OfficialJournalAct, RegulatorySource
from src.audit.models import AuditLog, EventRecord, DecisionRecord
from src.compliance.sar_filing import SARFilingSystem, UARFilingSystem
from src.auth.dependencies import require_any_role, CurrentUser
from src.utils.event_bus import publish_event_safe
from src.compliance.scope import normalize_scopes, scope_keywords
from sqlalchemy.dialects import postgresql
from src.models.travel_rule import TravelRuleRequestRecord

router = APIRouter(prefix="/api/reporting", tags=["reporting"])

def _apply_scope_filter_to_docs(query, scopes: list[str], db: Session):
    if not scopes:
        return query
    dialect = db.get_bind().dialect.name if db.get_bind() else ""
    if dialect == "postgresql":
        conditions = []
        for scope in scopes:
            conditions.append(
                sa.cast(LegalDocument.scope_tags, postgresql.JSONB).op("@>")(
                    sa.func.jsonb_build_array(scope)
                )
            )
        return query.filter(or_(*conditions))

    keywords = scope_keywords(scopes)
    if not keywords:
        return query
    conditions = [LegalDocument.title.ilike(f"%{keyword}%") for keyword in keywords]
    return query.filter(or_(*conditions))


def _apply_scope_filter_to_obligations(query, scopes: list[str], db: Session):
    if not scopes:
        return query
    dialect = db.get_bind().dialect.name if db.get_bind() else ""
    if dialect == "postgresql":
        conditions = []
        for scope in scopes:
            conditions.append(
                sa.cast(LegalDocument.scope_tags, postgresql.JSONB).op("@>")(
                    sa.func.jsonb_build_array(scope)
                )
            )
            conditions.append(
                sa.cast(RegulatoryObligation.scope_tags, postgresql.JSONB).op("@>")(
                    sa.func.jsonb_build_array(scope)
                )
            )
        return query.filter(or_(*conditions))

    keywords = scope_keywords(scopes)
    if not keywords:
        return query
    conditions = []
    for keyword in keywords:
        like = f"%{keyword}%"
        conditions.append(LegalDocument.title.ilike(like))
        conditions.append(RegulatoryObligation.obligation_text.ilike(like))
    return query.filter(or_(*conditions))


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
        date_from = utc_now() - timedelta(days=30)
    if not date_to:
        date_to = utc_now()

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
        "export_id": f"EVID-{utc_now().strftime('%Y%m%d')}-{request.request_id}",
        "exported_at": utc_now().isoformat(),
        "travel_rule_request": _model_to_dict(request),
        "audit_logs": [_model_to_dict(l) for l in audit_logs],
    }


# ============================================================================
# COMPLIANCE OFFICER HOME DASHBOARD
# ============================================================================

@router.get("/dashboard/home")
def compliance_home_dashboard(
    intake_days: int = Query(7, ge=1, le=90),
    intake_jurisdiction: Optional[str] = Query(None),
    intake_source: Optional[str] = Query(None),
    intake_limit: int = Query(8, ge=1, le=50),
    obligation_status: Optional[str] = Query(None, description="Comma-separated statuses"),
    obligation_limit: int = Query(8, ge=1, le=50),
    scope: Optional[str] = Query(None, description="Comma-separated scope tags: psp,eme,vasp"),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "auditor", "user"]))
):
    """
    Aggregated home dashboard metrics for Compliance Officer.
    """
    now = utc_now()
    last_24h = now - timedelta(hours=24)
    last_30d = now - timedelta(days=30)

    scopes = normalize_scopes(scope)
    docs_query = db.query(LegalDocument)
    docs_query = _apply_scope_filter_to_docs(docs_query, scopes, db)
    scope_doc_ids_subq = docs_query.with_entities(LegalDocument.id).subquery()

    total_docs = docs_query.count()
    rules_total = db.query(func.count(MonitoringRule.id)).scalar() or 0
    rules_with_celex = db.query(func.count(MonitoringRule.id)).filter(
        MonitoringRule.regulatory_source_id.isnot(None)
    ).scalar() or 0
    celex_covered = db.query(func.count(func.distinct(MonitoringRule.regulatory_source_id))).filter(
        MonitoringRule.regulatory_source_id.isnot(None),
        MonitoringRule.regulatory_source_id.in_(scope_doc_ids_subq),
    ).scalar() or 0

    celex_coverage_pct = round((celex_covered / total_docs * 100), 2) if total_docs > 0 else 0
    rules_coverage_pct = round((rules_with_celex / rules_total * 100), 2) if rules_total > 0 else 0

    mapped_ids_subq = db.query(MonitoringRule.regulatory_source_id).filter(
        MonitoringRule.regulatory_source_id.isnot(None)
    ).subquery()

    uncovered_docs = docs_query.filter(
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

    latest_decision_row = db.query(DecisionRecord, EventRecord).outerjoin(
        EventRecord, DecisionRecord.event_id == EventRecord.event_id
    ).order_by(DecisionRecord.created_at.desc()).first()
    latest_decision = None
    if latest_decision_row:
        latest_decision, latest_event = latest_decision_row
        latest_decision = {
            "decision_id": latest_decision.decision_id,
            "decision": latest_decision.decision,
            "event_id": latest_decision.event_id,
            "created_at": latest_decision.created_at.isoformat(),
            "event_type": getattr(latest_event, "event_type", None) if latest_event else None,
            "entity_id": getattr(latest_event, "entity_id", None) if latest_event else None,
        }

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

    last_window = now - timedelta(days=intake_days)
    new_docs_query = docs_query.filter(LegalDocument.last_modified >= last_window)
    if intake_jurisdiction:
        new_docs_query = new_docs_query.filter(LegalDocument.jurisdiction == intake_jurisdiction)
    if intake_source:
        new_docs_query = new_docs_query.filter(LegalDocument.source_system == intake_source)
    new_docs_total = new_docs_query.count()
    new_docs_by_jurisdiction_rows = new_docs_query.with_entities(
        LegalDocument.jurisdiction,
        func.count(LegalDocument.id)
    ).group_by(LegalDocument.jurisdiction).all()
    new_docs_by_jurisdiction = {
        (row[0] or "unknown"): row[1] for row in new_docs_by_jurisdiction_rows
    }
    new_docs = new_docs_query.order_by(LegalDocument.last_modified.desc()).limit(intake_limit).all()

    oj_total = db.query(func.count(OfficialJournalAct.id)).scalar() or 0
    oj_latest_date = db.query(func.max(OfficialJournalAct.publication_date)).scalar()
    oj_source = db.query(RegulatorySource).filter(
        RegulatorySource.source_key == "eur-lex-oj-act-by-act"
    ).first()
    oj_last_ingested = oj_source.last_ingested_at if oj_source else None

    statuses = None
    if obligation_status:
        statuses = [item.strip().lower() for item in obligation_status.split(",") if item.strip()]

    pending_obligations_query = db.query(RegulatoryObligation, LegalDocument).join(
        LegalDocument, RegulatoryObligation.doc_id == LegalDocument.id
    )
    pending_obligations_query = _apply_scope_filter_to_obligations(pending_obligations_query, scopes, db)
    if statuses:
        pending_obligations_query = pending_obligations_query.filter(RegulatoryObligation.status.in_(statuses))
    else:
        pending_obligations_query = pending_obligations_query.filter(RegulatoryObligation.status.in_(["draft", "in_review"]))
    pending_obligations_query = pending_obligations_query.order_by(RegulatoryObligation.updated_at.desc())
    pending_obligations_total = pending_obligations_query.count()
    pending_obligations = pending_obligations_query.limit(obligation_limit).all()

    policies_query = db.query(PolicyDocument)
    policies_total = policies_query.count()
    policy_status_rows = policies_query.with_entities(
        PolicyDocument.status,
        func.count(PolicyDocument.id)
    ).group_by(PolicyDocument.status).all()
    policy_by_status = {row[0] or "unknown": row[1] for row in policy_status_rows}
    focus_statuses = ["draft", "in_review"]
    policies_focus = policies_query.filter(
        PolicyDocument.status.in_(focus_statuses)
    ).order_by(PolicyDocument.updated_at.desc()).limit(5).all()

    def _doc_to_dict(doc):
        title = (doc.title or "").strip() or doc.celex or doc.source_reference or "Untitled document"
        return {
            "id": doc.id,
            "celex": doc.celex,
            "title": title,
            "risk_level": doc.risk_level,
            "compliance_domain": doc.compliance_domain,
        }

    def _doc_to_intake_dict(doc):
        title = (doc.title or "").strip() or doc.celex or doc.source_reference or "Untitled document"
        return {
            "id": doc.id,
            "celex": doc.celex,
            "title": title,
            "jurisdiction": doc.jurisdiction,
            "source_system": doc.source_system,
            "publication_date": doc.publication_date.isoformat() if doc.publication_date else None,
            "last_modified": doc.last_modified.isoformat() if doc.last_modified else None,
            "oj_act_identifier": doc.oj_act_identifier,
            "oj_signature_identifier": doc.oj_signature_identifier,
        }

    def _obligation_to_dict(obligation, doc):
        text = (obligation.obligation_text or "").strip()
        summary = text[:180] + ("…" if len(text) > 180 else "")
        title = (doc.title or "").strip() or doc.celex or doc.source_reference or "Untitled document"
        return {
            "id": obligation.id,
            "obligation_id": obligation.obligation_id,
            "status": obligation.status,
            "article_ref": obligation.article_ref,
            "summary": summary,
            "doc_id": doc.id,
            "celex": doc.celex,
            "doc_title": title,
            "updated_at": obligation.updated_at.isoformat() if obligation.updated_at else None,
        }

    def _rule_to_dict(rule):
        return {
            "rule_id": rule.rule_id,
            "name": rule.name,
            "severity": rule.severity,
            "category": rule.category,
        }

    def _policy_to_dict(policy: PolicyDocument):
        return {
            "id": policy.id,
            "policy_id": policy.policy_id,
            "name": policy.name,
            "status": policy.status,
            "owner": policy.owner,
            "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
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
            "latest": latest_decision,
        },
        "reporting": {
            "sar_filed_30d": sar_filed_30d,
            "travel_pending": travel_pending,
            "travel_submitted": travel_submitted,
            "onchain_checks_24h": onchain_checks,
        },
        "policy_summary": {
            "total": policies_total,
            "by_status": policy_by_status,
            "items": [_policy_to_dict(policy) for policy in policies_focus],
        },
        "regulatory_intake": {
            "new_documents": {
                "total_7d": new_docs_total,
                "by_jurisdiction": new_docs_by_jurisdiction,
                "items": [_doc_to_intake_dict(doc) for doc in new_docs],
            },
            "pending_obligations": {
                "total": pending_obligations_total,
                "items": [_obligation_to_dict(obligation, doc) for obligation, doc in pending_obligations],
            },
        },
        "official_journal": {
            "acts_total": oj_total,
            "latest_publication_date": oj_latest_date.isoformat() if oj_latest_date else None,
            "last_ingested_at": oj_last_ingested.isoformat() if oj_last_ingested else None,
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
# AML SCOPE REVIEW
# ============================================================================

@router.get("/aml-scope")
def aml_scope_review(
    jurisdiction: Optional[str] = Query(None),
    scope: Optional[str] = Query(None, description="Comma-separated scope tags: psp,eme,vasp"),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "auditor"])),
):
    """
    AML scope coverage summary for obligations and controls.
    """
    scopes = normalize_scopes(scope)
    base_query = db.query(RegulatoryObligation, LegalDocument).join(
        LegalDocument, RegulatoryObligation.doc_id == LegalDocument.id
    )
    if jurisdiction:
        base_query = base_query.filter(LegalDocument.jurisdiction == jurisdiction)
    base_query = _apply_scope_filter_to_obligations(base_query, scopes, db)

    total_obligations = base_query.count()

    status_rows = db.query(
        RegulatoryObligation.status,
        func.count(RegulatoryObligation.id).label("count"),
    ).join(
        LegalDocument, RegulatoryObligation.doc_id == LegalDocument.id
    )
    if jurisdiction:
        status_rows = status_rows.filter(LegalDocument.jurisdiction == jurisdiction)
    status_rows = _apply_scope_filter_to_obligations(status_rows, scopes, db)
    status_rows = status_rows.group_by(RegulatoryObligation.status).all()
    status_counts = {row.status: row.count for row in status_rows}

    covered_subq = db.query(
        InternalRule.obligation_id.label("obligation_id")
    ).distinct().subquery()
    policy_mapped_subq = db.query(
        InternalRule.obligation_id.label("obligation_id")
    ).filter(InternalRule.policy_section_id.isnot(None)).distinct().subquery()

    covered_count_query = db.query(func.count(RegulatoryObligation.id)).join(
        LegalDocument, RegulatoryObligation.doc_id == LegalDocument.id
    ).join(
        covered_subq, covered_subq.c.obligation_id == RegulatoryObligation.id
    )
    if jurisdiction:
        covered_count_query = covered_count_query.filter(LegalDocument.jurisdiction == jurisdiction)
    covered_count_query = _apply_scope_filter_to_obligations(covered_count_query, scopes, db)
    covered_count = covered_count_query.scalar() or 0

    policy_mapped_query = db.query(func.count(RegulatoryObligation.id)).join(
        LegalDocument, RegulatoryObligation.doc_id == LegalDocument.id
    ).join(
        policy_mapped_subq, policy_mapped_subq.c.obligation_id == RegulatoryObligation.id
    )
    if jurisdiction:
        policy_mapped_query = policy_mapped_query.filter(LegalDocument.jurisdiction == jurisdiction)
    policy_mapped_query = _apply_scope_filter_to_obligations(policy_mapped_query, scopes, db)
    policy_mapped_count = policy_mapped_query.scalar() or 0

    jurisdiction_query = db.query(
        LegalDocument.jurisdiction.label("jurisdiction"),
        func.count(RegulatoryObligation.id).label("total"),
        func.sum(case((RegulatoryObligation.status == "approved", 1), else_=0)).label("approved"),
        func.sum(case((RegulatoryObligation.status == "in_review", 1), else_=0)).label("in_review"),
        func.sum(case((RegulatoryObligation.status == "draft", 1), else_=0)).label("draft"),
        func.sum(case((RegulatoryObligation.status == "rejected", 1), else_=0)).label("rejected"),
        func.sum(case((covered_subq.c.obligation_id.isnot(None), 1), else_=0)).label("covered"),
        func.sum(case((policy_mapped_subq.c.obligation_id.isnot(None), 1), else_=0)).label("policy_mapped"),
    ).join(
        LegalDocument, RegulatoryObligation.doc_id == LegalDocument.id
    ).outerjoin(
        covered_subq, covered_subq.c.obligation_id == RegulatoryObligation.id
    ).outerjoin(
        policy_mapped_subq, policy_mapped_subq.c.obligation_id == RegulatoryObligation.id
    )

    if jurisdiction:
        jurisdiction_query = jurisdiction_query.filter(LegalDocument.jurisdiction == jurisdiction)
    jurisdiction_query = _apply_scope_filter_to_obligations(jurisdiction_query, scopes, db)

    jurisdiction_rows = jurisdiction_query.group_by(LegalDocument.jurisdiction).order_by(
        LegalDocument.jurisdiction.asc()
    ).all()

    by_jurisdiction = []
    for row in jurisdiction_rows:
        total = row.total or 0
        coverage_pct = round((row.covered / total * 100), 2) if total else 0
        policy_pct = round((row.policy_mapped / total * 100), 2) if total else 0
        by_jurisdiction.append(
            {
                "jurisdiction": row.jurisdiction or "unknown",
                "total": total,
                "approved": row.approved or 0,
                "in_review": row.in_review or 0,
                "draft": row.draft or 0,
                "rejected": row.rejected or 0,
                "covered": row.covered or 0,
                "policy_mapped": row.policy_mapped or 0,
                "coverage_pct": coverage_pct,
                "policy_mapping_pct": policy_pct,
            }
        )

    gaps_query = db.query(RegulatoryObligation, LegalDocument).join(
        LegalDocument, RegulatoryObligation.doc_id == LegalDocument.id
    ).outerjoin(
        covered_subq, covered_subq.c.obligation_id == RegulatoryObligation.id
    ).filter(covered_subq.c.obligation_id.is_(None))
    if jurisdiction:
        gaps_query = gaps_query.filter(LegalDocument.jurisdiction == jurisdiction)
    gaps_query = _apply_scope_filter_to_obligations(gaps_query, scopes, db)

    gap_rows = gaps_query.order_by(RegulatoryObligation.updated_at.desc()).limit(limit).all()
    gap_items = []
    for obligation, doc in gap_rows:
        gap_items.append(
            {
                "id": obligation.id,
                "obligation_id": obligation.obligation_id,
                "status": obligation.status,
                "obligation_text": obligation.obligation_text,
                "updated_at": obligation.updated_at.isoformat() if obligation.updated_at else None,
                "document": {
                    "celex": doc.celex,
                    "title": doc.title,
                    "jurisdiction": doc.jurisdiction,
                },
            }
        )

    coverage_pct = round((covered_count / total_obligations * 100), 2) if total_obligations else 0
    policy_mapping_pct = round((policy_mapped_count / total_obligations * 100), 2) if total_obligations else 0

    return {
        "as_of": utc_now().isoformat(),
        "jurisdiction": jurisdiction,
        "scope": scope,
        "total_obligations": total_obligations,
        "status_counts": status_counts,
        "coverage": {
            "covered": covered_count,
            "coverage_pct": coverage_pct,
            "policy_mapped": policy_mapped_count,
            "policy_mapping_pct": policy_mapping_pct,
        },
        "by_jurisdiction": by_jurisdiction,
        "gap_items": gap_items,
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
