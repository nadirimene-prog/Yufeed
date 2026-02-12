"""Findings API — finding-first workbench.

Provides CRUD, triage actions, close, and escalate-to-case for normalized
compliance signals.
"""

import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.database import get_db
from src.auth.dependencies import require_any_role, CurrentUser
from src.audit.recorders import record_event
from src.models.finding_models import Finding, FindingStatus
from src.models.transaction_models import Case
from src.schemas.finding_schemas import (
    FindingCreate,
    FindingUpdate,
    FindingCloseRequest,
    FindingResponse,
    EscalateToCaseRequest,
    CaseLiteResponse,
)
from src.services.finding_service import FindingService
from src.tenancy.queries import get_tenant_filtered_query
from src.utils.time import utc_now


router = APIRouter(prefix="/api/findings", tags=["findings"])

_ALLOWED_ROLES = ["admin", "compliance", "aml_officer"]


# ---------------------------------------------------------------------------
# LIST
# ---------------------------------------------------------------------------


@router.get("", response_model=List[FindingResponse])
def list_findings(
    status: Optional[str] = Query(None, description="Comma-separated statuses"),
    finding_type: Optional[str] = None,
    severity: Optional[str] = Query(None, description="Comma-separated severities"),
    assigned_to: Optional[str] = None,
    from_date: Optional[datetime] = Query(None, description="created_at >="),
    to_date: Optional[datetime] = Query(None, description="created_at <="),
    q: Optional[str] = Query(None, description="Search in title and summary"),
    sort: Optional[str] = Query(
        "created_at_desc",
        description="Sort: created_at_asc, created_at_desc, severity_desc",
    ),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(_ALLOWED_ROLES)),
):
    """List findings with filtering, search and sorting."""
    q_filter = get_tenant_filtered_query(Finding, db)

    # --- status ---
    if status:
        statuses = [s.strip().lower() for s in status.split(",") if s.strip()]
        if statuses:
            q_filter = q_filter.filter(Finding.status.in_(statuses))

    # --- finding_type ---
    if finding_type:
        q_filter = q_filter.filter(Finding.finding_type == finding_type)

    # --- severity ---
    if severity:
        severities = [s.strip().lower() for s in severity.split(",") if s.strip()]
        if severities:
            q_filter = q_filter.filter(Finding.severity.in_(severities))

    # --- assignee ---
    if assigned_to:
        q_filter = q_filter.filter(Finding.assigned_to == assigned_to)

    # --- date range ---
    if from_date:
        q_filter = q_filter.filter(Finding.created_at >= from_date)
    if to_date:
        q_filter = q_filter.filter(Finding.created_at <= to_date)

    # --- free-text search ---
    if q:
        pattern = f"%{q}%"
        q_filter = q_filter.filter(
            or_(
                Finding.title.ilike(pattern),
                Finding.summary.ilike(pattern),
            )
        )

    # --- sorting ---
    if sort == "created_at_asc":
        q_filter = q_filter.order_by(Finding.created_at.asc())
    elif sort == "severity_desc":
        q_filter = q_filter.order_by(Finding.severity.desc(), Finding.created_at.desc())
    else:
        q_filter = q_filter.order_by(Finding.created_at.desc())

    items = q_filter.offset(offset).limit(limit).all()
    return items


# ---------------------------------------------------------------------------
# GET
# ---------------------------------------------------------------------------


@router.get("/{finding_id}", response_model=FindingResponse)
def get_finding(
    finding_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(_ALLOWED_ROLES)),
):
    """Get a single finding by ID."""
    finding = get_tenant_filtered_query(Finding, db).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    return finding


# ---------------------------------------------------------------------------
# CREATE (idempotent upsert via FindingService)
# ---------------------------------------------------------------------------


@router.post("", response_model=FindingResponse, status_code=201)
def create_finding(
    payload: FindingCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(_ALLOWED_ROLES)),
):
    """Create a finding (idempotent by fingerprint — returns existing on match)."""
    svc = FindingService(db)
    finding, is_new = svc.create_or_update_finding(
        tenant_id=current_user.tenant_id,
        finding_type=payload.finding_type,
        fingerprint=payload.fingerprint,
        severity=payload.severity,
        title=payload.title,
        summary=payload.summary,
        source_refs=payload.source_refs,
        explainability=payload.explainability,
        assigned_to=payload.assigned_to,
        sla_due_at=payload.sla_due_at,
    )
    db.commit()
    db.refresh(finding)
    return finding


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------


@router.patch("/{finding_id}", response_model=FindingResponse)
def update_finding(
    finding_id: int,
    payload: FindingUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(_ALLOWED_ROLES)),
):
    """Partially update a finding (assign, triage, change severity, etc.)."""
    finding = get_tenant_filtered_query(Finding, db).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    changes = {}
    if payload.status is not None:
        changes["status"] = payload.status.lower().strip()
        finding.status = changes["status"]
    if payload.severity is not None:
        changes["severity"] = payload.severity.lower().strip()
        finding.severity = changes["severity"]
    if payload.assigned_to is not None:
        changes["assigned_to"] = payload.assigned_to
        finding.assigned_to = payload.assigned_to
    if payload.title is not None:
        changes["title"] = payload.title
        finding.title = payload.title
    if payload.summary is not None:
        changes["summary"] = payload.summary
        finding.summary = payload.summary
    if payload.sla_due_at is not None:
        changes["sla_due_at"] = str(payload.sla_due_at)
        finding.sla_due_at = payload.sla_due_at

    finding.updated_at = utc_now()

    record_event(
        db,
        event_type="finding.updated",
        entity_type="finding",
        entity_id=str(finding.id),
        tenant_id=finding.tenant_id,
        payload={"changes": changes, "actor": current_user.user_id},
    )

    db.commit()
    db.refresh(finding)
    return finding


# ---------------------------------------------------------------------------
# CLOSE
# ---------------------------------------------------------------------------


@router.post("/{finding_id}/close", response_model=FindingResponse)
def close_finding(
    finding_id: int,
    payload: FindingCloseRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(_ALLOWED_ROLES)),
):
    """Close a finding with a reason (e.g. false_positive, resolved, duplicate)."""
    finding = get_tenant_filtered_query(Finding, db).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    if finding.status == FindingStatus.closed.value:
        raise HTTPException(status_code=409, detail="Finding is already closed")

    svc = FindingService(db)
    svc.close_finding(finding, payload.closed_reason, payload.closed_comment, current_user.user_id)

    db.commit()
    db.refresh(finding)
    return finding


# ---------------------------------------------------------------------------
# ESCALATE → Case
# ---------------------------------------------------------------------------


@router.post("/{finding_id}/escalate", response_model=CaseLiteResponse)
def escalate_finding_to_case(
    finding_id: int,
    payload: EscalateToCaseRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(_ALLOWED_ROLES)),
):
    """Escalate a finding into a Case (new or existing)."""
    finding = get_tenant_filtered_query(Finding, db).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    # Idempotency: if already linked to a case, return the first one
    if finding.cases:
        return finding.cases[0]

    # Link to existing case or create a new one
    if payload.existing_case_id:
        case = (
            get_tenant_filtered_query(Case, db)
            .filter(Case.case_id == payload.existing_case_id)
            .first()
        )
        if not case:
            raise HTTPException(status_code=404, detail="Existing case not found")
    else:
        case_public_id = f"CAS-{utc_now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        case = Case(
            tenant_id=current_user.tenant_id,
            case_id=case_public_id,
            case_type=payload.case_type or "investigation",
            status="open",
            priority=(payload.priority or "medium").lower(),
            assigned_to=current_user.email,
            title=payload.title or finding.title or f"Case for finding #{finding.id}",
            description=payload.description or finding.summary,
            opened_at=utc_now(),
        )
        db.add(case)

    case.findings.append(finding)
    finding.status = FindingStatus.escalated.value
    finding.updated_at = utc_now()

    record_event(
        db,
        event_type="finding.escalated",
        entity_type="finding",
        entity_id=str(finding.id),
        tenant_id=finding.tenant_id,
        payload={
            "case_id": case.case_id if hasattr(case, "case_id") else None,
            "actor": current_user.user_id,
        },
    )
    record_event(
        db,
        event_type="case.created" if not payload.existing_case_id else "case.finding_linked",
        entity_type="case",
        entity_id=case.case_id if hasattr(case, "case_id") else str(case.id),
        tenant_id=current_user.tenant_id,
        payload={"finding_id": finding.id},
    )

    db.commit()
    db.refresh(case)
    return case
