from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from datetime import datetime
from src.database import get_db
from src import models
from src.schemas import schemas
from src.schemas import transaction_schemas
from src.search import search_documents
from src.ingestion.diff_analyzer import DiffAnalyzer
from src.api import monitoring_rules as monitoring_rules_api
from src.auth.dependencies import get_current_user
from src.tenancy.queries import require_tenant
from src.middleware import limiter, RateLimits

router = APIRouter(
    dependencies=[Depends(get_current_user), Depends(require_tenant)]
)

_DEPRECATION_WARNING = '299 - "Deprecated endpoint; use /api/monitoring-rules"'


def _set_deprecation_headers(response: Response) -> None:
    response.headers["Warning"] = _DEPRECATION_WARNING
    response.headers["X-Deprecated"] = "true"
    response.headers["X-Deprecated-Use"] = "/api/monitoring-rules"


def _legacy_rule_from_model(rule: models.MonitoringRule) -> schemas.MonitoringRuleRead:
    return schemas.MonitoringRuleRead(
        id=rule.id,
        rule_id=rule.rule_id,
        name=rule.name,
        description=rule.description,
        category=rule.category,
        severity=rule.severity,
        priority=rule.priority,
        enabled=rule.enabled,
        is_template=rule.is_template,
        conditions_json=rule.conditions,
        aggregation_json=rule.thresholds,
        regulatory_source_id=rule.regulatory_source_id,
        regulation_article=rule.regulation_article,
        regulatory_requirement=rule.regulatory_requirement,
        alert_count=rule.alert_count,
        true_positive_rate=rule.true_positive_rate,
        false_positive_rate=rule.false_positive_rate,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )

@router.get("/search", response_model=schemas.SearchResponse)
@limiter.limit(RateLimits.SEARCH)
def search_api(
    request: Request,
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
@limiter.limit(RateLimits.READ)
def get_document(request: Request, celex: str, db: Session = Depends(get_db)):
    """
    Get a specific legal document by CELEX.
    """
    db_doc = db.query(models.LegalDocument).filter(models.LegalDocument.celex == celex).first()
    if not db_doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return db_doc

@router.get("/documents/{celex}/versions")
@limiter.limit(RateLimits.READ)
def get_document_versions(request: Request, celex: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
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
@limiter.limit(RateLimits.READ)
def compare_document_versions(
    request: Request,
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


# --- Legacy Monitoring Rules Management (Deprecated) ---

@router.post("/rules", response_model=schemas.MonitoringRuleRead, deprecated=True)
@limiter.limit(RateLimits.CREATE)
def create_rule(
    request: Request,
    rule: schemas.MonitoringRuleCreate,
    response: Response,
    db: Session = Depends(get_db),
):
    _set_deprecation_headers(response)
    new_rule_payload = transaction_schemas.MonitoringRuleCreate(
        name=rule.name,
        description=rule.description,
        category=rule.category,
        severity=rule.severity,
        conditions=rule.conditions_json,
        thresholds=rule.aggregation_json,
        regulatory_source_id=rule.regulatory_source_id,
        regulation_article=rule.regulation_article,
        regulatory_requirement=rule.regulatory_requirement,
        enabled=rule.enabled,
    )
    created = monitoring_rules_api.create_rule(new_rule_payload, db)

    if rule.priority is not None or rule.is_template:
        created.priority = rule.priority
        created.is_template = rule.is_template
        version = db.query(models.RuleVersion).filter(
            models.RuleVersion.rule_id == created.id,
            models.RuleVersion.version_number == created.version,
        ).first()
        if version:
            version.priority = created.priority
        db.commit()
        db.refresh(created)

    return _legacy_rule_from_model(created)


@router.get("/rules", response_model=List[schemas.MonitoringRuleRead], deprecated=True)
@limiter.limit(RateLimits.READ)
def read_rules(
    request: Request,
    response: Response,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    _set_deprecation_headers(response)
    rules = monitoring_rules_api.list_rules(skip, limit, None, None, None, db)
    return [_legacy_rule_from_model(rule) for rule in rules]


@router.get("/rules/{rule_id}", response_model=schemas.MonitoringRuleRead, deprecated=True)
@limiter.limit(RateLimits.READ)
def get_rule(
    request: Request,
    rule_id: str,
    response: Response,
    tenant_id: str = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    _set_deprecation_headers(response)
    rule = monitoring_rules_api.get_rule(rule_id, db, tenant_id)
    return _legacy_rule_from_model(rule)
