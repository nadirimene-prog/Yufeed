"""
AI Agents API Endpoints
Exposes AI-powered compliance analysis and triage capabilities.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from src.database import get_db, SessionLocal
from src.ai.alert_triage import AlertTriageAgent
from src.ai.regulatory_enrichment import RegulatoryEnrichmentService
from src.models.transaction_models import Alert
from src.auth.dependencies import require_any_role
from src.utils.event_bus import publish_event_safe

router = APIRouter(
    prefix="/api/ai",
    tags=["ai-agents"],
    dependencies=[Depends(require_any_role(["admin", "compliance", "analyst", "aml_officer"]))],
)


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================


class TriageRequest(BaseModel):
    alert_id: int


class TriageResponse(BaseModel):
    alert_id: str
    recommendation: str
    confidence: float
    priority: int
    reasoning: str
    true_positive_likelihood: float
    sar_likelihood: float
    investigation_steps: List[str]
    recommended_actions: List[str]
    red_flags: List[str]
    regulatory_concerns: str


class SARDraftResponse(BaseModel):
    filing_institution: str
    filing_date: str
    alert_id: str
    subject: dict
    suspicious_activity: dict
    narrative: str
    related_regulations: List[int]
    filing_reason: str


class BatchTriageRequest(BaseModel):
    limit: int = 50
    alert_ids: Optional[List[int]] = None


class EnrichmentRequest(BaseModel):
    alert_id: int


# ============================================================================
# ALERT TRIAGE ENDPOINTS
# ============================================================================


@router.post("/triage", response_model=TriageResponse)
def triage_alert(request: TriageRequest, db: Session = Depends(get_db)):
    """
    Perform AI-powered triage on a single alert.

    Returns:
    - Recommendation (escalate/investigate/false_positive/monitor)
    - Confidence level
    - Investigation steps
    - Regulatory concerns
    - SAR likelihood
    """
    agent = AlertTriageAgent(db)

    # Get alert
    alert = db.query(Alert).filter(Alert.id == request.alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    try:
        analysis = agent.triage_alert(request.alert_id)

        publish_event_safe(
            "events.raw",
            {
                "event_type": "ai.triage.completed",
                "entity_type": "alert",
                "entity_id": alert.alert_id,
                "source": "ai_agents",
                "payload": {
                    "alert_id": alert.alert_id,
                    "recommendation": analysis.get("recommendation"),
                    "confidence": analysis.get("confidence"),
                    "sar_likelihood": analysis.get("sar_likelihood"),
                },
            },
        )

        return TriageResponse(alert_id=alert.alert_id, **analysis)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Triage failed: {str(e)}")


@router.post("/triage/batch")
def batch_triage_alerts(
    request: BatchTriageRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """
    Triage multiple pending alerts in batch.

    This is a background task that processes alerts asynchronously.
    """
    mode = "selected_ids" if request.alert_ids else "pending_limit"

    if request.alert_ids:
        # Validate alerts exist up front
        found_alerts = db.query(Alert).filter(Alert.id.in_(request.alert_ids)).all()
        found_ids = {a.id for a in found_alerts}
        missing_ids = [alert_id for alert_id in request.alert_ids if alert_id not in found_ids]
        if missing_ids:
            raise HTTPException(
                status_code=404, detail=f"Some alerts not found: {', '.join(map(str, missing_ids))}"
            )

        background_tasks.add_task(_batch_triage_selected_task, request.alert_ids)
    else:
        background_tasks.add_task(_batch_triage_pending_task, request.limit)

    publish_event_safe(
        "events.raw",
        {
            "event_type": "ai.triage.batch.started",
            "entity_type": "alert",
            "source": "ai_agents",
            "payload": {
                "limit": request.limit,
                "alert_ids": request.alert_ids or [],
                "mode": mode,
            },
        },
    )

    return {
        "status": "started",
        "message": (
            f"Batch triage of {len(request.alert_ids)} selected alerts initiated"
            if request.alert_ids
            else f"Batch triage of up to {request.limit} alerts initiated"
        ),
        "note": "Processing in background. Check alert statuses for updates.",
        "mode": mode,
        "requested_count": len(request.alert_ids) if request.alert_ids else None,
        "processed_target": len(request.alert_ids) if request.alert_ids else request.limit,
    }


@router.get("/triage/pending-count")
def get_pending_triage_count(db: Session = Depends(get_db)):
    """
    Get count of alerts pending AI triage.
    """
    from sqlalchemy import func, and_

    pending_count = db.query(func.count(Alert.id)).filter(Alert.status == "pending").scalar() or 0

    return {
        "pending_alerts": pending_count,
        "recommendation": "Run batch triage" if pending_count > 10 else "No action needed",
    }


@router.get("/investigation-report/{alert_id}")
def generate_investigation_report(alert_id: int, db: Session = Depends(get_db)):
    """
    Generate a detailed investigation report for an alert.

    Returns a formatted report suitable for documentation.
    """
    agent = AlertTriageAgent(db)

    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    try:
        report = agent.generate_investigation_report(alert_id)

        publish_event_safe(
            "events.raw",
            {
                "event_type": "ai.investigation.report.generated",
                "entity_type": "alert",
                "entity_id": alert.alert_id,
                "source": "ai_agents",
                "payload": {
                    "alert_id": alert.alert_id,
                },
            },
        )

        return {
            "alert_id": alert.alert_id,
            "report": report,
            "generated_at": "now",  # TODO: Add timestamp
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


# ============================================================================
# REGULATORY ENRICHMENT ENDPOINTS
# ============================================================================


@router.post("/enrich/regulatory-context")
def enrich_regulatory_context(request: EnrichmentRequest, db: Session = Depends(get_db)):
    """
    Enrich an alert with AI-generated regulatory context.

    This explains why the alert matters from a compliance perspective
    and links to specific regulations.
    """
    service = RegulatoryEnrichmentService(db)

    alert = db.query(Alert).filter(Alert.id == request.alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    try:
        context = service.enrich_alert_with_regulations(request.alert_id)

        publish_event_safe(
            "events.raw",
            {
                "event_type": "ai.regulatory.enriched",
                "entity_type": "alert",
                "entity_id": alert.alert_id,
                "source": "ai_agents",
                "payload": {
                    "alert_id": alert.alert_id,
                    "related_regulations": alert.related_regulations,
                },
            },
        )

        return {
            "alert_id": alert.alert_id,
            "regulatory_context": context,
            "related_regulations": alert.related_regulations,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enrichment failed: {str(e)}")


@router.post("/enrich/batch")
def batch_enrich_alerts(
    alert_ids: List[int], background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """
    Enrich multiple alerts with regulatory context in batch.
    """
    # Validate alerts exist
    alerts = db.query(Alert).filter(Alert.id.in_(alert_ids)).all()
    if len(alerts) != len(alert_ids):
        raise HTTPException(status_code=404, detail="Some alerts not found")

    # Run enrichment in background using a fresh DB session
    background_tasks.add_task(_batch_enrich_alerts_task, alert_ids)

    publish_event_safe(
        "events.raw",
        {
            "event_type": "ai.regulatory.enrichment.batch.started",
            "entity_type": "alert",
            "source": "ai_agents",
            "payload": {
                "alert_ids": alert_ids,
                "count": len(alert_ids),
            },
        },
    )

    return {
        "status": "started",
        "message": f"Batch enrichment of {len(alert_ids)} alerts initiated",
        "alert_count": len(alert_ids),
    }


def _batch_triage_pending_task(limit: int) -> None:
    db = SessionLocal()
    try:
        agent = AlertTriageAgent(db)
        agent.batch_triage_pending_alerts(limit=limit)
    finally:
        db.close()


def _batch_triage_selected_task(alert_ids: List[int]) -> None:
    db = SessionLocal()
    try:
        agent = AlertTriageAgent(db)
        agent.batch_triage_alert_ids(alert_ids)
    finally:
        db.close()


def _batch_enrich_alerts_task(alert_ids: List[int]) -> None:
    db = SessionLocal()
    try:
        service = RegulatoryEnrichmentService(db)
        service.batch_enrich_alerts(alert_ids)
    finally:
        db.close()


@router.post("/enrich/auto-link-regulations")
def auto_link_regulations(request: EnrichmentRequest, db: Session = Depends(get_db)):
    """
    Automatically find and link relevant regulations to an alert.

    Uses semantic search to identify applicable legal documents.
    """
    service = RegulatoryEnrichmentService(db)

    alert = db.query(Alert).filter(Alert.id == request.alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    try:
        regulation_ids = service.auto_link_regulations(request.alert_id)

        publish_event_safe(
            "events.raw",
            {
                "event_type": "ai.regulations.auto_linked",
                "entity_type": "alert",
                "entity_id": alert.alert_id,
                "source": "ai_agents",
                "payload": {
                    "alert_id": alert.alert_id,
                    "linked_regulations": regulation_ids,
                },
            },
        )

        return {
            "alert_id": alert.alert_id,
            "linked_regulations": regulation_ids,
            "count": len(regulation_ids),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auto-linking failed: {str(e)}")


# ============================================================================
# SAR GENERATION ENDPOINTS
# ============================================================================


@router.post("/sar/draft", response_model=SARDraftResponse)
def generate_sar_draft(
    alert_id: int, include_narrative: bool = True, db: Session = Depends(get_db)
):
    """
    Generate a draft Suspicious Activity Report (SAR) for an alert.

    Returns structured SAR data ready for filing with authorities.
    """
    service = RegulatoryEnrichmentService(db)

    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    try:
        sar_draft = service.generate_sar_draft(alert_id, include_narrative)

        publish_event_safe(
            "events.raw",
            {
                "event_type": "ai.sar.draft.generated",
                "entity_type": "alert",
                "entity_id": alert.alert_id,
                "source": "ai_agents",
                "payload": {
                    "alert_id": alert.alert_id,
                    "include_narrative": include_narrative,
                    "filing_reason": sar_draft.get("filing_reason"),
                },
            },
        )

        return SARDraftResponse(**sar_draft)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SAR generation failed: {str(e)}")


@router.get("/sar/preview/{alert_id}")
def preview_sar(alert_id: int, db: Session = Depends(get_db)):
    """
    Preview SAR data without full narrative generation.

    Faster endpoint for checking if alert is SAR-worthy.
    """
    service = RegulatoryEnrichmentService(db)

    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    try:
        sar_draft = service.generate_sar_draft(alert_id, include_narrative=False)

        publish_event_safe(
            "events.raw",
            {
                "event_type": "ai.sar.preview.generated",
                "entity_type": "alert",
                "entity_id": alert.alert_id,
                "source": "ai_agents",
                "payload": {
                    "alert_id": alert.alert_id,
                    "filing_reason": sar_draft.get("filing_reason"),
                },
            },
        )

        return {
            "alert_id": alert.alert_id,
            "sar_preview": sar_draft,
            "sar_worthy": True,  # TODO: Add logic to determine SAR-worthiness
            "filing_reason": sar_draft.get("filing_reason"),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SAR preview failed: {str(e)}")


# ============================================================================
# AI AGENT STATUS
# ============================================================================


@router.get("/status")
def get_ai_status():
    """
    Get status of AI agents and capabilities.
    """
    import os

    anthropic_key_set = bool((os.getenv("ANTHROPIC_API_KEY") or "").strip())
    openai_key_set = bool((os.getenv("OPENAI_API_KEY") or "").strip())

    return {
        "status": "operational" if anthropic_key_set else "degraded",
        "capabilities": {
            "alert_triage": anthropic_key_set,
            "regulatory_enrichment": anthropic_key_set,
            "sar_generation": anthropic_key_set,
            "investigation_reports": anthropic_key_set,
        },
        "providers": {
            "anthropic_configured": anthropic_key_set,
            "openai_configured": openai_key_set,
        },
        "model": "claude-sonnet-4-20250514" if anthropic_key_set else None,
        "note": (
            "AI agent routes use ANTHROPIC_API_KEY. OPENAI_API_KEY alone will not enable /api/ai triage/enrichment."
            if not anthropic_key_set
            else "All AI features available"
        ),
    }


@router.get("/analytics")
def get_ai_analytics(db: Session = Depends(get_db)):
    """
    Get analytics on AI agent performance.
    """
    from sqlalchemy import func, and_

    # Count auto-resolved alerts
    auto_resolved = (
        db.query(func.count(Alert.id)).filter(Alert.resolved_by == "AI_AGENT").scalar() or 0
    )

    # Count escalated by AI
    auto_escalated = (
        db.query(func.count(Alert.id))
        .filter(and_(Alert.status == "escalated", Alert.resolution_notes.like("%AI TRIAGE%")))
        .scalar()
        or 0
    )

    # Count enriched alerts
    enriched = (
        db.query(func.count(Alert.id)).filter(Alert.regulation_context.isnot(None)).scalar() or 0
    )

    total_alerts = db.query(func.count(Alert.id)).scalar() or 0

    return {
        "total_alerts": total_alerts,
        "ai_auto_resolved": auto_resolved,
        "ai_escalated": auto_escalated,
        "regulatory_enriched": enriched,
        "enrichment_rate": (enriched / total_alerts * 100) if total_alerts > 0 else 0,
        "automation_rate": (
            ((auto_resolved + auto_escalated) / total_alerts * 100) if total_alerts > 0 else 0
        ),
    }
