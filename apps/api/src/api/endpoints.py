from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from src.database import get_db
from src.models import models
from src.schemas import schemas
from src.search import search_documents
from src.ingestion.diff_analyzer import DiffAnalyzer

router = APIRouter()

@router.get("/search", response_model=schemas.SearchResponse)
def search_api(
    q: Optional[str] = None,
    type: Optional[str] = None,
    status: Optional[str] = None,
    compliance_domain: Optional[str] = None,
    risk_level: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    page: int = 1,
    limit: int = 10,
):
    """
    Search documents using OpenSearch with filters including compliance domain and risk level.
    """
    # Calculate offset
    from_ = (page - 1) * limit
    
    results = search_documents(
        q=q,
        doc_type=type,
        status=status,
        compliance_domain=compliance_domain,
        risk_level=risk_level,
        date_from=date_from,
        date_to=date_to,
        from_=from_,
        size=limit
    )

    return results

@router.get("/documents/{celex}", response_model=schemas.LegalDocumentRead)
def get_document(celex: str, db: Session = Depends(get_db)):
    """
    Get a specific legal document by CELEX.
    """
    db_doc = db.query(models.LegalDocument).filter(models.LegalDocument.celex == celex).first()
    if not db_doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return db_doc

# --- Monitoring Rules Management ---

@router.post("/rules", response_model=schemas.MonitoringRuleRead)
def create_rule(rule: schemas.MonitoringRuleCreate, db: Session = Depends(get_db)):
    db_rule = models.MonitoringRule(**rule.model_dump())
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule

@router.get("/rules", response_model=List[schemas.MonitoringRuleRead])
def read_rules(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.MonitoringRule).offset(skip).limit(limit).all()

@router.get("/rules/{rule_id}", response_model=schemas.MonitoringRuleRead)
def get_rule(rule_id: str, db: Session = Depends(get_db)):
    db_rule = db.query(models.MonitoringRule).filter(models.MonitoringRule.rule_id == rule_id).first()
    if not db_rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return db_rule

# --- Transaction Alerts Management ---

@router.get("/alerts", response_model=List[schemas.AlertRead])
def read_alerts(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(models.Alert)
    if status:
        query = query.filter(models.Alert.status == status)
    if severity:
        query = query.filter(models.Alert.severity == severity)
    
    return query.order_by(models.Alert.created_at.desc()).offset(skip).limit(limit).all()

@router.get("/alerts/{alert_id}", response_model=schemas.AlertRead)
def get_alert_detail(alert_id: str, db: Session = Depends(get_db)):
    alert = db.query(models.Alert).filter(models.Alert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert

@router.post("/alerts/{alert_id}/action")
def take_alert_action(alert_id: str, action: Dict[str, str], db: Session = Depends(get_db)):
    alert = db.query(models.Alert).filter(models.Alert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Simple status update for now
    alert.status = action.get("status", alert.status)
    alert.resolution_notes = action.get("notes", alert.resolution_notes)
    db.commit()
    return {"status": "success", "new_status": alert.status}

@router.get("/documents/{celex}/versions")
def get_document_versions(celex: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get all versions of a document.
    """
    doc = db.query(models.LegalDocument).filter(models.LegalDocument.celex == celex).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    versions = db.query(models.LegalVersion).filter(models.LegalVersion.doc_id == doc.id).all()

    return {
        "celex": celex,
        "title": doc.title,
        "versions": [
            {
                "id": v.id,
                "kind": v.kind,
                "language": v.language,
                "source_url": v.source_url,
                "retrieved_at": v.retrieved_at.isoformat() if v.retrieved_at else None
            }
            for v in versions
        ]
    }

@router.get("/documents/{celex}/diff")
def compare_document_versions(
    celex: str,
    version1_id: Optional[int] = Query(None, description="ID of first version (older)"),
    version2_id: Optional[int] = Query(None, description="ID of second version (newer)"),
    format: str = Query("json", description="Output format: json or html"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Compare two versions of a document and return the diff.
    If version IDs are not provided, compares the two most recent versions.
    """
    doc = db.query(models.LegalDocument).filter(models.LegalDocument.celex == celex).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get versions
    versions = db.query(models.LegalVersion).filter(
        models.LegalVersion.doc_id == doc.id
    ).order_by(models.LegalVersion.retrieved_at.desc()).all()

    if len(versions) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 versions required for comparison"
        )

    # Select versions to compare
    if version1_id and version2_id:
        version1 = db.query(models.LegalVersion).filter(models.LegalVersion.id == version1_id).first()
        version2 = db.query(models.LegalVersion).filter(models.LegalVersion.id == version2_id).first()
        if not version1 or not version2:
            raise HTTPException(status_code=404, detail="Version not found")
    else:
        # Use two most recent versions
        version2 = versions[0]  # Newest
        version1 = versions[1]  # Second newest

    # For now, we'll use the document's full_text as a proxy
    # In a complete implementation, versions would have their own content
    if not doc.full_text:
        raise HTTPException(
            status_code=400,
            detail="Document content not available for comparison"
        )

    # Initialize diff analyzer
    analyzer = DiffAnalyzer()

    # For demo purposes, compare document with itself (showing the structure)
    # In production, you'd fetch actual version content
    old_text = doc.full_text
    new_text = doc.full_text  # Replace with actual version content

    old_articles = doc.article_breakdown.get("articles", []) if doc.article_breakdown else []
    new_articles = doc.article_breakdown.get("articles", []) if doc.article_breakdown else []

    if format == "html":
        html_diff = analyzer.generate_html_diff(old_text, new_text)
        return {
            "celex": celex,
            "version1_id": version1.id,
            "version2_id": version2.id,
            "format": "html",
            "diff_html": html_diff
        }
    else:
        diff_result = analyzer.compare_documents(old_text, new_text, old_articles, new_articles)
        return {
            "celex": celex,
            "title": doc.title,
            "version1": {
                "id": version1.id,
                "retrieved_at": version1.retrieved_at.isoformat() if version1.retrieved_at else None
            },
            "version2": {
                "id": version2.id,
                "retrieved_at": version2.retrieved_at.isoformat() if version2.retrieved_at else None
            },
            "diff": diff_result
        }
