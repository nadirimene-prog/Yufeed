from datetime import datetime, timezone
import uuid


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from src.database import get_db
from src.auth.dependencies import require_any_role, CurrentUser
from src.models.compliance_workflow import (
    RegulatoryObligation,
    PolicyDocument,
    InternalRule,
    RiskEntry,
    ObligationRiskLink,
)
from src.models.models import LegalDocument
from src.schemas.obligation_schemas import ObligationUpdate, ObligationApproval
from src.compliance.scope import normalize_scopes, scope_keywords
from src.websocket.manager import ws_manager
from src.websocket.events import EventType, NotificationEvent

router = APIRouter(prefix="/api/obligations", tags=["obligations"])


def _normalize_statuses(status: Optional[str]) -> Optional[List[str]]:
    if not status:
        return None
    statuses = [item.strip().lower() for item in status.split(",") if item.strip()]
    return statuses or None


def _obligation_to_dict(obligation: RegulatoryObligation, doc: LegalDocument, db: Session = None) -> dict:
    title = doc.title or doc.celex or doc.source_reference or "Untitled document"

    # Get linked policy info if available
    linked_policy = None
    if obligation.linked_policy_id and db:
        policy = db.query(PolicyDocument).filter(
            PolicyDocument.id == obligation.linked_policy_id
        ).first()
        if policy:
            linked_policy = {
                "id": policy.id,
                "policy_id": policy.policy_id,
                "name": policy.name,
                "status": policy.status,
            }

    # Get linked risks count
    linked_risks_count = 0
    if db:
        linked_risks_count = db.query(ObligationRiskLink).filter(
            ObligationRiskLink.obligation_id == obligation.id
        ).count()

    # Get internal rules count
    internal_rules_count = 0
    if db:
        internal_rules_count = db.query(InternalRule).filter(
            InternalRule.obligation_id == obligation.id
        ).count()

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
        "linked_policy_id": obligation.linked_policy_id,
        "linked_policy": linked_policy,
        "linked_risks_count": linked_risks_count,
        "internal_rules_count": internal_rules_count,
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
        "items": [_obligation_to_dict(obligation, doc, db) for obligation, doc in rows],
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
    result = _obligation_to_dict(obligation, doc, db)

    # Get linked risks details
    risk_links = db.query(ObligationRiskLink).filter(
        ObligationRiskLink.obligation_id == obligation.id
    ).all()
    result["linked_risks"] = []
    for link in risk_links:
        risk_entry = db.query(RiskEntry).filter(RiskEntry.id == link.risk_entry_id).first()
        if risk_entry:
            result["linked_risks"].append({
                "link_id": link.id,
                "link_type": link.link_type,
                "risk_id": risk_entry.risk_id,
                "name": risk_entry.name,
                "inherent_risk_level": risk_entry.inherent_risk_level,
                "residual_risk_level": risk_entry.residual_risk_level,
            })

    # Get internal rules
    internal_rules = db.query(InternalRule).filter(
        InternalRule.obligation_id == obligation.id
    ).all()
    result["internal_rules"] = [
        {
            "id": rule.id,
            "internal_rule_id": rule.internal_rule_id,
            "name": rule.name,
            "status": rule.status,
            "control_owner": rule.control_owner,
        }
        for rule in internal_rules
    ]

    return result


@router.patch("/{obligation_id}")
async def update_obligation(
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
    obligation.updated_at = utc_now()

    if payload.note and payload.note.strip():
        note_entry = f"[{utc_now().isoformat()}] {current_user.email}: {payload.note.strip()}"
        if obligation.review_notes:
            obligation.review_notes = f"{obligation.review_notes.rstrip()}\n{note_entry}"
        else:
            obligation.review_notes = note_entry

    if new_status == "in_review":
        obligation.reviewed_by = current_user.email
    if new_status == "approved":
        obligation.approved_by = current_user.email
        obligation.approved_at = utc_now()
    if new_status == "rejected":
        obligation.reviewed_by = current_user.email

    db.commit()
    db.refresh(obligation)

    doc = db.query(LegalDocument).filter(LegalDocument.id == obligation.doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Linked document not found")

    # Send WebSocket notification
    try:
        event_type = EventType.OBLIGATION_APPROVED if new_status == "approved" else (
            EventType.OBLIGATION_REJECTED if new_status == "rejected" else EventType.OBLIGATION_UPDATED
        )
        await ws_manager.broadcast(NotificationEvent(
            event_type=event_type,
            title=f"Obligation {new_status.title()}",
            message=f"Obligation {obligation.obligation_id} has been {new_status}",
            data={
                "obligation_id": obligation.obligation_id,
                "status": new_status,
                "approved_by": current_user.email,
            },
            priority="high" if new_status == "rejected" else "normal",
            link=f"/compliance/obligations/{obligation.id}",
        ))
    except Exception:
        pass

    return _obligation_to_dict(obligation, doc, db)


@router.patch("/{obligation_id}/approve")
async def approve_obligation(
    obligation_id: int,
    payload: ObligationApproval,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    """Enhanced approval with policy linking and internal rule creation."""
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

    # Validate linked policy if provided
    if payload.linked_policy_id:
        policy = db.query(PolicyDocument).filter(
            PolicyDocument.id == payload.linked_policy_id
        ).first()
        if not policy:
            raise HTTPException(status_code=404, detail="Linked policy not found")
        obligation.linked_policy_id = payload.linked_policy_id

    # Update status
    obligation.status = new_status
    obligation.updated_at = utc_now()

    if payload.note and payload.note.strip():
        note_entry = f"[{utc_now().isoformat()}] {current_user.email}: {payload.note.strip()}"
        if obligation.review_notes:
            obligation.review_notes = f"{obligation.review_notes.rstrip()}\n{note_entry}"
        else:
            obligation.review_notes = note_entry

    if new_status == "in_review":
        obligation.reviewed_by = current_user.email
    if new_status == "approved":
        obligation.approved_by = current_user.email
        obligation.approved_at = utc_now()
    if new_status == "rejected":
        obligation.reviewed_by = current_user.email

    # Create internal rule if requested
    internal_rule = None
    if payload.create_internal_rule and new_status == "approved":
        rule_name = payload.internal_rule_name or f"Rule for {obligation.obligation_id}"
        internal_rule = InternalRule(
            internal_rule_id=f"IR-{uuid.uuid4().hex[:8].upper()}",
            obligation_id=obligation.id,
            name=rule_name,
            description=payload.internal_rule_description or obligation.obligation_text[:500],
            control_owner=current_user.email,
            status="draft",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(internal_rule)

    # Link to risk entries if provided
    if payload.link_risk_entry_ids:
        for risk_entry_id in payload.link_risk_entry_ids:
            risk_entry = db.query(RiskEntry).filter(RiskEntry.id == risk_entry_id).first()
            if not risk_entry:
                continue  # Skip invalid risk entries

            # Check if link already exists
            existing_link = db.query(ObligationRiskLink).filter(
                ObligationRiskLink.obligation_id == obligation.id,
                ObligationRiskLink.risk_entry_id == risk_entry_id,
            ).first()
            if existing_link:
                continue

            link = ObligationRiskLink(
                obligation_id=obligation.id,
                risk_entry_id=risk_entry_id,
                link_type="mitigates",
                created_by=current_user.email,
                created_at=utc_now(),
            )
            db.add(link)

    db.commit()
    db.refresh(obligation)

    if internal_rule:
        db.refresh(internal_rule)

    doc = db.query(LegalDocument).filter(LegalDocument.id == obligation.doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Linked document not found")

    # Send WebSocket notifications
    try:
        event_type = EventType.OBLIGATION_APPROVED if new_status == "approved" else (
            EventType.OBLIGATION_REJECTED if new_status == "rejected" else EventType.OBLIGATION_UPDATED
        )
        await ws_manager.broadcast(NotificationEvent(
            event_type=event_type,
            title=f"Obligation {new_status.title()}",
            message=f"Obligation {obligation.obligation_id} has been {new_status}",
            data={
                "obligation_id": obligation.obligation_id,
                "status": new_status,
                "approved_by": current_user.email,
                "internal_rule_id": internal_rule.internal_rule_id if internal_rule else None,
            },
            priority="high" if new_status == "rejected" else "normal",
            link=f"/compliance/obligations/{obligation.id}",
        ))

        if internal_rule:
            await ws_manager.broadcast(NotificationEvent(
                event_type=EventType.INTERNAL_RULE_CREATED,
                title="Internal Rule Created",
                message=f"Internal rule created: {internal_rule.name}",
                data={
                    "internal_rule_id": internal_rule.internal_rule_id,
                    "obligation_id": obligation.obligation_id,
                },
                priority="normal",
                link=f"/compliance/obligations/{obligation.id}",
            ))
    except Exception:
        pass

    result = _obligation_to_dict(obligation, doc, db)
    if internal_rule:
        result["created_internal_rule"] = {
            "id": internal_rule.id,
            "internal_rule_id": internal_rule.internal_rule_id,
            "name": internal_rule.name,
        }

    return result


@router.get("/{obligation_id}/risks")
def get_obligation_risks(
    obligation_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])),
):
    """Get risks linked to an obligation."""
    obligation = db.query(RegulatoryObligation).filter(RegulatoryObligation.id == obligation_id).first()
    if not obligation:
        raise HTTPException(status_code=404, detail="Obligation not found")

    links = db.query(ObligationRiskLink).filter(
        ObligationRiskLink.obligation_id == obligation_id
    ).all()

    result = []
    for link in links:
        risk_entry = db.query(RiskEntry).filter(RiskEntry.id == link.risk_entry_id).first()
        if risk_entry:
            result.append({
                "link_id": link.id,
                "link_type": link.link_type,
                "notes": link.notes,
                "created_at": link.created_at.isoformat() if link.created_at else None,
                "risk": {
                    "id": risk_entry.id,
                    "risk_id": risk_entry.risk_id,
                    "name": risk_entry.name,
                    "category_id": risk_entry.category_id,
                    "inherent_risk_level": risk_entry.inherent_risk_level,
                    "residual_risk_level": risk_entry.residual_risk_level,
                    "mitigation_status": risk_entry.mitigation_status,
                },
            })

    return {"items": result}


@router.get("/{obligation_id}/internal-rules")
def get_obligation_internal_rules(
    obligation_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])),
):
    """Get internal rules for an obligation."""
    obligation = db.query(RegulatoryObligation).filter(RegulatoryObligation.id == obligation_id).first()
    if not obligation:
        raise HTTPException(status_code=404, detail="Obligation not found")

    rules = db.query(InternalRule).filter(
        InternalRule.obligation_id == obligation_id
    ).all()

    return {
        "items": [
            {
                "id": rule.id,
                "internal_rule_id": rule.internal_rule_id,
                "name": rule.name,
                "description": rule.description,
                "status": rule.status,
                "control_owner": rule.control_owner,
                "policy_section_id": rule.policy_section_id,
                "created_at": rule.created_at.isoformat() if rule.created_at else None,
                "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
            }
            for rule in rules
        ]
    }
