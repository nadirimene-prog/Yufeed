"""Case Decisions API — governance workflow for case outcomes.

Nested under ``/api/cases/{case_id}/decisions``.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.auth.dependencies import require_any_role, CurrentUser
from src.models.case_decision import CaseDecision
from src.models.transaction_models import Case
from src.schemas.case_decision_schemas import (
    CaseDecisionCreate,
    CaseDecisionSubmit,
    CaseDecisionApprove,
    CaseDecisionReject,
    CaseDecisionResponse,
)
from src.services.case_decision_service import CaseDecisionService
from src.tenancy.queries import get_tenant_filtered_query


router = APIRouter(prefix="/api/cases/{case_id}/decisions", tags=["case-decisions"])

_WRITE_ROLES = ["admin", "compliance", "aml_officer"]
_APPROVE_ROLES = ["admin", "compliance"]


def _resolve_case_pk(case_id: str, tenant_id: str, db: Session) -> int:
    """Resolve the public ``case_id`` string to the integer PK."""
    case = get_tenant_filtered_query(Case, db).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case.id


# ---------------------------------------------------------------------------
# CREATE draft
# ---------------------------------------------------------------------------


@router.post("", response_model=CaseDecisionResponse, status_code=201)
def create_decision(
    case_id: str,
    payload: CaseDecisionCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(_WRITE_ROLES)),
):
    """Create a draft decision for a case."""
    case_pk = _resolve_case_pk(case_id, current_user.tenant_id, db)
    svc = CaseDecisionService(db)
    decision = svc.create_decision(
        case_id=case_pk,
        tenant_id=current_user.tenant_id,
        disposition=payload.disposition,
        rationale=payload.rationale,
        created_by=current_user.user_id,
    )
    db.commit()
    db.refresh(decision)
    return decision


# ---------------------------------------------------------------------------
# LIST
# ---------------------------------------------------------------------------


@router.get("", response_model=List[CaseDecisionResponse])
def list_decisions(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(_WRITE_ROLES)),
):
    """List all decisions for a case, ordered by version descending."""
    case_pk = _resolve_case_pk(case_id, current_user.tenant_id, db)
    decisions = (
        db.query(CaseDecision)
        .filter(
            CaseDecision.case_id == case_pk,
            CaseDecision.tenant_id == current_user.tenant_id,
        )
        .order_by(CaseDecision.version.desc())
        .all()
    )
    return decisions


# ---------------------------------------------------------------------------
# GET single
# ---------------------------------------------------------------------------


@router.get("/{decision_id}", response_model=CaseDecisionResponse)
def get_decision(
    case_id: str,
    decision_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(_WRITE_ROLES)),
):
    """Get a single decision by ID."""
    _resolve_case_pk(case_id, current_user.tenant_id, db)  # ensure case exists
    decision = (
        db.query(CaseDecision)
        .filter(
            CaseDecision.id == decision_id,
            CaseDecision.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    return decision


# ---------------------------------------------------------------------------
# SUBMIT
# ---------------------------------------------------------------------------


@router.post("/{decision_id}/submit", response_model=CaseDecisionResponse)
def submit_decision(
    case_id: str,
    decision_id: int,
    payload: CaseDecisionSubmit,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(_WRITE_ROLES)),
):
    """Submit a draft decision for approval."""
    case_pk = _resolve_case_pk(case_id, current_user.tenant_id, db)
    svc = CaseDecisionService(db)
    decision = svc.submit_decision(
        decision_id=decision_id,
        tenant_id=current_user.tenant_id,
        rationale=payload.rationale,
        actor_id=current_user.user_id,
        case_id=case_pk,
    )
    db.commit()
    db.refresh(decision)
    return decision


# ---------------------------------------------------------------------------
# APPROVE
# ---------------------------------------------------------------------------


@router.post("/{decision_id}/approve", response_model=CaseDecisionResponse)
def approve_decision(
    case_id: str,
    decision_id: int,
    payload: CaseDecisionApprove,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(_APPROVE_ROLES)),
):
    """Approve a submitted decision (4-eyes enforced)."""
    case_pk = _resolve_case_pk(case_id, current_user.tenant_id, db)
    svc = CaseDecisionService(db)
    decision = svc.approve_decision(
        decision_id=decision_id,
        tenant_id=current_user.tenant_id,
        approver_id=current_user.user_id,
        comment=payload.comment,
        case_id=case_pk,
    )
    db.commit()
    db.refresh(decision)
    return decision


# ---------------------------------------------------------------------------
# REJECT
# ---------------------------------------------------------------------------


@router.post("/{decision_id}/reject", response_model=CaseDecisionResponse)
def reject_decision(
    case_id: str,
    decision_id: int,
    payload: CaseDecisionReject,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(_APPROVE_ROLES)),
):
    """Reject a submitted decision."""
    case_pk = _resolve_case_pk(case_id, current_user.tenant_id, db)
    svc = CaseDecisionService(db)
    decision = svc.reject_decision(
        decision_id=decision_id,
        tenant_id=current_user.tenant_id,
        rejector_id=current_user.user_id,
        rejection_reason=payload.rejection_reason,
        case_id=case_pk,
    )
    db.commit()
    db.refresh(decision)
    return decision
