"""
Regulatory Context Enrichment Service
Uses Claude to generate detailed regulatory explanations for alerts and transactions.

YUFEED INNOVATION: Automatically links transaction patterns to specific regulatory
requirements and generates human-readable compliance explanations.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from anthropic import Anthropic
from sqlalchemy.orm import Session

from src.models.transaction_models import Alert, Transaction, MonitoringRule
from src.models.models import LegalDocument
from src.ai.usage_instrumentation import UsageLogContext, log_anthropic_response_usage
from src.ai.prompts.guardrails import FACTUAL_NARRATIVE_RULES

logger = logging.getLogger(__name__)
REGULATORY_CONTEXT_PROMPT_VERSION = "2026-02-25.1"
SAR_NARRATIVE_PROMPT_VERSION = "2026-02-25.1"


class RegulatoryEnrichmentService:
    """
    AI service for enriching alerts with regulatory context.

    Automatically generates:
    1. Plain-language regulatory explanations
    2. Compliance officer guidance
    3. Links to specific regulation articles
    4. SAR preparation assistance
    """

    def __init__(self, db: Session):
        self.db = db
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set - regulatory enrichment disabled")
            self.client = None
        else:
            self.client = Anthropic(api_key=api_key)

    def enrich_alert_with_regulations(self, alert_id: int) -> str:
        """
        Generate detailed regulatory context for an alert.

        Returns a comprehensive explanation of why this alert matters
        from a regulatory compliance perspective.
        """
        if not self.client:
            return self._fallback_regulatory_context()

        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        # Get related documents
        regulations = []
        if alert.related_regulations:
            regulations = (
                self.db.query(LegalDocument)
                .filter(LegalDocument.id.in_(alert.related_regulations))
                .all()
            )

        # Get transaction
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

        # Generate context
        context = self._generate_regulatory_context(alert, transaction, rule, regulations)

        # Save to alert
        alert.regulation_context = context
        self.db.commit()

        return context

    def _generate_regulatory_context(
        self,
        alert: Alert,
        transaction: Optional[Transaction],
        rule: Optional[MonitoringRule],
        regulations: List[LegalDocument],
    ) -> str:
        """
        Use Claude to generate regulatory context.
        """
        prompt = f"""# Regulatory Context Generation

## Alert Information
- Type: {alert.alert_type}
- Severity: {alert.severity}
- Description: {alert.description}

"""

        if transaction:
            prompt += f"""## Transaction Details
- Amount: {transaction.amount} {transaction.currency}
- Type: {transaction.transaction_type}
- Country: {transaction.country_code}
- Risk Level: {transaction.risk_level}

"""

        if rule:
            prompt += f"""## Triggered Rule
- Rule: {rule.name}
- Category: {rule.category}
- Regulatory Requirement: {rule.regulatory_requirement}
- Regulation Article: {rule.regulation_article}

"""

        if regulations:
            prompt += "## Applicable EU Regulations\n"
            for reg in regulations:
                prompt += f"""
### {reg.celex} - {reg.title}
- Document Type: {reg.document_type}
- Publication Date: {reg.publication_date}
"""
                if hasattr(reg, "summary") and reg.summary:
                    prompt += f"- Summary: {reg.summary}\n"

        prompt += f"""

# Your Task

You are an EU compliance expert. Generate a clear, concise regulatory context explanation for this alert.

Your explanation should:
1. Explain WHY this transaction triggered the alert from a regulatory perspective
2. Reference specific EU regulations and articles
3. Explain the compliance obligations
4. Note any potential violations or concerns
5. Provide guidance for compliance officers

Write in professional but accessible language. Focus on actionable compliance insights.
{FACTUAL_NARRATIVE_RULES}
If a specific article, obligation, or fact is missing from the provided data, say so explicitly.

Keep it concise (2-3 paragraphs maximum).
"""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
            )
            log_anthropic_response_usage(
                response,
                context=UsageLogContext(
                    tenant_id=getattr(alert, "tenant_id", None),
                    user_id=getattr(alert, "user_id", None),
                    operation="regulatory_enrichment_context",
                    request_metadata={
                        "feature": "regulatory_enrichment",
                        "prompt_version": REGULATORY_CONTEXT_PROMPT_VERSION,
                        "alert_id": alert.id,
                        "prompt_chars": len(prompt),
                        "max_tokens": 1000,
                    },
                ),
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"Error generating regulatory context: {e}")
            return self._fallback_regulatory_context()

    def generate_sar_draft(self, alert_id: int, include_narrative: bool = True) -> Dict[str, Any]:
        """
        Generate a draft Suspicious Activity Report (SAR) for an alert.

        Returns structured SAR data that can be used to file with authorities.
        """
        if not self.client:
            raise ValueError("SAR generation requires ANTHROPIC_API_KEY")

        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        # Get transaction
        transaction = None
        if alert.transaction_id:
            transaction = (
                self.db.query(Transaction).filter(Transaction.id == alert.transaction_id).first()
            )

        # Build context
        context = self._build_sar_context(alert, transaction)

        # Generate SAR narrative
        narrative = ""
        if include_narrative:
            narrative = self._generate_sar_narrative(context, alert=alert)

        # Build SAR structure
        sar_draft = {
            "filing_institution": "Your Institution Name",  # TODO: Get from config
            "filing_date": alert.created_at.isoformat(),
            "alert_id": alert.alert_id,
            "subject": {
                "type": "individual",  # or "entity"
                "user_id": alert.user_id,
                "identification": "MASKED",  # Mask for draft
            },
            "suspicious_activity": {
                "type": alert.alert_type,
                "date": (
                    transaction.timestamp.isoformat()
                    if transaction
                    else alert.created_at.isoformat()
                ),
                "amount": float(transaction.amount) if transaction else None,
                "currency": transaction.currency if transaction else None,
                "description": alert.description,
            },
            "narrative": narrative,
            "related_regulations": alert.related_regulations or [],
            "supporting_documentation": {
                "evidence": alert.evidence,
                "risk_score": float(alert.risk_score) if alert.risk_score else None,
            },
            "filing_reason": self._determine_filing_reason(alert, transaction),
        }

        return sar_draft

    def _build_sar_context(self, alert: Alert, transaction: Optional[Transaction]) -> str:
        """Build context for SAR generation."""
        context = f"""# SAR Context

## Alert Information
- Alert ID: {alert.alert_id}
- Type: {alert.alert_type}
- Severity: {alert.severity}
- Created: {alert.created_at}
- Description: {alert.description}

## Evidence
{self._format_evidence(alert.evidence)}

"""

        if transaction:
            context += f"""## Transaction Details
- Transaction ID: {transaction.transaction_id}
- User ID: {transaction.user_id}
- Amount: {transaction.amount} {transaction.currency}
- Type: {transaction.transaction_type}
- Country: {transaction.country_code}
- Timestamp: {transaction.timestamp}
- Risk Level: {transaction.risk_level}

"""

        if alert.regulation_context:
            context += f"""## Regulatory Context
{alert.regulation_context}

"""

        return context

    def _generate_sar_narrative(self, context: str, alert: Optional[Alert] = None) -> str:
        """
        Generate SAR narrative using Claude.
        """
        prompt = f"""{context}

# Generate SAR Narrative

You are a compliance officer preparing a Suspicious Activity Report (SAR) for regulatory authorities.

Write a clear, factual narrative describing:
1. The suspicious activity observed
2. Why it is considered suspicious
3. Regulatory concerns
4. Supporting evidence

Use professional, objective language suitable for regulatory filing.
Be specific about amounts, dates, and patterns.
Do not speculate - stick to observable facts.
{FACTUAL_NARRATIVE_RULES}
If key details are unavailable, identify the information gap rather than inventing specifics.

Format: 3-5 concise paragraphs.
"""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
            )
            log_anthropic_response_usage(
                response,
                context=UsageLogContext(
                    tenant_id=getattr(alert, "tenant_id", None) if alert else None,
                    user_id=getattr(alert, "user_id", None) if alert else None,
                    operation="sar_narrative_generation",
                    request_metadata={
                        "feature": "sar_narrative",
                        "prompt_version": SAR_NARRATIVE_PROMPT_VERSION,
                        "alert_id": getattr(alert, "id", None) if alert else None,
                        "prompt_chars": len(prompt),
                        "max_tokens": 1500,
                    },
                ),
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"Error generating SAR narrative: {e}")
            return "Error generating SAR narrative. Manual preparation required."

    def auto_link_regulations(self, alert_id: int, search_threshold: float = 0.7) -> List[int]:
        """
        Automatically find and link relevant regulations to an alert.

        Uses semantic search to find applicable legal documents.
        Returns list of LegalDocument IDs.
        """
        if not self.client:
            logger.warning("Auto-linking regulations unavailable")
            return []

        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        # Build search query from alert
        search_query = f"{alert.alert_type} {alert.description}"

        # TODO: Implement semantic search against legal documents
        # For now, use simple keyword matching

        # Get potentially relevant documents
        keywords = self._extract_keywords(alert)

        relevant_docs = []
        for keyword in keywords:
            docs = (
                self.db.query(LegalDocument)
                .filter(LegalDocument.title.ilike(f"%{keyword}%"))
                .limit(5)
                .all()
            )
            relevant_docs.extend(docs)

        # Deduplicate
        unique_doc_ids = list(set(doc.id for doc in relevant_docs))

        # Update alert
        if unique_doc_ids:
            alert.related_regulations = unique_doc_ids
            self.db.commit()
            logger.info(f"Auto-linked {len(unique_doc_ids)} regulations to alert {alert.alert_id}")

        return unique_doc_ids

    def _extract_keywords(self, alert: Alert) -> List[str]:
        """Extract regulatory keywords from alert."""
        keywords = []

        # Map alert types to regulatory keywords
        keyword_map = {
            "sanctions": ["sanctions", "embargo", "restrictive measures"],
            "velocity": ["money laundering", "AML", "suspicious"],
            "amount_threshold": ["customer due diligence", "CDD", "EDD"],
            "structuring": ["structuring", "smurfing", "layering"],
            "high_risk_geography": ["high risk", "third countries"],
            "wire_transfer": ["transfer of funds", "payment services"],
        }

        if alert.alert_type in keyword_map:
            keywords.extend(keyword_map[alert.alert_type])

        return keywords

    def _determine_filing_reason(self, alert: Alert, transaction: Optional[Transaction]) -> str:
        """Determine why SAR should be filed."""
        reasons = []

        if alert.severity == "critical":
            reasons.append("Critical severity alert")

        if transaction:
            if transaction.risk_level in ["high", "critical"]:
                reasons.append(f"{transaction.risk_level.capitalize()} risk transaction")

            if transaction.country_code in ["KP", "IR", "SY"]:
                reasons.append("Sanctioned jurisdiction involvement")

        if alert.alert_type == "structuring":
            reasons.append("Potential structuring activity")

        if not reasons:
            reasons.append("Suspicious activity pattern detected")

        return "; ".join(reasons)

    def _format_evidence(self, evidence: Optional[Dict]) -> str:
        """Format evidence for display."""
        if not evidence:
            return "No evidence available"

        formatted = []
        for key, value in evidence.items():
            formatted.append(f"- {key}: {value}")

        return "\n".join(formatted)

    def _fallback_regulatory_context(self) -> str:
        """Fallback regulatory context when AI unavailable."""
        return """
This alert was triggered based on compliance monitoring rules designed to detect
potentially suspicious activities and ensure regulatory compliance.

Manual review required to determine specific regulatory implications.
Please consult relevant EU Anti-Money Laundering Directives and institution policies.
"""

    def batch_enrich_alerts(self, alert_ids: List[int]) -> Dict[int, str]:
        """
        Enrich multiple alerts with regulatory context in batch.
        """
        results = {}

        for alert_id in alert_ids:
            try:
                context = self.enrich_alert_with_regulations(alert_id)
                results[alert_id] = context
                logger.info(f"Enriched alert {alert_id} with regulatory context")
            except Exception as e:
                logger.error(f"Error enriching alert {alert_id}: {e}")
                results[alert_id] = f"Error: {str(e)}"

        return results
