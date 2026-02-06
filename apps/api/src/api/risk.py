"""Risk management API endpoints."""
from datetime import datetime, timezone
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.database import get_db
from src.auth.dependencies import require_any_role, CurrentUser
from src.models.compliance_workflow import (
    RiskCategory,
    RiskEntry,
    ObligationRiskLink,
    RegulatoryObligation,
)
from src.schemas.risk_schemas import (
    RiskCategoryCreate,
    RiskCategoryUpdate,
    RiskCategoryResponse,
    RiskCategoryTreeResponse,
    RiskEntryCreate,
    RiskEntryUpdate,
    RiskEntryResponse,
    RiskEntryListResponse,
    ObligationRiskLinkCreate,
    ObligationRiskLinkResponse,
    RiskMapSummary,
    RiskHeatMapResponse,
    RiskHeatMapCell,
)
from src.websocket.manager import ws_manager
from src.websocket.events import EventType, NotificationEvent


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


router = APIRouter(prefix="/api/risk", tags=["risk"])


def generate_category_id() -> str:
    """Generate a unique category ID."""
    return f"RISK-CAT-{uuid.uuid4().hex[:6].upper()}"


def generate_risk_id() -> str:
    """Generate a unique risk entry ID."""
    return f"RISK-{uuid.uuid4().hex[:8].upper()}"


def category_to_dict(category: RiskCategory, db: Session) -> dict:
    """Convert risk category model to response dict."""
    children_count = db.query(func.count(RiskCategory.id)).filter(
        RiskCategory.parent_id == category.id
    ).scalar() or 0

    entries_count = db.query(func.count(RiskEntry.id)).filter(
        RiskEntry.category_id == category.id
    ).scalar() or 0

    return {
        "id": category.id,
        "category_id": category.category_id,
        "name": category.name,
        "description": category.description,
        "parent_id": category.parent_id,
        "risk_level": category.risk_level,
        "status": category.status,
        "created_at": category.created_at.isoformat() if category.created_at else None,
        "updated_at": category.updated_at.isoformat() if category.updated_at else None,
        "children_count": children_count,
        "entries_count": entries_count,
    }


def entry_to_dict(entry: RiskEntry, db: Session) -> dict:
    """Convert risk entry model to response dict."""
    category = db.query(RiskCategory).filter(RiskCategory.id == entry.category_id).first()
    category_name = category.name if category else None

    linked_obligations_count = db.query(func.count(ObligationRiskLink.id)).filter(
        ObligationRiskLink.risk_entry_id == entry.id
    ).scalar() or 0

    return {
        "id": entry.id,
        "risk_id": entry.risk_id,
        "category_id": entry.category_id,
        "category_name": category_name,
        "name": entry.name,
        "description": entry.description,
        "inherent_risk_level": entry.inherent_risk_level,
        "residual_risk_level": entry.residual_risk_level,
        "likelihood": entry.likelihood,
        "impact": entry.impact,
        "mitigation_status": entry.mitigation_status,
        "control_owner": entry.control_owner,
        "review_date": entry.review_date.isoformat() if entry.review_date else None,
        "metadata": entry.metadata_json,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
        "linked_obligations_count": linked_obligations_count,
    }


def link_to_dict(link: ObligationRiskLink, db: Session) -> dict:
    """Convert obligation-risk link model to response dict."""
    obligation = db.query(RegulatoryObligation).filter(
        RegulatoryObligation.id == link.obligation_id
    ).first()

    return {
        "id": link.id,
        "obligation_id": link.obligation_id,
        "risk_entry_id": link.risk_entry_id,
        "link_type": link.link_type,
        "notes": link.notes,
        "created_by": link.created_by,
        "created_at": link.created_at.isoformat() if link.created_at else None,
        "obligation_text": obligation.obligation_text[:200] + "..." if obligation and len(obligation.obligation_text or "") > 200 else (obligation.obligation_text if obligation else None),
        "obligation_article_ref": obligation.article_ref if obligation else None,
    }


# ========== Risk Categories ==========

@router.get("/categories")
def list_risk_categories(
    status: Optional[str] = Query(None, description="Filter by status"),
    parent_id: Optional[int] = Query(None, description="Filter by parent category"),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])),
):
    """List all risk categories."""
    query = db.query(RiskCategory)

    if status:
        query = query.filter(RiskCategory.status == status)

    if parent_id is not None:
        query = query.filter(RiskCategory.parent_id == parent_id)
    else:
        # Return top-level categories by default
        query = query.filter(RiskCategory.parent_id.is_(None))

    categories = query.order_by(RiskCategory.name).all()
    return {"items": [category_to_dict(c, db) for c in categories]}


@router.get("/categories/tree")
def get_category_tree(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])),
):
    """Get hierarchical category tree."""
    def build_tree(parent_id=None):
        categories = db.query(RiskCategory).filter(
            RiskCategory.parent_id == parent_id,
            RiskCategory.status == "active"
        ).order_by(RiskCategory.name).all()

        result = []
        for cat in categories:
            entries_count = db.query(func.count(RiskEntry.id)).filter(
                RiskEntry.category_id == cat.id
            ).scalar() or 0

            result.append({
                "id": cat.id,
                "category_id": cat.category_id,
                "name": cat.name,
                "description": cat.description,
                "risk_level": cat.risk_level,
                "status": cat.status,
                "children": build_tree(cat.id),
                "entries_count": entries_count,
            })
        return result

    return {"items": build_tree()}


@router.post("/categories")
async def create_risk_category(
    payload: RiskCategoryCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    """Create a new risk category."""
    if payload.parent_id:
        parent = db.query(RiskCategory).filter(RiskCategory.id == payload.parent_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent category not found")

    category = RiskCategory(
        category_id=generate_category_id(),
        name=payload.name,
        description=payload.description,
        parent_id=payload.parent_id,
        risk_level=payload.risk_level,
        status=payload.status,
        created_at=utc_now(),
        updated_at=utc_now(),
    )

    db.add(category)
    db.commit()
    db.refresh(category)

    return category_to_dict(category, db)


@router.get("/categories/{category_id}")
def get_risk_category(
    category_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])),
):
    """Get a risk category by ID."""
    category = db.query(RiskCategory).filter(RiskCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    return category_to_dict(category, db)


@router.patch("/categories/{category_id}")
def update_risk_category(
    category_id: int,
    payload: RiskCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    """Update a risk category."""
    category = db.query(RiskCategory).filter(RiskCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if payload.parent_id is not None and payload.parent_id != category.parent_id:
        if payload.parent_id == category.id:
            raise HTTPException(status_code=400, detail="Category cannot be its own parent")
        if payload.parent_id:
            parent = db.query(RiskCategory).filter(RiskCategory.id == payload.parent_id).first()
            if not parent:
                raise HTTPException(status_code=404, detail="Parent category not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)

    category.updated_at = utc_now()
    db.commit()
    db.refresh(category)

    return category_to_dict(category, db)


@router.delete("/categories/{category_id}")
def delete_risk_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance"])),
):
    """Delete a risk category."""
    category = db.query(RiskCategory).filter(RiskCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Check for child categories
    children_count = db.query(func.count(RiskCategory.id)).filter(
        RiskCategory.parent_id == category_id
    ).scalar() or 0

    if children_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete category with {children_count} child categories"
        )

    # Check for risk entries
    entries_count = db.query(func.count(RiskEntry.id)).filter(
        RiskEntry.category_id == category_id
    ).scalar() or 0

    if entries_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete category with {entries_count} risk entries"
        )

    db.delete(category)
    db.commit()

    return {"message": "Category deleted", "category_id": category.category_id}


# ========== Risk Entries ==========

@router.get("/entries")
def list_risk_entries(
    category_id: Optional[int] = Query(None, description="Filter by category"),
    inherent_risk_level: Optional[str] = Query(None, description="Filter by inherent risk level"),
    residual_risk_level: Optional[str] = Query(None, description="Filter by residual risk level"),
    mitigation_status: Optional[str] = Query(None, description="Filter by mitigation status"),
    q: Optional[str] = Query(None, description="Search by name or description"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])),
):
    """List risk entries with optional filters."""
    query = db.query(RiskEntry)

    if category_id:
        query = query.filter(RiskEntry.category_id == category_id)

    if inherent_risk_level:
        levels = [l.strip().lower() for l in inherent_risk_level.split(",")]
        query = query.filter(RiskEntry.inherent_risk_level.in_(levels))

    if residual_risk_level:
        levels = [l.strip().lower() for l in residual_risk_level.split(",")]
        query = query.filter(RiskEntry.residual_risk_level.in_(levels))

    if mitigation_status:
        statuses = [s.strip().lower() for s in mitigation_status.split(",")]
        query = query.filter(RiskEntry.mitigation_status.in_(statuses))

    if q:
        like = f"%{q}%"
        query = query.filter(
            (RiskEntry.name.ilike(like)) | (RiskEntry.description.ilike(like))
        )

    total = query.count()
    entries = query.order_by(RiskEntry.updated_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [entry_to_dict(e, db) for e in entries],
    }


@router.post("/entries")
async def create_risk_entry(
    payload: RiskEntryCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    """Create a new risk entry."""
    category = db.query(RiskCategory).filter(RiskCategory.id == payload.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    entry = RiskEntry(
        risk_id=generate_risk_id(),
        category_id=payload.category_id,
        name=payload.name,
        description=payload.description,
        inherent_risk_level=payload.inherent_risk_level,
        residual_risk_level=payload.residual_risk_level,
        likelihood=payload.likelihood,
        impact=payload.impact,
        mitigation_status=payload.mitigation_status,
        control_owner=payload.control_owner,
        review_date=payload.review_date,
        metadata_json=payload.metadata,
        created_at=utc_now(),
        updated_at=utc_now(),
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)

    # Send WebSocket notification
    try:
        await ws_manager.send_notification(NotificationEvent(
            event_type=EventType.RISK_ENTRY_CREATED,
            title="Risk Entry Created",
            message=f"New risk entry created: {entry.name}",
            data={"risk_id": entry.risk_id, "name": entry.name, "category": category.name},
            priority="normal",
            link=f"/compliance/risk-map?risk={entry.id}",
        ))
    except Exception:
        pass

    return entry_to_dict(entry, db)


@router.get("/entries/{entry_id}")
def get_risk_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])),
):
    """Get a risk entry by ID."""
    entry = db.query(RiskEntry).filter(RiskEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Risk entry not found")

    return entry_to_dict(entry, db)


@router.patch("/entries/{entry_id}")
def update_risk_entry(
    entry_id: int,
    payload: RiskEntryUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    """Update a risk entry."""
    entry = db.query(RiskEntry).filter(RiskEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Risk entry not found")

    if payload.category_id is not None and payload.category_id != entry.category_id:
        category = db.query(RiskCategory).filter(RiskCategory.id == payload.category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "metadata" in update_data:
        update_data["metadata_json"] = update_data.pop("metadata")

    for key, value in update_data.items():
        setattr(entry, key, value)

    entry.updated_at = utc_now()
    db.commit()
    db.refresh(entry)

    return entry_to_dict(entry, db)


@router.delete("/entries/{entry_id}")
def delete_risk_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance"])),
):
    """Delete a risk entry."""
    entry = db.query(RiskEntry).filter(RiskEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Risk entry not found")

    db.delete(entry)
    db.commit()

    return {"message": "Risk entry deleted", "risk_id": entry.risk_id}


# ========== Obligation-Risk Links ==========

@router.get("/entries/{entry_id}/obligations")
def list_risk_entry_obligations(
    entry_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])),
):
    """List obligations linked to a risk entry."""
    entry = db.query(RiskEntry).filter(RiskEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Risk entry not found")

    links = db.query(ObligationRiskLink).filter(
        ObligationRiskLink.risk_entry_id == entry_id
    ).all()

    return {"items": [link_to_dict(l, db) for l in links]}


@router.post("/entries/{entry_id}/obligations")
async def link_obligation_to_risk(
    entry_id: int,
    payload: ObligationRiskLinkCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    """Link an obligation to a risk entry."""
    entry = db.query(RiskEntry).filter(RiskEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Risk entry not found")

    obligation = db.query(RegulatoryObligation).filter(
        RegulatoryObligation.id == payload.obligation_id
    ).first()
    if not obligation:
        raise HTTPException(status_code=404, detail="Obligation not found")

    # Check for existing link
    existing = db.query(ObligationRiskLink).filter(
        ObligationRiskLink.risk_entry_id == entry_id,
        ObligationRiskLink.obligation_id == payload.obligation_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Obligation already linked to this risk")

    link = ObligationRiskLink(
        obligation_id=payload.obligation_id,
        risk_entry_id=entry_id,
        link_type=payload.link_type,
        notes=payload.notes,
        created_by=current_user.email,
        created_at=utc_now(),
    )

    db.add(link)
    db.commit()
    db.refresh(link)

    return link_to_dict(link, db)


@router.delete("/links/{link_id}")
def delete_obligation_risk_link(
    link_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
):
    """Remove an obligation-risk link."""
    link = db.query(ObligationRiskLink).filter(ObligationRiskLink.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    db.delete(link)
    db.commit()

    return {"message": "Link removed"}


# ========== Risk Map Overview ==========

@router.get("/map")
def get_risk_map(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])),
):
    """Get aggregated risk map overview."""
    total_categories = db.query(func.count(RiskCategory.id)).filter(
        RiskCategory.status == "active"
    ).scalar() or 0

    total_entries = db.query(func.count(RiskEntry.id)).scalar() or 0

    # Count by inherent risk level
    by_inherent = {}
    for level in ["low", "medium", "high", "critical"]:
        count = db.query(func.count(RiskEntry.id)).filter(
            RiskEntry.inherent_risk_level == level
        ).scalar() or 0
        by_inherent[level] = count

    # Count by residual risk level
    by_residual = {}
    for level in ["low", "medium", "high", "critical"]:
        count = db.query(func.count(RiskEntry.id)).filter(
            RiskEntry.residual_risk_level == level
        ).scalar() or 0
        by_residual[level] = count

    # Count by mitigation status
    by_mitigation = {}
    for status in ["not_started", "in_progress", "implemented", "monitored"]:
        count = db.query(func.count(RiskEntry.id)).filter(
            RiskEntry.mitigation_status == status
        ).scalar() or 0
        by_mitigation[status] = count

    # Count by category
    categories = db.query(RiskCategory).filter(RiskCategory.status == "active").all()
    by_category = []
    for cat in categories:
        count = db.query(func.count(RiskEntry.id)).filter(
            RiskEntry.category_id == cat.id
        ).scalar() or 0
        by_category.append({
            "id": cat.id,
            "category_id": cat.category_id,
            "name": cat.name,
            "entries_count": count,
        })

    # High priority risks (high or critical inherent level)
    high_priority = db.query(RiskEntry).filter(
        RiskEntry.inherent_risk_level.in_(["high", "critical"])
    ).order_by(RiskEntry.updated_at.desc()).limit(10).all()

    return {
        "total_categories": total_categories,
        "total_entries": total_entries,
        "by_inherent_level": by_inherent,
        "by_residual_level": by_residual,
        "by_mitigation_status": by_mitigation,
        "by_category": by_category,
        "high_priority_risks": [entry_to_dict(e, db) for e in high_priority],
    }


@router.get("/heatmap")
def get_risk_heatmap(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer", "auditor", "user"])),
):
    """Get risk heat map data (likelihood x impact matrix)."""
    likelihoods = ["rare", "unlikely", "possible", "likely", "almost_certain"]
    impacts = ["insignificant", "minor", "moderate", "major", "catastrophic"]

    cells = []
    total_risks = 0

    for likelihood in likelihoods:
        for impact in impacts:
            entries = db.query(RiskEntry).filter(
                RiskEntry.likelihood == likelihood,
                RiskEntry.impact == impact,
            ).all()

            count = len(entries)
            total_risks += count

            cells.append({
                "likelihood": likelihood,
                "impact": impact,
                "count": count,
                "risk_ids": [e.risk_id for e in entries],
            })

    return {
        "cells": cells,
        "total_risks": total_risks,
    }
