"""
Prompt Templates - Centralized prompt management for AI agents.

This module provides:
- Reusable prompt templates
- EU regulatory context snippets
- Investigation framework templates
- SAR generation templates
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from string import Template


@dataclass
class PromptTemplate:
    """A reusable prompt template with variable substitution."""

    name: str
    template: str
    description: str = ""
    variables: List[str] = field(default_factory=list)
    category: str = "general"

    def render(self, **kwargs) -> str:
        """Render the template with provided variables."""
        try:
            return Template(self.template).safe_substitute(**kwargs)
        except Exception as e:
            return self.template


class PromptLibrary:
    """Central library of prompt templates."""

    _templates: Dict[str, PromptTemplate] = {}

    @classmethod
    def register(cls, template: PromptTemplate) -> None:
        """Register a template."""
        cls._templates[template.name] = template

    @classmethod
    def get(cls, name: str) -> Optional[PromptTemplate]:
        """Get a template by name."""
        return cls._templates.get(name)

    @classmethod
    def render(cls, name: str, **kwargs) -> str:
        """Render a template by name."""
        template = cls.get(name)
        if template:
            return template.render(**kwargs)
        return ""


# =============================================================================
# EU REGULATORY CONTEXT
# =============================================================================

EU_REGULATORY_CONTEXT = """
## EU AML/CFT Regulatory Framework

### Primary Legislation

**AMLD 5 (Directive (EU) 2018/843)**
- Enhanced CDD for high-risk third countries
- Beneficial ownership registers
- Virtual currency providers regulation
- Centralized bank account registries

**AMLD 6 (Directive (EU) 2018/1673)**
- Expanded predicate offences list
- Criminal liability for legal persons
- Minimum sanctions harmonization
- Enhanced cooperation mechanisms

**Regulation (EU) 2015/847 - Transfer of Funds**
- Payer/payee information requirements
- Crypto-asset service provider obligations
- Travel rule implementation

### Key Thresholds (EU)

- **€10,000**: Cash transaction reporting threshold
- **€15,000**: CDD threshold for occasional transactions
- **€1,000**: Simplified CDD threshold

### High-Risk Indicators (per EBA Guidelines)

1. Customer risk factors
2. Product/service risk factors
3. Geographic risk factors
4. Delivery channel risk factors

### Reporting Obligations

- **STR/SAR**: To national FIU within prescribed timeframe
- **CTR**: Cash transactions above threshold
- **Sanctions hits**: Immediate reporting
"""

COMPLIANCE_CONTEXT = """
## Compliance Officer Role

As an AI AML Officer assistant, your role is to:

1. **Support Decision Making**
   - Provide analysis and recommendations
   - Never make final compliance decisions
   - Always flag uncertainty

2. **Maintain Audit Trail**
   - Document reasoning for all conclusions
   - Cite regulatory sources
   - Enable traceability

3. **Prioritize Accuracy**
   - Acknowledge limitations
   - Prefer false positives over false negatives
   - Flag edge cases for human review

4. **Ensure Regulatory Compliance**
   - Reference specific articles/provisions
   - Consider jurisdictional requirements
   - Account for regulatory updates
"""

# =============================================================================
# INVESTIGATION TEMPLATES
# =============================================================================

INVESTIGATION_TEMPLATES = {
    "alert_analysis": PromptTemplate(
        name="alert_analysis",
        category="investigation",
        description="Template for initial alert analysis",
        template="""
Analyze this alert and provide your assessment:

## Alert Information
$alert_data

## Context
$context

## Required Analysis

1. What triggered this alert?
2. What is the risk level?
3. What additional information is needed?
4. What is your preliminary recommendation?

Provide your analysis in structured JSON format.
""",
        variables=["alert_data", "context"],
    ),
    "transaction_pattern": PromptTemplate(
        name="transaction_pattern",
        category="investigation",
        description="Template for transaction pattern analysis",
        template="""
Analyze these transactions for suspicious patterns:

## Transactions
$transactions

## Analysis Framework

Check for these patterns:
1. **Structuring**: Amounts just below €10,000
2. **Layering**: Complex transaction chains
3. **Smurfing**: Multiple small transactions
4. **Round-tripping**: Circular fund flows
5. **Velocity anomalies**: Unusual frequency

## Output

Provide pattern analysis with:
- Pattern type identified
- Confidence level
- Supporting evidence
- Regulatory implications
""",
        variables=["transactions"],
    ),
    "risk_assessment": PromptTemplate(
        name="risk_assessment",
        category="investigation",
        description="Template for comprehensive risk assessment",
        template="""
Conduct a risk assessment for this entity:

## Entity Information
$entity_data

## Transaction History
$transaction_history

## Risk Factors to Consider

1. **Customer Risk**
   - Business type
   - Geographic exposure
   - Beneficial ownership complexity

2. **Behavioral Risk**
   - Transaction patterns
   - Historical alerts
   - KYC status

3. **Product Risk**
   - Services used
   - Channel preferences

## Output

Calculate a risk score (0-100) with factor breakdown.
""",
        variables=["entity_data", "transaction_history"],
    ),
    "evidence_summary": PromptTemplate(
        name="evidence_summary",
        category="investigation",
        description="Template for evidence summarization",
        template="""
Summarize the evidence for this investigation:

## Investigation ID: $investigation_id

## Evidence Items
$evidence_items

## Task

Create a comprehensive evidence summary that:
1. Lists all evidence items with significance ratings
2. Identifies gaps in evidence
3. Highlights key findings
4. Assesses overall evidence strength

Format as a structured report suitable for case file.
""",
        variables=["investigation_id", "evidence_items"],
    ),
}

# =============================================================================
# SAR TEMPLATES
# =============================================================================

SAR_TEMPLATES = {
    "narrative_eu": PromptTemplate(
        name="narrative_eu",
        category="sar",
        description="EU FIU SAR narrative template",
        template="""
Generate a Suspicious Activity Report narrative for EU FIU submission.

## Case Information
$case_data

## Subject Information
$subject_data

## Suspicious Activity Details
$activity_details

## Narrative Requirements

The narrative must include:
1. **Subject Description**: Who is involved
2. **Activity Description**: What happened
3. **Why Suspicious**: Why this is suspicious
4. **Timeline**: When it occurred
5. **Amount**: Financial impact
6. **Supporting Evidence**: What supports the suspicion

## Format

Write a clear, professional narrative in paragraph form.
Avoid jargon. Be specific and factual.
Target length: 500-1000 words.

Include specific transaction references and dates.
Cite applicable regulations (AMLD, national law).
""",
        variables=["case_data", "subject_data", "activity_details"],
    ),
    "narrative_fincen": PromptTemplate(
        name="narrative_fincen",
        category="sar",
        description="FinCEN SAR narrative template (for future US support)",
        template="""
Generate a FinCEN SAR narrative.

## Case Information
$case_data

## Subject Information
$subject_data

## Activity Summary
$activity_details

## FinCEN Narrative Requirements

Address the 5 W's:
1. WHO is conducting the suspicious activity?
2. WHAT is the suspicious activity?
3. WHEN did the activity occur?
4. WHERE did the activity occur?
5. WHY is the activity suspicious?

Include:
- Specific dates and amounts
- Account numbers (masked as appropriate)
- Transaction types
- Red flags observed
- Any law enforcement contact

Target length: Part III narrative box (approximately 15,000 characters max).
""",
        variables=["case_data", "subject_data", "activity_details"],
    ),
    "activity_classification": PromptTemplate(
        name="activity_classification",
        category="sar",
        description="Classify suspicious activity type",
        template="""
Classify the suspicious activity type for this case:

## Activity Details
$activity_details

## Classification Categories

Select all applicable categories:

### Money Laundering
- [ ] Structuring
- [ ] Layering
- [ ] Integration
- [ ] Trade-based ML
- [ ] Real estate ML
- [ ] Shell company activity

### Terrorist Financing
- [ ] Fundraising
- [ ] Fund movement
- [ ] Material support

### Fraud
- [ ] Identity fraud
- [ ] Account takeover
- [ ] Investment fraud
- [ ] Payment fraud

### Sanctions
- [ ] OFAC/EU sanctions violation
- [ ] Correspondent banking issues

### Other
- [ ] Unusual activity
- [ ] Customer concern
- [ ] Third-party tip

Provide classification with confidence level.
""",
        variables=["activity_details"],
    ),
}

# =============================================================================
# COMPLIANCE Q&A TEMPLATES
# =============================================================================

QA_TEMPLATES = {
    "regulatory_query": PromptTemplate(
        name="regulatory_query",
        category="qa",
        description="Answer regulatory compliance questions",
        template="""
You are an EU AML/CFT regulatory expert. Answer this compliance question:

## Question
$question

## Available Regulatory Context
$regulatory_context

## Guidelines

1. Cite specific regulations (AMLD article numbers, EBA guidelines)
2. Distinguish between requirements and best practices
3. Note any jurisdictional variations
4. Acknowledge uncertainty where applicable
5. Suggest where to find authoritative guidance

Provide a clear, actionable answer with citations.
""",
        variables=["question", "regulatory_context"],
    ),
    "policy_guidance": PromptTemplate(
        name="policy_guidance",
        category="qa",
        description="Provide policy implementation guidance",
        template="""
Provide policy guidance for implementing this regulatory requirement:

## Requirement
$requirement

## Current Policy (if any)
$current_policy

## Guidance Needed
$guidance_request

## Output

Provide:
1. Regulatory background
2. Implementation requirements
3. Policy language suggestions
4. Control recommendations
5. Testing/validation approach
""",
        variables=["requirement", "current_policy", "guidance_request"],
    ),
}

# =============================================================================
# BRIEFING TEMPLATES
# =============================================================================

BRIEFING_TEMPLATES = {
    "daily_briefing": PromptTemplate(
        name="daily_briefing",
        category="briefing",
        description="Generate daily compliance briefing",
        template="""
Generate a daily compliance briefing for $date.

## Overnight Activity Summary
$activity_summary

## Open Cases
$open_cases

## Regulatory Calendar
$regulatory_calendar

## Generate Briefing

Create an executive briefing that includes:

1. **Priority Actions** (top 3-5 items requiring attention)
2. **Risk Indicators** (any concerning trends)
3. **Regulatory Updates** (new or pending regulations)
4. **Case Status** (key case milestones)
5. **Recommendations** (suggested focus areas)

Write in clear, professional tone suitable for AMLRO review.
Start with most urgent items.
""",
        variables=["date", "activity_summary", "open_cases", "regulatory_calendar"],
    ),
    "weekly_summary": PromptTemplate(
        name="weekly_summary",
        category="briefing",
        description="Generate weekly compliance summary",
        template="""
Generate a weekly compliance summary for the week of $week_start.

## Weekly Statistics
$weekly_stats

## Significant Events
$significant_events

## Generate Summary

Create a weekly summary report including:

1. **Key Metrics** (alert volume, resolution rates, SAR filings)
2. **Notable Cases** (significant investigations)
3. **Trends** (patterns observed during the week)
4. **Team Performance** (if applicable)
5. **Next Week Focus** (recommended priorities)

Format suitable for management reporting.
""",
        variables=["week_start", "weekly_stats", "significant_events"],
    ),
}

# Register all templates
for template_dict in [INVESTIGATION_TEMPLATES, SAR_TEMPLATES, QA_TEMPLATES, BRIEFING_TEMPLATES]:
    for template in template_dict.values():
        PromptLibrary.register(template)
