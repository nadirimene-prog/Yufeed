"""
Compliance-specific API endpoints for AMLRO features.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from src.database import get_db
from src.models import models
from src.models.annotation import Annotation
from src.schemas import schemas
from src.ai.analyzer import analyze_document
from pydantic import BaseModel

router = APIRouter(prefix="/compliance", tags=["compliance"])

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

@router.post("/documents/{celex}/analyze")
def analyze_document_endpoint(
    celex: str,
    request: AnalyzeRequest,
    db: Session = Depends(get_db)
):
    """
    Trigger AI analysis on a document.
    """
    doc = db.query(models.LegalDocument).filter(models.LegalDocument.celex == celex).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check if already analyzed
    if doc.analyzed_at and not request.force:
        return {
            "message": "Document already analyzed",
            "analyzed_at": doc.analyzed_at,
            "use_force": "Set force=true to re-analyze"
        }
    
    # Perform analysis
    try:
        analysis_results = analyze_document({
            "celex": doc.celex,
            "title": doc.title,
            "publication_date": doc.publication_date
        })
        
        # Update document with results
        doc.compliance_domain = analysis_results.get("compliance_domain")
        doc.risk_level = analysis_results.get("risk_level")
        doc.obligations_json = analysis_results.get("obligations_json")
        doc.implementation_deadline = analysis_results.get("implementation_deadline")
        doc.ai_summary = analysis_results.get("ai_summary")
        doc.analyzed_at = analysis_results.get("analyzed_at")
        
        db.commit()
        db.refresh(doc)
        
        return {
            "message": "Analysis complete",
            "results": analysis_results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.get("/documents/{celex}/annotations", response_model=List[AnnotationResponse])
def get_annotations(celex: str, db: Session = Depends(get_db)):
    """
    Get all annotations for a document.
    """
    doc = db.query(models.LegalDocument).filter(models.LegalDocument.celex == celex).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    annotations = db.query(Annotation).filter(Annotation.doc_id == doc.id).order_by(Annotation.created_at.desc()).all()
    return annotations

@router.post("/documents/{celex}/annotations", response_model=AnnotationResponse)
def create_annotation(
    celex: str,
    annotation: AnnotationCreate,
    db: Session = Depends(get_db)
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
        article_reference=annotation.article_reference
    )
    db.add(db_annotation)
    db.commit()
    db.refresh(db_annotation)
    
    return db_annotation

@router.delete("/annotations/{annotation_id}")
def delete_annotation(annotation_id: int, db: Session = Depends(get_db)):
    """
    Delete an annotation.
    """
    annotation = db.query(Annotation).filter(Annotation.id == annotation_id).first()
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    db.delete(annotation)
    db.commit()
    return {"message": "Annotation deleted"}

@router.get("/dashboard/metrics", response_model=ComplianceMetrics)
def get_dashboard_metrics(db: Session = Depends(get_db)):
    """
    Get compliance dashboard metrics.
    """
    total = db.query(models.LegalDocument).count()
    
    high_risk = db.query(models.LegalDocument).filter(
        models.LegalDocument.risk_level == "high"
    ).count()
    
    medium_risk = db.query(models.LegalDocument).filter(
        models.LegalDocument.risk_level == "medium"
    ).count()
    
    low_risk = db.query(models.LegalDocument).filter(
        models.LegalDocument.risk_level == "low"
    ).count()
    
    # Upcoming deadlines
    now = datetime.utcnow()
    deadlines_30d = db.query(models.LegalDocument).filter(
        models.LegalDocument.implementation_deadline.between(now, now + timedelta(days=30))
    ).count()
    
    deadlines_60d = db.query(models.LegalDocument).filter(
        models.LegalDocument.implementation_deadline.between(now, now + timedelta(days=60))
    ).count()
    
    deadlines_90d = db.query(models.LegalDocument).filter(
        models.LegalDocument.implementation_deadline.between(now, now + timedelta(days=90))
    ).count()
    
    # By domain
    from sqlalchemy import func
    domain_counts = db.query(
        models.LegalDocument.compliance_domain,
        func.count(models.LegalDocument.id)
    ).group_by(models.LegalDocument.compliance_domain).all()
    
    by_domain = {domain or "unknown": count for domain, count in domain_counts}
    
    return ComplianceMetrics(
        total_documents=total,
        high_risk_count=high_risk,
        medium_risk_count=medium_risk,
        low_risk_count=low_risk,
        upcoming_deadlines_30d=deadlines_30d,
        upcoming_deadlines_60d=deadlines_60d,
        upcoming_deadlines_90d=deadlines_90d,
        by_domain=by_domain
    )

@router.get("/documents/high-risk")
def get_high_risk_documents(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get high-risk documents requiring attention.
    """
    docs = db.query(models.LegalDocument).filter(
        models.LegalDocument.risk_level == "high"
    ).order_by(models.LegalDocument.publication_date.desc()).limit(limit).all()
    
    return [schemas.LegalDocumentRead.from_orm(doc) for doc in docs]

@router.get("/documents/deadlines")
def get_upcoming_deadlines(
    days: int = 90,
    db: Session = Depends(get_db)
):
    """
    Get documents with upcoming implementation deadlines.
    """
    now = datetime.utcnow()
    cutoff = now + timedelta(days=days)
    
    docs = db.query(models.LegalDocument).filter(
        models.LegalDocument.implementation_deadline.between(now, cutoff)
    ).order_by(models.LegalDocument.implementation_deadline).all()
    
    return [schemas.LegalDocumentRead.from_orm(doc) for doc in docs]
