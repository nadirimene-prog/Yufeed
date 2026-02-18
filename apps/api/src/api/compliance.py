"""
Compliance-specific API endpoints for AMLRO features.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, timezone


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


from src.database import get_db
from src.auth.dependencies import require_any_role
from src import models
from src.models.annotation import Annotation
from src.schemas import schemas
from src.schemas import compliance as comp_schemas
from src.ai.analyzer import analyze_document
from src.services.obligation_service import seed_obligations_for_doc
from src.compliance.scope import infer_scope_tags
from pydantic import BaseModel
from src.models import compliance as comp_models
from src.middleware import limiter, RateLimits

router = APIRouter(
    prefix="/compliance",
    tags=["compliance"],
    dependencies=[Depends(require_any_role(["admin"]))],
)


# Pydantic models for requests/responses
class AnalyzeRequest(BaseModel):
    force: bool = False  # Force re-analysis even if already analyzed


class AnnotationCreate(BaseModel):
    content: str
    article_reference: Optional[str] = None
    user_email: str


class AnnotationResponse(BaseModel):
    id: int
    content: str
    article_reference: Optional[str]
    user_email: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ComplianceMetrics(BaseModel):
    total_documents: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    upcoming_deadlines_30d: int
    upcoming_deadlines_60d: int
    upcoming_deadlines_90d: int
    by_domain: dict


class TimelineEventResponse(BaseModel):
    id: str
    date: datetime
    type: str
    title: str
    description: Optional[str] = None
    status: str
    related_doc_celex: Optional[str] = None


def _relation_to_timeline_type(relation_type: str) -> str:
    relation = (relation_type or "").lower()
    if "repeal" in relation:
        return "REPEAL"
    if "correct" in relation:
        return "CORRIGENDUM"
    if "consolid" in relation:
        return "CONSOLIDATION"
    if "amend" in relation:
        return "AMENDMENT"
    if "base" in relation:
        return "PROPOSAL"
    return "AMENDMENT"


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _event_status_for_date(event_date: datetime, now: datetime) -> str:
    return "future" if _as_utc(event_date) > _as_utc(now) else "completed"


@router.post("/documents/{celex}/analyze")
@limiter.limit(RateLimits.AI_ANALYSIS)
def analyze_document_endpoint(
    request: Request, celex: str, payload: AnalyzeRequest, db: Session = Depends(get_db)
):
    """
    Trigger AI analysis on a document.
    """
    doc = db.query(models.LegalDocument).filter(models.LegalDocument.celex == celex).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check if already analyzed
    if doc.analyzed_at and not payload.force:
        return {
            "message": "Document already analyzed",
            "analyzed_at": doc.analyzed_at,
            "use_force": "Set force=true to re-analyze",
        }

    # Perform analysis
    try:
        article_breakdown = None
        if isinstance(doc.article_breakdown, dict):
            article_breakdown = doc.article_breakdown.get("articles")
        elif isinstance(doc.article_breakdown, list):
            article_breakdown = doc.article_breakdown

        analysis_results = analyze_document(
            {
                "celex": doc.celex,
                "title": doc.title,
                "publication_date": doc.publication_date,
                "full_text": doc.full_text,
                "article_breakdown": article_breakdown,
            }
        )

        # Update document with results
        doc.compliance_domain = analysis_results.get("compliance_domain")
        doc.risk_level = analysis_results.get("risk_level")
        doc.obligations_json = analysis_results.get("obligations_json")
        doc.implementation_deadline = analysis_results.get("implementation_deadline")
        doc.ai_summary = analysis_results.get("ai_summary")
        doc.analyzed_at = analysis_results.get("analyzed_at")
        scope_tags = infer_scope_tags(
            doc.title,
            doc.full_text,
            doc.ai_summary,
            doc.obligations_json,
        )
        if scope_tags:
            doc.scope_tags = scope_tags

        db.commit()
        db.refresh(doc)
        seed_obligations_for_doc(db, doc, allow_existing=True)

        return {"message": "Analysis complete", "results": analysis_results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/documents/{celex}/annotations", response_model=List[AnnotationResponse])
@limiter.limit(RateLimits.READ)
def get_annotations(request: Request, celex: str, db: Session = Depends(get_db)):
    """
    Get all annotations for a document.
    """
    doc = db.query(models.LegalDocument).filter(models.LegalDocument.celex == celex).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    annotations = (
        db.query(Annotation)
        .filter(Annotation.doc_id == doc.id)
        .order_by(Annotation.created_at.desc())
        .all()
    )
    return annotations


@router.post("/documents/{celex}/annotations", response_model=AnnotationResponse)
@limiter.limit(RateLimits.CREATE)
def create_annotation(
    request: Request, celex: str, annotation: AnnotationCreate, db: Session = Depends(get_db)
):
    """
    Create a new annotation on a document.
    """
    doc = db.query(models.LegalDocument).filter(models.LegalDocument.celex == celex).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    db_annotation = Annotation(
        doc_id=doc.id,
        user_email=annotation.user_email,
        content=annotation.content,
        article_reference=annotation.article_reference,
    )
    db.add(db_annotation)
    db.commit()
    db.refresh(db_annotation)

    return db_annotation


@router.delete("/annotations/{annotation_id}")
@limiter.limit(RateLimits.DELETE)
def delete_annotation(request: Request, annotation_id: int, db: Session = Depends(get_db)):
    """
    Delete an annotation.
    """
    annotation = db.query(Annotation).filter(Annotation.id == annotation_id).first()
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    db.delete(annotation)
    db.commit()
    return {"message": "Annotation deleted"}


@router.get("/documents/{celex}/timeline", response_model=List[TimelineEventResponse])
@limiter.limit(RateLimits.READ)
def get_document_timeline(request: Request, celex: str, db: Session = Depends(get_db)):
    """
    Get timeline events for a legal document.
    """
    doc = db.query(models.LegalDocument).filter(models.LegalDocument.celex == celex).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    now = utc_now()
    timeline_events: List[TimelineEventResponse] = []

    if doc.publication_date:
        publication_date = _as_utc(doc.publication_date)
        timeline_events.append(
            TimelineEventResponse(
                id=f"{celex}:publication",
                date=publication_date,
                type="PUBLICATION",
                title="Published",
                description="Document publication date",
                status=_event_status_for_date(publication_date, now),
            )
        )

    if doc.entry_into_force_date:
        entry_into_force_date = _as_utc(doc.entry_into_force_date)
        timeline_events.append(
            TimelineEventResponse(
                id=f"{celex}:entry-into-force",
                date=entry_into_force_date,
                type="ENTRY_INTO_FORCE",
                title="Entered into force",
                description="Date when the act became legally binding",
                status=_event_status_for_date(entry_into_force_date, now),
            )
        )

    relations = (
        db.query(models.LegalRelation)
        .filter(
            (models.LegalRelation.from_doc_id == doc.id)
            | (models.LegalRelation.to_doc_id == doc.id)
        )
        .all()
    )

    for relation in relations:
        related_doc = (
            relation.to_document if relation.from_doc_id == doc.id else relation.from_document
        )
        if not related_doc:
            continue

        relation_date = (
            related_doc.publication_date or related_doc.last_modified or doc.last_modified
        )
        if not relation_date:
            continue
        relation_date = _as_utc(relation_date)

        if relation.from_doc_id == doc.id:
            direction_text = f"Relates to {related_doc.celex} via {relation.relation_type}"
            title = f"{relation.relation_type.replace('_', ' ').title()} {related_doc.celex}"
        else:
            direction_text = (
                f"{related_doc.celex} relates to this document via {relation.relation_type}"
            )
            title = f"{related_doc.celex} {relation.relation_type.replace('_', ' ').title()}"

        timeline_events.append(
            TimelineEventResponse(
                id=f"{celex}:relation:{relation.id}",
                date=relation_date,
                type=_relation_to_timeline_type(relation.relation_type),
                title=title,
                description=direction_text,
                status=_event_status_for_date(relation_date, now),
                related_doc_celex=related_doc.celex,
            )
        )

    versions = (
        db.query(models.LegalVersion)
        .filter(models.LegalVersion.doc_id == doc.id)
        .order_by(models.LegalVersion.retrieved_at.desc())
        .all()
    )
    for version in versions:
        if not version.retrieved_at:
            continue
        version_date = _as_utc(version.retrieved_at)

        version_kind = (version.kind or "").lower()
        if version_kind == "corrigendum":
            event_type = "CORRIGENDUM"
            title = "Corrigendum published"
        elif version_kind == "consolidated":
            event_type = "CONSOLIDATION"
            title = "Consolidated version available"
        else:
            continue

        timeline_events.append(
            TimelineEventResponse(
                id=f"{celex}:version:{version.id}",
                date=version_date,
                type=event_type,
                title=title,
                description=f"{version.kind} ({version.language})",
                status=_event_status_for_date(version_date, now),
            )
        )

    timeline_events.sort(key=lambda e: e.date, reverse=True)
    return timeline_events


@router.get("/dashboard/metrics", response_model=ComplianceMetrics)
@limiter.limit(RateLimits.READ)
def get_dashboard_metrics(request: Request, db: Session = Depends(get_db)):
    """
    Get compliance dashboard metrics.
    """
    total = db.query(models.LegalDocument).count()

    high_risk = (
        db.query(models.LegalDocument).filter(models.LegalDocument.risk_level == "high").count()
    )

    medium_risk = (
        db.query(models.LegalDocument).filter(models.LegalDocument.risk_level == "medium").count()
    )

    low_risk = (
        db.query(models.LegalDocument).filter(models.LegalDocument.risk_level == "low").count()
    )

    # Upcoming deadlines
    now = utc_now()
    deadlines_30d = (
        db.query(models.LegalDocument)
        .filter(models.LegalDocument.implementation_deadline.between(now, now + timedelta(days=30)))
        .count()
    )

    deadlines_60d = (
        db.query(models.LegalDocument)
        .filter(models.LegalDocument.implementation_deadline.between(now, now + timedelta(days=60)))
        .count()
    )

    deadlines_90d = (
        db.query(models.LegalDocument)
        .filter(models.LegalDocument.implementation_deadline.between(now, now + timedelta(days=90)))
        .count()
    )

    # By domain
    from sqlalchemy import func

    domain_counts = (
        db.query(models.LegalDocument.compliance_domain, func.count(models.LegalDocument.id))
        .group_by(models.LegalDocument.compliance_domain)
        .all()
    )

    by_domain = {domain or "unknown": count for domain, count in domain_counts}

    return ComplianceMetrics(
        total_documents=total,
        high_risk_count=high_risk,
        medium_risk_count=medium_risk,
        low_risk_count=low_risk,
        upcoming_deadlines_30d=deadlines_30d,
        upcoming_deadlines_60d=deadlines_60d,
        upcoming_deadlines_90d=deadlines_90d,
        by_domain=by_domain,
    )


@router.get("/documents/high-risk")
@limiter.limit(RateLimits.READ)
def get_high_risk_documents(request: Request, limit: int = 10, db: Session = Depends(get_db)):
    """
    Get high-risk documents requiring attention.
    """
    docs = (
        db.query(models.LegalDocument)
        .filter(models.LegalDocument.risk_level == "high")
        .order_by(models.LegalDocument.publication_date.desc())
        .limit(limit)
        .all()
    )

    return [schemas.LegalDocumentRead.from_orm(doc) for doc in docs]


@router.get("/documents/deadlines")
@limiter.limit(RateLimits.READ)
def get_upcoming_deadlines(request: Request, days: int = 90, db: Session = Depends(get_db)):
    """
    Get documents with upcoming implementation deadlines.
    """
    now = utc_now()
    cutoff = now + timedelta(days=days)

    docs = (
        db.query(models.LegalDocument)
        .filter(models.LegalDocument.implementation_deadline.between(now, cutoff))
        .order_by(models.LegalDocument.implementation_deadline)
        .all()
    )

    return [schemas.LegalDocumentRead.from_orm(doc) for doc in docs]


# --- KYC/KYB Endpoints ---


@router.post("/kyc", response_model=comp_schemas.KYCProfileRead)
@limiter.limit(RateLimits.CREATE)
def create_kyc_profile(
    request: Request, profile: comp_schemas.KYCProfileCreate, db: Session = Depends(get_db)
):
    """
    Submit a new KYC application.
    """
    db_profile = comp_models.KYCProfile(
        **profile.model_dump(exclude={"type"}),
        status=comp_models.ComplianceStatus.PENDING,
        risk_level=comp_models.RiskLevel.LOW,  # Default, to be updated by risk engine
    )
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile


@router.post("/kyb", response_model=comp_schemas.KYBProfileRead)
@limiter.limit(RateLimits.CREATE)
def create_kyb_profile(
    request: Request, profile: comp_schemas.KYBProfileCreate, db: Session = Depends(get_db)
):
    """
    Submit a new KYB application.
    """
    db_profile = comp_models.KYBProfile(
        **profile.model_dump(exclude={"type"}),
        status=comp_models.ComplianceStatus.PENDING,
        risk_level=comp_models.RiskLevel.LOW,
    )
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)
    return db_profile


@router.get("/cases", response_model=List[comp_schemas.ComplianceProfileRead])
@limiter.limit(RateLimits.READ)
def get_compliance_cases(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Get list of compliance cases (KYC/KYB) for the dashboard.
    """
    query = db.query(comp_models.ComplianceProfile)

    if status:
        query = query.filter(comp_models.ComplianceProfile.status == status)

    if type:
        query = query.filter(comp_models.ComplianceProfile.type == type)

    profiles = (
        query.order_by(comp_models.ComplianceProfile.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return profiles


@router.get("/cases/{id}", response_model=comp_schemas.ComplianceProfileRead)
@limiter.limit(RateLimits.READ)
def get_compliance_case(request: Request, id: int, db: Session = Depends(get_db)):
    """
    Get detailed view of a compliance case.
    """
    profile = (
        db.query(comp_models.ComplianceProfile)
        .filter(comp_models.ComplianceProfile.id == id)
        .first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Case not found")

    # Polymorphic load should handle specific fields, but Pydantic might need help if strict
    # Ideally, we return the specific type (KYC or KYB) but the response model is generic Read
    # for list views. For detail views, we might want to return the specific subclass.
    # However, ComplianceProfileRead contains fields from both or we can genericize.
    # Let's verify if ComplianceProfileRead handles subclass fields.
    # Actually, polymorphic response models in FastAPI can be tricky.
    # For now, we return as is, assuming the client handles common fields + extra data if available.

    return profile


@router.post("/cases/{id}/review", response_model=comp_schemas.ComplianceProfileRead)
@limiter.limit(RateLimits.UPDATE)
def review_compliance_case(
    request: Request, id: int, review: comp_schemas.ReviewAction, db: Session = Depends(get_db)
):
    """
    Approve or Reject a compliance case.
    """
    profile = (
        db.query(comp_models.ComplianceProfile)
        .filter(comp_models.ComplianceProfile.id == id)
        .first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Case not found")

    if review.action == "approve":
        profile.status = comp_models.ComplianceStatus.APPROVED
    elif review.action == "reject":
        profile.status = comp_models.ComplianceStatus.REJECTED

    # Log the reason/note (could be added to a "ReviewHistory" table later)
    # For now we just update status

    db.commit()
    db.refresh(profile)
    return profile
