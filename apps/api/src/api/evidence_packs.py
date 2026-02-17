"""Evidence Packs API — audit-proof case snapshots.

Nested under ``/api/cases/{case_id}/evidence-packs``.
"""

import json
import os
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from src.database import get_db
from src.auth.dependencies import require_any_role, CurrentUser
from src.audit.recorders import record_event
from src.models.evidence_pack import EvidencePack
from src.models.transaction_models import Case
from src.schemas.evidence_pack_schemas import (
    EvidencePackCreateRequest,
    EvidencePackResponse,
    EvidencePackDetailResponse,
)
from src.services.evidence_pack_builder import EvidencePackBuilder
from src.tenancy.queries import get_tenant_filtered_query

router = APIRouter(prefix="/api/cases/{case_id}/evidence-packs", tags=["evidence-packs"])

_ALLOWED_ROLES = ["admin", "compliance", "auditor", "aml_officer"]


def _resolve_case_pk(case_id: str, tenant_id: str, db: Session) -> int:
    case = get_tenant_filtered_query(Case, db).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case.id


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------


@router.post("", response_model=EvidencePackResponse, status_code=201)
def create_evidence_pack(
    case_id: str,
    payload: EvidencePackCreateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(_ALLOWED_ROLES)),
):
    """Generate a new evidence pack (JSON or PDF) for a case."""
    case_pk = _resolve_case_pk(case_id, current_user.tenant_id, db)
    builder = EvidencePackBuilder(db)
    pack = builder.create_pack(
        case_id=case_pk,
        tenant_id=current_user.tenant_id,
        created_by=current_user.user_id,
        pack_format=payload.format,
    )
    db.commit()
    db.refresh(pack)
    return pack


# ---------------------------------------------------------------------------
# LIST
# ---------------------------------------------------------------------------


@router.get("", response_model=List[EvidencePackResponse])
def list_evidence_packs(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(_ALLOWED_ROLES)),
):
    """List evidence packs for a case (metadata only, no snapshot)."""
    case_pk = _resolve_case_pk(case_id, current_user.tenant_id, db)
    packs = (
        db.query(EvidencePack)
        .filter(
            EvidencePack.case_id == case_pk,
            EvidencePack.tenant_id == current_user.tenant_id,
        )
        .order_by(EvidencePack.version.desc())
        .all()
    )
    return packs


# ---------------------------------------------------------------------------
# GET (with full snapshot)
# ---------------------------------------------------------------------------


@router.get("/{pack_id}", response_model=EvidencePackDetailResponse)
def get_evidence_pack(
    case_id: str,
    pack_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(_ALLOWED_ROLES)),
):
    """Get an evidence pack including its full snapshot."""
    _resolve_case_pk(case_id, current_user.tenant_id, db)
    pack = (
        db.query(EvidencePack)
        .filter(
            EvidencePack.pack_id == pack_id,
            EvidencePack.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not pack:
        raise HTTPException(status_code=404, detail="Evidence pack not found")
    return pack


# ---------------------------------------------------------------------------
# DOWNLOAD
# ---------------------------------------------------------------------------


@router.get("/{pack_id}/download")
def download_evidence_pack(
    case_id: str,
    pack_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(_ALLOWED_ROLES)),
):
    """Download an evidence pack as a file (JSON or PDF)."""
    _resolve_case_pk(case_id, current_user.tenant_id, db)
    pack = (
        db.query(EvidencePack)
        .filter(
            EvidencePack.pack_id == pack_id,
            EvidencePack.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not pack:
        raise HTTPException(status_code=404, detail="Evidence pack not found")

    record_event(
        db,
        event_type="evidence_pack.downloaded",
        entity_type="evidence_pack",
        entity_id=pack.pack_id,
        tenant_id=current_user.tenant_id,
        payload={"actor": current_user.user_id, "format": pack.format},
    )
    db.commit()

    if pack.format == "pdf" and pack.storage_ref and os.path.exists(pack.storage_ref):
        return FileResponse(
            path=pack.storage_ref,
            media_type="application/pdf",
            filename=f"{pack.pack_id}.pdf",
        )

    # Default: return canonical JSON
    canonical = json.dumps(
        pack.snapshot_json,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return Response(
        content=canonical,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{pack.pack_id}.json"',
            "X-Integrity-Hash": pack.integrity_hash,
        },
    )
