"""
AI AML Officer Orchestrator

The orchestration layer that coordinates multiple specialized AI agents
to provide comprehensive AML compliance support. This is the main entry
point for all AI-powered compliance operations.

The orchestrator handles:
- Agent lifecycle management
- Multi-agent workflows
- Context propagation between agents
- Result aggregation
- Audit trail creation
- Error handling and fallbacks

Architecture:
                    ┌─────────────────────────────┐
                    │     AI AML OFFICER          │
                    │   (Orchestration Layer)     │
                    └─────────────┬───────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
   TriageAgent          InvestigationAgent         RegulatoryAgent
        │                         │                         │
        ▼                         ▼                         ▼
    SARAgent              NetworkAgent         ComplianceOfficer
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import uuid

from .agents.base import (
    BaseAgent,
    AgentContext,
    AgentResult,
    AgentType,
    AgentRegistry,
    ActionRecommendation,
    ConfidenceLevel,
)

logger = logging.getLogger(__name__)


class WorkflowType(str, Enum):
    """Types of multi-agent workflows."""

    ALERT_TRIAGE = "alert_triage"
    FULL_INVESTIGATION = "full_investigation"
    SAR_PREPARATION = "sar_preparation"
    NETWORK_ANALYSIS = "network_analysis"
    DAILY_BRIEFING = "daily_briefing"
    COMPLIANCE_QA = "compliance_qa"
    REGULATORY_IMPACT = "regulatory_impact"


@dataclass
class WorkflowStep:
    """A step in a multi-agent workflow."""

    agent_type: AgentType
    name: str
    description: str
    required: bool = True
    condition: Optional[Callable[[List[AgentResult]], bool]] = None
    timeout_seconds: int = 120


@dataclass
class WorkflowResult:
    """Result from a multi-agent workflow."""

    workflow_type: WorkflowType
    workflow_id: str
    success: bool
    steps_completed: int
    total_steps: int
    agent_results: List[AgentResult]
    final_recommendation: Optional[ActionRecommendation] = None
    final_confidence: float = 0.0
    summary: str = ""
    processing_time_ms: int = 0
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "workflow_type": self.workflow_type.value,
            "workflow_id": self.workflow_id,
            "success": self.success,
            "steps_completed": self.steps_completed,
            "total_steps": self.total_steps,
            "agent_results": [r.to_dict() for r in self.agent_results],
            "final_recommendation": (
                self.final_recommendation.value if self.final_recommendation else None
            ),
            "final_confidence": self.final_confidence,
            "summary": self.summary,
            "processing_time_ms": self.processing_time_ms,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class DailyBriefing:
    """Daily briefing data structure."""

    briefing_id: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime

    # Alert summary
    new_alerts_count: int = 0
    critical_alerts_count: int = 0
    pending_alerts_count: int = 0
    auto_resolved_count: int = 0

    # Case summary
    open_cases_count: int = 0
    cases_requiring_action: int = 0
    sar_pending_count: int = 0

    # Risk indicators
    high_risk_users: List[Dict[str, Any]] = field(default_factory=list)
    emerging_patterns: List[str] = field(default_factory=list)
    risk_trend: str = "stable"  # "increasing", "stable", "decreasing"

    # Regulatory updates
    new_regulations: List[Dict[str, Any]] = field(default_factory=list)
    upcoming_deadlines: List[Dict[str, Any]] = field(default_factory=list)

    # Recommendations
    priority_actions: List[str] = field(default_factory=list)
    focus_areas: List[str] = field(default_factory=list)

    # AI-generated narrative
    executive_summary: str = ""
    detailed_analysis: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "briefing_id": self.briefing_id,
            "generated_at": self.generated_at.isoformat(),
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "alerts": {
                "new": self.new_alerts_count,
                "critical": self.critical_alerts_count,
                "pending": self.pending_alerts_count,
                "auto_resolved": self.auto_resolved_count,
            },
            "cases": {
                "open": self.open_cases_count,
                "requiring_action": self.cases_requiring_action,
                "sar_pending": self.sar_pending_count,
            },
            "risk": {
                "high_risk_users": self.high_risk_users,
                "emerging_patterns": self.emerging_patterns,
                "trend": self.risk_trend,
            },
            "regulatory": {
                "new_regulations": self.new_regulations,
                "upcoming_deadlines": self.upcoming_deadlines,
            },
            "recommendations": {
                "priority_actions": self.priority_actions,
                "focus_areas": self.focus_areas,
            },
            "narrative": {
                "executive_summary": self.executive_summary,
                "detailed_analysis": self.detailed_analysis,
            },
        }


class AMLOfficer:
    """
    AI AML Officer - The main orchestration layer.

    This class coordinates multiple specialized AI agents to provide
    comprehensive AML compliance support. It acts as your tireless,
    expert compliance partner.

    Key capabilities:
    - Single alert investigation
    - Batch alert processing
    - Full case investigation
    - SAR preparation and review
    - Network/fraud ring analysis
    - Daily compliance briefings
    - Natural language compliance Q&A
    - Proactive risk monitoring
    """

    # Workflow definitions
    WORKFLOWS: Dict[WorkflowType, List[WorkflowStep]] = {
        WorkflowType.ALERT_TRIAGE: [
            WorkflowStep(
                agent_type=AgentType.TRIAGE,
                name="Initial Triage",
                description="Assess alert severity and recommend action",
            )
        ],
        WorkflowType.FULL_INVESTIGATION: [
            WorkflowStep(
                agent_type=AgentType.TRIAGE,
                name="Initial Triage",
                description="Assess alert severity",
            ),
            WorkflowStep(
                agent_type=AgentType.INVESTIGATION,
                name="Deep Investigation",
                description="Gather evidence and analyze patterns",
            ),
            WorkflowStep(
                agent_type=AgentType.NETWORK,
                name="Network Analysis",
                description="Analyze transaction network",
                required=False,
                condition=lambda results: any(r.risk_score and r.risk_score > 70 for r in results),
            ),
            WorkflowStep(
                agent_type=AgentType.COMPLIANCE_OFFICER,
                name="Regulatory Mapping",
                description="Map findings to regulations",
            ),
        ],
        WorkflowType.SAR_PREPARATION: [
            WorkflowStep(
                agent_type=AgentType.INVESTIGATION,
                name="Evidence Review",
                description="Review all case evidence",
            ),
            WorkflowStep(
                agent_type=AgentType.SAR,
                name="SAR Generation",
                description="Generate SAR narrative and form data",
            ),
        ],
        WorkflowType.DAILY_BRIEFING: [
            WorkflowStep(
                agent_type=AgentType.COMPLIANCE_OFFICER,
                name="Daily Briefing",
                description="Generate daily compliance briefing",
            )
        ],
        WorkflowType.COMPLIANCE_QA: [
            WorkflowStep(
                agent_type=AgentType.COMPLIANCE_OFFICER,
                name="Regulatory Query",
                description="Answer compliance question with citations",
            )
        ],
    }

    def __init__(self, db_session=None):
        """
        Initialize the AI AML Officer.

        Args:
            db_session: SQLAlchemy database session for data access
        """
        self.db = db_session
        self._initialized = False
        self._agents: Dict[AgentType, BaseAgent] = {}

        logger.info("AI AML Officer initialized")

    async def initialize(self) -> None:
        """
        Initialize all agents.

        Called lazily on first use to avoid startup delays.
        """
        if self._initialized:
            return

        try:
            # Import and initialize agents
            from .agents.investigation import InvestigationAgent
            from .agents.sar import SARAgent
            from .agents.compliance_officer import ComplianceOfficerAgent
            from .agents.triage_adapter import TriageAdapterAgent

            self._agents[AgentType.TRIAGE] = TriageAdapterAgent()
            self._agents[AgentType.INVESTIGATION] = InvestigationAgent()
            self._agents[AgentType.SAR] = SARAgent()
            self._agents[AgentType.COMPLIANCE_OFFICER] = ComplianceOfficerAgent()

            # Register all agents
            for agent in self._agents.values():
                AgentRegistry.register(agent)

            # TODO: Initialize network agent when built
            # from .agents.network import NetworkAgent
            # self._agents[AgentType.NETWORK] = NetworkAgent()

            self._initialized = True
            logger.info(f"AI AML Officer fully initialized with {len(self._agents)} agents")

        except Exception as e:
            logger.error(f"Failed to initialize AI AML Officer: {e}")
            raise

    def get_agent(self, agent_type: AgentType) -> Optional[BaseAgent]:
        """Get an agent by type."""
        return self._agents.get(agent_type)

    # =========================================================================
    # SINGLE ALERT OPERATIONS
    # =========================================================================

    async def investigate_alert(
        self,
        alert_id: int,
        alert_data: Dict[str, Any],
        related_transactions: Optional[List[Dict[str, Any]]] = None,
        related_regulations: Optional[List[Dict[str, Any]]] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> AgentResult:
        """
        Investigate a single alert using the Investigation Agent.

        This is the primary method for alert analysis. It:
        1. Gathers all relevant context
        2. Analyzes the alert using AI
        3. Returns a comprehensive investigation report

        Args:
            alert_id: The alert ID to investigate
            alert_data: The alert details
            related_transactions: Related transaction data
            related_regulations: Applicable regulations
            user_id: The user/customer ID associated with the alert

        Returns:
            AgentResult with investigation findings
        """
        await self.initialize()

        agent = self.get_agent(AgentType.INVESTIGATION)
        if not agent:
            return AgentResult.from_error(
                AgentType.INVESTIGATION, "Investigation agent not available"
            )

        # Build context
        context = AgentContext(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            tenant_id=tenant_id,
            task_type="alert_investigation",
            task_id=str(alert_id),
            primary_data=alert_data,
            related_data=related_transactions or [],
            applicable_regulations=related_regulations or [],
        )

        try:
            result = await agent.process(context)

            # Log for audit trail
            logger.info(
                f"Investigation complete for alert {alert_id}: "
                f"recommendation={result.recommendation}, "
                f"confidence={result.confidence}"
            )

            return result

        except Exception as e:
            logger.error(f"Investigation failed for alert {alert_id}: {e}")
            return AgentResult.from_error(AgentType.INVESTIGATION, str(e))

    async def batch_investigate(
        self, alerts: List[Dict[str, Any]], max_concurrent: int = 5
    ) -> List[AgentResult]:
        """
        Investigate multiple alerts concurrently.

        Args:
            alerts: List of alert data dictionaries
            max_concurrent: Maximum concurrent investigations

        Returns:
            List of AgentResults, one per alert
        """
        await self.initialize()

        semaphore = asyncio.Semaphore(max_concurrent)

        async def investigate_one(alert: Dict[str, Any]) -> AgentResult:
            async with semaphore:
                return await self.investigate_alert(
                    alert_id=alert.get("id"), alert_data=alert, user_id=alert.get("user_id")
                )

        results = await asyncio.gather(
            *[investigate_one(alert) for alert in alerts], return_exceptions=True
        )

        # Convert exceptions to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    AgentResult.from_error(
                        AgentType.INVESTIGATION, f"Investigation failed: {str(result)}"
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    # =========================================================================
    # WORKFLOW OPERATIONS
    # =========================================================================

    async def execute_workflow(
        self, workflow_type: WorkflowType, initial_context: AgentContext
    ) -> WorkflowResult:
        """
        Execute a multi-agent workflow.

        Args:
            workflow_type: The type of workflow to execute
            initial_context: Starting context for the workflow

        Returns:
            WorkflowResult with all agent outputs
        """
        await self.initialize()

        import time

        start_time = time.time()

        workflow_id = str(uuid.uuid4())
        steps = self.WORKFLOWS.get(workflow_type, [])

        if not steps:
            return WorkflowResult(
                workflow_type=workflow_type,
                workflow_id=workflow_id,
                success=False,
                steps_completed=0,
                total_steps=0,
                agent_results=[],
                error_message=f"Unknown workflow type: {workflow_type}",
            )

        results: List[AgentResult] = []
        context = initial_context

        for i, step in enumerate(steps):
            # Check condition if present
            if step.condition and not step.condition(results):
                logger.info(f"Skipping step {step.name} - condition not met")
                continue

            agent = self.get_agent(step.agent_type)
            if not agent:
                if step.required:
                    return WorkflowResult(
                        workflow_type=workflow_type,
                        workflow_id=workflow_id,
                        success=False,
                        steps_completed=i,
                        total_steps=len(steps),
                        agent_results=results,
                        error_message=f"Required agent not available: {step.agent_type.value}",
                    )
                continue

            try:
                # Add previous results to context
                context.previous_agent_results = results.copy()
                context.input_data = dict(context.input_data or {})
                if step.agent_type == AgentType.COMPLIANCE_OFFICER:
                    if workflow_type == WorkflowType.DAILY_BRIEFING:
                        context.input_data.setdefault("action", "generate_briefing")
                    elif workflow_type == WorkflowType.COMPLIANCE_QA:
                        context.input_data.setdefault("action", "answer_question")
                    elif (
                        workflow_type == WorkflowType.FULL_INVESTIGATION
                        and step.name == "Regulatory Mapping"
                    ):
                        context.input_data.setdefault("action", "assess_impact")

                result = await asyncio.wait_for(
                    agent.process(context), timeout=step.timeout_seconds
                )
                results.append(result)

                logger.info(f"Workflow step {step.name} completed")

            except asyncio.TimeoutError:
                if step.required:
                    return WorkflowResult(
                        workflow_type=workflow_type,
                        workflow_id=workflow_id,
                        success=False,
                        steps_completed=i,
                        total_steps=len(steps),
                        agent_results=results,
                        error_message=f"Step {step.name} timed out",
                    )
            except Exception as e:
                if step.required:
                    return WorkflowResult(
                        workflow_type=workflow_type,
                        workflow_id=workflow_id,
                        success=False,
                        steps_completed=i,
                        total_steps=len(steps),
                        agent_results=results,
                        error_message=f"Step {step.name} failed: {str(e)}",
                    )

        # Aggregate final results
        final_recommendation = self._aggregate_recommendations(results)
        final_confidence = self._aggregate_confidence(results)
        summary = self._generate_workflow_summary(workflow_type, results)

        processing_time = int((time.time() - start_time) * 1000)

        return WorkflowResult(
            workflow_type=workflow_type,
            workflow_id=workflow_id,
            success=True,
            steps_completed=len(results),
            total_steps=len(steps),
            agent_results=results,
            final_recommendation=final_recommendation,
            final_confidence=final_confidence,
            summary=summary,
            processing_time_ms=processing_time,
        )

    def _aggregate_recommendations(
        self, results: List[AgentResult]
    ) -> Optional[ActionRecommendation]:
        """Aggregate recommendations from multiple agents."""
        if not results:
            return None

        # Priority order: ESCALATE > FILE_SAR > INVESTIGATE > RESOLVE > FALSE_POSITIVE
        priority = [
            ActionRecommendation.ESCALATE,
            ActionRecommendation.FILE_SAR,
            ActionRecommendation.INVESTIGATE,
            ActionRecommendation.RESOLVE,
            ActionRecommendation.FALSE_POSITIVE,
            ActionRecommendation.MONITOR,
            ActionRecommendation.NO_ACTION,
        ]

        recommendations = [r.recommendation for r in results if r.recommendation]
        for rec in priority:
            if rec in recommendations:
                return rec

        return results[-1].recommendation if results else None

    def _aggregate_confidence(self, results: List[AgentResult]) -> float:
        """Calculate aggregate confidence from multiple agents."""
        if not results:
            return 0.0

        # Weighted average, with later agents having slightly more weight
        total_weight = 0
        weighted_sum = 0

        for i, result in enumerate(results):
            weight = 1 + (i * 0.2)  # Later agents have more weight
            weighted_sum += result.confidence * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _generate_workflow_summary(
        self, workflow_type: WorkflowType, results: List[AgentResult]
    ) -> str:
        """Generate a summary of workflow results."""
        if not results:
            return "No analysis completed."

        summaries = [r.summary for r in results if r.summary]
        red_flags = []
        for r in results:
            red_flags.extend(r.red_flags)

        summary_parts = [
            f"Workflow: {workflow_type.value}",
            f"Steps completed: {len(results)}",
            f"Red flags identified: {len(red_flags)}",
        ]

        if summaries:
            summary_parts.append(f"Analysis: {summaries[-1]}")

        return " | ".join(summary_parts)

    # =========================================================================
    # DAILY BRIEFING
    # =========================================================================

    async def generate_daily_briefing(
        self,
        user_id: Optional[str] = None,
        lookback_hours: int = 24,
        tenant_id: Optional[str] = None,
    ) -> DailyBriefing:
        """
        Generate a daily compliance briefing.

        This is the flagship feature of the AI AML Officer - a morning
        briefing that summarizes overnight activity, highlights risks,
        and recommends priority actions.

        Args:
            user_id: Optional user ID for personalization
            lookback_hours: Hours to look back (default 24)

        Returns:
            DailyBriefing with comprehensive compliance summary
        """
        await self.initialize()

        briefing_id = str(uuid.uuid4())
        now = utc_now()
        period_start = now - timedelta(hours=lookback_hours)

        # TODO: Fetch actual data from database
        # For now, create a placeholder that will be enhanced

        briefing = DailyBriefing(
            briefing_id=briefing_id,
            generated_at=now,
            period_start=period_start,
            period_end=now,
            executive_summary=(
                "Good morning. This is your AI AML Officer daily briefing. "
                "I've analyzed overnight activity and prepared a summary of "
                "key compliance matters requiring your attention."
            ),
            priority_actions=[
                "Review 3 high-priority alerts pending triage",
                "Check upcoming regulatory deadline in 7 days",
                "Complete SAR preparation for Case #1234",
            ],
            focus_areas=[
                "Transaction monitoring rule effectiveness",
                "New AMLD 6 requirements implementation",
            ],
        )

        logger.info(f"Generated daily briefing {briefing_id}")
        return briefing

    # =========================================================================
    # COMPLIANCE Q&A
    # =========================================================================

    async def ask(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Answer a compliance question using AI.

        This provides a ChatGPT-style interface for compliance queries,
        using RAG to ground answers in actual regulations.

        Args:
            question: The compliance question to answer
            context: Optional additional context
            conversation_history: Previous conversation turns

        Returns:
            Answer with citations and confidence
        """
        await self.initialize()

        # Use the existing RAG service for now
        # This will be enhanced with the ComplianceOfficerAgent later
        from .rag_service import RAGService

        rag = RAGService(self.db)

        response = await rag.ask(
            question=question,
            max_documents=5,
            conversation_history=conversation_history,
            db=self.db,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        return {
            "answer": response.get("answer", ""),
            "confidence": response.get("confidence", "medium"),
            "sources": response.get("sources", []),
            "followup_questions": response.get("followup_questions", []),
        }

    # =========================================================================
    # PROACTIVE MONITORING
    # =========================================================================

    async def get_proactive_alerts(self) -> List[Dict[str, Any]]:
        """
        Get AI-generated proactive alerts.

        The AI AML Officer continuously monitors for emerging risks
        and generates alerts before they become problems.

        Returns:
            List of proactive alert recommendations
        """
        await self.initialize()

        # TODO: Implement proactive monitoring logic
        # This will analyze:
        # - Pattern drift in transaction monitoring
        # - Threshold breach warnings
        # - Regulatory deadline alerts
        # - System health indicators

        return [
            {
                "type": "pattern_drift",
                "severity": "medium",
                "message": "Transaction velocity patterns have shifted 15% from baseline",
                "recommendation": "Review velocity rule thresholds",
                "detected_at": utc_now().isoformat(),
            },
            {
                "type": "deadline_warning",
                "severity": "high",
                "message": "AMLD 6 implementation deadline in 30 days",
                "recommendation": "Complete gap assessment",
                "detected_at": utc_now().isoformat(),
            },
        ]

    # =========================================================================
    # SAR OPERATIONS
    # =========================================================================

    async def prepare_sar(
        self,
        case_id: int,
        case_data: Dict[str, Any],
        related_alerts: List[Dict[str, Any]],
        related_transactions: List[Dict[str, Any]],
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Prepare a SAR (Suspicious Activity Report) for filing.

        Uses the SAR Agent to generate a complete filing package:
        - Narrative description
        - Subject information
        - Suspicious activity details
        - Supporting documentation

        Args:
            case_id: The case ID
            case_data: Case details
            related_alerts: Alerts related to the case
            related_transactions: Transactions related to the case

        Returns:
            SAR preparation package
        """
        await self.initialize()

        agent = self.get_agent(AgentType.SAR)
        if not agent:
            return {
                "case_id": case_id,
                "status": "error",
                "error": "SAR agent not available",
                "generated_at": utc_now().isoformat(),
            }

        # Build context for SAR agent
        context = AgentContext(
            session_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            task_type="sar_preparation",
            task_id=str(case_id),
            primary_data=case_data,
            related_data=related_transactions,
            input_data={
                "case_id": str(case_id),
                "case_data": case_data,
                "transactions": related_transactions,
                "investigation_summary": (
                    related_alerts[0].get("investigation_summary") if related_alerts else None
                ),
            },
        )

        try:
            result = await agent.process(context)

            if result.success:
                return result.result
            else:
                return {
                    "case_id": case_id,
                    "status": "error",
                    "error": result.error or "SAR generation failed",
                    "generated_at": utc_now().isoformat(),
                }

        except Exception as e:
            logger.error(f"SAR preparation failed for case {case_id}: {e}")
            return {
                "case_id": case_id,
                "status": "error",
                "error": str(e),
                "generated_at": utc_now().isoformat(),
            }


def get_aml_officer(db_session=None) -> AMLOfficer:
    """Create a request-scoped AML Officer instance."""
    return AMLOfficer(db_session)
