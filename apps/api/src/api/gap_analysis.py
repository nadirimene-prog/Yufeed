"""
Compliance Gap Analysis API

Endpoints for analyzing and managing compliance gaps.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime, timezone

from src.database import get_db
from src.auth.dependencies import require_any_role, CurrentUser
from src.services.gap_analyzer import GapAnalyzer, GapSeverity, ObligationCategory

router = APIRouter(
    prefix="/api/gap-analysis",
    tags=["gap-analysis"],
    dependencies=[Depends(require_any_role(["admin", "compliance", "aml_officer", "user"]))],
)


@router.get("/dashboard")
def get_gap_dashboard(
    scope: Optional[List[str]] = Query(default=None, description="Filter by scope tags"),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "user"])
    ),
    db: Session = Depends(get_db),
):
    """
    Get the compliance gap analysis dashboard.

    Returns overall coverage metrics, category breakdowns, and top gaps.
    """
    analyzer = GapAnalyzer(db)
    report = analyzer.analyze_coverage(scope_filter=scope)

    return {
        "summary": {
            "overall_coverage": report.overall_coverage,
            "total_obligations": report.total_obligations,
            "covered": report.covered_count,
            "partial": report.partial_count,
            "uncovered": report.uncovered_count,
            "gap_count": len(report.gaps),
        },
        "metrics": [
            {
                "category": m.category,
                "total": m.total,
                "covered": m.covered,
                "partial": m.partial,
                "uncovered": m.uncovered,
                "coverage_percentage": m.coverage_percentage,
                "trend": m.trend,
            }
            for m in report.metrics
        ],
        "top_gaps": [
            {
                "obligation_id": g.obligation_id,
                "celex": g.celex,
                "document_title": g.document_title,
                "article_ref": g.article_ref,
                "severity": g.severity.value,
                "category": g.category.value,
                "days_until_effective": g.days_until_effective,
                "suggested_template": (
                    {"id": g.suggested_template_id, "name": g.suggested_template_name}
                    if g.suggested_template_id
                    else None
                ),
                "description": g.description,
            }
            for g in report.gaps[:10]  # Top 10 most critical
        ],
        "recommendations": report.recommendations,
        "generated_at": report.generated_at.isoformat(),
    }


@router.get("/gaps")
def list_gaps(
    severity: Optional[str] = Query(
        default=None, description="Filter by severity: critical, high, medium, low"
    ),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    scope: Optional[List[str]] = Query(default=None),
    sort_by: str = Query(default="severity", description="Sort by: severity, date, category"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "user"])
    ),
    db: Session = Depends(get_db),
):
    """
    List all compliance gaps with filtering and sorting.
    """
    analyzer = GapAnalyzer(db)
    report = analyzer.analyze_coverage(scope_filter=scope)

    # Filter gaps
    gaps = report.gaps

    if severity:
        gaps = [g for g in gaps if g.severity.value == severity]

    if category:
        gaps = [g for g in gaps if g.category.value == category]

    # Sort
    severity_order = {
        GapSeverity.CRITICAL: 0,
        GapSeverity.HIGH: 1,
        GapSeverity.MEDIUM: 2,
        GapSeverity.LOW: 3,
        GapSeverity.INFO: 4,
    }

    if sort_by == "severity":
        gaps.sort(key=lambda x: (severity_order[x.severity], x.days_until_effective or 999))
    elif sort_by == "date":
        gaps.sort(key=lambda x: x.days_until_effective or 999)
    elif sort_by == "category":
        gaps.sort(key=lambda x: x.category.value)

    total = len(gaps)
    gaps = gaps[offset : offset + limit]

    return {
        "gaps": [
            {
                "obligation_id": g.obligation_id,
                "obligation_text": g.obligation_text,
                "celex": g.celex,
                "document_title": g.document_title,
                "article_ref": g.article_ref,
                "gap_type": g.gap_type,
                "severity": g.severity.value,
                "category": g.category.value,
                "description": g.description,
                "suggested_template": (
                    {"id": g.suggested_template_id, "name": g.suggested_template_name}
                    if g.suggested_template_id
                    else None
                ),
                "ai_recommendation": g.ai_recommendation,
                "effective_date": g.effective_date.isoformat() if g.effective_date else None,
                "days_until_effective": g.days_until_effective,
            }
            for g in gaps
        ],
        "total": total,
        "offset": offset,
        "limit": limit,
        "filters": {"severity": severity, "category": category},
    }


@router.get("/coverage-by-document")
def get_coverage_by_document(
    doc_id: Optional[int] = Query(default=None),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "user"])
    ),
    db: Session = Depends(get_db),
):
    """
    Get coverage analysis for a specific document or all documents.
    """
    from src.models.models import LegalDocument
    from sqlalchemy import func

    if doc_id:
        # Single document analysis
        doc = db.query(LegalDocument).get(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        analyzer = GapAnalyzer(db)
        report = analyzer.analyze_coverage(doc_id=doc_id)

        return {
            "document": {"id": doc.id, "celex": doc.celex, "title": doc.title},
            "coverage": {
                "percentage": report.overall_coverage,
                "total_obligations": report.total_obligations,
                "covered": report.covered_count,
                "uncovered": report.uncovered_count,
            },
            "gaps": [
                {
                    "obligation_id": g.obligation_id,
                    "article_ref": g.article_ref,
                    "severity": g.severity.value,
                    "category": g.category.value,
                    "days_until_effective": g.days_until_effective,
                }
                for g in report.gaps
            ],
        }
    else:
        # All documents summary
        results = db.execute(
            text(
                """
            SELECT
                ld.id,
                ld.celex,
                ld.title,
                COUNT(DISTINCT ro.id) as total_obligations,
                COUNT(
                    DISTINCT CASE
                        WHEN opm.id IS NOT NULL OR ro.linked_policy_id IS NOT NULL THEN ro.id
                        ELSE NULL
                    END
                ) as covered,
                (
                    COUNT(DISTINCT ro.id) - COUNT(
                        DISTINCT CASE
                            WHEN opm.id IS NOT NULL OR ro.linked_policy_id IS NOT NULL THEN ro.id
                            ELSE NULL
                        END
                    )
                ) as uncovered
            FROM legal_documents ld
            LEFT JOIN regulatory_obligations ro ON ld.id = ro.doc_id
            LEFT JOIN obligation_policy_mappings opm ON ro.id = opm.obligation_id
            WHERE ro.id IS NOT NULL
            GROUP BY ld.id
            ORDER BY uncovered DESC
        """
            )
        ).fetchall()

        return {
            "documents": [
                {
                    "id": row[0],
                    "celex": row[1],
                    "title": row[2],
                    "total_obligations": row[3],
                    "covered": row[4] or 0,
                    "uncovered": row[5] or 0,
                    "coverage_percentage": round((row[4] or 0) / max(row[3], 1) * 100, 1),
                }
                for row in results
            ]
        }


@router.post("/map-obligation")
def map_obligation_to_policy(
    obligation_id: int,
    policy_id: int,
    notes: Optional[str] = None,
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
    db: Session = Depends(get_db),
):
    """
    Manually map an obligation to a policy, marking it as covered.
    """
    analyzer = GapAnalyzer(db)

    try:
        analyzer.map_obligation_to_policy(
            obligation_id=obligation_id,
            policy_id=policy_id,
            mapped_by=f"user:{current_user.user_id}",
            confidence=1.0,
            notes=notes,
        )

        return {
            "status": "success",
            "message": f"Obligation {obligation_id} mapped to policy {policy_id}",
            "mapped_by": current_user.user_id,
            "mapped_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/unmap-obligation/{obligation_id}")
def unmap_obligation(
    obligation_id: int,
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
    db: Session = Depends(get_db),
):
    """
    Remove the policy mapping from an obligation.
    """
    from sqlalchemy import text

    # Remove mappings
    result = db.execute(
        text(
            """
        DELETE FROM obligation_policy_mappings
        WHERE obligation_id = :obl_id
    """
        ),
        {"obl_id": obligation_id},
    )

    # Update obligation status
    db.execute(
        text(
            """
        UPDATE regulatory_obligations
        SET linked_policy_id = NULL
        WHERE id = :obl_id
    """
        ),
        {"obl_id": obligation_id},
    )

    db.commit()

    return {
        "status": "success",
        "message": f"Obligation {obligation_id} unmapped",
        "mappings_removed": result.rowcount,
    }


@router.get("/obligation/{obligation_id}/coverage")
def get_obligation_coverage(
    obligation_id: int,
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "user"])
    ),
    db: Session = Depends(get_db),
):
    """
    Get detailed coverage information for a specific obligation.
    """
    from src.models.compliance_workflow import RegulatoryObligation

    obl = db.query(RegulatoryObligation).get(obligation_id)
    if not obl:
        raise HTTPException(status_code=404, detail="Obligation not found")

    # Get mappings
    mappings = db.execute(
        text(
            """
        SELECT
            m.id,
            m.policy_id,
            p.name as policy_title,
            m.mapping_confidence,
            m.mapped_by,
            m.mapped_at
        FROM obligation_policy_mappings m
        JOIN policy_documents p ON m.policy_id = p.id
        WHERE m.obligation_id = :obl_id
    """
        ),
        {"obl_id": obligation_id},
    ).fetchall()

    analyzer = GapAnalyzer(db)
    coverage_status = "covered" if mappings or obl.linked_policy_id else "uncovered"
    category = analyzer.auto_categorize_obligation(obl.obligation_text).value
    severity = analyzer.calculate_severity(obl, ObligationCategory(category)).value

    return {
        "obligation": {
            "id": obl.id,
            "celex": obl.celex,
            "article_ref": obl.article_ref,
            "text": (
                obl.obligation_text[:500] if len(obl.obligation_text) > 500 else obl.obligation_text
            ),
            "coverage_status": coverage_status,
            "category": category,
            "severity": severity,
            "effective_date": obl.effective_date.isoformat() if obl.effective_date else None,
        },
        "coverage": {
            "status": coverage_status,
            "linked_policy_id": obl.linked_policy_id,
            "mapped_policies": [
                {
                    "mapping_id": m[0],
                    "policy_id": m[1],
                    "policy_title": m[2],
                    "confidence": m[3],
                    "mapped_by": m[4],
                    "mapped_at": m[5].isoformat() if m[5] else None,
                }
                for m in mappings
            ],
        },
    }


@router.get("/trend")
def get_coverage_trend(
    days: int = Query(default=30, ge=7, le=365),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
    db: Session = Depends(get_db),
):
    """
    Get coverage trend over time.
    """
    analyzer = GapAnalyzer(db)
    trend = analyzer.get_coverage_trend(days=days)

    return {
        "period_days": days,
        "trend": trend,
        "summary": {
            "start_coverage": trend[0]["coverage_percentage"] if trend else 0,
            "current_coverage": trend[-1]["coverage_percentage"] if trend else 0,
            "change": (
                (trend[-1]["coverage_percentage"] - trend[0]["coverage_percentage"])
                if len(trend) >= 2
                else 0
            ),
        },
    }


@router.post("/recalculate")
def recalculate_coverage(
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance"])),
    db: Session = Depends(get_db),
):
    """
    Force a recalculation of all coverage metrics.

    This will re-categorize all obligations and recalculate coverage.
    """

    def recalculate():
        analyzer = GapAnalyzer(db)
        analyzer.analyze_coverage()

    background_tasks.add_task(recalculate)

    return {
        "status": "queued",
        "message": "Coverage recalculation started in background",
        "triggered_by": current_user.user_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================================
# Admin Endpoints
# ============================================================================


@router.get("/admin/mappings")
def admin_list_mappings(
    limit: int = Query(default=100, ge=1, le=500),
    current_user: CurrentUser = Depends(require_any_role(["admin"])),
    db: Session = Depends(get_db),
):
    """
    Admin: List all obligation-policy mappings.
    """
    mappings = db.execute(
        text(
            """
        SELECT
            m.id,
            m.obligation_id,
            ro.celex,
            ro.article_ref,
            m.policy_id,
            p.name as policy_title,
            m.mapped_by,
            m.mapping_confidence,
            m.mapped_at
        FROM obligation_policy_mappings m
        JOIN regulatory_obligations ro ON m.obligation_id = ro.id
        JOIN policy_documents p ON m.policy_id = p.id
        ORDER BY m.mapped_at DESC
        LIMIT :limit
    """
        ),
        {"limit": limit},
    ).fetchall()

    return {
        "mappings": [
            {
                "id": m[0],
                "obligation_id": m[1],
                "celex": m[2],
                "article_ref": m[3],
                "policy_id": m[4],
                "policy_title": m[5],
                "mapped_by": m[6],
                "confidence": m[7],
                "mapped_at": m[8].isoformat() if m[8] else None,
            }
            for m in mappings
        ]
    }


@router.get("/categories")
def list_categories(
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "user"])
    ),
):
    """
    List all obligation categories with descriptions.
    """
    categories = [
        {"value": cat.value, "label": cat.value.replace("_", " ").title()}
        for cat in ObligationCategory
    ]

    return {"categories": categories}
