"""Policy management API endpoints."""
from datetime import datetime, timezone
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.database import get_db
from src.auth.dependencies import require_any_role, CurrentUser
from src.models.compliance_workflow import PolicyDocument, PolicySection, RegulatoryObligation, PolicyTemplate
from src.schemas.policy_schemas import (
    PolicyCreate,
    PolicyUpdate,
    PolicyApprove,
    PolicySectionCreate,
    PolicySectionUpdate,
    PolicyResponse,
    PolicyListResponse,
    PolicySectionResponse,
    PolicyFromTemplateCreate,
)
from src.websocket.manager import ws_manager
from src.websocket.events import EventType, NotificationEvent
from src.services.policy_library import ensure_master_policy_for_template


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


router = APIRouter(prefix="/api/policies", tags=["policies"])


def generate_policy_id() -> str:
    """Generate a unique policy ID."""
    return f"POL-{uuid.uuid4().hex[:8].upper()}"


def policy_to_dict(policy: PolicyDocument, db: Session) -> dict:
    """Convert policy model to response dict."""
    sections_count = db.query(func.count(PolicySection.id)).filter(
        PolicySection.policy_id == policy.id
    ).scalar() or 0

    linked_obligations_count = db.query(func.count(RegulatoryObligation.id)).filter(
        RegulatoryObligation.linked_policy_id == policy.id
    ).scalar() or 0

    return {
        "id": policy.id,
        "policy_id": policy.policy_id,
        "name": policy.name,
        "version": policy.version,
        "owner": policy.owner,
        "status": policy.status,
        "language": policy.language,
        "effective_date": policy.effective_date.isoformat() if policy.effective_date else None,
        "last_reviewed_at": policy.last_reviewed_at.isoformat() if policy.last_reviewed_at else None,
        "source_url": policy.source_url,
        "content": policy.content,
        "metadata": policy.metadata_json,
        "created_at": policy.created_at.isoformat() if policy.created_at else None,
        "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
        "sections_count": sections_count,
        "linked_obligations_count": linked_obligations_count,
    }


def section_to_dict(section: PolicySection) -> dict:
    """Convert policy section model to response dict."""
    return {
        "id": section.id,
        "policy_id": section.policy_id,
        "section_ref": section.section_ref,
        "title": section.title,
        "content": section.content,
        "status": section.status,
        "version": section.version,
        "last_reviewed_at": section.last_reviewed_at.isoformat() if section.last_reviewed_at else None,
        "created_at": section.created_at.isoformat() if section.created_at else None,
        "updated_at": section.updated_at.isoformat() if section.updated_at else None,
    }


def template_to_dict(template: PolicyTemplate) -> dict:
    return {
        "id": template.id,
        "template_id": template.template_id,
        "name": template.name,
        "category": template.category,
        "version": template.version,
        "owner": template.owner,
        "review_frequency_months": template.review_frequency_months,
        "regulatory_basis": template.regulatory_basis,
        "source_url": template.source_url,
        "content": template.content,
        "metadata": template.metadata_json,
        "is_active": template.is_active,
        "created_at": template.created_at.isoformat() if template.created_at else None,
        "updated_at": template.updated_at.isoformat() if template.updated_at else None,
    }


@router.get("/templates")
def list_policy_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    q: Optional[str] = Query(None, description="Search by name or template_id"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])),
):
    query = db.query(PolicyTemplate).filter(PolicyTemplate.is_active == True)
    if category:
        query = query.filter(PolicyTemplate.category.ilike(f"%{category}%"))
    if q:
        like = f"%{q}%"
        query = query.filter(
            (PolicyTemplate.name.ilike(like)) | (PolicyTemplate.template_id.ilike(like))
        )

    total = query.count()
    items = query.order_by(PolicyTemplate.name.asc()).offset(skip).limit(limit).all()
    return {"total": total, "items": [template_to_dict(item) for item in items]}


@router.get("/templates/{template_id}")
def get_policy_template(
    template_id: str,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])),
):
    template = db.query(PolicyTemplate).filter(
        PolicyTemplate.template_id == template_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Policy template not found")
    return template_to_dict(template)


@router.post("/from-template/{template_id}")
async def create_policy_from_template(
    template_id: str,
    payload: PolicyFromTemplateCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    template = db.query(PolicyTemplate).filter(
        PolicyTemplate.template_id == template_id,
        PolicyTemplate.is_active == True,
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Policy template not found")

    # Templates represent the canonical policy library: ensure (idempotently) the master policy exists.
    policy, stats = ensure_master_policy_for_template(db, template)

    # Apply optional metadata overrides without clobbering canonical template markers.
    if payload.metadata:
        merged = dict(policy.metadata_json or {})
        merged.update(payload.metadata)
        merged["template_id"] = template.template_id
        merged["category"] = template.category
        merged["regulatory_basis"] = template.regulatory_basis
        merged["review_frequency_months"] = template.review_frequency_months
        merged["template_version"] = template.version
        merged["is_master_policy"] = True
        policy.metadata_json = merged or None
        policy.updated_at = utc_now()

    db.commit()
    db.refresh(policy)

    if stats.get("created"):
        try:
            await ws_manager.broadcast(NotificationEvent(
                event_type=EventType.POLICY_CREATED,
                title="Policy Created",
                message=f"New master policy created: {policy.name}",
                data={"policy_id": policy.policy_id, "name": policy.name},
                priority="normal",
                link=f"/compliance/policies?id={policy.id}",
            ))
        except Exception:
            pass

    return policy_to_dict(policy, db)


@router.get("")
def list_policies(
    status: Optional[str] = Query(None, description="Filter by status"),
    owner: Optional[str] = Query(None, description="Filter by owner"),
    q: Optional[str] = Query(None, description="Search by name or policy_id"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])),
):
    """List all policies with optional filters."""
    query = db.query(PolicyDocument)

    if status:
        statuses = [s.strip().lower() for s in status.split(",") if s.strip()]
        if statuses:
            query = query.filter(PolicyDocument.status.in_(statuses))

    if owner:
        query = query.filter(PolicyDocument.owner.ilike(f"%{owner}%"))

    if q:
        like = f"%{q}%"
        query = query.filter(
            (PolicyDocument.name.ilike(like)) | (PolicyDocument.policy_id.ilike(like))
        )

    total = query.count()
    policies = query.order_by(PolicyDocument.updated_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [policy_to_dict(p, db) for p in policies],
    }


@router.post("")
async def create_policy(
    payload: PolicyCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    """Create a new policy document."""
    policy = PolicyDocument(
        policy_id=generate_policy_id(),
        name=payload.name,
        version=payload.version,
        owner=payload.owner or current_user.email,
        status=payload.status,
        language=payload.language,
        effective_date=payload.effective_date,
        source_url=payload.source_url,
        content=payload.content,
        metadata_json=payload.metadata,
        created_at=utc_now(),
        updated_at=utc_now(),
    )

    db.add(policy)
    db.commit()
    db.refresh(policy)

    # Send WebSocket notification
    try:
        await ws_manager.broadcast(NotificationEvent(
            event_type=EventType.POLICY_CREATED,
            title="Policy Created",
            message=f"New policy created: {policy.name}",
            data={"policy_id": policy.policy_id, "name": policy.name},
            priority="normal",
            link=f"/compliance/policies?id={policy.id}",
        ))
    except Exception:
        pass  # Don't fail request if notification fails

    return policy_to_dict(policy, db)


@router.get("/{policy_id}")
def get_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])),
):
    """Get a policy by ID."""
    policy = db.query(PolicyDocument).filter(PolicyDocument.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    return policy_to_dict(policy, db)


@router.patch("/{policy_id}")
def update_policy(
    policy_id: int,
    payload: PolicyUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    """Update a policy document."""
    policy = db.query(PolicyDocument).filter(PolicyDocument.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "metadata" in update_data:
        update_data["metadata_json"] = update_data.pop("metadata")

    for key, value in update_data.items():
        setattr(policy, key, value)

    policy.updated_at = utc_now()
    db.commit()
    db.refresh(policy)

    return policy_to_dict(policy, db)


@router.delete("/{policy_id}")
def delete_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance"])),
):
    """Delete a policy document."""
    policy = db.query(PolicyDocument).filter(PolicyDocument.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    # Check for linked obligations
    linked_count = db.query(func.count(RegulatoryObligation.id)).filter(
        RegulatoryObligation.linked_policy_id == policy.id
    ).scalar() or 0

    if linked_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete policy with {linked_count} linked obligations"
        )

    db.delete(policy)
    db.commit()

    return {"message": "Policy deleted", "policy_id": policy.policy_id}


@router.post("/{policy_id}/approve")
async def approve_policy(
    policy_id: int,
    payload: PolicyApprove,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance"])),
):
    """Approve a policy document."""
    policy = db.query(PolicyDocument).filter(PolicyDocument.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    if policy.status not in ("draft", "in_review"):
        raise HTTPException(status_code=400, detail="Policy cannot be approved from current status")

    policy.status = "approved"
    policy.last_reviewed_at = utc_now()
    policy.updated_at = utc_now()

    db.commit()
    db.refresh(policy)

    # Send notification
    try:
        await ws_manager.broadcast(NotificationEvent(
            event_type=EventType.POLICY_APPROVED,
            title="Policy Approved",
            message=f"Policy approved: {policy.name}",
            data={"policy_id": policy.policy_id, "name": policy.name},
            priority="normal",
            link=f"/compliance/policies?id={policy.id}",
        ))
    except Exception:
        pass

    return policy_to_dict(policy, db)


@router.get("/{policy_id}/obligations")
def list_policy_obligations(
    policy_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])),
):
    """List obligations linked to a policy."""
    policy = db.query(PolicyDocument).filter(PolicyDocument.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    query = db.query(RegulatoryObligation).filter(
        RegulatoryObligation.linked_policy_id == policy_id
    )

    total = query.count()
    obligations = query.order_by(RegulatoryObligation.updated_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "id": o.id,
                "obligation_id": o.obligation_id,
                "status": o.status,
                "article_ref": o.article_ref,
                "obligation_text": o.obligation_text[:200] + "..." if len(o.obligation_text or "") > 200 else o.obligation_text,
                "updated_at": o.updated_at.isoformat() if o.updated_at else None,
            }
            for o in obligations
        ],
    }


@router.post("/{policy_id}/link-obligation/{obligation_id}")
async def link_obligation_to_policy(
    policy_id: int,
    obligation_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    """Link an obligation to a policy."""
    policy = db.query(PolicyDocument).filter(PolicyDocument.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    obligation = db.query(RegulatoryObligation).filter(RegulatoryObligation.id == obligation_id).first()
    if not obligation:
        raise HTTPException(status_code=404, detail="Obligation not found")

    obligation.linked_policy_id = policy.id
    obligation.updated_at = utc_now()
    db.commit()
    db.refresh(obligation)

    try:
        await ws_manager.broadcast(NotificationEvent(
            event_type=EventType.OBLIGATION_UPDATED,
            title="Obligation Linked",
            message=f"Linked obligation {obligation.obligation_id} to policy {policy.name}",
            data={
                "obligation_id": obligation.obligation_id,
                "policy_id": policy.policy_id,
            },
            priority="normal",
            link=f"/compliance/obligations/{obligation.id}",
        ))
    except Exception:
        pass

    return {
        "message": "Obligation linked",
        "policy_id": policy.policy_id,
        "obligation_id": obligation.obligation_id,
    }


# Policy Sections endpoints

@router.get("/{policy_id}/sections")
def list_policy_sections(
    policy_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])),
):
    """List all sections for a policy."""
    policy = db.query(PolicyDocument).filter(PolicyDocument.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    sections = db.query(PolicySection).filter(
        PolicySection.policy_id == policy_id
    ).order_by(PolicySection.section_ref).all()

    return {"items": [section_to_dict(s) for s in sections]}


@router.post("/{policy_id}/sections")
def create_policy_section(
    policy_id: int,
    payload: PolicySectionCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    """Create a new section within a policy."""
    policy = db.query(PolicyDocument).filter(PolicyDocument.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    section = PolicySection(
        policy_id=policy_id,
        section_ref=payload.section_ref,
        title=payload.title,
        content=payload.content,
        status=payload.status,
        version=payload.version,
        created_at=utc_now(),
        updated_at=utc_now(),
    )

    db.add(section)
    db.commit()
    db.refresh(section)

    return section_to_dict(section)


@router.patch("/sections/{section_id}")
def update_policy_section(
    section_id: int,
    payload: PolicySectionUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    """Update a policy section."""
    section = db.query(PolicySection).filter(PolicySection.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(section, key, value)

    section.updated_at = utc_now()
    db.commit()
    db.refresh(section)

    return section_to_dict(section)


@router.delete("/sections/{section_id}")
def delete_policy_section(
    section_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance"])),
):
    """Delete a policy section."""
    section = db.query(PolicySection).filter(PolicySection.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    db.delete(section)
    db.commit()

    return {"message": "Section deleted"}
