"""
Ingestion Status API Endpoints

Provides visibility into the ingestion pipeline status, history, and failed items.
"""

from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from src.database import get_db
from src.auth.dependencies import require_any_role, CurrentUser
from src.models.compliance_workflow import (
    RegulatorySource,
    IngestionRun,
    FailedIngestionItem,
)
from src.models.models import LegalDocument
from src.utils.time import utc_now


router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])


@router.get("/status")
def get_ingestion_status(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    """
    Get overall ingestion pipeline status.

    Returns summary of recent activity, sources, and health indicators.
    """
    # Get active sources
    sources = db.query(RegulatorySource).filter(RegulatorySource.is_active == True).all()

    # Get recent run stats (last 7 days)
    seven_days_ago = utc_now() - timedelta(days=7)
    recent_runs = db.query(IngestionRun).filter(IngestionRun.started_at >= seven_days_ago).all()

    total_runs = len(recent_runs)
    successful_runs = len([r for r in recent_runs if r.status == "completed"])
    failed_runs = len([r for r in recent_runs if r.status == "failed"])
    partial_runs = len([r for r in recent_runs if r.status == "partial"])

    total_new = sum(r.items_new or 0 for r in recent_runs)
    total_updated = sum(r.items_updated or 0 for r in recent_runs)
    total_seen = sum(r.items_seen or 0 for r in recent_runs)

    # Get DLQ stats
    dlq_pending = (
        db.query(func.count(FailedIngestionItem.id))
        .filter(FailedIngestionItem.status == "pending")
        .scalar()
        or 0
    )

    dlq_exhausted = (
        db.query(func.count(FailedIngestionItem.id))
        .filter(FailedIngestionItem.status == "exhausted")
        .scalar()
        or 0
    )

    # Get document stats
    total_docs = db.query(func.count(LegalDocument.id)).scalar() or 0
    docs_with_content = (
        db.query(func.count(LegalDocument.id))
        .filter(
            LegalDocument.full_text.isnot(None),
            LegalDocument.full_text != "",
        )
        .scalar()
        or 0
    )

    docs_analyzed = (
        db.query(func.count(LegalDocument.id))
        .filter(LegalDocument.analyzed_at.isnot(None))
        .scalar()
        or 0
    )

    # Determine overall health
    if failed_runs > successful_runs:
        health = "unhealthy"
    elif dlq_pending > 10 or dlq_exhausted > 5:
        health = "degraded"
    elif partial_runs > successful_runs:
        health = "degraded"
    else:
        health = "healthy"

    return {
        "health": health,
        "timestamp": utc_now().isoformat(),
        "sources": {
            "total": len(sources),
            "active": len([s for s in sources if s.is_active]),
            "items": [
                {
                    "source_key": s.source_key,
                    "name": s.name,
                    "jurisdiction": s.jurisdiction,
                    "last_ingested_at": (
                        s.last_ingested_at.isoformat() if s.last_ingested_at else None
                    ),
                }
                for s in sources
            ],
        },
        "recent_activity": {
            "period_days": 7,
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "partial_runs": partial_runs,
            "documents_seen": total_seen,
            "documents_new": total_new,
            "documents_updated": total_updated,
        },
        "dead_letter_queue": {
            "pending": dlq_pending,
            "exhausted": dlq_exhausted,
        },
        "documents": {
            "total": total_docs,
            "with_content": docs_with_content,
            "analyzed": docs_analyzed,
            "content_coverage": (
                round(docs_with_content / total_docs * 100, 1) if total_docs > 0 else 0
            ),
            "analysis_coverage": (
                round(docs_analyzed / total_docs * 100, 1) if total_docs > 0 else 0
            ),
        },
    }


@router.get("/runs")
def list_ingestion_runs(
    source_key: Optional[str] = Query(None, description="Filter by source key"),
    status: Optional[str] = Query(None, description="Filter by status"),
    days: int = Query(30, ge=1, le=365, description="Days to look back"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    """
    List recent ingestion runs with optional filters.
    """
    cutoff = utc_now() - timedelta(days=days)

    query = (
        db.query(IngestionRun, RegulatorySource)
        .join(RegulatorySource, IngestionRun.source_id == RegulatorySource.id)
        .filter(IngestionRun.started_at >= cutoff)
    )

    if source_key:
        query = query.filter(RegulatorySource.source_key == source_key)

    if status:
        query = query.filter(IngestionRun.status == status)

    total = query.count()
    rows = query.order_by(desc(IngestionRun.started_at)).offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "id": run.id,
                "source_key": source.source_key,
                "source_name": source.name,
                "status": run.status,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "duration_seconds": (
                    (run.completed_at - run.started_at).total_seconds()
                    if run.completed_at and run.started_at
                    else None
                ),
                "items_seen": run.items_seen,
                "items_new": run.items_new,
                "items_updated": run.items_updated,
                "error_count": len(run.errors_json) if run.errors_json else 0,
            }
            for run, source in rows
        ],
    }


@router.get("/runs/{run_id}")
def get_ingestion_run(
    run_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    """
    Get detailed information about a specific ingestion run.
    """
    row = (
        db.query(IngestionRun, RegulatorySource)
        .join(RegulatorySource, IngestionRun.source_id == RegulatorySource.id)
        .filter(IngestionRun.id == run_id)
        .first()
    )

    if not row:
        raise HTTPException(status_code=404, detail="Ingestion run not found")

    run, source = row

    return {
        "id": run.id,
        "source_key": source.source_key,
        "source_name": source.name,
        "jurisdiction": source.jurisdiction,
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "duration_seconds": (
            (run.completed_at - run.started_at).total_seconds()
            if run.completed_at and run.started_at
            else None
        ),
        "items_seen": run.items_seen,
        "items_new": run.items_new,
        "items_updated": run.items_updated,
        "errors": run.errors_json or [],
    }


@router.get("/failed")
def list_failed_items(
    status: Optional[str] = Query(
        None, description="Filter by status: pending, retrying, exhausted, resolved"
    ),
    source_key: Optional[str] = Query(None, description="Filter by source key"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    """
    List failed ingestion items in the dead letter queue.
    """
    query = db.query(FailedIngestionItem)

    if status:
        query = query.filter(FailedIngestionItem.status == status)

    if source_key:
        query = query.filter(FailedIngestionItem.source_key == source_key)

    total = query.count()
    items = query.order_by(desc(FailedIngestionItem.created_at)).offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "id": item.id,
                "celex": item.celex,
                "source_key": item.source_key,
                "status": item.status,
                "retry_count": item.retry_count,
                "max_retries": item.max_retries,
                "error_message": item.error_message[:500] if item.error_message else None,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "last_retry_at": item.last_retry_at.isoformat() if item.last_retry_at else None,
            }
            for item in items
        ],
    }


@router.get("/failed/{item_id}")
def get_failed_item(
    item_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    """
    Get detailed information about a failed ingestion item.
    """
    item = db.query(FailedIngestionItem).filter(FailedIngestionItem.id == item_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Failed item not found")

    return {
        "id": item.id,
        "celex": item.celex,
        "source_key": item.source_key,
        "status": item.status,
        "retry_count": item.retry_count,
        "max_retries": item.max_retries,
        "error_message": item.error_message,
        "error_traceback": item.error_traceback,
        "entry_json": item.entry_json,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "last_retry_at": item.last_retry_at.isoformat() if item.last_retry_at else None,
        "resolved_at": item.resolved_at.isoformat() if item.resolved_at else None,
        "resolved_doc_id": item.resolved_doc_id,
    }


@router.post("/failed/{item_id}/retry")
def retry_failed_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance"])),
):
    """
    Manually trigger a retry for a failed ingestion item.
    """
    item = db.query(FailedIngestionItem).filter(FailedIngestionItem.id == item_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Failed item not found")

    if item.status == "resolved":
        raise HTTPException(status_code=400, detail="Item already resolved")

    if item.status == "retrying":
        raise HTTPException(status_code=400, detail="Item already being retried")

    # Reset status to pending for retry
    item.status = "pending"
    item.retry_count = max(0, item.retry_count - 1)  # Give it another chance
    db.commit()

    # Trigger async retry
    from src.worker import retry_failed_ingestion_items

    retry_failed_ingestion_items.delay(limit=1)

    return {
        "message": "Retry triggered",
        "item_id": item.id,
        "celex": item.celex,
    }


@router.delete("/failed/{item_id}")
def delete_failed_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin"])),
):
    """
    Delete a failed ingestion item from the DLQ.

    Only admins can permanently delete items.
    """
    item = db.query(FailedIngestionItem).filter(FailedIngestionItem.id == item_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Failed item not found")

    db.delete(item)
    db.commit()

    return {
        "message": "Item deleted",
        "item_id": item_id,
    }


@router.get("/sources")
def list_sources(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "auditor"])),
):
    """
    List all configured ingestion sources.
    """
    sources = db.query(RegulatorySource).order_by(RegulatorySource.name).all()

    return {
        "total": len(sources),
        "items": [
            {
                "id": s.id,
                "source_key": s.source_key,
                "name": s.name,
                "jurisdiction": s.jurisdiction,
                "language": s.language,
                "source_type": s.source_type,
                "base_url": s.base_url,
                "schedule": s.schedule,
                "is_active": s.is_active,
                "last_ingested_at": s.last_ingested_at.isoformat() if s.last_ingested_at else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in sources
        ],
    }


@router.patch("/sources/{source_key}/toggle")
def toggle_source(
    source_key: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin"])),
):
    """
    Toggle a source's active status.
    """
    source = db.query(RegulatorySource).filter(RegulatorySource.source_key == source_key).first()

    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    source.is_active = not source.is_active
    source.updated_at = utc_now()
    db.commit()

    return {
        "source_key": source.source_key,
        "is_active": source.is_active,
        "message": f"Source {'activated' if source.is_active else 'deactivated'}",
    }


@router.get("/compliance/metrics")
def get_compliance_metrics(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "auditor"])),
):
    """
    Get comprehensive compliance metrics.

    Returns aggregated statistics on:
    - Obligations by status and deadline
    - Document analysis coverage
    - Policy linkage
    - Risk coverage
    """
    from datetime import timedelta
    from src.models.compliance_workflow import (
        RegulatoryObligation,
        PolicyDocument,
        InternalRule,
        RiskEntry,
        ObligationRiskLink,
    )

    now = utc_now()

    # Obligation metrics
    total_obligations = db.query(func.count(RegulatoryObligation.id)).scalar() or 0

    obligations_by_status = dict(
        db.query(RegulatoryObligation.status, func.count(RegulatoryObligation.id))
        .group_by(RegulatoryObligation.status)
        .all()
    )

    obligations_with_deadline = (
        db.query(func.count(RegulatoryObligation.id))
        .filter(RegulatoryObligation.effective_date.isnot(None))
        .scalar()
        or 0
    )

    # Deadline breakdown
    overdue = (
        db.query(func.count(RegulatoryObligation.id))
        .filter(
            RegulatoryObligation.effective_date < now,
            RegulatoryObligation.status.in_(["draft", "in_review", "approved"]),
        )
        .scalar()
        or 0
    )

    due_7_days = (
        db.query(func.count(RegulatoryObligation.id))
        .filter(
            RegulatoryObligation.effective_date >= now,
            RegulatoryObligation.effective_date < now + timedelta(days=7),
            RegulatoryObligation.status.in_(["draft", "in_review", "approved"]),
        )
        .scalar()
        or 0
    )

    due_30_days = (
        db.query(func.count(RegulatoryObligation.id))
        .filter(
            RegulatoryObligation.effective_date >= now,
            RegulatoryObligation.effective_date < now + timedelta(days=30),
            RegulatoryObligation.status.in_(["draft", "in_review", "approved"]),
        )
        .scalar()
        or 0
    )

    # Policy linkage
    obligations_linked_to_policy = (
        db.query(func.count(RegulatoryObligation.id))
        .filter(RegulatoryObligation.linked_policy_id.isnot(None))
        .scalar()
        or 0
    )

    # Document metrics
    total_docs = db.query(func.count(LegalDocument.id)).scalar() or 0
    docs_analyzed = (
        db.query(func.count(LegalDocument.id))
        .filter(LegalDocument.analyzed_at.isnot(None))
        .scalar()
        or 0
    )
    docs_with_obligations = (
        db.query(func.count(func.distinct(RegulatoryObligation.doc_id))).scalar() or 0
    )
    docs_with_content = (
        db.query(func.count(LegalDocument.id))
        .filter(
            LegalDocument.full_text.isnot(None),
            LegalDocument.full_text != "",
        )
        .scalar()
        or 0
    )

    # Policy metrics
    total_policies = db.query(func.count(PolicyDocument.id)).scalar() or 0
    active_policies = (
        db.query(func.count(PolicyDocument.id)).filter(PolicyDocument.status == "active").scalar()
        or 0
    )

    # Internal rules metrics
    total_internal_rules = db.query(func.count(InternalRule.id)).scalar() or 0
    internal_rules_by_status = dict(
        db.query(InternalRule.status, func.count(InternalRule.id))
        .group_by(InternalRule.status)
        .all()
    )

    # Risk metrics
    total_risk_entries = db.query(func.count(RiskEntry.id)).scalar() or 0
    obligations_with_risk_links = (
        db.query(func.count(func.distinct(ObligationRiskLink.obligation_id))).scalar() or 0
    )

    # DLQ metrics
    dlq_pending = (
        db.query(func.count(FailedIngestionItem.id))
        .filter(FailedIngestionItem.status == "pending")
        .scalar()
        or 0
    )
    dlq_analysis_pending = (
        db.query(func.count(FailedIngestionItem.id))
        .filter(
            FailedIngestionItem.status == "pending",
            FailedIngestionItem.source_key == "ai_analysis",
        )
        .scalar()
        or 0
    )

    return {
        "timestamp": now.isoformat(),
        "obligations": {
            "total": total_obligations,
            "by_status": {
                "draft": obligations_by_status.get("draft", 0),
                "in_review": obligations_by_status.get("in_review", 0),
                "approved": obligations_by_status.get("approved", 0),
                "rejected": obligations_by_status.get("rejected", 0),
                "deprecated": obligations_by_status.get("deprecated", 0),
            },
            "with_deadline": obligations_with_deadline,
            "linked_to_policy": obligations_linked_to_policy,
            "with_risk_links": obligations_with_risk_links,
            "policy_linkage_rate": (
                round(obligations_linked_to_policy / total_obligations * 100, 1)
                if total_obligations > 0
                else 0
            ),
        },
        "deadlines": {
            "overdue": overdue,
            "due_7_days": due_7_days,
            "due_30_days": due_30_days,
        },
        "documents": {
            "total": total_docs,
            "analyzed": docs_analyzed,
            "with_obligations": docs_with_obligations,
            "with_content": docs_with_content,
            "analysis_rate": round(docs_analyzed / total_docs * 100, 1) if total_docs > 0 else 0,
            "obligation_coverage": (
                round(docs_with_obligations / total_docs * 100, 1) if total_docs > 0 else 0
            ),
        },
        "policies": {
            "total": total_policies,
            "active": active_policies,
        },
        "internal_rules": {
            "total": total_internal_rules,
            "by_status": internal_rules_by_status,
        },
        "risks": {
            "total_entries": total_risk_entries,
            "obligations_covered": obligations_with_risk_links,
        },
        "dlq": {
            "pending_total": dlq_pending,
            "pending_analysis": dlq_analysis_pending,
        },
    }
