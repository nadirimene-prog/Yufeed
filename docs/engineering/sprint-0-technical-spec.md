# Sprint 0 Technical Specification

**Version:** 1.0  
**Date:** January 29, 2026  
**Purpose:** Technical details required before Sprint 1 kickoff

---

## Table of Contents

1. [AI Prompt Templates](#1-ai-prompt-templates)
2. [Database Migrations](#2-database-migrations)
3. [File/Module Structure](#3-filemodule-structure)
4. [Environment Variables](#4-environment-variables)
5. [Test Fixtures](#5-test-fixtures)
6. [API Contract Updates](#6-api-contract-updates)

---

## 1. AI Prompt Templates

### 1.1 Obligation Extraction Prompt

**File:** `apps/api/src/ai/prompts/obligation_extraction.py`

```python
OBLIGATION_EXTRACTION_SYSTEM_PROMPT = """
You are a regulatory compliance expert specializing in EU financial services law.
Your task is to extract specific, actionable compliance obligations from regulatory documents.

For each obligation you identify, extract:
1. obligation_text: The exact requirement in clear, actionable language
2. article_ref: The article/paragraph reference (e.g., "Article 5(2)(a)")
3. applicability: Who this applies to (e.g., "PSPs", "EMIs", "CASPs")
4. effective_date: When this comes into force (parse relative dates)
5. scope_tags: Array of tags ["PSP", "EMI", "CASP", "credit_institution"]

Rules:
- Extract ONLY mandatory requirements (must, shall, required to)
- Skip definitions, recitals, and preamble text
- Each obligation should be independently actionable
- If effective_date is relative (e.g., "18 months after entry into force"), calculate the actual date
- Return JSON array of obligations
"""

OBLIGATION_EXTRACTION_USER_PROMPT = """
Document: {document_title}
CELEX: {celex_number}
Publication Date: {publication_date}

Content:
{document_text}

---

Extract all compliance obligations from this regulatory document.
Return as JSON array with fields: obligation_text, article_ref, applicability, effective_date, scope_tags
"""
```

### 1.2 Policy Section Generation Prompt

**File:** `apps/api/src/ai/prompts/policy_writer.py`

```python
POLICY_SECTION_SYSTEM_PROMPT = """
You are a compliance policy writer for a European Electronic Money Institution (EMI)
and Crypto-Asset Service Provider (CASP) named Yufeed.

Your task is to write professional policy sections that:
1. Address specific regulatory obligations
2. Use first-person institutional voice ("We implement...", "Yufeed maintains...")
3. Are supervisor-ready (suitable for regulatory inspection)
4. Include specific, measurable controls where applicable
5. Reference the source regulation

Style guidelines:
- Professional, formal tone
- Clear, unambiguous language
- Active voice preferred
- Include specific procedures, not just principles
- Be as detailed and accurate as necessary - actionable policies require precision
"""

POLICY_SECTION_USER_PROMPT = """
Generate a policy section for the following regulatory obligation:

Policy Name: {policy_name}
Section Context: {existing_section_titles}

Obligation Details:
- Regulation: {regulation_title} ({celex_number})
- Article: {article_ref}
- Requirement: {obligation_text}
- Effective Date: {effective_date}
- Applicability: {applicability}

---

Write a policy section that addresses this obligation. Include:
1. Section title (e.g., "2.3 Real-Time Transaction Monitoring")
2. Section content with:
   - Purpose statement
   - Specific procedures/controls
   - Responsibilities
   - Reference to source regulation

Return as JSON with fields: section_title, content, regulatory_reference
"""
```

### 1.3 Monitoring Rule Suggestion Prompt

**File:** `apps/api/src/ai/prompts/monitoring_rule_suggester.py`

```python
MONITORING_RULE_SYSTEM_PROMPT = """
You are a transaction monitoring specialist. Your task is to translate
regulatory obligations into configurable monitoring rule parameters.

You understand:
- Velocity rules (transaction counts/amounts over time windows)
- Threshold rules (amount limits, frequency limits)
- Pattern rules (structuring, rapid movement, round amounts)
- Behavioral rules (deviation from baseline, unusual timing)

Output monitoring rule configurations as JSON that can be loaded into
a transaction monitoring system.
"""

MONITORING_RULE_USER_PROMPT = """
Convert this regulatory obligation into a monitoring rule configuration:

Obligation: {obligation_text}
Article: {article_ref} from {regulation_title}
Scope: {applicability}

---

Generate a monitoring rule JSON configuration with:
- name: Short rule name
- description: What the rule detects
- logic: "AND" or "OR" for combining conditions
- conditions: Array of condition objects
  - field: Transaction field to check (amount, count, velocity_1h, etc.)
  - operator: ">", "<", ">=", "<=", "==", "in"
  - value: Threshold value
  - window: Time window if applicable ("1h", "24h", "7d", "30d")
- severity: "low", "medium", "high", "critical"
- alert_message: Template for alert text

Return ONLY the JSON configuration.
"""
```

### 1.4 Policy Matching Prompt

**File:** `apps/api/src/ai/prompts/policy_matcher.py`

```python
POLICY_MATCHING_SYSTEM_PROMPT = """
You are a compliance mapping expert. Your task is to match regulatory obligations
to existing internal policies based on:
1. Subject matter alignment
2. Regulatory basis overlap
3. Keyword and concept similarity

Return a ranked list of matching policies with confidence scores.
"""

POLICY_MATCHING_USER_PROMPT = """
Find the best matching policies for this obligation:

Obligation:
- Text: {obligation_text}
- Regulation: {regulation_title}
- Scope: {applicability}

Available Policies:
{policies_json}

---

Return JSON array of matches sorted by relevance:
[
  {{"policy_id": 1, "policy_name": "...", "match_score": 0.95, "reason": "..."}},
  ...
]

Include only policies with match_score > 0.5. Maximum 5 matches.
"""
```

---

## 2. Database Migrations

### 2.1 New Tables Migration

**File:** `apps/api/alembic/versions/xxxx_add_regulatory_pipeline_tables.py`

```python
"""Add regulatory pipeline tables

Revision ID: xxxx_regulatory_pipeline
Revises: [previous_revision]
Create Date: 2026-01-29

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers
revision = 'xxxx_regulatory_pipeline'
down_revision = '[previous_revision]'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Obligation Rejections table (AI feedback loop)
    op.create_table(
        'obligation_rejections',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('obligation_id', sa.Integer(), sa.ForeignKey('regulatory_obligations.id'), nullable=False),
        sa.Column('rejected_by', sa.String(255), nullable=False),
        sa.Column('rejection_category', sa.String(50), nullable=False),  # not_applicable, duplicate, incorrect_parsing, wrong_article
        sa.Column('feedback_text', sa.Text(), nullable=True),
        sa.Column('document_excerpt', sa.Text(), nullable=True),
        sa.Column('correct_interpretation', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Index('ix_obligation_rejections_obligation_id', 'obligation_id'),
        sa.Index('ix_obligation_rejections_category', 'rejection_category'),
    )

    # 2. Add 'implemented' status to regulatory_obligations
    # (status column already exists, just documenting the new value)

    # 3. Add indexes for deadline queries
    op.create_index(
        'ix_obligations_effective_date',
        'regulatory_obligations',
        ['effective_date'],
        postgresql_where=sa.text("status NOT IN ('rejected', 'deprecated')")
    )

    op.create_index(
        'ix_obligations_linked_policy',
        'regulatory_obligations',
        ['linked_policy_id'],
        postgresql_where=sa.text("linked_policy_id IS NOT NULL")
    )

    op.create_index(
        'ix_internal_rules_obligation_status',
        'internal_rules',
        ['obligation_id', 'status']
    )


def downgrade():
    op.drop_index('ix_internal_rules_obligation_status')
    op.drop_index('ix_obligations_linked_policy')
    op.drop_index('ix_obligations_effective_date')
    op.drop_table('obligation_rejections')
```

### 2.2 Policy Templates Seed Data

**File:** `apps/api/scripts/seed_policy_templates.py`

```python
"""
Seed standard EMI+CASP policy templates.
Run once during deployment: python -m scripts.seed_policy_templates
"""

from src.database import get_db
from src.models.compliance_workflow import PolicyDocument
from datetime import datetime

POLICY_TEMPLATES = [
    # AML/CFT Policies
    {
        "policy_id": "TPL-AML-001",
        "name": "Anti-Money Laundering Policy",
        "owner": "MLRO",
        "status": "template",
        "regulatory_basis": ["AMLD6", "Regulation 2024/1624"],
        "review_frequency_months": 12,
        "category": "AML/CFT"
    },
    {
        "policy_id": "TPL-AML-002",
        "name": "Customer Due Diligence Policy",
        "owner": "MLRO",
        "status": "template",
        "regulatory_basis": ["AMLD6", "Regulation 2024/1624"],
        "review_frequency_months": 12,
        "category": "AML/CFT"
    },
    {
        "policy_id": "TPL-AML-003",
        "name": "Transaction Monitoring Policy",
        "owner": "MLRO",
        "status": "template",
        "regulatory_basis": ["AMLD6", "Regulation 2024/1624"],
        "review_frequency_months": 12,
        "category": "AML/CFT"
    },
    {
        "policy_id": "TPL-AML-004",
        "name": "Suspicious Activity Reporting Policy",
        "owner": "MLRO",
        "status": "template",
        "regulatory_basis": ["AMLD6", "Regulation 2024/1624"],
        "review_frequency_months": 12,
        "category": "AML/CFT"
    },
    {
        "policy_id": "TPL-AML-005",
        "name": "Sanctions Screening Policy",
        "owner": "MLRO",
        "status": "template",
        "regulatory_basis": ["EU Sanctions Regulations"],
        "review_frequency_months": 6,
        "category": "AML/CFT"
    },
    # EMI Policies
    {
        "policy_id": "TPL-EMI-001",
        "name": "Safeguarding Policy",
        "owner": "CFO",
        "status": "template",
        "regulatory_basis": ["EMD2", "PSD2"],
        "review_frequency_months": 12,
        "category": "EMI"
    },
    {
        "policy_id": "TPL-EMI-002",
        "name": "Payment Services Policy",
        "owner": "COO",
        "status": "template",
        "regulatory_basis": ["PSD2", "PSD3"],
        "review_frequency_months": 12,
        "category": "EMI"
    },
    # CASP Policies
    {
        "policy_id": "TPL-CASP-001",
        "name": "Crypto-Asset Custody Policy",
        "owner": "CTO",
        "status": "template",
        "regulatory_basis": ["MiCA"],
        "review_frequency_months": 12,
        "category": "CASP"
    },
    {
        "policy_id": "TPL-CASP-002",
        "name": "Travel Rule Compliance Policy",
        "owner": "MLRO",
        "status": "template",
        "regulatory_basis": ["MiCA", "TFR"],
        "review_frequency_months": 6,
        "category": "CASP"
    },
    {
        "policy_id": "TPL-CASP-003",
        "name": "Market Abuse Prevention Policy",
        "owner": "CCO",
        "status": "template",
        "regulatory_basis": ["MiCA"],
        "review_frequency_months": 12,
        "category": "CASP"
    },
    # Governance Policies
    {
        "policy_id": "TPL-GOV-001",
        "name": "Compliance Management Policy",
        "owner": "CCO",
        "status": "template",
        "regulatory_basis": ["Multiple"],
        "review_frequency_months": 12,
        "category": "Governance"
    },
    {
        "policy_id": "TPL-GOV-002",
        "name": "Outsourcing Policy",
        "owner": "COO",
        "status": "template",
        "regulatory_basis": ["EBA Guidelines"],
        "review_frequency_months": 12,
        "category": "Governance"
    },
    {
        "policy_id": "TPL-GOV-003",
        "name": "Business Continuity Policy",
        "owner": "CTO",
        "status": "template",
        "regulatory_basis": ["DORA"],
        "review_frequency_months": 12,
        "category": "Governance"
    },
    # Data Protection
    {
        "policy_id": "TPL-GDPR-001",
        "name": "Data Protection Policy",
        "owner": "DPO",
        "status": "template",
        "regulatory_basis": ["GDPR"],
        "review_frequency_months": 12,
        "category": "Data Protection"
    },
    {
        "policy_id": "TPL-GDPR-002",
        "name": "Data Retention Policy",
        "owner": "DPO",
        "status": "template",
        "regulatory_basis": ["GDPR", "AMLD6"],
        "review_frequency_months": 12,
        "category": "Data Protection"
    },
]


def seed_templates():
    db = next(get_db())

    for template in POLICY_TEMPLATES:
        existing = db.query(PolicyDocument).filter_by(
            policy_id=template["policy_id"]
        ).first()

        if not existing:
            policy = PolicyDocument(
                policy_id=template["policy_id"],
                name=template["name"],
                owner=template["owner"],
                status=template["status"],
                version="1.0",
                language="en",
            )
            db.add(policy)
            print(f"Created template: {template['name']}")
        else:
            print(f"Skipped (exists): {template['name']}")

    db.commit()
    print(f"\nSeeded {len(POLICY_TEMPLATES)} policy templates")


if __name__ == "__main__":
    seed_templates()
```

---

## 3. File/Module Structure

### 3.1 New Files to Create

```
apps/api/src/
├── ai/
│   ├── prompts/                          # NEW DIRECTORY
│   │   ├── __init__.py
│   │   ├── obligation_extraction.py      # Obligation extraction prompts
│   │   ├── policy_writer.py              # Policy section generation
│   │   ├── monitoring_rule_suggester.py  # TM rule suggestion
│   │   └── policy_matcher.py             # Policy matching
│   ├── policy_writer.py                  # NEW: AI policy section generator
│   ├── monitoring_rule_suggester.py      # NEW: AI monitoring rule suggester
│   ├── action_item_generator.py          # NEW: Auto-generate action items
│   └── ai_feedback.py                    # NEW: Collect rejection feedback
├── compliance/                           # NEW DIRECTORY
│   ├── __init__.py
│   ├── regulatory_alerts.py              # Create alerts from obligations
│   ├── deadline_monitor.py               # Celery deadline check tasks
│   └── escalation.py                     # Email escalation for overdue
├── ingestion/
│   ├── oj_acts.py                        # NEW: OJ Act-by-Act fetcher
│   └── batch.py                          # NEW: Content backfill fetcher
├── models/
│   └── audit.py                          # NEW: AuditLog model (if not exists)
├── services/
│   └── internal_rules_service.py         # NEW: Internal rule management
├── api/
│   └── policies.py                       # MODIFY: Add new endpoints
└── scripts/
    └── seed_policy_templates.py          # NEW: Template seeding script
```

### 3.2 Module Dependencies

```python
# apps/api/src/ai/policy_writer.py
from src.ai.prompts.policy_writer import (
    POLICY_SECTION_SYSTEM_PROMPT,
    POLICY_SECTION_USER_PROMPT
)
from src.ai.base import AnthropicClient  # Existing
from src.models.compliance_workflow import PolicySection, RegulatoryObligation

# apps/api/src/compliance/regulatory_alerts.py
from src.models.transaction_models import Alert
from src.models.compliance_workflow import RegulatoryObligation, PolicyDocument
from src.services.alert_service import create_alert  # Existing or new

# apps/api/src/compliance/deadline_monitor.py
from src.celery_app import celery_app
from src.database import get_db
from src.models.compliance_workflow import RegulatoryObligation
from src.compliance.regulatory_alerts import create_deadline_alert
```

---

## 4. Environment Variables

### 4.1 New Variables Required

Add to `.env.example`:

```bash
# ===========================================
# REGULATORY INTELLIGENCE PIPELINE
# ===========================================

# AI Configuration (Anthropic Claude)
ANTHROPIC_API_KEY=sk-ant-...                    # Already exists
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022      # Model for policy writing
ANTHROPIC_MAX_TOKENS_POLICY=2000                # Max tokens for policy sections
ANTHROPIC_MAX_TOKENS_EXTRACTION=4000            # Max tokens for obligation extraction

# Deadline Monitoring
DEADLINE_ALERT_THRESHOLDS=90,60,30,7,1          # Days before deadline to alert
DEADLINE_CHECK_SCHEDULE=0 8 * * *               # Cron: Daily at 8 AM UTC
OVERDUE_CHECK_SCHEDULE=0 9 * * *                # Cron: Daily at 9 AM UTC

# Email Escalation (Optional)
ESCALATION_ENABLED=false                        # Enable email escalation
ESCALATION_DAYS_THRESHOLD=7                     # Days overdue before email
MLRO_EMAIL=mlro@company.com                     # MLRO email for escalation

# Policy Templates
POLICY_TEMPLATES_AUTO_SEED=true                 # Auto-seed templates on startup
POLICY_TEMPLATES_COUNT=15                       # Expected template count

# Feature Flags
FEATURE_AI_POLICY_WRITER=false                  # Enable AI policy sections
FEATURE_MONITORING_SUGGESTIONS=false            # Enable AI monitoring rule suggestions
FEATURE_DEADLINE_ALERTS=true                    # Enable deadline monitoring
FEATURE_AUDIT_TRAIL=true                        # Enable audit logging
```

### 4.2 Configuration Class Update

**File:** `apps/api/src/config.py`

```python
# Add to existing Settings class

class Settings(BaseSettings):
    # ... existing settings ...

    # Regulatory Pipeline
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    anthropic_max_tokens_policy: int = 2000
    anthropic_max_tokens_extraction: int = 4000

    deadline_alert_thresholds: str = "90,60,30,7,1"
    deadline_check_schedule: str = "0 8 * * *"
    overdue_check_schedule: str = "0 9 * * *"

    escalation_enabled: bool = False
    escalation_days_threshold: int = 7
    mlro_email: str = ""

    policy_templates_auto_seed: bool = True

    # Feature Flags
    feature_ai_policy_writer: bool = False
    feature_monitoring_suggestions: bool = False
    feature_deadline_alerts: bool = True
    feature_audit_trail: bool = True

    @property
    def deadline_thresholds(self) -> list[int]:
        return [int(x) for x in self.deadline_alert_thresholds.split(",")]
```

---

## 5. Test Fixtures

### 5.1 Sample CELEX Documents

**File:** `apps/api/tests/fixtures/sample_regulations.json`

```json
{
  "regulations": [
    {
      "celex": "32024R1624",
      "title": "Regulation (EU) 2024/1624 on the prevention of the use of the financial system for the purposes of money laundering or terrorist financing",
      "publication_date": "2024-06-19",
      "effective_date": "2027-07-10",
      "sample_articles": [
        {
          "article_ref": "Article 15(1)",
          "text": "Obliged entities shall apply customer due diligence measures when establishing a business relationship."
        },
        {
          "article_ref": "Article 50(1)",
          "text": "Obliged entities shall have in place systems enabling them to respond fully and rapidly to enquiries from the FIU."
        },
        {
          "article_ref": "Article 58(1)",
          "text": "Member States shall ensure that obliged entities keep records of transactions for a period of five years after the business relationship has ended."
        }
      ],
      "expected_obligations": 3
    },
    {
      "celex": "32023R1113",
      "title": "Regulation (EU) 2023/1113 on information accompanying transfers of funds and certain crypto-assets (Recast)",
      "publication_date": "2023-05-31",
      "effective_date": "2024-12-30",
      "sample_articles": [
        {
          "article_ref": "Article 14(1)",
          "text": "The crypto-asset service provider of the originator shall ensure that transfers of crypto-assets are accompanied by the name of the originator and the originator's account number."
        },
        {
          "article_ref": "Article 14(5)",
          "text": "For transfers of crypto-assets exceeding EUR 1000, the crypto-asset service provider of the originator shall verify the accuracy of the information before the transfer."
        }
      ],
      "expected_obligations": 2
    },
    {
      "celex": "32023R1114",
      "title": "Regulation (EU) 2023/1114 on markets in crypto-assets (MiCA)",
      "publication_date": "2023-06-09",
      "effective_date": "2024-12-30",
      "sample_articles": [
        {
          "article_ref": "Article 67(1)",
          "text": "Crypto-asset service providers shall act honestly, fairly and professionally in the best interests of their clients."
        },
        {
          "article_ref": "Article 68(1)",
          "text": "Crypto-asset service providers shall provide clients with fair, clear and not misleading information."
        },
        {
          "article_ref": "Article 75(1)",
          "text": "Crypto-asset service providers providing custody and administration of crypto-assets shall segregate holdings of crypto-assets held on behalf of clients from their own holdings."
        }
      ],
      "expected_obligations": 3
    }
  ]
}
```

### 5.2 Sample Policy Template

**File:** `apps/api/tests/fixtures/sample_policy.json`

```json
{
  "policy_id": "POL-AML-001",
  "name": "Anti-Money Laundering Policy",
  "version": "2.1",
  "owner": "MLRO",
  "status": "active",
  "effective_date": "2025-01-01",
  "sections": [
    {
      "section_id": "SEC-001",
      "title": "1. Introduction and Purpose",
      "content": "This Anti-Money Laundering (AML) Policy sets out Yufeed's commitment to preventing money laundering and terrorist financing...",
      "status": "approved"
    },
    {
      "section_id": "SEC-002",
      "title": "2. Customer Due Diligence",
      "content": "We implement risk-based customer due diligence procedures in accordance with AMLD6...",
      "status": "approved",
      "regulatory_reference": "32024R1624 Article 15"
    }
  ],
  "linked_obligations": [
    "OBL-2024-001",
    "OBL-2024-002"
  ]
}
```

### 5.3 Test Helper Functions

**File:** `apps/api/tests/fixtures/helpers.py`

```python
"""Test helpers for regulatory pipeline testing."""

import json
from pathlib import Path
from datetime import datetime, timedelta
from src.models.compliance_workflow import (
    RegulatoryObligation,
    PolicyDocument,
    PolicySection,
    InternalRule,
)
from src.models.legal_document import LegalDocument


FIXTURES_DIR = Path(__file__).parent


def load_fixture(name: str) -> dict:
    """Load a JSON fixture file."""
    with open(FIXTURES_DIR / f"{name}.json") as f:
        return json.load(f)


def create_test_obligation(
    db,
    celex: str = "32024R1624",
    status: str = "draft",
    effective_date: datetime = None,
    linked_policy_id: int = None,
) -> RegulatoryObligation:
    """Create a test obligation for testing."""
    if effective_date is None:
        effective_date = datetime.utcnow() + timedelta(days=90)

    obligation = RegulatoryObligation(
        obligation_id=f"OBL-TEST-{datetime.utcnow().timestamp()}",
        doc_id=1,  # Assumes test legal_document exists
        celex=celex,
        article_ref="Article 15(1)",
        obligation_text="Test obligation text for unit testing.",
        applicability="EMI, CASP",
        effective_date=effective_date,
        status=status,
        linked_policy_id=linked_policy_id,
        scope_tags=["EMI", "CASP"],
    )
    db.add(obligation)
    db.commit()
    db.refresh(obligation)
    return obligation


def create_test_policy(
    db,
    name: str = "Test AML Policy",
    status: str = "draft",
) -> PolicyDocument:
    """Create a test policy for testing."""
    policy = PolicyDocument(
        policy_id=f"POL-TEST-{datetime.utcnow().timestamp()}",
        name=name,
        version="1.0",
        owner="MLRO",
        status=status,
        language="en",
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def create_test_internal_rule(
    db,
    obligation_id: int,
    policy_section_id: int = None,
    status: str = "draft",
) -> InternalRule:
    """Create a test internal rule for testing."""
    rule = InternalRule(
        obligation_id=obligation_id,
        policy_section_id=policy_section_id,
        name=f"Test Rule {datetime.utcnow().timestamp()}",
        description="Test internal rule for unit testing.",
        status=status,
        control_owner="Compliance",
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule
```

---

## 6. API Contract Updates

### 6.1 OpenAPI Additions

Add to `apps/api/src/api/policies.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/api/policies", tags=["policies"])


# Request/Response Models

class PolicyTemplateResponse(BaseModel):
    policy_id: str
    name: str
    owner: str
    category: str
    regulatory_basis: List[str]
    review_frequency_months: int


class CreateFromTemplateRequest(BaseModel):
    name: Optional[str] = None  # Override template name
    owner: Optional[str] = None  # Override owner


class LinkObligationResponse(BaseModel):
    policy_id: int
    obligation_id: int
    linked_at: datetime
    ai_section_generated: bool
    section_id: Optional[int] = None


class GeneratedSectionResponse(BaseModel):
    section_id: int
    title: str
    content: str
    status: str  # "draft"
    regulatory_reference: str
    generated_at: datetime


class ApproveSectionRequest(BaseModel):
    approved_by: str
    comments: Optional[str] = None


class PolicyExportResponse(BaseModel):
    markdown: str
    compliance_matrix: List[dict]
    export_date: datetime
    policy_version: str


# Endpoints

@router.get("/templates", response_model=List[PolicyTemplateResponse])
async def list_policy_templates(
    category: Optional[str] = None,
    db = Depends(get_db)
):
    """List available policy templates."""
    pass


@router.post("/from-template/{template_id}")
async def create_policy_from_template(
    template_id: str,
    request: CreateFromTemplateRequest,
    db = Depends(get_db)
):
    """Create a new policy from a template."""
    pass


@router.post("/{policy_id}/link-obligation/{obligation_id}",
             response_model=LinkObligationResponse)
async def link_obligation_to_policy(
    policy_id: int,
    obligation_id: int,
    db = Depends(get_db)
):
    """
    Link an obligation to a policy.
    Triggers AI policy section generation automatically.
    """
    pass


@router.post("/{policy_id}/sections/{section_id}/approve")
async def approve_policy_section(
    policy_id: int,
    section_id: int,
    request: ApproveSectionRequest,
    current_user = Depends(require_role("mlro")),
    db = Depends(get_db)
):
    """
    Approve a policy section for publication.
    Requires MLRO role.
    """
    pass


@router.get("/{policy_id}/export", response_model=PolicyExportResponse)
async def export_policy(
    policy_id: int,
    format: str = "markdown",
    db = Depends(get_db)
):
    """
    Export policy as formatted document with compliance matrix.
    """
    pass


@router.get("/{policy_id}/compliance-matrix")
async def get_compliance_matrix(
    policy_id: int,
    db = Depends(get_db)
):
    """
    Get obligation-to-section mapping for a policy.
    """
    pass
```

---

## Checklist: Ready for Sprint 1?

### Pre-Sprint Validation

- [ ] All prompt files created in `src/ai/prompts/`
- [ ] Database migration tested locally
- [ ] `.env.example` updated with new variables
- [ ] Test fixtures loaded and passing
- [ ] Policy templates seeded (15 templates)
- [ ] File structure created (empty files OK)
- [ ] API contracts reviewed with frontend

### Sprint 1 Kickoff Criteria

- [ ] Team has read Sprint 0 spec
- [ ] Development environment setup verified
- [ ] First 3 design partner customers identified
- [ ] Anthropic API key with sufficient credits
- [ ] Celery Beat configured for scheduled tasks

---

**Document Status:** Complete  
**Next Step:** Review and approve, then begin Sprint 1
