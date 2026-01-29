"""
API endpoints for Impact Assessment functionality.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)
from pydantic import BaseModel

from src.database import get_db
from src.models import models
from src.models.impact_assessment import (
    ImpactAssessment, ActionItem, GapAnalysis,
    ImpactLevel, BusinessArea, ActionStatus
)
from src.ai.impact_analyzer import ImpactAnalyzer

router = APIRouter(prefix="/impact", tags=["impact-assessment"])

# Pydantic models for requests/responses

class ActionItemCreate(BaseModel):
    title: str
    description: Optional[str] = None
    business_area: str
    priority: int = 3
    estimated_hours: Optional[int] = None
    complexity: Optional[str] = None
    assigned_to: Optional[str] = None
    target_date: Optional[datetime] = None


class ActionItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    target_date: Optional[datetime] = None
    progress_percentage: Optional[int] = None
    notes: Optional[str] = None


class ActionItemResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    business_area: str
    priority: int
    estimated_hours: Optional[int]
    complexity: Optional[str]
    assigned_to: Optional[str]
    status: str
    target_date: Optional[datetime]
    progress_percentage: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ImpactAssessmentResponse(BaseModel):
    id: int
    doc_id: int
    overall_impact_level: str
    executive_summary: Optional[str]
    affected_areas_json: Optional[dict]
    key_changes: Optional[dict]
    estimated_effort_hours: Optional[int]
    estimated_cost: Optional[int]
    requires_system_changes: bool
    requires_process_changes: bool
    requires_policy_updates: bool
    assessed_at: datetime
    action_items: List[ActionItemResponse]

    class Config:
        from_attributes = True


class AnalyzeRequest(BaseModel):
    force: bool = False


@router.post("/documents/{celex}/analyze")
def create_impact_assessment(
    celex: str,
    request: AnalyzeRequest = AnalyzeRequest(),
    db: Session = Depends(get_db)
):
    """
    Generate AI-powered impact assessment for a document.
    """
    # Get document
    doc = db.query(models.LegalDocument).filter(models.LegalDocument.celex == celex).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check if assessment already exists
    existing = db.query(ImpactAssessment).filter(ImpactAssessment.doc_id == doc.id).first()
    if existing and not request.force:
        return {
            "message": "Impact assessment already exists",
            "assessment_id": existing.id,
            "use_force": "Set force=true to regenerate"
        }

    # Prepare document data for analysis
    doc_data = {
        "celex": doc.celex,
        "title": doc.title,
        "type": doc.type,
        "publication_date": doc.publication_date.isoformat() if doc.publication_date else None,
        "compliance_domain": doc.compliance_domain,
        "risk_level": doc.risk_level,
        "implementation_deadline": doc.implementation_deadline.isoformat() if doc.implementation_deadline else None,
        "ai_summary": doc.ai_summary
    }

    # Run AI analysis
    analyzer = ImpactAnalyzer()
    analysis = analyzer.analyze_impact(doc_data)

    # Delete existing if force regeneration
    if existing and request.force:
        db.delete(existing)
        db.commit()

    # Create impact assessment
    assessment = ImpactAssessment(
        doc_id=doc.id,
        overall_impact_level=analysis["overall_impact_level"],
        executive_summary=analysis.get("executive_summary"),
        affected_areas_json={"areas": analysis.get("affected_areas", [])},
        key_changes={"changes": analysis.get("key_changes", [])},
        new_obligations=analysis.get("resource_estimates", {}),
        estimated_effort_hours=analysis.get("resource_estimates", {}).get("total_hours"),
        estimated_cost=analysis.get("resource_estimates", {}).get("total_cost_eur"),
        requires_system_changes=analysis.get("resource_estimates", {}).get("requires_system_changes", False),
        requires_process_changes=analysis.get("resource_estimates", {}).get("requires_process_changes", False),
        requires_policy_updates=analysis.get("resource_estimates", {}).get("requires_policy_updates", False),
        assessed_at=utc_now()
    )

    db.add(assessment)
    db.flush()  # Get assessment ID

    # Create action items
    for item_data in analysis.get("action_items", []):
        action = ActionItem(
            assessment_id=assessment.id,
            title=item_data.get("title", ""),
            description=item_data.get("description"),
            business_area=item_data.get("business_area", "compliance_function"),
            priority=item_data.get("priority", 3),
            estimated_hours=item_data.get("estimated_hours"),
            complexity=item_data.get("complexity"),
            status=ActionStatus.NOT_STARTED
        )
        db.add(action)

    # Create gap analyses
    for gap_data in analysis.get("gaps", []):
        gap = GapAnalysis(
            assessment_id=assessment.id,
            gap_category=gap_data.get("category", "process"),
            current_state=gap_data.get("current_state", ""),
            required_state=gap_data.get("required_state", ""),
            gap_description=gap_data.get("gap_description"),
            severity=gap_data.get("severity", "medium"),
            business_area=gap_data.get("business_area", "compliance_function"),
            remediation_approach=gap_data.get("remediation_approach"),
            estimated_cost=gap_data.get("estimated_cost"),
            estimated_timeline_days=gap_data.get("estimated_timeline_days")
        )
        db.add(gap)

    db.commit()
    db.refresh(assessment)

    return {
        "message": "Impact assessment created successfully",
        "assessment_id": assessment.id,
        "overall_impact": assessment.overall_impact_level,
        "action_items_count": len(analysis.get("action_items", [])),
        "gaps_count": len(analysis.get("gaps", []))
    }


@router.get("/documents/{celex}/assessment", response_model=ImpactAssessmentResponse)
def get_impact_assessment(celex: str, db: Session = Depends(get_db)):
    """
    Get impact assessment for a document.
    """
    doc = db.query(models.LegalDocument).filter(models.LegalDocument.celex == celex).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    assessment = db.query(ImpactAssessment).filter(ImpactAssessment.doc_id == doc.id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="No impact assessment found for this document")

    return assessment


@router.get("/documents/{celex}/actions", response_model=List[ActionItemResponse])
def get_action_items(celex: str, db: Session = Depends(get_db)):
    """
    Get all action items for a document.
    """
    doc = db.query(models.LegalDocument).filter(models.LegalDocument.celex == celex).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    assessment = db.query(ImpactAssessment).filter(ImpactAssessment.doc_id == doc.id).first()
    if not assessment:
        return []

    return assessment.action_items


@router.put("/actions/{action_id}", response_model=ActionItemResponse)
def update_action_item(
    action_id: int,
    update: ActionItemUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an action item (status, assignment, progress, etc.).
    """
    action = db.query(ActionItem).filter(ActionItem.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action item not found")

    # Update fields
    if update.title is not None:
        action.title = update.title
    if update.description is not None:
        action.description = update.description
    if update.status is not None:
        action.status = ActionStatus(update.status)
        if update.status == "completed" and not action.completed_at:
            action.completed_at = utc_now()
    if update.assigned_to is not None:
        action.assigned_to = update.assigned_to
    if update.target_date is not None:
        action.target_date = update.target_date
    if update.progress_percentage is not None:
        action.progress_percentage = update.progress_percentage
    if update.notes is not None:
        action.notes = update.notes

    action.updated_at = utc_now()

    db.commit()
    db.refresh(action)

    return action


@router.get("/actions/all")
def get_all_action_items(
    status: Optional[str] = None,
    business_area: Optional[str] = None,
    assigned_to: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all action items across all assessments with filters.
    """
    query = db.query(ActionItem)

    if status:
        query = query.filter(ActionItem.status == ActionStatus(status))
    if business_area:
        query = query.filter(ActionItem.business_area == BusinessArea(business_area))
    if assigned_to:
        query = query.filter(ActionItem.assigned_to == assigned_to)

    # Use eager loading to avoid N+1 query problem
    from sqlalchemy.orm import joinedload

    actions = query.options(
        joinedload(ActionItem.assessment).joinedload(ImpactAssessment.document)
    ).order_by(ActionItem.priority.asc(), ActionItem.target_date.asc()).all()

    # Build response with pre-loaded relationships
    results = []
    for action in actions:
        assessment = action.assessment
        if assessment and assessment.document:
            result = {
                **ActionItemResponse.from_orm(action).dict(),
                "document": {
                    "celex": assessment.document.celex,
                    "title": assessment.document.title
                }
            }
            results.append(result)

    return results


@router.get("/dashboard/stats")
def get_impact_dashboard_stats(db: Session = Depends(get_db)):
    """
    Get statistics for impact assessment dashboard.
    """
    total_assessments = db.query(ImpactAssessment).count()

    critical_high = db.query(ImpactAssessment).filter(
        ImpactAssessment.overall_impact_level.in_([ImpactLevel.CRITICAL, ImpactLevel.HIGH])
    ).count()

    total_actions = db.query(ActionItem).count()
    completed_actions = db.query(ActionItem).filter(ActionItem.status == ActionStatus.COMPLETED).count()
    blocked_actions = db.query(ActionItem).filter(ActionItem.status == ActionStatus.BLOCKED).count()

    # Actions by business area
    from sqlalchemy import func
    actions_by_area = db.query(
        ActionItem.business_area,
        func.count(ActionItem.id)
    ).group_by(ActionItem.business_area).all()

    # Total estimated effort
    total_effort = db.query(func.sum(ImpactAssessment.estimated_effort_hours)).scalar() or 0
    total_cost = db.query(func.sum(ImpactAssessment.estimated_cost)).scalar() or 0

    return {
        "total_assessments": total_assessments,
        "critical_high_impact": critical_high,
        "total_action_items": total_actions,
        "completed_actions": completed_actions,
        "blocked_actions": blocked_actions,
        "completion_rate": (completed_actions / total_actions * 100) if total_actions > 0 else 0,
        "actions_by_business_area": {area: count for area, count in actions_by_area},
        "total_estimated_effort_hours": total_effort,
        "total_estimated_cost_eur": total_cost
    }
