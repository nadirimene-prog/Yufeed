"""
Compliance Dashboard API
Comprehensive compliance reporting dashboards and analytics.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, select
import sqlalchemy as sa
from typing import Optional
from datetime import datetime, timedelta, timezone

from src.database import get_db
from src.models.transaction_models import (
    Transaction, Alert, Case, MonitoringRule, UserRiskProfile
)
from src.models.travel_rule import TravelRuleRequestRecord
from src.models.models import LegalDocument
from src.models.compliance_workflow import RegulatoryObligation, PolicyDocument, InternalRule, OfficialJournalAct, RegulatorySource
from src.audit.models import EventRecord, DecisionRecord
from src.auth.dependencies import require_any_role, CurrentUser
from src.compliance.scope import normalize_scopes, scope_keywords
from sqlalchemy.dialects import postgresql


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


router = APIRouter(prefix="/api/reporting", tags=["compliance-dashboard"])


def _apply_scope_filter_to_docs(query, scopes: list[str], db: Session):
    """Apply scope filter to LegalDocument query."""
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
    """Apply scope filter to RegulatoryObligation query."""
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

    total_rules = db.query(func.count(MonitoringRule.id)).scalar() or 1

    recent_updates = db.query(LegalDocument).filter(
        LegalDocument.last_modified >= date_from
    ).count()

    # Risk metrics
    high_risk_users = db.query(func.count(UserRiskProfile.id)).filter(
        UserRiskProfile.risk_level.in_(['high', 'critical'])
    ).scalar() or 0

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
    scope_doc_ids_select = select(scope_doc_ids_subq.c.id)

    total_docs = docs_query.count()
    rules_total = db.query(func.count(MonitoringRule.id)).scalar() or 0
    rules_with_celex = db.query(func.count(MonitoringRule.id)).filter(
        MonitoringRule.regulatory_source_id.isnot(None)
    ).scalar() or 0
    celex_covered = db.query(func.count(func.distinct(MonitoringRule.regulatory_source_id))).filter(
        MonitoringRule.regulatory_source_id.isnot(None),
        MonitoringRule.regulatory_source_id.in_(scope_doc_ids_select),
    ).scalar() or 0

    celex_coverage_pct = round((celex_covered / total_docs * 100), 2) if total_docs > 0 else 0
    rules_coverage_pct = round((rules_with_celex / rules_total * 100), 2) if rules_total > 0 else 0

    mapped_ids_subq = db.query(MonitoringRule.regulatory_source_id).filter(
        MonitoringRule.regulatory_source_id.isnot(None)
    ).subquery()
    mapped_ids_select = select(mapped_ids_subq.c.regulatory_source_id)

    uncovered_docs = docs_query.filter(
        ~LegalDocument.id.in_(mapped_ids_select)
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
