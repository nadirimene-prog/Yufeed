"""Traceability matrix API endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.auth.dependencies import CurrentUser, require_any_role
from src.database import get_db
from src.services.traceability_matrix import TraceabilityMatrixService

router = APIRouter(
    prefix="/traceability-matrix",
    tags=["traceability-matrix"],
)


def _enforce_tenant_access(tenant_id: str, current_user: CurrentUser) -> None:
    if current_user.is_superuser:
        return
    if current_user.tenant_id and current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=403, detail="Cannot access another tenant's traceability data"
        )


@router.get("/{tenant_id}/regulation/{doc_id}")
def get_traceability_for_regulation(
    tenant_id: str,
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])
    ),
):
    _enforce_tenant_access(tenant_id, current_user)
    service = TraceabilityMatrixService(db)
    return service.get_regulation_coverage(tenant_id=tenant_id, doc_id=doc_id)


@router.get("/{tenant_id}/gaps")
def get_traceability_gaps(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])
    ),
):
    _enforce_tenant_access(tenant_id, current_user)
    service = TraceabilityMatrixService(db)
    return service.find_gaps(tenant_id=tenant_id)


@router.get("/{tenant_id}")
def get_traceability_matrix(
    tenant_id: str,
    obligation_id: Optional[str] = Query(
        None, description="Optional obligation ID/business key to filter the matrix"
    ),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])
    ),
):
    _enforce_tenant_access(tenant_id, current_user)
    service = TraceabilityMatrixService(db)
    chain = service.get_full_chain(tenant_id=tenant_id, obligation_id=obligation_id)
    coverage = service.build_coverage_from_chain(chain)
    return {
        "tenant_id": tenant_id,
        "coverage": coverage,
        "matrix": chain,
    }
