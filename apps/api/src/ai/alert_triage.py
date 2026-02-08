"""
AI Alert Triage Agent
Uses Claude to automatically analyze, prioritize, and recommend actions for alerts.

YUFEED INNOVATION: AI agent that understands both transaction patterns AND
regulatory requirements to provide compliance-aware triage.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from anthropic import Anthropic
from sqlalchemy.orm import Session

from src.models.transaction_models import Alert, Transaction, MonitoringRule
from src.models.models import LegalDocument

logger = logging.getLogger(__name__)


class AlertTriageAgent:
    """
    AI agent for intelligent alert triage and analysis.

    Capabilities:
    1. Analyze alert context and evidence
    2. Assess true positive likelihood
    3. Recommend priority level
    4. Suggest investigation steps
    5. Link to relevant regulations
    6. Draft initial case summary
    """

    def __init__(self, db: Session):
        self.db = db
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set - AI triage disabled")
            self.client = None
        else:
            self.client = Anthropic(api_key=api_key)

    def triage_alert(self, alert_id: int) -> Dict[str, Any]:
        """
        Perform AI-powered triage on an alert.

        Returns:
        {
            "recommendation": "escalate|investigate|false_positive|monitor",
            "confidence": 0.85,
            "priority": 1-5,
            "reasoning": "...",
            "investigation_steps": [...],
            "regulatory_context": "...",
            "estimated_sar_likelihood": 0.3
        }
        """
        if not self.client:
            logger.warning("AI triage unavailable - ANTHROPIC_API_KEY not set")
            return self._fallback_triage()

        # Get alert with related data
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        # Get transaction if available
        transaction = None
        if alert.transaction_id:
            transaction = (
                self.db.query(Transaction).filter(Transaction.id == alert.transaction_id).first()
            )

        # Get rule
        rule = None
        if alert.rule_id:
            rule = (
                self.db.query(MonitoringRule)
                .filter(MonitoringRule.rule_id == alert.rule_id)
                .first()
            )

        # Get regulatory documents
        regulations = []
        if alert.related_regulations:
            regulations = (
                self.db.query(LegalDocument)
                .filter(LegalDocument.id.in_(alert.related_regulations))
                .all()
            )

        # Build context for Claude
        context = self._build_alert_context(alert, transaction, rule, regulations)

        # Get AI analysis
        analysis = self._analyze_with_claude(context)

        # Update alert with AI insights
        if analysis:
            self._apply_triage_results(alert, analysis)

        return analysis

    def batch_triage_pending_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Triage multiple pending alerts in batch.

        Prioritizes:
        1. Critical severity alerts first
        2. High-value transactions
        3. Sanctions-related alerts
        """
        if not self.client:
            logger.warning("AI batch triage unavailable")
            return []

        # Get pending alerts ordered by priority
        pending_alerts = (
            self.db.query(Alert)
            .filter(Alert.status == "pending")
            .order_by(Alert.severity.desc(), Alert.priority.asc(), Alert.created_at.desc())
            .limit(limit)
            .all()
        )

        results = []
        for alert in pending_alerts:
            try:
                analysis = self.triage_alert(alert.id)
                results.append({"alert_id": alert.alert_id, "analysis": analysis})
                logger.info(f"Triaged alert {alert.alert_id}: {analysis.get('recommendation')}")
            except Exception as e:
                logger.error(f"Error triaging alert {alert.id}: {e}")

        return results

    def _build_alert_context(
        self,
        alert: Alert,
        transaction: Optional[Transaction],
        rule: Optional[MonitoringRule],
        regulations: List[LegalDocument],
    ) -> str:
        """
        Build comprehensive context for Claude analysis.
        """
        context = f"""# Alert Triage Request

## Alert Information
- Alert ID: {alert.alert_id}
- Type: {alert.alert_type}
- Severity: {alert.severity}
- Status: {alert.status}
- Created: {alert.created_at}
- Description: {alert.description}

## Evidence
{self._format_evidence(alert.evidence)}

## Risk Score
{alert.risk_score if alert.risk_score else 'Not calculated'}

"""

        # Add transaction details
        if transaction:
            context += f"""## Transaction Details
- Transaction ID: {transaction.transaction_id}
- User ID: {transaction.user_id}
- Amount: {transaction.amount} {transaction.currency}
- Type: {transaction.transaction_type}
- Country: {transaction.country_code}
- IP Address: {transaction.ip_address}
- Timestamp: {transaction.timestamp}
- Risk Level: {transaction.risk_level}
- Status: {transaction.status}

"""

        # Add rule information
        if rule:
            context += f"""## Triggered Rule
- Rule: {rule.name}
- Category: {rule.category}
- Description: {rule.description}
- Regulatory Requirement: {rule.regulatory_requirement}

"""

        # Add regulatory context
        if regulations:
            context += "## Applicable Regulations\n"
            for reg in regulations:
                context += f"""
### {reg.celex}
- Title: {reg.title}
- Type: {reg.document_type}
- Summary: {reg.summary if hasattr(reg, 'summary') else 'N/A'}

"""

        # Add existing regulatory context
        if alert.regulation_context:
            context += f"""## System-Generated Regulatory Context
{alert.regulation_context}

"""

        return context

    def _analyze_with_claude(self, context: str) -> Dict[str, Any]:
        """
        Send context to Claude for analysis.
        """
        try:
            prompt = f"""{context}

# Your Task

You are an expert AML/CFT compliance analyst with deep knowledge of EU regulations. Analyze this alert and provide a comprehensive triage assessment.

Provide your analysis in the following JSON format:

{{
    "recommendation": "escalate|investigate|false_positive|monitor",
    "confidence": 0.0-1.0,
    "priority": 1-5,
    "reasoning": "Brief explanation of your assessment",
    "true_positive_likelihood": 0.0-1.0,
    "investigation_steps": [
        "Step 1: ...",
        "Step 2: ...",
        "Step 3: ..."
    ],
    "regulatory_concerns": "Key regulatory issues identified",
    "sar_likelihood": 0.0-1.0,
    "recommended_actions": [
        "Action 1",
        "Action 2"
    ],
    "red_flags": [
        "Any suspicious patterns or red flags identified"
    ],
    "mitigating_factors": [
        "Any factors that reduce suspicion"
    ]
}}

Consider:
1. Transaction patterns and behavioral indicators
2. Regulatory requirements and obligations
3. Risk level and potential impact
4. Evidence quality and completeness
5. Similar historical cases (if mentioned)
6. False positive indicators

Be thorough but concise. Focus on actionable insights."""

            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract JSON from response
            import json

            response_text = response.content[0].text

            # Try to extract JSON (Claude might wrap it in markdown)
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            analysis = json.loads(response_text)

            logger.info(
                f"Claude analysis: {analysis.get('recommendation')} (confidence: {analysis.get('confidence')})"
            )

            return analysis

        except Exception as e:
            logger.error(f"Error calling Claude API: {e}")
            return self._fallback_triage()

    def _apply_triage_results(self, alert: Alert, analysis: Dict[str, Any]):
        """
        Apply AI triage results to the alert.
        """
        # Update priority if AI suggests different
        ai_priority = analysis.get("priority")
        if ai_priority and ai_priority != alert.priority:
            alert.priority = ai_priority

        # Add AI analysis to resolution notes
        triage_summary = f"""
=== AI TRIAGE ANALYSIS ===
Recommendation: {analysis.get('recommendation')}
Confidence: {analysis.get('confidence', 0):.0%}
True Positive Likelihood: {analysis.get('true_positive_likelihood', 0):.0%}
SAR Likelihood: {analysis.get('sar_likelihood', 0):.0%}

Reasoning: {analysis.get('reasoning')}

Regulatory Concerns: {analysis.get('regulatory_concerns')}

Red Flags:
{self._format_list(analysis.get('red_flags', []))}

Recommended Actions:
{self._format_list(analysis.get('recommended_actions', []))}

Investigation Steps:
{self._format_list(analysis.get('investigation_steps', []))}
"""

        if alert.resolution_notes:
            alert.resolution_notes += "\n\n" + triage_summary
        else:
            alert.resolution_notes = triage_summary

        # Auto-escalate if AI recommends and confidence is high
        if analysis.get("recommendation") == "escalate" and analysis.get("confidence", 0) > 0.8:
            alert.status = "escalated"
            logger.info(f"Auto-escalated alert {alert.alert_id} based on AI recommendation")

        # Auto-mark as false positive if confidence is very high
        elif (
            analysis.get("recommendation") == "false_positive"
            and analysis.get("confidence", 0) > 0.9
        ):
            alert.status = "false_positive"
            alert.resolution_status = "false_positive"
            alert.resolved_by = "AI_AGENT"
            alert.resolution_notes += (
                "\n\n[AUTO-RESOLVED] High-confidence false positive identified by AI"
            )
            logger.info(f"Auto-resolved alert {alert.alert_id} as false positive")

        self.db.commit()

    def _format_evidence(self, evidence: Optional[Dict]) -> str:
        """Format evidence dictionary for display."""
        if not evidence:
            return "No evidence available"

        formatted = []
        for key, value in evidence.items():
            formatted.append(f"- {key}: {value}")

        return "\n".join(formatted)

    def _format_list(self, items: List[str]) -> str:
        """Format list items."""
        if not items:
            return "None"

        return "\n".join(f"- {item}" for item in items)

    def _fallback_triage(self) -> Dict[str, Any]:
        """
        Fallback triage when AI is unavailable.

        Uses simple heuristics.
        """
        return {
            "recommendation": "investigate",
            "confidence": 0.5,
            "priority": 3,
            "reasoning": "AI triage unavailable - manual review required",
            "true_positive_likelihood": 0.5,
            "investigation_steps": [
                "Review transaction details",
                "Check user history",
                "Verify regulatory requirements",
                "Consult with senior analyst",
            ],
            "regulatory_concerns": "Unknown - AI analysis unavailable",
            "sar_likelihood": 0.0,
            "recommended_actions": ["Manual review required"],
            "red_flags": [],
            "mitigating_factors": [],
        }

    def generate_investigation_report(self, alert_id: int) -> str:
        """
        Generate a detailed investigation report for an alert.

        This can be used to start a case or for documentation.
        """
        if not self.client:
            return "AI report generation unavailable - ANTHROPIC_API_KEY not set"

        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        # Get related data
        transaction = None
        if alert.transaction_id:
            transaction = (
                self.db.query(Transaction).filter(Transaction.id == alert.transaction_id).first()
            )

        context = self._build_alert_context(
            alert,
            transaction,
            (
                self.db.query(MonitoringRule)
                .filter(MonitoringRule.rule_id == alert.rule_id)
                .first()
                if alert.rule_id
                else None
            ),
            (
                self.db.query(LegalDocument)
                .filter(LegalDocument.id.in_(alert.related_regulations))
                .all()
                if alert.related_regulations
                else []
            ),
        )

        prompt = f"""{context}

# Generate Investigation Report

Create a comprehensive investigation report for this alert suitable for compliance documentation.

Include:
1. Executive Summary
2. Alert Details
3. Transaction Analysis
4. Regulatory Implications
5. Risk Assessment
6. Recommended Actions
7. Next Steps

Format as professional compliance documentation."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}],
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"Error generating investigation report: {e}")
            return f"Error generating report: {str(e)}"
