"""
AI AML Officer API Endpoints

Main API interface for the AI AML Officer system.
Provides endpoints for:
- Alert investigation
- Daily briefings
- Compliance Q&A
- SAR preparation
- Sanctions screening
- Proactive monitoring
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.ai.orchestrator import get_aml_officer, AMLOfficer, WorkflowType
from src.ai.agents.base import AgentContext, ActionRecommendation
from src.integrations.sanctions import SanctionsService, SanctionsListType

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/aml-officer", tags=["AI AML Officer"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class InvestigateAlertRequest(BaseModel):
    """Request to investigate an alert."""
    alert_id: int
    alert_data: Dict[str, Any]
    related_transactions: Optional[List[Dict[str, Any]]] = None
    related_regulations: Optional[List[Dict[str, Any]]] = None
    user_id: Optional[str] = None


class BatchInvestigateRequest(BaseModel):
    """Request to investigate multiple alerts."""
    alerts: List[Dict[str, Any]]
    max_concurrent: int = Field(default=5, ge=1, le=20)


class ComplianceQuestionRequest(BaseModel):
    """Request to ask a compliance question."""
    question: str
    context: Optional[Dict[str, Any]] = None
    conversation_history: Optional[List[Dict[str, str]]] = None


class SanctionsScreenRequest(BaseModel):
    """Request to screen a name against sanctions lists."""
    name: str
    entity_type: Optional[str] = None
    nationality: Optional[str] = None
    birth_date: Optional[str] = None
    lists: Optional[List[str]] = None


class BatchSanctionsScreenRequest(BaseModel):
    """Request to screen multiple names."""
    names: List[str]
    max_concurrent: int = Field(default=10, ge=1, le=50)


class SARPrepareRequest(BaseModel):
    """Request to prepare a SAR."""
    case_id: int
    case_data: Dict[str, Any]
    related_alerts: List[Dict[str, Any]] = []
    related_transactions: List[Dict[str, Any]] = []


class InvestigationResponse(BaseModel):
    """Response from an investigation."""
    success: bool
    alert_id: Optional[int] = None
    recommendation: Optional[str] = None
    confidence: float = 0.0
    confidence_level: str = "low"
    summary: str = ""
    detailed_analysis: str = ""
    risk_score: Optional[float] = None
    risk_factors: List[str] = []
    red_flags: List[str] = []
    mitigating_factors: List[str] = []
    citations: List[Dict[str, Any]] = []
    next_steps: List[str] = []
    sar_likelihood: Optional[float] = None
    processing_time_ms: int = 0
    error_message: Optional[str] = None


class DailyBriefingResponse(BaseModel):
    """Response containing daily briefing."""
    briefing_id: str
    generated_at: str
    period_start: str
    period_end: str
    alerts: Dict[str, int]
    cases: Dict[str, int]
    risk: Dict[str, Any]
    regulatory: Dict[str, Any]
    recommendations: Dict[str, List[str]]
    narrative: Dict[str, str]


class ComplianceAnswerResponse(BaseModel):
    """Response to a compliance question."""
    answer: str
    confidence: str
    sources: List[Dict[str, Any]]
    followup_questions: List[str]


class SanctionsScreenResponse(BaseModel):
    """Response from sanctions screening."""
    screened_name: str
    screened_at: str
    is_hit: bool
    match_count: int
    highest_score: float
    matches: List[Dict[str, Any]]
    lists_checked: List[str]
    processing_time_ms: int


# =============================================================================
# INVESTIGATION ENDPOINTS
# =============================================================================

@router.post("/investigate", response_model=InvestigationResponse)
async def investigate_alert(
    request: InvestigateAlertRequest,
    db: Session = Depends(get_db)
):
    """
    Investigate a single alert using the AI Investigation Agent.

    The Investigation Agent performs:
    - Multi-step chain-of-thought analysis
    - Evidence gathering and correlation
    - Pattern identification
    - Risk assessment
    - Regulatory citation matching
    - Action recommendation

    Returns a comprehensive investigation report.
    """
    try:
        aml_officer = get_aml_officer(db)

        result = await aml_officer.investigate_alert(
            alert_id=request.alert_id,
            alert_data=request.alert_data,
            related_transactions=request.related_transactions,
            related_regulations=request.related_regulations,
            user_id=request.user_id
        )

        return InvestigationResponse(
            success=result.success,
            alert_id=request.alert_id,
            recommendation=result.recommendation.value if result.recommendation else None,
            confidence=result.confidence,
            confidence_level=result.confidence_level.value,
            summary=result.summary,
            detailed_analysis=result.detailed_analysis,
            risk_score=result.risk_score,
            risk_factors=result.risk_factors,
            red_flags=result.red_flags,
            mitigating_factors=result.mitigating_factors,
            citations=[c.to_dict() if hasattr(c, 'to_dict') else c for c in result.citations] if hasattr(result, 'citations') else [],
            next_steps=result.next_steps,
            sar_likelihood=result.sar_likelihood,
            processing_time_ms=result.processing_time_ms,
            error_message=result.error_message
        )

    except Exception as e:
        logger.error(f"Investigation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/investigate/batch")
async def batch_investigate_alerts(
    request: BatchInvestigateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Investigate multiple alerts concurrently.

    Useful for batch processing of pending alerts.
    Results are returned for all alerts, with errors handled gracefully.
    """
    try:
        aml_officer = get_aml_officer(db)

        results = await aml_officer.batch_investigate(
            alerts=request.alerts,
            max_concurrent=request.max_concurrent
        )

        return {
            "total_alerts": len(request.alerts),
            "successful": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success),
            "results": [
                {
                    "alert_id": request.alerts[i].get("id"),
                    "success": r.success,
                    "recommendation": r.recommendation.value if r.recommendation else None,
                    "confidence": r.confidence,
                    "risk_score": r.risk_score,
                    "red_flags": r.red_flags,
                    "error_message": r.error_message
                }
                for i, r in enumerate(results)
            ]
        }

    except Exception as e:
        logger.error(f"Batch investigation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/investigation/{investigation_id}")
async def get_investigation(
    investigation_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a previously completed investigation by ID.

    Note: Investigation results are currently not persisted.
    This endpoint is a placeholder for future database storage.
    """
    # TODO: Implement investigation storage and retrieval
    raise HTTPException(
        status_code=501,
        detail="Investigation storage not yet implemented"
    )


# =============================================================================
# DAILY BRIEFING ENDPOINTS
# =============================================================================

@router.get("/briefing/daily", response_model=DailyBriefingResponse)
async def get_daily_briefing(
    lookback_hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(get_db)
):
    """
    Generate a daily compliance briefing.

    The AI Compliance Officer analyzes overnight activity and generates
    an executive briefing including:
    - Alert summary (new, critical, pending)
    - Case status (open, requiring action, SAR pending)
    - Risk indicators (high-risk users, emerging patterns)
    - Regulatory updates (new regulations, upcoming deadlines)
    - Priority recommendations

    This is the flagship feature for starting your compliance day.
    """
    try:
        aml_officer = get_aml_officer(db)

        briefing = await aml_officer.generate_daily_briefing(
            lookback_hours=lookback_hours
        )

        return DailyBriefingResponse(
            briefing_id=briefing.briefing_id,
            generated_at=briefing.generated_at.isoformat(),
            period_start=briefing.period_start.isoformat(),
            period_end=briefing.period_end.isoformat(),
            alerts={
                "new": briefing.new_alerts_count,
                "critical": briefing.critical_alerts_count,
                "pending": briefing.pending_alerts_count,
                "auto_resolved": briefing.auto_resolved_count
            },
            cases={
                "open": briefing.open_cases_count,
                "requiring_action": briefing.cases_requiring_action,
                "sar_pending": briefing.sar_pending_count
            },
            risk={
                "high_risk_users": briefing.high_risk_users,
                "emerging_patterns": briefing.emerging_patterns,
                "trend": briefing.risk_trend
            },
            regulatory={
                "new_regulations": briefing.new_regulations,
                "upcoming_deadlines": briefing.upcoming_deadlines
            },
            recommendations={
                "priority_actions": briefing.priority_actions,
                "focus_areas": briefing.focus_areas
            },
            narrative={
                "executive_summary": briefing.executive_summary,
                "detailed_analysis": briefing.detailed_analysis
            }
        )

    except Exception as e:
        logger.error(f"Failed to generate daily briefing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/briefing/weekly")
async def get_weekly_briefing(
    db: Session = Depends(get_db)
):
    """
    Generate a weekly compliance summary.

    Provides a higher-level view suitable for management reporting.
    """
    # TODO: Implement weekly briefing
    return {
        "status": "coming_soon",
        "message": "Weekly briefing feature is under development"
    }


# =============================================================================
# COMPLIANCE Q&A ENDPOINTS
# =============================================================================

@router.post("/ask", response_model=ComplianceAnswerResponse)
async def ask_compliance_question(
    request: ComplianceQuestionRequest,
    db: Session = Depends(get_db)
):
    """
    Ask a compliance question and get an AI-powered answer.

    The AI uses RAG (Retrieval Augmented Generation) to:
    - Search relevant EU regulations
    - Synthesize an accurate answer
    - Provide regulatory citations
    - Suggest follow-up questions

    Example questions:
    - "What are the CDD requirements for high-risk customers?"
    - "When must we file a SAR?"
    - "What are the AMLD 6 implementation deadlines?"
    """
    try:
        aml_officer = get_aml_officer(db)

        response = await aml_officer.ask(
            question=request.question,
            context=request.context,
            conversation_history=request.conversation_history
        )

        return ComplianceAnswerResponse(
            answer=response.get("answer", ""),
            confidence=response.get("confidence", "medium"),
            sources=response.get("sources", []),
            followup_questions=response.get("followup_questions", [])
        )

    except Exception as e:
        logger.error(f"Failed to answer compliance question: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PROACTIVE MONITORING ENDPOINTS
# =============================================================================

@router.get("/alerts/proactive")
async def get_proactive_alerts(
    db: Session = Depends(get_db)
):
    """
    Get AI-generated proactive alerts.

    The AI AML Officer continuously monitors for emerging risks and
    generates alerts before they become problems:
    - Pattern drift detection
    - Threshold breach warnings
    - Regulatory deadline alerts
    - System health indicators
    """
    try:
        aml_officer = get_aml_officer(db)
        alerts = await aml_officer.get_proactive_alerts()

        return {
            "count": len(alerts),
            "alerts": alerts
        }

    except Exception as e:
        logger.error(f"Failed to get proactive alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SAR PREPARATION ENDPOINTS
# =============================================================================

@router.post("/sar/prepare")
async def prepare_sar(
    request: SARPrepareRequest,
    db: Session = Depends(get_db)
):
    """
    Prepare a Suspicious Activity Report (SAR).

    The SAR Agent generates:
    - Narrative description of suspicious activity
    - Subject information extraction
    - Activity timeline
    - Supporting evidence summary
    - Filing-ready document

    The draft requires human review before filing.
    """
    try:
        aml_officer = get_aml_officer(db)

        sar_draft = await aml_officer.prepare_sar(
            case_id=request.case_id,
            case_data=request.case_data,
            related_alerts=request.related_alerts,
            related_transactions=request.related_transactions
        )

        return {
            "success": True,
            "sar_draft": sar_draft
        }

    except Exception as e:
        logger.error(f"Failed to prepare SAR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sar/templates")
async def get_sar_templates():
    """
    Get available SAR templates by jurisdiction.
    """
    return {
        "templates": [
            {
                "id": "eu_fiu",
                "name": "EU FIU Standard",
                "jurisdiction": "EU",
                "description": "Standard EU Financial Intelligence Unit format"
            },
            {
                "id": "goaml",
                "name": "goAML",
                "jurisdiction": "International",
                "description": "UNODC goAML format for international reporting"
            }
        ]
    }


# =============================================================================
# SANCTIONS SCREENING ENDPOINTS
# =============================================================================

@router.post("/sanctions/screen", response_model=SanctionsScreenResponse)
async def screen_sanctions(
    request: SanctionsScreenRequest
):
    """
    Screen a name against sanctions lists.

    Checks against:
    - EU Consolidated Financial Sanctions List
    - OFAC SDN (Specially Designated Nationals) List

    Returns match details with confidence scores.
    """
    try:
        service = SanctionsService()

        # Determine lists to check
        lists_to_check = None
        if request.lists:
            lists_to_check = [
                SanctionsListType(l) for l in request.lists
                if l in [t.value for t in SanctionsListType]
            ]

        # Build additional info for matching
        additional_info = {}
        if request.nationality:
            additional_info["nationality"] = request.nationality
        if request.birth_date:
            additional_info["birth_date"] = request.birth_date

        result = await service.screen_name(
            name=request.name,
            lists=lists_to_check,
            additional_info=additional_info if additional_info else None
        )

        return SanctionsScreenResponse(
            screened_name=result.screened_name,
            screened_at=result.screened_at.isoformat(),
            is_hit=result.is_hit,
            match_count=len(result.matches),
            highest_score=result.highest_score,
            matches=[m.to_dict() for m in result.matches],
            lists_checked=[l.value for l in result.lists_checked],
            processing_time_ms=result.processing_time_ms
        )

    except Exception as e:
        logger.error(f"Sanctions screening failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sanctions/screen/batch")
async def batch_screen_sanctions(
    request: BatchSanctionsScreenRequest
):
    """
    Screen multiple names against sanctions lists.

    Efficient batch processing for bulk screening operations.
    """
    try:
        service = SanctionsService()

        results = await service.screen_batch(
            names=request.names,
            max_concurrent=request.max_concurrent
        )

        return {
            "total_screened": len(request.names),
            "hits": sum(1 for r in results if r.is_hit),
            "clear": sum(1 for r in results if not r.is_hit),
            "results": [r.to_dict() for r in results]
        }

    except Exception as e:
        logger.error(f"Batch sanctions screening failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sanctions/statistics")
async def get_sanctions_statistics():
    """
    Get statistics about loaded sanctions lists.
    """
    try:
        service = SanctionsService()
        stats = await service.get_list_statistics()

        return stats

    except Exception as e:
        logger.error(f"Failed to get sanctions statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# WORKFLOW ENDPOINTS
# =============================================================================

@router.post("/workflow/execute")
async def execute_workflow(
    workflow_type: str,
    context_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Execute a multi-agent workflow.

    Available workflows:
    - alert_triage: Quick triage of an alert
    - full_investigation: Complete investigation with all agents
    - sar_preparation: Prepare a SAR from a case
    - compliance_qa: Answer a compliance question
    """
    try:
        # Map string to WorkflowType
        workflow_map = {
            "alert_triage": WorkflowType.ALERT_TRIAGE,
            "full_investigation": WorkflowType.FULL_INVESTIGATION,
            "sar_preparation": WorkflowType.SAR_PREPARATION,
            "compliance_qa": WorkflowType.COMPLIANCE_QA,
            "daily_briefing": WorkflowType.DAILY_BRIEFING
        }

        if workflow_type not in workflow_map:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown workflow type: {workflow_type}"
            )

        aml_officer = get_aml_officer(db)

        context = AgentContext(
            session_id=context_data.get("session_id", ""),
            user_id=context_data.get("user_id"),
            task_type=workflow_type,
            primary_data=context_data.get("primary_data"),
            related_data=context_data.get("related_data", []),
            applicable_regulations=context_data.get("applicable_regulations", [])
        )

        result = await aml_officer.execute_workflow(
            workflow_type=workflow_map[workflow_type],
            initial_context=context
        )

        return result.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# HEALTH & STATUS ENDPOINTS
# =============================================================================

@router.get("/health")
async def health_check():
    """
    Check the health of the AI AML Officer system.
    """
    try:
        # Check sanctions service
        sanctions_service = SanctionsService()
        sanctions_healthy = await sanctions_service.health_check()

        return {
            "status": "healthy" if sanctions_healthy else "degraded",
            "components": {
                "orchestrator": "healthy",
                "investigation_agent": "healthy",
                "sanctions_service": "healthy" if sanctions_healthy else "unhealthy"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/capabilities")
async def get_capabilities():
    """
    Get the capabilities of the AI AML Officer.
    """
    return {
        "agents": [
            {
                "type": "investigation",
                "status": "active",
                "description": "Deep-dive alert analysis and investigation"
            },
            {
                "type": "triage",
                "status": "active",
                "description": "Real-time alert scoring and prioritization"
            },
            {
                "type": "sar",
                "status": "active",
                "description": "SAR narrative generation and filing"
            },
            {
                "type": "compliance_officer",
                "status": "active",
                "description": "Daily briefings and proactive monitoring"
            },
            {
                "type": "network",
                "status": "planned",
                "description": "Graph-based fraud detection"
            }
        ],
        "integrations": [
            {
                "name": "EU Consolidated Sanctions List",
                "status": "active"
            },
            {
                "name": "OFAC SDN List",
                "status": "active"
            },
            {
                "name": "EU CELLAR (Regulations)",
                "status": "active"
            }
        ],
        "features": {
            "investigation": True,
            "batch_investigation": True,
            "daily_briefing": True,
            "compliance_qa": True,
            "sanctions_screening": True,
            "sar_preparation": True,
            "proactive_alerts": True
        }
    }
