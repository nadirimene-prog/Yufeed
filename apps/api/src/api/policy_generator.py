"""
Smart Policy Generator API

Endpoints for AI-powered policy generation from obligations.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from src.database import get_db
from src.auth.dependencies import require_any_role, CurrentUser
from src.models.compliance_workflow import PolicyTemplate, RegulatoryObligation
from src.services.policy_generator import (
    PolicyGenerator,
    PolicyGenerationRequest,
    get_policy_generator,
)

router = APIRouter(
    prefix="/api/policy-generator",
    tags=["policy-generator"],
    dependencies=[Depends(require_any_role(["admin", "compliance", "aml_officer"]))],
)


@router.post("/generate")
async def generate_policy(
    request: PolicyGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
    db: Session = Depends(get_db),
):
    """
    Generate a policy from selected obligations.

    This endpoint starts a background generation job and returns immediately.
    Use the returned job_id to check status and retrieve results.
    """
    generator = get_policy_generator(db)

    # Validate template exists
    template = (
        db.query(PolicyTemplate).filter(PolicyTemplate.template_id == request.template_id).first()
    )

    if not template:
        raise HTTPException(status_code=404, detail=f"Template {request.template_id} not found")

    # Validate obligations exist
    obligations = (
        db.query(RegulatoryObligation)
        .filter(RegulatoryObligation.id.in_(request.obligation_ids))
        .all()
    )

    if len(obligations) != len(request.obligation_ids):
        found_ids = {o.id for o in obligations}
        missing = set(request.obligation_ids) - found_ids
        raise HTTPException(status_code=404, detail=f"Obligations not found: {missing}")

    # Add creator to request
    request.created_by = current_user.id

    # Start generation
    try:
        result = await generator.generate_policy(request)

        return {
            "status": "completed",
            "job_id": result.job_id,
            "word_count": result.word_count,
            "reading_time": result.estimated_reading_time,
            "ai_confidence": result.ai_confidence,
            "summary": result.summary,
            "obligations_covered": len(result.obligations_covered),
            "preview_url": f"/api/policy-generator/results/{result.job_id}/preview",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Policy generation failed: {str(e)}")


@router.get("/templates")
def list_templates(
    category: Optional[str] = Query(default=None, description="Filter by category"),
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "user"])
    ),
    db: Session = Depends(get_db),
):
    """
    List available policy templates for generation.
    """
    from src.services.policy_templates import POLICY_TEMPLATES

    templates = POLICY_TEMPLATES

    if category:
        templates = [t for t in templates if t.get("category") == category]

    # Enrich with variable count
    enriched = []
    for template in templates:
        var_count = db.execute(
            text(
                """
            SELECT COUNT(*) FROM policy_template_variables
            WHERE template_id = :template_id
        """
            ),
            {"template_id": template["template_id"]},
        ).scalar()

        enriched.append({**template, "variable_count": var_count})

    return {
        "templates": enriched,
        "total": len(enriched),
        "categories": list(set(t.get("category") for t in POLICY_TEMPLATES)),
    }


@router.get("/templates/{template_id}/variables")
def get_template_variables(
    template_id: str,
    current_user: CurrentUser = Depends(
        require_any_role(["admin", "compliance", "aml_officer", "user"])
    ),
    db: Session = Depends(get_db),
):
    """
    Get all variables required for a template.
    """
    generator = get_policy_generator(db)
    variables = generator.get_template_variables(template_id)

    return {
        "template_id": template_id,
        "variables": variables,
        "required_count": sum(1 for v in variables if v.get("required")),
        "optional_count": sum(1 for v in variables if not v.get("required")),
    }


@router.post("/templates/{template_id}/preview")
async def preview_generation(
    template_id: str,
    obligation_ids: List[int],
    variable_values: Dict[str, Any],
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
    db: Session = Depends(get_db),
):
    """
    Preview what a policy generation would look like without saving.

    Returns a summary of what would be generated.
    """
    # Validate
    template = db.query(PolicyTemplate).filter(PolicyTemplate.template_id == template_id).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    obligations = (
        db.query(RegulatoryObligation).filter(RegulatoryObligation.id.in_(obligation_ids)).all()
    )

    # Build preview
    sections = db.execute(
        text(
            """
        SELECT section_name, depends_on_obligations
        FROM policy_section_templates
        WHERE template_id = :template_id
        ORDER BY section_order
    """
        ),
        {"template_id": template_id},
    ).fetchall()

    return {
        "template": {
            "id": template_id,
            "name": template.name if template else "Unknown",
            "regulatory_basis": template.regulatory_basis if template else None,
        },
        "obligations_selected": len(obligations),
        "obligations": [
            {
                "id": o.id,
                "celex": o.celex,
                "article_ref": o.article_ref,
                "category": o.category,
                "text_preview": (
                    o.obligation_text[:100] + "..."
                    if len(o.obligation_text) > 100
                    else o.obligation_text
                ),
            }
            for o in obligations
        ],
        "variables_provided": list(variable_values.keys()),
        "sections_to_generate": [
            {"name": s[0], "will_use_obligations": bool(s[1])} for s in sections
        ],
        "estimated_word_count": len(obligations) * 400,  # Rough estimate
    }


@router.get("/results/{job_id}")
def get_generation_result(
    job_id: str,
    include_content: bool = Query(default=True, description="Include full generated content"),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
    db: Session = Depends(get_db),
):
    """
    Get the result of a policy generation job.
    """
    generator = get_policy_generator(db)
    result = generator.get_generation_result(job_id)

    if not result:
        # Check if job exists but not completed
        status = generator.get_generation_status(job_id)
        if status:
            return {
                "job_id": job_id,
                "status": status["status"],
                "created_at": status["created_at"],
                "started_at": status["started_at"],
                "completed_at": status["completed_at"],
                "error": status["error"],
            }
        else:
            raise HTTPException(status_code=404, detail="Generation job not found")

    response = {
        "job_id": result.job_id,
        "status": result.status,
        "summary": result.summary,
        "obligations_covered": result.obligations_covered,
        "ai_confidence": result.ai_confidence,
        "word_count": result.word_count,
        "reading_time": result.estimated_reading_time,
        "sections": [
            {
                "order": s.section_order,
                "title": s.title,
                "content_preview": s.content[:200] + "..." if len(s.content) > 200 else s.content,
                "confidence": s.ai_confidence,
            }
            for s in result.sections
        ],
    }

    if include_content:
        response["full_content"] = result.generated_content

    return response


@router.get("/results/{job_id}/preview")
def preview_generated_policy(
    job_id: str,
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
    db: Session = Depends(get_db),
):
    """
    Get a formatted preview of the generated policy for review.
    """
    generator = get_policy_generator(db)
    result = generator.get_generation_result(job_id)

    if not result:
        raise HTTPException(status_code=404, detail="Generation result not found")

    return {
        "job_id": job_id,
        "title": "Generated Policy Preview",
        "content_html": result.generated_content.replace("\n", "<br>"),
        "content_markdown": result.generated_content,
        "summary": result.summary,
        "metadata": {
            "word_count": result.word_count,
            "reading_time": result.estimated_reading_time,
            "ai_confidence": result.ai_confidence,
            "obligations_count": len(result.obligations_covered),
        },
    }


@router.post("/results/{job_id}/approve")
def approve_generated_policy(
    job_id: str,
    notes: Optional[str] = None,
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
    db: Session = Depends(get_db),
):
    """
    Approve a generated policy and create the actual policy document.

    This converts the generation result into a real policy that can be published.
    """
    generator = get_policy_generator(db)

    try:
        policy_id = generator.approve_generation(
            job_id=job_id, reviewed_by=current_user.id, notes=notes
        )

        return {
            "status": "approved",
            "message": "Generated policy approved and created",
            "job_id": job_id,
            "policy_id": policy_id,
            "policy_url": f"/api/policies/{policy_id}",
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Approval failed: {str(e)}")


@router.post("/results/{job_id}/reject")
def reject_generated_policy(
    job_id: str,
    reason: str,
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
    db: Session = Depends(get_db),
):
    """
    Reject a generated policy.
    """
    db.execute(
        text(
            """
        UPDATE policy_generation_jobs
        SET status = 'rejected',
            reviewed_by = :reviewer,
            reviewed_at = CURRENT_TIMESTAMP,
            review_notes = :reason
        WHERE job_id = :job_id
    """
        ),
        {"job_id": job_id, "reviewer": current_user.id, "reason": reason},
    )
    db.commit()

    return {
        "status": "rejected",
        "message": "Generation rejected",
        "job_id": job_id,
        "reason": reason,
    }


@router.get("/jobs")
def list_generation_jobs(
    status: Optional[str] = Query(
        default=None,
        description="Filter by status: pending, generating, completed, approved, rejected",
    ),
    template_id: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
    db: Session = Depends(get_db),
):
    """
    List policy generation jobs.
    """
    query = """
        SELECT
            j.job_id,
            j.template_id,
            j.status,
            j.generated_summary,
            j.ai_confidence,
            j.created_at,
            j.completed_at,
            j.final_policy_id,
            u.email as created_by_email
        FROM policy_generation_jobs j
        LEFT JOIN users u ON j.created_by = u.id
        WHERE 1=1
    """
    params = {}

    if status:
        query += " AND j.status = :status"
        params["status"] = status

    if template_id:
        query += " AND j.template_id = :template_id"
        params["template_id"] = template_id

    query += " ORDER BY j.created_at DESC LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = offset

    results = db.execute(text(query), params).fetchall()

    return {
        "jobs": [
            {
                "job_id": r[0],
                "template_id": r[1],
                "status": r[2],
                "summary": r[3],
                "ai_confidence": r[4],
                "created_at": r[5].isoformat() if r[5] else None,
                "completed_at": r[6].isoformat() if r[6] else None,
                "final_policy_id": r[7],
                "created_by": r[8],
            }
            for r in results
        ],
        "total": len(results),
        "filters": {"status": status, "template_id": template_id},
    }


@router.get("/stats")
def get_generator_stats(
    days: int = Query(default=30, ge=1, le=365),
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance"])),
    db: Session = Depends(get_db),
):
    """
    Get policy generator usage statistics.
    """
    since = datetime.now(timezone.utc).replace(day=datetime.now(timezone.utc).day - days)

    stats = db.execute(
        text(
            """
        SELECT
            COUNT(*) as total_jobs,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
            SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
            AVG(ai_confidence) as avg_confidence,
            COUNT(DISTINCT template_id) as templates_used
        FROM policy_generation_jobs
        WHERE created_at > :since
    """
        ),
        {"since": since},
    ).fetchone()

    return {
        "period_days": days,
        "total_jobs": stats[0] or 0,
        "completed": stats[1] or 0,
        "approved": stats[2] or 0,
        "rejected": stats[3] or 0,
        "failed": stats[4] or 0,
        "average_confidence": round(stats[5], 2) if stats[5] else 0,
        "templates_used": stats[6] or 0,
        "approval_rate": round((stats[2] or 0) / max(stats[0] or 1, 1) * 100, 1),
    }


# ============================================================================
# Quick Generate Endpoint (Simplified)
# ============================================================================


@router.post("/quick-generate")
async def quick_generate(
    template_id: str,
    obligation_ids: List[int],
    institution_name: str,
    mlro_name: str,
    current_user: CurrentUser = Depends(require_any_role(["admin", "compliance", "aml_officer"])),
    db: Session = Depends(get_db),
):
    """
    Quick policy generation with minimal parameters.

    Uses sensible defaults for all other variables.
    """
    request = PolicyGenerationRequest(
        template_id=template_id,
        obligation_ids=obligation_ids,
        variable_values={
            "institution_name": institution_name,
            "mlro_name": mlro_name,
            "jurisdiction": "European Union",
        },
        created_by=current_user.id,
    )

    generator = get_policy_generator(db)

    try:
        result = await generator.generate_policy(request)

        return {
            "status": "completed",
            "job_id": result.job_id,
            "message": "Policy generated successfully",
            "word_count": result.word_count,
            "preview_url": f"/api/policy-generator/results/{result.job_id}/preview",
            "approve_url": f"/api/policy-generator/results/{result.job_id}/approve",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
