from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from src.database import get_db
from src import models
from src.schemas import schemas
from src.schemas import transaction_schemas
from src.search import search_documents
from src.ingestion.diff_analyzer import DiffAnalyzer
from src.auth.dependencies import get_current_user
from src.models.transaction_models import Alert, Case, MonitoringRule, UserRiskProfile
from src.tenancy.queries import require_tenant
from src.middleware import limiter, RateLimits
from pydantic import BaseModel

router = APIRouter(dependencies=[Depends(get_current_user), Depends(require_tenant)])

logger = logging.getLogger(__name__)


class OmniscientSearchItem(BaseModel):
    id: str
    type: str
    title: str
    subtitle: Optional[str] = None
    href: str


class OmniscientSearchResponse(BaseModel):
    query: str
    scope: str
    results: List[OmniscientSearchItem]


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
        size=limit,
    )

    return results


@router.get("/search/omniscient", response_model=OmniscientSearchResponse)
@limiter.limit(RateLimits.SEARCH)
def omniscient_search(
    request: Request,
    q: str = Query(..., min_length=1, max_length=200),
    scope: str = Query("all", description="Search scope: all|entities|alerts|cases|rules"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Tenant-scoped omniscient search for command palette navigation.

    Returns normalized hits across entities, alerts, cases, and monitoring rules.
    """
    normalized_scope = scope.lower()
    allowed_scopes = {"all", "entities", "alerts", "cases", "rules"}
    if normalized_scope not in allowed_scopes:
        raise HTTPException(status_code=400, detail=f"Unsupported scope: {scope}")

    needle = f"%{q.strip()}%"
    if needle == "%%":
        return OmniscientSearchResponse(query=q, scope=normalized_scope, results=[])

    tenant_id = require_tenant()
    results: list[OmniscientSearchItem] = []

    if normalized_scope in {"all", "entities"}:
        # Entity candidates from user risk profiles first, then alert/case subjects.
        risk_profiles = (
            db.query(UserRiskProfile)
            .filter(
                UserRiskProfile.tenant_id == tenant_id,
                UserRiskProfile.user_id.ilike(needle),
            )
            .order_by(UserRiskProfile.updated_at.desc())
            .limit(limit)
            .all()
        )

        seen_entity_ids: set[str] = set()
        for profile in risk_profiles:
            seen_entity_ids.add(profile.user_id)
            results.append(
                OmniscientSearchItem(
                    id=profile.user_id,
                    type="entity",
                    title=profile.user_id,
                    subtitle=f"Risk {profile.risk_level or 'unknown'}",
                    href=f"/entities/user/{profile.user_id}",
                )
            )

        if len(results) < limit:
            alert_entities = (
                db.query(Alert.user_id)
                .filter(
                    Alert.tenant_id == tenant_id,
                    Alert.user_id.isnot(None),
                    Alert.user_id.ilike(needle),
                )
                .distinct()
                .limit(limit)
                .all()
            )
            for (user_id,) in alert_entities:
                if not user_id or user_id in seen_entity_ids:
                    continue
                seen_entity_ids.add(user_id)
                results.append(
                    OmniscientSearchItem(
                        id=user_id,
                        type="entity",
                        title=user_id,
                        subtitle="Entity from alert activity",
                        href=f"/entities/user/{user_id}",
                    )
                )
                if len(results) >= limit:
                    break

            if len(results) < limit:
                case_entities = (
                    db.query(Case.subject_id)
                    .filter(
                        Case.tenant_id == tenant_id,
                        Case.subject_id.isnot(None),
                        Case.subject_id.ilike(needle),
                    )
                    .distinct()
                    .limit(limit)
                    .all()
                )
                for (subject_id,) in case_entities:
                    if not subject_id or subject_id in seen_entity_ids:
                        continue
                    seen_entity_ids.add(subject_id)
                    results.append(
                        OmniscientSearchItem(
                            id=subject_id,
                            type="entity",
                            title=subject_id,
                            subtitle="Entity from case activity",
                            href=f"/entities/user/{subject_id}",
                        )
                    )
                    if len(results) >= limit:
                        break

    if normalized_scope in {"all", "alerts"} and len(results) < limit:
        alert_hits = (
            db.query(Alert)
            .filter(
                Alert.tenant_id == tenant_id,
                (
                    Alert.alert_id.ilike(needle)
                    | Alert.alert_type.ilike(needle)
                    | Alert.user_id.ilike(needle)
                ),
            )
            .order_by(Alert.created_at.desc())
            .limit(limit)
            .all()
        )
        for alert in alert_hits:
            results.append(
                OmniscientSearchItem(
                    id=alert.alert_id,
                    type="alert",
                    title=alert.alert_id,
                    subtitle=f"{alert.alert_type} · {alert.user_id}",
                    href=f"/transaction-alerts?search={alert.alert_id}",
                )
            )
            if len(results) >= limit:
                break

    if normalized_scope in {"all", "cases"} and len(results) < limit:
        case_hits = (
            db.query(Case)
            .filter(
                Case.tenant_id == tenant_id,
                (
                    Case.case_id.ilike(needle)
                    | Case.subject_id.ilike(needle)
                    | Case.title.ilike(needle)
                ),
            )
            .order_by(Case.updated_at.desc(), Case.opened_at.desc())
            .limit(limit)
            .all()
        )
        for case in case_hits:
            results.append(
                OmniscientSearchItem(
                    id=case.case_id,
                    type="case",
                    title=case.case_id,
                    subtitle=f"{case.status} · {case.subject_id or 'no subject'}",
                    href=f"/cases?search={case.case_id}",
                )
            )
            if len(results) >= limit:
                break

    if normalized_scope in {"all", "rules"} and len(results) < limit:
        rule_hits = (
            db.query(MonitoringRule)
            .filter(
                MonitoringRule.tenant_id == tenant_id,
                (MonitoringRule.rule_id.ilike(needle) | MonitoringRule.name.ilike(needle)),
            )
            .order_by(MonitoringRule.updated_at.desc())
            .limit(limit)
            .all()
        )
        for rule in rule_hits:
            results.append(
                OmniscientSearchItem(
                    id=rule.rule_id,
                    type="rule",
                    title=rule.name,
                    subtitle=rule.rule_id,
                    href=f"/transaction-monitoring/rules/{rule.rule_id}",
                )
            )
            if len(results) >= limit:
                break

    # Preserve insertion order but deduplicate by (type, id).
    deduped: list[OmniscientSearchItem] = []
    seen_keys: set[tuple[str, str]] = set()
    for item in results:
        key = (item.type, item.id)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(item)
        if len(deduped) >= limit:
            break

    return OmniscientSearchResponse(query=q, scope=normalized_scope, results=deduped)


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
def get_document_versions(
    request: Request, celex: str, db: Session = Depends(get_db)
) -> Dict[str, Any]:
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
                "retrieved_at": v.retrieved_at.isoformat() if v.retrieved_at else None,
            }
            for v in versions
        ],
    }


@router.get("/documents/{celex}/diff")
@limiter.limit(RateLimits.READ)
def compare_document_versions(
    request: Request,
    celex: str,
    version1_id: Optional[int] = Query(None, description="ID of first version (older)"),
    version2_id: Optional[int] = Query(None, description="ID of second version (newer)"),
    format: str = Query("json", description="Output format: json or html"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Compare two versions of a document and return the diff.
    If version IDs are not provided, compares the two most recent versions.
    """
    doc = db.query(models.LegalDocument).filter(models.LegalDocument.celex == celex).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get versions
    versions = (
        db.query(models.LegalVersion)
        .filter(models.LegalVersion.doc_id == doc.id)
        .order_by(models.LegalVersion.retrieved_at.desc())
        .all()
    )

    if len(versions) < 2:
        raise HTTPException(status_code=400, detail="At least 2 versions required for comparison")

    # Select versions to compare
    if version1_id and version2_id:
        version1 = (
            db.query(models.LegalVersion).filter(models.LegalVersion.id == version1_id).first()
        )
        version2 = (
            db.query(models.LegalVersion).filter(models.LegalVersion.id == version2_id).first()
        )
        if not version1 or not version2:
            raise HTTPException(status_code=404, detail="Version not found")
    else:
        # Use two most recent versions
        version2 = versions[0]  # Newest
        version1 = versions[1]  # Second newest

    # For now, we'll use the document's full_text as a proxy
    # In a complete implementation, versions would have their own content
    if not doc.full_text:
        raise HTTPException(status_code=400, detail="Document content not available for comparison")

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
            "diff_html": html_diff,
        }
    else:
        diff_result = analyzer.compare_documents(old_text, new_text, old_articles, new_articles)
        return {
            "celex": celex,
            "title": doc.title,
            "version1": {
                "id": version1.id,
                "retrieved_at": (
                    version1.retrieved_at.isoformat() if version1.retrieved_at else None
                ),
            },
            "version2": {
                "id": version2.id,
                "retrieved_at": (
                    version2.retrieved_at.isoformat() if version2.retrieved_at else None
                ),
            },
            "diff": diff_result,
        }


# Note: Legacy /rules endpoints have been removed.
# Use /api/monitoring-rules instead.
