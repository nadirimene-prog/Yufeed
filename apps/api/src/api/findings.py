import hashlib
import uuid
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.database import get_db
from src.auth.dependencies import require_any_role, CurrentUser
from src.models.finding_models import Finding, FindingStatus
from src.models.transaction_models import Case
from src.schemas.finding_schemas import (
    FindingCreate,
    FindingUpdate,
    FindingResponse,
    EscalateToCaseRequest,
    CaseLiteResponse,
)
from src.utils.time import utc_now


router = APIRouter(prefix="/api/findings", tags=["findings"])


def _hash_fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:128]


@router.get("", response_model=List[FindingResponse])
def list_findings(
    status: Optional[str] = Query(None, description="Comma-separated statuses"),
    finding_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    q = db.query(Finding)

    statuses = None
    if status:
        statuses = [s.strip().lower() for s in status.split(",") if s.strip()]
    if statuses:
        q = q.filter(Finding.status.in_(statuses))
    if finding_type:
        q = q.filter(Finding.finding_type == finding_type)

    # Tenant isolation is enforced by middleware/context in other parts of the app,
    # but Findings table is explicitly tenant-scoped for safety.
    q = q.filter(Finding.tenant_id == current_user.tenant_id)

    items = q.order_by(Finding.created_at.desc()).offset(offset).limit(limit).all()
    return items


@router.get("/{finding_id}", response_model=FindingResponse)
def get_finding(
    finding_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    finding = (
        db.query(Finding)
        .filter(Finding.id == finding_id, Finding.tenant_id == current_user.tenant_id)
        .first()
    )
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    return finding


@router.post("", response_model=FindingResponse)
def create_finding(
    payload: FindingCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    fingerprint = payload.fingerprint
    if len(fingerprint) < 8:
        # allow callers to pass a raw fingerprint key, we hash it to a stable length
        fingerprint = _hash_fingerprint(f"{current_user.tenant_id}:{fingerprint}")
    elif len(fingerprint) > 128:
        fingerprint = fingerprint[:128]

    finding = Finding(
        tenant_id=current_user.tenant_id,
        finding_type=payload.finding_type,
        severity=(payload.severity or "").lower() or None,
        status=(payload.status or FindingStatus.new.value).lower(),
        title=payload.title,
        summary=payload.summary,
        source_refs_json=payload.source_refs,
        explainability_json=payload.explainability,
        assigned_to=payload.assigned_to,
        sla_due_at=payload.sla_due_at,
        fingerprint=fingerprint,
    )

    db.add(finding)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        # Unique constraint hit => return existing finding
        existing = (
            db.query(Finding)
            .filter(Finding.tenant_id == current_user.tenant_id, Finding.fingerprint == fingerprint)
            .first()
        )
        if existing:
            return existing
        raise HTTPException(status_code=400, detail=f"Failed to create finding: {exc}")

    db.refresh(finding)
    return finding


@router.patch("/{finding_id}", response_model=FindingResponse)
def update_finding(
    finding_id: int,
    payload: FindingUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    finding = (
        db.query(Finding)
        .filter(Finding.id == finding_id, Finding.tenant_id == current_user.tenant_id)
        .first()
    )
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    if payload.status is not None:
        finding.status = payload.status.lower().strip()
    if payload.assigned_to is not None:
        finding.assigned_to = payload.assigned_to
    if payload.title is not None:
        finding.title = payload.title
    if payload.summary is not None:
        finding.summary = payload.summary
    if payload.sla_due_at is not None:
        finding.sla_due_at = payload.sla_due_at
    finding.updated_at = utc_now()

    db.commit()
    db.refresh(finding)
    return finding


@router.post("/{finding_id}/escalate", response_model=CaseLiteResponse)
def escalate_finding_to_case(
    finding_id: int,
    payload: EscalateToCaseRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    finding = (
        db.query(Finding)
        .filter(Finding.id == finding_id, Finding.tenant_id == current_user.tenant_id)
        .first()
    )
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    # Idempotency: if already linked to a case, return the first one
    if finding.cases:
        return finding.cases[0]

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

    # Link
    case.findings.append(finding)
    finding.status = FindingStatus.escalated.value
    finding.updated_at = utc_now()

    db.add(case)
    db.commit()
    db.refresh(case)
    return case
