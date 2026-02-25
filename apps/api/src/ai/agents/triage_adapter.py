"""
Lightweight triage adapter agent for AML Officer workflows.

This allows orchestrated workflows to execute a TRIAGE step using the shared
AgentResult/AgentContext contract even when the standalone alert triage service
is used elsewhere via `/api/ai/*`.
"""

from __future__ import annotations

from typing import Any, Dict

from .base import (
    ActionRecommendation,
    AgentContext,
    AgentResult,
    AgentType,
    BaseAgent,
)


class TriageAdapterAgent(BaseAgent[AgentResult]):
    @property
    def agent_type(self) -> AgentType:
        return AgentType.TRIAGE

    @property
    def system_prompt(self) -> str:
        return (
            "You are an AML alert triage analyst. Return concise, structured triage "
            "analysis based on the supplied alert context."
        )

    async def process(self, context: AgentContext) -> AgentResult:
        primary = context.primary_data or {}
        recommendation = ActionRecommendation.INVESTIGATE
        severity = str(primary.get("severity") or "").lower()
        risk_score = primary.get("risk_score")

        try:
            score = float(risk_score) if risk_score is not None else None
        except Exception:
            score = None

        if severity == "critical" or (score is not None and score >= 85):
            recommendation = ActionRecommendation.ESCALATE
        elif severity == "low" and (score is None or score < 30):
            recommendation = ActionRecommendation.MONITOR

        summary = (
            f"Triage assessment for alert {primary.get('alert_id') or context.task_id or 'unknown'}: "
            f"recommend {recommendation.value}."
        )
        if severity:
            summary += f" Severity={severity}."
        if score is not None:
            summary += f" Risk score={score:.1f}."

        return AgentResult(
            agent_type=self.agent_type,
            success=True,
            recommendation=recommendation,
            summary=summary,
            detailed_analysis="Workflow triage adapter completed preliminary alert assessment.",
            confidence=0.7,
            risk_score=score,
            red_flags=[],
            next_steps=["Review evidence", "Confirm recommendation with human analyst"],
        )
