from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from src.database import get_db
from src.auth.dependencies import require_any_role, CurrentUser
from src.models.compliance_workflow import RegulatoryObligation
from src.models.models import LegalDocument
from src.schemas.obligation_schemas import ObligationUpdate
from src.compliance.scope import normalize_scopes, scope_keywords

router = APIRouter(prefix="/api/obligations", tags=["obligations"])


def _normalize_statuses(status: Optional[str]) -> Optional[List[str]]:
    if not status:
        return None
    statuses = [item.strip().lower() for item in status.split(",") if item.strip()]
    return statuses or None


def _obligation_to_dict(obligation: RegulatoryObligation, doc: LegalDocument) -> dict:
    title = doc.title or doc.celex or doc.source_reference or "Untitled document"
    return {
        "id": obligation.id,
        "obligation_id": obligation.obligation_id,
        "status": obligation.status,
        "article_ref": obligation.article_ref,
        "obligation_text": obligation.obligation_text,
        "applicability": obligation.applicability,
        "effective_date": obligation.effective_date.isoformat() if obligation.effective_date else None,
        "created_by": obligation.created_by,
        "reviewed_by": obligation.reviewed_by,
        "approved_by": obligation.approved_by,
        "approved_at": obligation.approved_at.isoformat() if obligation.approved_at else None,
        "review_notes": obligation.review_notes,
        "updated_at": obligation.updated_at.isoformat() if obligation.updated_at else None,
        "scope_tags": obligation.scope_tags,
        "tags": obligation.tags_json,
        "evidence": obligation.evidence_json,
        "document": {
            "id": doc.id,
            "celex": doc.celex,
            "title": title,
            "jurisdiction": doc.jurisdiction,
            "source_system": doc.source_system,
            "publication_date": doc.publication_date.isoformat() if doc.publication_date else None,
            "scope_tags": doc.scope_tags,
        },
    }

def _apply_scope_filter(query, scope: Optional[str], db: Session):
    scopes = normalize_scopes(scope)
    if not scopes:
        return query
    dialect = db.get_bind().dialect.name if db.get_bind() else ""
    if dialect == "postgresql":
        conditions = []
        for scope_key in scopes:
            conditions.append(
                sa.cast(LegalDocument.scope_tags, postgresql.JSONB).op("@>")(
                    sa.func.jsonb_build_array(scope_key)
                )
            )
            conditions.append(
                sa.cast(RegulatoryObligation.scope_tags, postgresql.JSONB).op("@>")(
                    sa.func.jsonb_build_array(scope_key)
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


@router.get("")
def list_obligations(
    status: Optional[str] = Query(None, description="Comma-separated statuses"),
    jurisdiction: Optional[str] = Query(None),
    source_system: Optional[str] = Query(None),
    scope: Optional[str] = Query(None, description="Comma-separated scope tags: psp,eme,vasp"),
    q: Optional[str] = Query(None, description="Search text"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])),
):
    statuses = _normalize_statuses(status)

    query = db.query(RegulatoryObligation, LegalDocument).join(
        LegalDocument, RegulatoryObligation.doc_id == LegalDocument.id
    )

    if statuses:
        query = query.filter(RegulatoryObligation.status.in_(statuses))
    if jurisdiction:
        query = query.filter(LegalDocument.jurisdiction == jurisdiction)
    if source_system:
        query = query.filter(LegalDocument.source_system == source_system)
    if scope:
        query = _apply_scope_filter(query, scope, db)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                RegulatoryObligation.obligation_text.ilike(like),
                RegulatoryObligation.article_ref.ilike(like),
                LegalDocument.title.ilike(like),
                LegalDocument.celex.ilike(like),
            )
        )

    total = query.count()
    rows = query.order_by(RegulatoryObligation.updated_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [_obligation_to_dict(obligation, doc) for obligation, doc in rows],
    }


@router.get("/{obligation_id}")
def get_obligation(
    obligation_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])),
):
    row = db.query(RegulatoryObligation, LegalDocument).join(
        LegalDocument, RegulatoryObligation.doc_id == LegalDocument.id
    ).filter(RegulatoryObligation.id == obligation_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Obligation not found")

    obligation, doc = row
    return _obligation_to_dict(obligation, doc)


@router.patch("/{obligation_id}")
def update_obligation(
    obligation_id: int,
    payload: ObligationUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    obligation = db.query(RegulatoryObligation).filter(RegulatoryObligation.id == obligation_id).first()
    if not obligation:
        raise HTTPException(status_code=404, detail="Obligation not found")

    new_status = payload.status.lower().strip()
    allowed_statuses = {"draft", "in_review", "approved", "rejected", "deprecated"}
    if new_status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Unsupported status")

    transition_map = {
        "draft": {"in_review", "rejected", "deprecated"},
        "in_review": {"approved", "rejected", "draft"},
        "approved": {"deprecated"},
        "rejected": {"draft", "in_review"},
        "deprecated": set(),
    }
    current_status = (obligation.status or "draft").lower()
    if new_status != current_status and new_status not in transition_map.get(current_status, set()):
        raise HTTPException(status_code=400, detail=f"Invalid status transition from {current_status} to {new_status}")

    obligation.status = new_status
    obligation.updated_at = datetime.utcnow()

    if payload.note and payload.note.strip():
        note_entry = f"[{datetime.utcnow().isoformat()}] {current_user.email}: {payload.note.strip()}"
        if obligation.review_notes:
            obligation.review_notes = f"{obligation.review_notes.rstrip()}\n{note_entry}"
        else:
            obligation.review_notes = note_entry

    if new_status == "in_review":
        obligation.reviewed_by = current_user.email
    if new_status == "approved":
        obligation.approved_by = current_user.email
        obligation.approved_at = datetime.utcnow()
    if new_status == "rejected":
        obligation.reviewed_by = current_user.email

    db.commit()
    db.refresh(obligation)

    doc = db.query(LegalDocument).filter(LegalDocument.id == obligation.doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Linked document not found")

    return _obligation_to_dict(obligation, doc)
