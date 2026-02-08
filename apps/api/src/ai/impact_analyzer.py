"""
AI-powered impact analysis for regulatory documents.
Uses Claude to assess how regulations affect bank operations.
"""

import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import anthropic

from src.models.impact_assessment import ImpactLevel, BusinessArea, ActionStatus

logger = logging.getLogger(__name__)


class ImpactAnalyzer:
    """
    Analyzes regulatory documents to determine operational impact.
    """

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            self.client = None
            logger.warning("ANTHROPIC_API_KEY not set - using fallback impact analysis")

    def analyze_impact(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive impact analysis on a legal document.

        Returns:
            Dictionary with:
            - overall_impact_level: ImpactLevel
            - executive_summary: str
            - affected_areas: List[BusinessArea]
            - key_changes: List[str]
            - action_items: List[Dict]
            - gaps: List[Dict]
            - resource_estimates: Dict
        """
        if not self.client:
            return self._fallback_analysis(document)

        try:
            # Build analysis prompt
            prompt = self._build_impact_prompt(document)

            # Call Claude for analysis
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse response
            response_text = message.content[0].text
            analysis = self._parse_impact_response(response_text)

            logger.info(f"Impact analysis completed for {document.get('celex')}")
            return analysis

        except Exception as e:
            logger.error(f"Error in AI impact analysis: {e}")
            return self._fallback_analysis(document)

    def _build_impact_prompt(self, document: Dict[str, Any]) -> str:
        """Build prompt for impact analysis."""
        celex = document.get("celex", "Unknown")
        title = document.get("title", "Unknown")
        doc_type = document.get("type", "Unknown")
        compliance_domain = document.get("compliance_domain", "Unknown")
        pub_date = document.get("publication_date", "Unknown")
        deadline = document.get("implementation_deadline")

        prompt = f"""You are an expert AML/CFT compliance analyst for a European bank. Analyze this EU regulation for operational impact.

**Document Details:**
- CELEX: {celex}
- Title: {title}
- Type: {doc_type}
- Compliance Domain: {compliance_domain}
- Publication Date: {pub_date}
"""

        if deadline:
            prompt += f"- Implementation Deadline: {deadline}\n"

        if document.get("ai_summary"):
            prompt += f"\n**Summary:** {document['ai_summary']}\n"

        prompt += """
**Your Task:**
Analyze how this regulation impacts a typical European bank's AML/CFT operations. Provide a structured assessment.

**Response Format (JSON):**
```json
{
  "overall_impact_level": "critical|high|medium|low|minimal",
  "executive_summary": "2-3 sentence summary for C-suite executives",
  "affected_areas": ["onboarding", "transaction_monitoring", "screening", ...],
  "key_changes": [
    "Specific change 1",
    "Specific change 2"
  ],
  "action_items": [
    {
      "title": "Action title",
      "description": "What needs to be done",
      "business_area": "onboarding|transaction_monitoring|...",
      "priority": 1-5,
      "estimated_hours": 40,
      "complexity": "simple|moderate|complex"
    }
  ],
  "gaps": [
    {
      "category": "policy|process|technology|training",
      "current_state": "What we likely have now",
      "required_state": "What regulation requires",
      "gap_description": "The delta",
      "severity": "critical|high|medium|low|minimal",
      "business_area": "...",
      "remediation_approach": "How to close the gap",
      "estimated_cost": 50000,
      "estimated_timeline_days": 90
    }
  ],
  "resource_estimates": {
    "total_hours": 200,
    "total_cost_eur": 100000,
    "requires_system_changes": true,
    "requires_process_changes": true,
    "requires_policy_updates": true
  }
}
```

**Business Areas:**
- onboarding: Customer onboarding / KYC
- transaction_monitoring: Transaction monitoring systems
- screening: Sanctions / PEP screening
- reporting: Regulatory reporting (SAR, CTR, etc.)
- due_diligence: CDD / EDD processes
- record_keeping: Data retention requirements
- training: Staff training requirements
- governance: Policies / procedures / oversight
- technology: IT systems / infrastructure
- third_party: Vendor / third-party management
- risk_assessment: Risk rating / assessment
- compliance_function: Compliance team operations

**Guidelines:**
- Be specific and actionable
- Focus on practical implementation steps
- Estimate realistic effort (hours) and costs
- Identify dependencies between actions
- Consider phased implementation if deadline allows
- Think about what a bank likely has vs. what's needed

Provide only the JSON response, no additional text.
"""

        return prompt

    def _parse_impact_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Claude's JSON response."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")

            json_str = response_text[json_start:json_end]
            parsed = json.loads(json_str)

            # Validate and normalize
            return {
                "overall_impact_level": parsed.get("overall_impact_level", "medium"),
                "executive_summary": parsed.get("executive_summary", ""),
                "affected_areas": parsed.get("affected_areas", []),
                "key_changes": parsed.get("key_changes", []),
                "action_items": parsed.get("action_items", []),
                "gaps": parsed.get("gaps", []),
                "resource_estimates": parsed.get("resource_estimates", {}),
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response was: {response_text[:500]}")
            return self._fallback_analysis_structure()

    def _fallback_analysis(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback analysis when AI is unavailable."""
        logger.info("Using fallback impact analysis (no AI)")

        # Basic heuristic-based analysis
        domain = document.get("compliance_domain", "other")
        risk_level = document.get("risk_level", "medium")

        # Map risk to impact
        impact_map = {"high": "high", "medium": "medium", "low": "low"}
        impact_level = impact_map.get(risk_level, "medium")

        # Domain-based affected areas
        area_map = {
            "aml": ["transaction_monitoring", "screening", "reporting", "due_diligence"],
            "kyc": ["onboarding", "due_diligence", "risk_assessment"],
            "sanctions": ["screening", "transaction_monitoring"],
            "cdd": ["due_diligence", "onboarding", "record_keeping"],
            "payments": ["transaction_monitoring", "reporting"],
            "crypto": ["onboarding", "transaction_monitoring", "risk_assessment"],
        }
        affected_areas = area_map.get(domain, ["compliance_function"])

        return {
            "overall_impact_level": impact_level,
            "executive_summary": f"This {domain.upper()} regulation requires review and potential updates to compliance procedures.",
            "affected_areas": affected_areas,
            "key_changes": [
                "Regulatory requirements updated",
                "Compliance procedures may need revision",
            ],
            "action_items": [
                {
                    "title": "Review regulation requirements",
                    "description": "Detailed review of new obligations",
                    "business_area": affected_areas[0] if affected_areas else "compliance_function",
                    "priority": 2,
                    "estimated_hours": 16,
                    "complexity": "moderate",
                }
            ],
            "gaps": [],
            "resource_estimates": {
                "total_hours": 40,
                "total_cost_eur": 20000,
                "requires_system_changes": False,
                "requires_process_changes": True,
                "requires_policy_updates": True,
            },
        }

    def _fallback_analysis_structure(self) -> Dict[str, Any]:
        """Return minimal valid analysis structure."""
        return {
            "overall_impact_level": "medium",
            "executive_summary": "Impact analysis pending - detailed review required.",
            "affected_areas": ["compliance_function"],
            "key_changes": [],
            "action_items": [],
            "gaps": [],
            "resource_estimates": {
                "total_hours": 0,
                "total_cost_eur": 0,
                "requires_system_changes": False,
                "requires_process_changes": False,
                "requires_policy_updates": False,
            },
        }
