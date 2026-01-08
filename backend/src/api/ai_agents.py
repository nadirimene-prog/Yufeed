"""
AI Agents API Endpoints
Exposes AI-powered compliance analysis and triage capabilities.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from src.database import get_db
from src.ai.alert_triage import AlertTriageAgent
from src.ai.regulatory_enrichment import RegulatoryEnrichmentService
from src.models.transaction_models import Alert

router = APIRouter(prefix="/api/ai", tags=["ai-agents"])


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


class EnrichmentRequest(BaseModel):
    alert_id: int


# ============================================================================
# ALERT TRIAGE ENDPOINTS
# ============================================================================

@router.post("/triage", response_model=TriageResponse)
def triage_alert(
    request: TriageRequest,
    db: Session = Depends(get_db)
):
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

        return TriageResponse(
            alert_id=alert.alert_id,
            **analysis
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Triage failed: {str(e)}")


@router.post("/triage/batch")
def batch_triage_alerts(
    request: BatchTriageRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Triage multiple pending alerts in batch.

    This is a background task that processes alerts asynchronously.
    """
    agent = AlertTriageAgent(db)

    # Run batch triage in background
    background_tasks.add_task(
        agent.batch_triage_pending_alerts,
        limit=request.limit
    )

    return {
        "status": "started",
        "message": f"Batch triage of up to {request.limit} alerts initiated",
        "note": "Processing in background. Check alert statuses for updates."
    }


@router.get("/triage/pending-count")
def get_pending_triage_count(db: Session = Depends(get_db)):
    """
    Get count of alerts pending AI triage.
    """
    from sqlalchemy import func, and_

    pending_count = db.query(func.count(Alert.id)).filter(
        Alert.status == 'pending'
    ).scalar() or 0

    return {
        "pending_alerts": pending_count,
        "recommendation": "Run batch triage" if pending_count > 10 else "No action needed"
    }


@router.get("/investigation-report/{alert_id}")
def generate_investigation_report(
    alert_id: int,
    db: Session = Depends(get_db)
):
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

        return {
            "alert_id": alert.alert_id,
            "report": report,
            "generated_at": "now"  # TODO: Add timestamp
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


# ============================================================================
# REGULATORY ENRICHMENT ENDPOINTS
# ============================================================================

@router.post("/enrich/regulatory-context")
def enrich_regulatory_context(
    request: EnrichmentRequest,
    db: Session = Depends(get_db)
):
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

        return {
            "alert_id": alert.alert_id,
            "regulatory_context": context,
            "related_regulations": alert.related_regulations
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enrichment failed: {str(e)}")


@router.post("/enrich/batch")
def batch_enrich_alerts(
    alert_ids: List[int],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Enrich multiple alerts with regulatory context in batch.
    """
    service = RegulatoryEnrichmentService(db)

    # Validate alerts exist
    alerts = db.query(Alert).filter(Alert.id.in_(alert_ids)).all()
    if len(alerts) != len(alert_ids):
        raise HTTPException(status_code=404, detail="Some alerts not found")

    # Run enrichment in background
    background_tasks.add_task(
        service.batch_enrich_alerts,
        alert_ids
    )

    return {
        "status": "started",
        "message": f"Batch enrichment of {len(alert_ids)} alerts initiated",
        "alert_count": len(alert_ids)
    }


@router.post("/enrich/auto-link-regulations")
def auto_link_regulations(
    request: EnrichmentRequest,
    db: Session = Depends(get_db)
):
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

        return {
            "alert_id": alert.alert_id,
            "linked_regulations": regulation_ids,
            "count": len(regulation_ids)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auto-linking failed: {str(e)}")


# ============================================================================
# SAR GENERATION ENDPOINTS
# ============================================================================

@router.post("/sar/draft", response_model=SARDraftResponse)
def generate_sar_draft(
    alert_id: int,
    include_narrative: bool = True,
    db: Session = Depends(get_db)
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

        return SARDraftResponse(**sar_draft)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SAR generation failed: {str(e)}")


@router.get("/sar/preview/{alert_id}")
def preview_sar(
    alert_id: int,
    db: Session = Depends(get_db)
):
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

        return {
            "alert_id": alert.alert_id,
            "sar_preview": sar_draft,
            "sar_worthy": True,  # TODO: Add logic to determine SAR-worthiness
            "filing_reason": sar_draft.get("filing_reason")
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

    anthropic_key_set = bool(os.getenv("ANTHROPIC_API_KEY"))

    return {
        "status": "operational" if anthropic_key_set else "degraded",
        "capabilities": {
            "alert_triage": anthropic_key_set,
            "regulatory_enrichment": anthropic_key_set,
            "sar_generation": anthropic_key_set,
            "investigation_reports": anthropic_key_set
        },
        "model": "claude-sonnet-4-20250514" if anthropic_key_set else None,
        "note": "Set ANTHROPIC_API_KEY to enable AI features" if not anthropic_key_set else "All AI features available"
    }


@router.get("/analytics")
def get_ai_analytics(db: Session = Depends(get_db)):
    """
    Get analytics on AI agent performance.
    """
    from sqlalchemy import func, and_

    # Count auto-resolved alerts
    auto_resolved = db.query(func.count(Alert.id)).filter(
        Alert.resolved_by == 'AI_AGENT'
    ).scalar() or 0

    # Count escalated by AI
    auto_escalated = db.query(func.count(Alert.id)).filter(
        and_(
            Alert.status == 'escalated',
            Alert.resolution_notes.like('%AI TRIAGE%')
        )
    ).scalar() or 0

    # Count enriched alerts
    enriched = db.query(func.count(Alert.id)).filter(
        Alert.regulation_context.isnot(None)
    ).scalar() or 0

    total_alerts = db.query(func.count(Alert.id)).scalar() or 0

    return {
        "total_alerts": total_alerts,
        "ai_auto_resolved": auto_resolved,
        "ai_escalated": auto_escalated,
        "regulatory_enriched": enriched,
        "enrichment_rate": (enriched / total_alerts * 100) if total_alerts > 0 else 0,
        "automation_rate": ((auto_resolved + auto_escalated) / total_alerts * 100) if total_alerts > 0 else 0
    }
