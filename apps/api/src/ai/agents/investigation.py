"""
Investigation Agent - Deep-dive Alert Analysis

The Investigation Agent is responsible for comprehensive alert analysis,
evidence gathering, and investigation report generation. It provides
the detailed analysis needed to make informed decisions about alerts.

Key Capabilities:
- Multi-step chain-of-thought reasoning
- Evidence gathering and correlation
- Pattern identification and analysis
- Regulatory citation matching
- Red flag detection
- Risk assessment
- Investigation report generation
- Recommended actions with rationale

The agent uses Claude Sonnet 4 for sophisticated analysis and
produces detailed, auditable investigation reports.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import (
    BaseAgent,
    AgentContext,
    AgentResult,
    AgentType,
    ActionRecommendation,
    ConfidenceLevel,
    Citation,
    ReasoningStep,
)

logger = logging.getLogger(__name__)


class InvestigationAgent(BaseAgent):
    """
    Investigation Agent - Comprehensive alert analysis.

    This agent performs deep-dive analysis of alerts, gathering evidence,
    identifying patterns, and generating detailed investigation reports.

    Processing Steps:
    1. Context Analysis - Understand the alert and its context
    2. Evidence Gathering - Collect relevant data points
    3. Pattern Analysis - Identify suspicious patterns
    4. Risk Assessment - Calculate risk scores
    5. Regulatory Mapping - Match to applicable regulations
    6. Report Generation - Create comprehensive report
    7. Action Recommendation - Suggest next steps
    """

    INVESTIGATION_PROMPT = """You are an expert AML/CFT Investigation Agent for a European financial institution.

Your task is to conduct a thorough investigation of the provided alert and generate a comprehensive investigation report.

## Investigation Framework

Follow this structured approach:

### 1. ALERT ANALYSIS
- What type of alert is this?
- What triggered the alert?
- What is the severity level?
- Who is the subject of the alert?

### 2. EVIDENCE GATHERING
- Review all available transaction data
- Identify key financial patterns
- Note any anomalies or red flags
- Document the evidence trail

### 3. PATTERN RECOGNITION
Analyze for these specific patterns:
- **Structuring**: Transactions just below reporting thresholds (€9,000-€9,999 for EU)
- **Layering**: Complex transaction chains to obscure origin
- **Velocity**: Unusual frequency or volume of transactions
- **Geographic Risk**: High-risk jurisdictions (per EU/FATF lists)
- **Round Amounts**: Suspicious round-number transactions
- **Time Patterns**: Unusual timing (late night, weekends)

### 4. RISK ASSESSMENT
Calculate a risk score (0-100) based on:
- Transaction characteristics (amount, type, frequency)
- Customer profile (history, KYC status, PEP status)
- Geographic factors (origin, destination countries)
- Behavioral indicators (deviation from baseline)

### 5. REGULATORY CONTEXT
Map findings to applicable EU regulations:
- AMLD 5/6 (Anti-Money Laundering Directives)
- EBA Guidelines on AML/CFT
- Regulation (EU) 2015/847 (Transfer of Funds)
- EU Sanctions Regulations

### 6. RECOMMENDATION
Based on your analysis, recommend one of:
- **ESCALATE**: High risk, requires senior review or immediate action
- **INVESTIGATE**: Further investigation needed
- **FILE_SAR**: Evidence supports suspicious activity report
- **RESOLVE**: No further action, document findings
- **FALSE_POSITIVE**: Clear false positive, close with explanation
- **MONITOR**: Enhanced monitoring recommended

## Output Format

Respond with a JSON object containing:

```json
{
    "summary": "Brief executive summary (2-3 sentences)",
    "detailed_analysis": "Comprehensive analysis (paragraph form)",
    "reasoning_chain": [
        {
            "description": "Step description",
            "evidence": ["Evidence point 1", "Evidence point 2"],
            "conclusion": "Step conclusion",
            "confidence": 0.85
        }
    ],
    "red_flags": ["Red flag 1", "Red flag 2"],
    "mitigating_factors": ["Mitigating factor 1"],
    "risk_factors": ["Risk factor 1", "Risk factor 2"],
    "risk_score": 75,
    "recommendation": "ESCALATE|INVESTIGATE|FILE_SAR|RESOLVE|FALSE_POSITIVE|MONITOR",
    "confidence": 0.85,
    "sar_likelihood": 0.7,
    "citations": [
        {
            "source_type": "regulation",
            "reference": "AMLD 5, Article 13",
            "celex_id": "32015L0849",
            "excerpt": "Relevant excerpt",
            "relevance_score": 0.9
        }
    ],
    "next_steps": [
        "Specific action 1",
        "Specific action 2"
    ],
    "evidence_summary": [
        {
            "type": "transaction",
            "description": "Evidence description",
            "significance": "high|medium|low"
        }
    ],
    "timeline": [
        {
            "timestamp": "ISO timestamp",
            "event": "Event description",
            "significance": "high|medium|low"
        }
    ],
    "investigation_checklist": [
        {
            "item": "Checklist item",
            "completed": true,
            "notes": "Any notes"
        }
    ]
}
```

## Important Guidelines

1. **Be thorough but concise** - Cover all relevant points without unnecessary verbosity
2. **Cite regulations** - Always reference applicable EU regulations
3. **Quantify when possible** - Use specific numbers and percentages
4. **Be objective** - Present evidence without bias
5. **Consider context** - Account for legitimate business reasons
6. **Document uncertainty** - Clearly state when evidence is inconclusive
7. **Actionable recommendations** - Provide specific, actionable next steps
8. **Audit trail** - Ensure all conclusions are traceable to evidence

Remember: Your analysis may be used in regulatory examinations and legal proceedings.
Maintain the highest standards of accuracy and professionalism."""

    @property
    def agent_type(self) -> AgentType:
        return AgentType.INVESTIGATION

    @property
    def system_prompt(self) -> str:
        return self.INVESTIGATION_PROMPT

    @property
    def agent_version(self) -> str:
        return "1.0.0"

    async def process(self, context: AgentContext) -> AgentResult:
        """
        Process an alert and generate investigation report.

        Args:
            context: AgentContext with alert data and related information

        Returns:
            AgentResult with comprehensive investigation findings
        """
        import time

        start_time = time.time()

        try:
            # Build the investigation prompt
            user_prompt = self._build_investigation_prompt(context)

            # Call Claude for analysis
            response = await self.call_claude(
                user_prompt=user_prompt, context=context, json_mode=True
            )

            # Parse and structure the response
            result = self._parse_response(response, context)

            # Add processing metadata
            result.processing_time_ms = int((time.time() - start_time) * 1000)
            result.tokens_used = response.get("_meta", {}).get("tokens_used", 0)
            result.model_used = response.get("_meta", {}).get("model_used", self.model)

            logger.info(
                f"Investigation complete: recommendation={result.recommendation}, "
                f"confidence={result.confidence}, risk_score={result.risk_score}"
            )

            return result

        except Exception as e:
            logger.error(f"Investigation failed: {e}")
            return AgentResult.from_error(self.agent_type, str(e))

    def _build_investigation_prompt(self, context: AgentContext) -> str:
        """Build the user prompt for investigation."""
        prompt_parts = []

        # Alert data
        if context.primary_data:
            prompt_parts.append("## ALERT DATA")
            prompt_parts.append(self._format_data(context.primary_data))

        # Related transactions
        if context.related_data:
            prompt_parts.append("\n## RELATED TRANSACTIONS")
            for i, txn in enumerate(context.related_data[:20]):  # Limit to 20
                prompt_parts.append(f"\n### Transaction {i+1}")
                prompt_parts.append(self._format_data(txn))

        # Applicable regulations
        if context.applicable_regulations:
            prompt_parts.append("\n## APPLICABLE REGULATIONS")
            for reg in context.applicable_regulations[:5]:  # Limit to 5
                prompt_parts.append(
                    f"- {reg.get('title', 'Unknown')} (CELEX: {reg.get('celex_id', 'N/A')})"
                )

        # Previous agent results (for multi-agent workflows)
        if context.previous_agent_results:
            prompt_parts.append("\n## PREVIOUS ANALYSIS")
            for prev in context.previous_agent_results:
                prompt_parts.append(f"- Agent: {prev.agent_type.value}")
                prompt_parts.append(f"  Summary: {prev.summary}")
                if prev.red_flags:
                    prompt_parts.append(f"  Red Flags: {', '.join(prev.red_flags)}")

        prompt_parts.append("\n## TASK")
        prompt_parts.append(
            "Conduct a comprehensive investigation of this alert and provide your analysis in the required JSON format."
        )

        return "\n".join(prompt_parts)

    def _format_data(self, data: Dict[str, Any]) -> str:
        """Format data dictionary for prompt."""
        lines = []
        for key, value in data.items():
            if value is not None:
                # Skip internal fields
                if key.startswith("_"):
                    continue
                # Format datetime objects
                if isinstance(value, datetime):
                    value = value.isoformat()
                lines.append(f"- **{key}**: {value}")
        return "\n".join(lines)

    def _parse_response(self, response: Dict[str, Any], context: AgentContext) -> AgentResult:
        """Parse Claude's response into AgentResult."""

        # Handle raw content fallback
        if "raw_content" in response:
            return AgentResult(
                agent_type=self.agent_type,
                success=False,
                error_message="Failed to parse AI response",
                summary=response.get("raw_content", "")[:500],
            )

        # Extract recommendation
        rec_str = response.get("recommendation", "INVESTIGATE").upper()
        try:
            recommendation = ActionRecommendation(rec_str.lower())
        except ValueError:
            recommendation = ActionRecommendation.INVESTIGATE

        # Extract confidence
        confidence = float(response.get("confidence", 0.5))
        confidence_level = self.calculate_confidence_level(confidence)

        # Build reasoning chain
        reasoning_chain = self.build_reasoning_chain(response.get("reasoning_chain", []))

        # Build citations
        citations = self.build_citations(response.get("citations", []))

        return AgentResult(
            agent_type=self.agent_type,
            agent_version=self.agent_version,
            success=True,
            recommendation=recommendation,
            summary=response.get("summary", ""),
            detailed_analysis=response.get("detailed_analysis", ""),
            confidence=confidence,
            confidence_level=confidence_level,
            reasoning_chain=reasoning_chain,
            citations=citations,
            regulatory_context=self._build_regulatory_context(citations),
            risk_score=response.get("risk_score"),
            risk_factors=response.get("risk_factors", []),
            mitigating_factors=response.get("mitigating_factors", []),
            red_flags=response.get("red_flags", []),
            next_steps=response.get("next_steps", []),
            sar_likelihood=response.get("sar_likelihood"),
            required_actions=self._build_required_actions(response),
        )

    def _build_regulatory_context(self, citations: List[Citation]) -> str:
        """Build regulatory context string from citations."""
        if not citations:
            return ""

        context_parts = []
        for c in citations:
            if c.excerpt:
                context_parts.append(f"{c.reference}: {c.excerpt}")
            else:
                context_parts.append(c.reference)

        return " | ".join(context_parts)

    def _build_required_actions(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build required actions from response."""
        actions = []

        # Convert next steps to actions
        for step in response.get("next_steps", []):
            actions.append(
                {
                    "action": step,
                    "priority": "high" if "immediate" in step.lower() else "medium",
                    "assignee": None,
                    "due_date": None,
                }
            )

        # Add SAR action if likelihood is high
        sar_likelihood = response.get("sar_likelihood", 0)
        if sar_likelihood and sar_likelihood >= 0.7:
            actions.append(
                {
                    "action": "Prepare SAR filing",
                    "priority": "high",
                    "assignee": None,
                    "due_date": None,
                }
            )

        return actions
