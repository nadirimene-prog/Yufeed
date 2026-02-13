"""
AML Scope Analysis API
AML scope coverage analysis and regulatory coverage reporting.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case, select
import sqlalchemy as sa
from typing import Optional
from datetime import datetime, timezone

from src.database import get_db
from src.models.transaction_models import MonitoringRule
from src.models.models import LegalDocument
from src.models.compliance_workflow import RegulatoryObligation, InternalRule
from src.auth.dependencies import require_any_role, CurrentUser
from src.compliance.scope import normalize_scopes, scope_keywords
from sqlalchemy.dialects import postgresql


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


router = APIRouter(prefix="/reporting", tags=["scope-analysis"])


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
    ).join(LegalDocument, RegulatoryObligation.doc_id == LegalDocument.id)
    if jurisdiction:
        status_rows = status_rows.filter(LegalDocument.jurisdiction == jurisdiction)
    status_rows = _apply_scope_filter_to_obligations(status_rows, scopes, db)
    status_rows = status_rows.group_by(RegulatoryObligation.status).all()
    status_counts = {row.status: row.count for row in status_rows}

    covered_subq = db.query(InternalRule.obligation_id.label("obligation_id")).distinct().subquery()
    policy_mapped_subq = (
        db.query(InternalRule.obligation_id.label("obligation_id"))
        .filter(InternalRule.policy_section_id.isnot(None))
        .distinct()
        .subquery()
    )

    covered_count_query = (
        db.query(func.count(RegulatoryObligation.id))
        .join(LegalDocument, RegulatoryObligation.doc_id == LegalDocument.id)
        .join(covered_subq, covered_subq.c.obligation_id == RegulatoryObligation.id)
    )
    if jurisdiction:
        covered_count_query = covered_count_query.filter(LegalDocument.jurisdiction == jurisdiction)
    covered_count_query = _apply_scope_filter_to_obligations(covered_count_query, scopes, db)
    covered_count = covered_count_query.scalar() or 0

    policy_mapped_query = (
        db.query(func.count(RegulatoryObligation.id))
        .join(LegalDocument, RegulatoryObligation.doc_id == LegalDocument.id)
        .join(policy_mapped_subq, policy_mapped_subq.c.obligation_id == RegulatoryObligation.id)
    )
    if jurisdiction:
        policy_mapped_query = policy_mapped_query.filter(LegalDocument.jurisdiction == jurisdiction)
    policy_mapped_query = _apply_scope_filter_to_obligations(policy_mapped_query, scopes, db)
    policy_mapped_count = policy_mapped_query.scalar() or 0

    jurisdiction_query = (
        db.query(
            LegalDocument.jurisdiction.label("jurisdiction"),
            func.count(RegulatoryObligation.id).label("total"),
            func.sum(case((RegulatoryObligation.status == "approved", 1), else_=0)).label(
                "approved"
            ),
            func.sum(case((RegulatoryObligation.status == "in_review", 1), else_=0)).label(
                "in_review"
            ),
            func.sum(case((RegulatoryObligation.status == "draft", 1), else_=0)).label("draft"),
            func.sum(case((RegulatoryObligation.status == "rejected", 1), else_=0)).label(
                "rejected"
            ),
            func.sum(case((covered_subq.c.obligation_id.isnot(None), 1), else_=0)).label("covered"),
            func.sum(case((policy_mapped_subq.c.obligation_id.isnot(None), 1), else_=0)).label(
                "policy_mapped"
            ),
        )
        .join(LegalDocument, RegulatoryObligation.doc_id == LegalDocument.id)
        .outerjoin(covered_subq, covered_subq.c.obligation_id == RegulatoryObligation.id)
        .outerjoin(
            policy_mapped_subq, policy_mapped_subq.c.obligation_id == RegulatoryObligation.id
        )
    )

    if jurisdiction:
        jurisdiction_query = jurisdiction_query.filter(LegalDocument.jurisdiction == jurisdiction)
    jurisdiction_query = _apply_scope_filter_to_obligations(jurisdiction_query, scopes, db)

    jurisdiction_rows = (
        jurisdiction_query.group_by(LegalDocument.jurisdiction)
        .order_by(LegalDocument.jurisdiction.asc())
        .all()
    )

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

    gaps_query = (
        db.query(RegulatoryObligation, LegalDocument)
        .join(LegalDocument, RegulatoryObligation.doc_id == LegalDocument.id)
        .outerjoin(covered_subq, covered_subq.c.obligation_id == RegulatoryObligation.id)
        .filter(covered_subq.c.obligation_id.is_(None))
    )
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
    policy_mapping_pct = (
        round((policy_mapped_count / total_obligations * 100), 2) if total_obligations else 0
    )

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


@router.get("/regulatory/coverage")
def get_regulatory_coverage_report(db: Session = Depends(get_db)):
    """
    Report on regulatory coverage and compliance monitoring.
    """
    # Total regulations
    total_regulations = db.query(func.count(LegalDocument.id)).scalar() or 0

    # Regulations with monitoring rules
    regs_with_rules = (
        db.query(func.count(func.distinct(MonitoringRule.regulatory_source_id)))
        .filter(MonitoringRule.regulatory_source_id.isnot(None))
        .scalar()
        or 0
    )

    # Coverage by domain
    by_domain = (
        db.query(LegalDocument.compliance_domain, func.count(LegalDocument.id).label("count"))
        .group_by(LegalDocument.compliance_domain)
        .all()
    )

    # Rules by regulation
    rules_per_reg = (
        db.query(
            MonitoringRule.regulatory_source_id, func.count(MonitoringRule.id).label("rule_count")
        )
        .filter(MonitoringRule.regulatory_source_id.isnot(None))
        .group_by(MonitoringRule.regulatory_source_id)
        .all()
    )

    return {
        "total_regulations_monitored": total_regulations,
        "regulations_with_rules": regs_with_rules,
        "coverage_rate": (
            round(regs_with_rules / total_regulations * 100, 2) if total_regulations > 0 else 0
        ),
        "by_compliance_domain": {
            row.compliance_domain or "uncategorized": row.count for row in by_domain
        },
        "average_rules_per_regulation": (
            round(sum(r.rule_count for r in rules_per_reg) / len(rules_per_reg), 2)
            if rules_per_reg
            else 0
        ),
    }
