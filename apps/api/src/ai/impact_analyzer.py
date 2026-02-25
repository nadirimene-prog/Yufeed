"""
AI-powered impact analysis for regulatory documents.
Uses Claude to assess how regulations affect bank operations.
"""

import logging
import os
import time
import random
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

    def _is_retryable_anthropic_error(self, exc: Exception) -> bool:
        status_code = getattr(exc, "status_code", None)
        if status_code in {429, 529}:
            return True
        response = getattr(exc, "response", None)
        response_status = getattr(response, "status_code", None)
        if response_status in {429, 529}:
            return True
        msg = str(exc).lower()
        return "overloaded_error" in msg or "rate_limit" in msg or "too many requests" in msg

    def _call_claude_with_retry(self, **kwargs):
        retries = max(0, int(os.getenv("ANTHROPIC_RETRIES", "2")))
        backoff = max(0.1, float(os.getenv("ANTHROPIC_BACKOFF_SECONDS", "1.0")))
        max_backoff = max(backoff, float(os.getenv("ANTHROPIC_MAX_BACKOFF_SECONDS", "8.0")))
        jitter = max(0.0, float(os.getenv("ANTHROPIC_JITTER_SECONDS", "0.25")))

        last_exc: Optional[Exception] = None
        for attempt in range(retries + 1):
            try:
                return self.client.messages.create(**kwargs)
            except Exception as exc:
                last_exc = exc
                if attempt >= retries or not self._is_retryable_anthropic_error(exc):
                    raise
                sleep_s = min(max_backoff, backoff * (2**attempt))
                if jitter:
                    sleep_s += random.uniform(0.0, jitter)
                logger.warning(
                    "Retryable Anthropic error in impact analysis (attempt %s/%s): %s. Retrying in %.2fs",
                    attempt + 1,
                    retries + 1,
                    exc,
                    sleep_s,
                )
                time.sleep(sleep_s)
        if last_exc:
            raise last_exc
        raise RuntimeError("Anthropic request failed")

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
            message = self._call_claude_with_retry(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse response
            response_text = message.content[0].text
            try:
                analysis = self._parse_impact_response_strict(response_text)
            except (json.JSONDecodeError, ValueError, TypeError) as parse_exc:
                logger.warning(
                    "Malformed JSON from impact analysis model, attempting repair: %s",
                    parse_exc,
                )
                repaired_text = self._repair_impact_json_response(response_text)
                analysis = self._parse_impact_response_strict(repaired_text)

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

    def _extract_json_payload_text(self, response_text: str) -> str:
        """Extract a JSON object from a response that may include markdown fences."""
        text = (response_text or "").strip()

        if "```json" in text:
            json_start = text.find("```json") + 7
            json_end = text.find("```", json_start)
            if json_end != -1:
                text = text[json_start:json_end].strip()
        elif "```" in text:
            fenced_start = text.find("```") + 3
            fenced_end = text.find("```", fenced_start)
            if fenced_end != -1:
                text = text[fenced_start:fenced_end].strip()

        obj_start = text.find("{")
        obj_end = text.rfind("}") + 1
        if obj_start == -1 or obj_end <= obj_start:
            raise ValueError("No JSON found in response")
        return text[obj_start:obj_end]

    def _normalize_impact_response(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "overall_impact_level": parsed.get("overall_impact_level", "medium"),
            "executive_summary": parsed.get("executive_summary", ""),
            "affected_areas": parsed.get("affected_areas", []),
            "key_changes": parsed.get("key_changes", []),
            "action_items": parsed.get("action_items", []),
            "gaps": parsed.get("gaps", []),
            "resource_estimates": parsed.get("resource_estimates", {}),
        }

    def _validate_impact_response_schema(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize impact schema (keys, top-level types, key ranges)."""
        if not isinstance(analysis, dict):
            raise TypeError("Impact analysis response must be a JSON object")

        required_keys = {
            "overall_impact_level",
            "executive_summary",
            "affected_areas",
            "key_changes",
            "action_items",
            "gaps",
            "resource_estimates",
        }
        missing = sorted(required_keys - set(analysis.keys()))
        if missing:
            raise ValueError(f"Missing required impact keys: {', '.join(missing)}")

        allowed_levels = {"critical", "high", "medium", "low", "minimal"}
        impact_level = analysis["overall_impact_level"]
        if not isinstance(impact_level, str) or impact_level not in allowed_levels:
            raise ValueError("overall_impact_level must be one of critical/high/medium/low/minimal")

        summary = analysis["executive_summary"]
        if not isinstance(summary, str):
            raise TypeError("executive_summary must be a string")

        def _string_list(key: str) -> List[str]:
            value = analysis[key]
            if not isinstance(value, list):
                raise TypeError(f"{key} must be a list")
            normalized: List[str] = []
            for item in value:
                if not isinstance(item, str):
                    raise TypeError(f"{key} items must be strings")
                normalized.append(item)
            return normalized

        affected_areas = _string_list("affected_areas")
        key_changes = _string_list("key_changes")

        action_items = analysis["action_items"]
        if not isinstance(action_items, list):
            raise TypeError("action_items must be a list")
        for idx, item in enumerate(action_items):
            if not isinstance(item, dict):
                raise TypeError(f"action_items[{idx}] must be an object")
            if "priority" in item:
                priority = item["priority"]
                if not isinstance(priority, (int, float)) or int(priority) != priority:
                    raise TypeError(f"action_items[{idx}].priority must be an integer")
                if not 1 <= int(priority) <= 5:
                    raise ValueError(f"action_items[{idx}].priority must be between 1 and 5")
            if "estimated_hours" in item:
                est_hours = item["estimated_hours"]
                if not isinstance(est_hours, (int, float)):
                    raise TypeError(f"action_items[{idx}].estimated_hours must be numeric")
                if est_hours < 0:
                    raise ValueError(f"action_items[{idx}].estimated_hours must be >= 0")

        gaps = analysis["gaps"]
        if not isinstance(gaps, list):
            raise TypeError("gaps must be a list")
        allowed_gap_severity = allowed_levels
        for idx, gap in enumerate(gaps):
            if not isinstance(gap, dict):
                raise TypeError(f"gaps[{idx}] must be an object")
            if "severity" in gap and gap["severity"] not in allowed_gap_severity:
                raise ValueError(f"gaps[{idx}].severity is invalid")
            for numeric_key in ("estimated_cost", "estimated_timeline_days"):
                if numeric_key in gap:
                    numeric_value = gap[numeric_key]
                    if not isinstance(numeric_value, (int, float)):
                        raise TypeError(f"gaps[{idx}].{numeric_key} must be numeric")
                    if numeric_value < 0:
                        raise ValueError(f"gaps[{idx}].{numeric_key} must be >= 0")

        resource_estimates = analysis["resource_estimates"]
        if not isinstance(resource_estimates, dict):
            raise TypeError("resource_estimates must be an object")
        for numeric_key in ("total_hours", "total_cost_eur"):
            if numeric_key in resource_estimates:
                numeric_value = resource_estimates[numeric_key]
                if not isinstance(numeric_value, (int, float)):
                    raise TypeError(f"resource_estimates.{numeric_key} must be numeric")
                if numeric_value < 0:
                    raise ValueError(f"resource_estimates.{numeric_key} must be >= 0")
        for bool_key in (
            "requires_system_changes",
            "requires_process_changes",
            "requires_policy_updates",
        ):
            if bool_key in resource_estimates and not isinstance(
                resource_estimates[bool_key], bool
            ):
                raise TypeError(f"resource_estimates.{bool_key} must be boolean")

        normalized = dict(analysis)
        normalized["overall_impact_level"] = impact_level
        normalized["executive_summary"] = summary
        normalized["affected_areas"] = affected_areas
        normalized["key_changes"] = key_changes
        return normalized

    def _parse_impact_response_strict(self, response_text: str) -> Dict[str, Any]:
        """Parse and normalize Claude JSON response, raising on malformed output."""
        json_str = self._extract_json_payload_text(response_text)
        parsed = json.loads(json_str)
        if not isinstance(parsed, dict):
            raise TypeError("Impact analysis response must be a JSON object")
        normalized = self._normalize_impact_response(parsed)
        return self._validate_impact_response_schema(normalized)

    def _repair_impact_json_response(self, malformed_response: str) -> str:
        """Ask Claude to repair malformed JSON without adding commentary."""
        repair_prompt = f"""The following assistant output is intended to be JSON but is malformed.

Return only valid JSON. Do not add markdown code fences. Do not add commentary.
Preserve the original meaning and keys as much as possible.

Malformed output:
{malformed_response}
"""
        repair = self._call_claude_with_retry(
            model="claude-sonnet-4-20250514",
            max_tokens=4500,
            temperature=0,
            messages=[{"role": "user", "content": repair_prompt}],
        )
        return repair.content[0].text

    def _parse_impact_response(self, response_text: str) -> Dict[str, Any]:
        """Backward-compatible parser that falls back to a minimal structure."""
        try:
            return self._parse_impact_response_strict(response_text)
        except (json.JSONDecodeError, ValueError, TypeError) as e:
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
