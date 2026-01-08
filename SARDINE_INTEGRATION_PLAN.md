# Yufeed × Sardine.ai Integration Plan
## Reverse-Engineering & Implementation Roadmap

**Date:** January 8, 2026
**Version:** 1.0
**Status:** Strategic Planning Phase
**Estimated Timeline:** 6-9 months (phased approach)

---

## EXECUTIVE SUMMARY

This document outlines a comprehensive plan to integrate [Sardine.ai](https://www.sardine.ai/)-inspired compliance capabilities into Yufeed, transforming it from a document monitoring platform into a **full-spectrum AML/CFT compliance intelligence system**.

### Key Objectives

1. **Real-Time Transaction Monitoring** - Move beyond document analysis to active transaction surveillance
2. **AI-Powered Case Management** - Automate alert triage and investigation workflows
3. **Risk Scoring Engine** - Implement feature-based risk assessment (4,800+ features)
4. **Behavioral Analytics** - Add device intelligence and behavioral biometrics
5. **Automated SAR/UAR Filing** - Streamline regulatory reporting
6. **Network Graph Analysis** - Detect fraud rings and money laundering networks

### Strategic Rationale

Yufeed currently excels at **regulatory document intelligence**. By integrating Sardine-style capabilities, we create a unique offering:

> **"The only compliance platform that combines regulatory intelligence with real-time transaction monitoring and AI-powered case management"**

---

## PART 1: SARDINE.AI ANALYSIS

### 1.1 Core Architecture Components

Based on [research](https://www.sardine.ai/platform) and [technical documentation](https://www.sardine.ai/blog/real-time-ai-and-machine-learning-for-transaction-monitoring), Sardine's architecture consists of:

```
┌─────────────────────────────────────────────────────────────┐
│                    Sardine Architecture                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐    │
│  │   Data       │   │   Feature    │   │   Risk       │    │
│  │ Ingestion    │──▶│  Engineering │──▶│   Engine     │    │
│  └──────────────┘   └──────────────┘   └──────────────┘    │
│         │                   │                   │            │
│         ▼                   ▼                   ▼            │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐    │
│  │ Device Intel │   │  4,800+      │   │  Real-Time   │    │
│  │ & Biometrics │   │  Features    │   │  ML Models   │    │
│  └──────────────┘   └──────────────┘   └──────────────┘    │
│         │                   │                   │            │
│         └───────────────────┴───────────────────┘            │
│                             │                                 │
│                             ▼                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │          Case Management & Alert System              │   │
│  │  • Alert Queues  • AI Agents  • SAR Filing          │   │
│  │  • Workflow Auto • Analytics  • Network Graphs      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Key Features Matrix

| Category | Sardine Feature | Implementation Complexity | Value to Yufeed |
|----------|----------------|--------------------------|----------------|
| **Transaction Monitoring** | Real-time + Batch alerts | HIGH | ⭐⭐⭐⭐⭐ |
| | 500+ pre-built rules | MEDIUM | ⭐⭐⭐⭐⭐ |
| | Custom rule builder | MEDIUM | ⭐⭐⭐⭐ |
| **Risk Scoring** | 4,800+ feature warehouse | VERY HIGH | ⭐⭐⭐⭐⭐ |
| | ML model training | HIGH | ⭐⭐⭐⭐ |
| | Real-time scoring (< 500ms) | HIGH | ⭐⭐⭐⭐⭐ |
| **Device Intelligence** | DIBB (Device + Biometrics) | VERY HIGH | ⭐⭐ |
| | Bot detection | HIGH | ⭐ |
| | Account takeover detection | HIGH | ⭐ |
| **Case Management** | Alert queues | MEDIUM | ⭐⭐⭐⭐⭐ |
| | Collaborative investigations | MEDIUM | ⭐⭐⭐⭐ |
| | Audit trails | LOW | ⭐⭐⭐⭐⭐ |
| **AI Agents** | Automated alert triage | HIGH | ⭐⭐⭐⭐⭐ |
| | SAR narrative generation | MEDIUM | ⭐⭐⭐⭐⭐ |
| | Document review | MEDIUM | ⭐⭐⭐⭐ |
| **Reporting** | SAR/UAR templates | MEDIUM | ⭐⭐⭐⭐⭐ |
| | FinCEN integration | HIGH | ⭐⭐⭐⭐ |
| | Custom reporting | LOW | ⭐⭐⭐⭐ |
| **Network Analysis** | Fraud ring detection | VERY HIGH | ⭐⭐⭐ |
| | Connections graph | HIGH | ⭐⭐⭐⭐ |

**Legend:**
- ⭐⭐⭐⭐⭐ = Critical for AMLROs, must implement
- ⭐⭐⭐⭐ = High value, implement in Phase 1-2
- ⭐⭐⭐ = Nice to have, Phase 3+
- ⭐⭐ = Lower priority for Yufeed's use case
- ⭐ = Not relevant to regulatory monitoring

### 1.3 Technical Stack Insights

From [Sardine's architecture](https://www.sardine.ai/blog/machine-learning-feature-store-for-fraud-and-compliance):

**Data Layer:**
- BigQuery / Snowflake for data warehouse
- Feature store with 4,800+ engineered features
- 40+ third-party data provider integrations

**Compute Layer:**
- Real-time processing (< 500ms latency)
- Batch processing for historical analysis
- GCP infrastructure

**ML/AI Layer:**
- Custom models trained on billions of transactions
- Pre-built models for specific fraud types
- GenAI copilot ("Finley") for case assistance

**Application Layer:**
- No-code rules engine
- Workflow automation
- API-first architecture

---

## PART 2: YUFEED CURRENT STATE ANALYSIS

### 2.1 Existing Capabilities

**Strengths:**
- ✅ EU regulatory document intelligence
- ✅ Full-text content extraction
- ✅ AI-powered compliance analysis (Claude-based)
- ✅ Impact assessment framework
- ✅ Natural language queries (RAG)
- ✅ Document version comparison

**Gaps (Compared to Sardine):**
- ❌ No transaction monitoring
- ❌ No real-time alerting system
- ❌ No risk scoring engine
- ❌ No case management workflow
- ❌ No SAR/UAR filing capabilities
- ❌ No network/graph analysis
- ❌ No AI agents for automation
- ❌ No feature engineering pipeline

### 2.2 Yufeed's Unique Advantage

**What Yufeed Has That Sardine Doesn't:**

1. **Regulatory Document Intelligence**
   - Automatic EUR-Lex monitoring
   - AI summaries of complex regulations
   - Change detection in amendments
   - Article-level parsing

2. **Contextual Compliance**
   - Links transactions to specific regulations
   - Impact assessments tied to legal requirements
   - Obligation tracking from source documents

3. **European Focus**
   - GDPR, AML6D, MiCA expertise
   - EUR-Lex integration
   - EU-specific compliance domains

**Strategic Positioning:**

> **Sardine:** Transaction monitoring → Find suspicious activity
>
> **Yufeed:** Regulation monitoring → Know what to look for
>
> **Yufeed + Sardine Features:** Regulation monitoring → Transaction monitoring → Holistic compliance

---

## PART 3: INTEGRATION ARCHITECTURE

### 3.1 Proposed Hybrid Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                      YUFEED 2.0 ARCHITECTURE                     │
│                   (Regulatory Intelligence + AML)                │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │        REGULATORY INTELLIGENCE LAYER (Existing)         │   │
│  │  • EUR-Lex Ingestion  • Document Analysis               │   │
│  │  • Change Detection   • Obligation Extraction           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                             │                                    │
│                             ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │         TRANSACTION MONITORING LAYER (NEW)               │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │   │
│  │  │ Data Ingestion│  │Feature Store │  │ Risk Engine  │  │   │
│  │  │  • Batch API  │  │ • 500+ Rules │  │ • ML Models  │  │   │
│  │  │  • Real-time  │  │ • Custom     │  │ • Scoring    │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                             │                                    │
│                             ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │         INTELLIGENT ALERTING LAYER (NEW)                 │   │
│  │  • Regulatory Context Enrichment                         │   │
│  │  • AI-Powered Triage                                     │   │
│  │  • Alert Prioritization (Regulation × Transaction)       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                             │                                    │
│                             ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │         CASE MANAGEMENT & REPORTING (NEW)                │   │
│  │  • Investigation Workflows                               │   │
│  │  • AI Agents (Triage, SAR Writing)                       │   │
│  │  • SAR/UAR Filing                                        │   │
│  │  • Network Graph Analysis                                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

### 3.2 Data Flow

```
Regulatory Update (EUR-Lex)
         │
         ▼
   Yufeed Analysis
  (What rules apply?)
         │
         ▼
   Rule Configuration ─────────┐
  (Auto-generate rules         │
   based on regulations)        │
         │                      │
         ▼                      │
   Transaction Stream           │
         │                      │
         ▼                      │
   Risk Engine  ◀───────────────┘
  (Apply reg-aware rules)
         │
         ▼
   Alert Generation
  (With regulatory context)
         │
         ▼
   AI Agent Triage
  (Using regulation knowledge)
         │
         ▼
   Case Management
  (Link to source regulations)
         │
         ▼
   SAR Filing
  (Auto-cite regulations)
```

**Key Innovation:** Transaction alerts are automatically enriched with **relevant regulatory context** from Yufeed's document intelligence.

---

## PART 4: FEATURE IMPLEMENTATION PLAN

### PHASE 1: Foundation (Months 1-2)

**Goal:** Build core transaction monitoring infrastructure

#### 1.1 Transaction Data Model

**New Tables:**
```sql
-- Transactions
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    transaction_type VARCHAR(50), -- 'deposit', 'withdrawal', 'transfer'
    counterparty_id VARCHAR(255),
    timestamp TIMESTAMP NOT NULL,
    status VARCHAR(50), -- 'pending', 'completed', 'flagged', 'blocked'

    -- Geographic data
    ip_address INET,
    country_code VARCHAR(2),
    geo_location POINT,

    -- Risk data
    risk_score DECIMAL(5, 2),
    risk_level VARCHAR(20), -- 'low', 'medium', 'high', 'critical'
    risk_factors JSONB,

    -- Metadata
    device_fingerprint VARCHAR(255),
    session_id VARCHAR(255),
    metadata JSONB,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Alert System
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    alert_id VARCHAR(255) UNIQUE NOT NULL,
    alert_type VARCHAR(100) NOT NULL, -- 'velocity', 'structuring', 'unusual_pattern'
    severity VARCHAR(20) NOT NULL, -- 'low', 'medium', 'high', 'critical'

    -- Triggered by
    transaction_id INTEGER REFERENCES transactions(id),
    user_id VARCHAR(255),
    rule_id VARCHAR(255),

    -- Status workflow
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'in_review', 'escalated', 'resolved', 'false_positive'
    assigned_to VARCHAR(255),
    priority INTEGER DEFAULT 3, -- 1 (highest) to 5 (lowest)

    -- Alert details
    description TEXT,
    risk_score DECIMAL(5, 2),
    matched_rules JSONB,
    evidence JSONB,

    -- REGULATORY CONTEXT (Yufeed Innovation)
    related_regulations JSONB, -- Link to LegalDocument IDs
    regulation_context TEXT, -- AI-generated explanation

    -- Resolution
    resolution_status VARCHAR(50),
    resolution_notes TEXT,
    resolved_by VARCHAR(255),
    resolved_at TIMESTAMP,

    -- SAR filing
    sar_filed BOOLEAN DEFAULT FALSE,
    sar_id VARCHAR(255),
    sar_filed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Cases (Investigation Management)
CREATE TABLE cases (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(255) UNIQUE NOT NULL,
    case_type VARCHAR(100), -- 'investigation', 'sar_preparation', 'audit'
    subject_type VARCHAR(50), -- 'user', 'transaction', 'pattern'
    subject_id VARCHAR(255),

    -- Status
    status VARCHAR(50) DEFAULT 'open', -- 'open', 'in_progress', 'escalated', 'closed'
    priority VARCHAR(20) DEFAULT 'medium', -- 'low', 'medium', 'high', 'critical'

    -- Assignment
    assigned_to VARCHAR(255),
    team VARCHAR(100),

    -- Content
    title VARCHAR(500),
    description TEXT,
    summary TEXT,

    -- Related entities
    related_alerts INTEGER[], -- Array of alert IDs
    related_transactions INTEGER[], -- Array of transaction IDs
    related_users VARCHAR(255)[],

    -- REGULATORY LINKAGE
    applicable_regulations INTEGER[], -- Array of LegalDocument IDs
    regulatory_violations JSONB,

    -- Evidence
    evidence JSONB,
    attachments JSONB,

    -- Timeline
    opened_at TIMESTAMP DEFAULT NOW(),
    closed_at TIMESTAMP,

    -- Outcomes
    outcome VARCHAR(100), -- 'sar_filed', 'no_action', 'account_closed', 'escalated'
    outcome_notes TEXT,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Monitoring Rules
CREATE TABLE monitoring_rules (
    id SERIAL PRIMARY KEY,
    rule_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(500) NOT NULL,
    description TEXT,

    -- Rule type
    category VARCHAR(100), -- 'velocity', 'structuring', 'unusual_behavior', 'sanctions'
    severity VARCHAR(20) DEFAULT 'medium',

    -- Rule logic (JSON-based DSL)
    conditions JSONB NOT NULL,
    thresholds JSONB,

    -- Regulatory basis (YUFEED INNOVATION)
    regulatory_source INTEGER REFERENCES legal_documents(id),
    regulation_article VARCHAR(255),
    regulatory_requirement TEXT,

    -- Status
    enabled BOOLEAN DEFAULT TRUE,
    version INTEGER DEFAULT 1,

    -- Performance tracking
    alert_count INTEGER DEFAULT 0,
    true_positive_rate DECIMAL(5, 2),
    false_positive_rate DECIMAL(5, 2),

    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- User Risk Profiles
CREATE TABLE user_risk_profiles (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) UNIQUE NOT NULL,

    -- Computed risk
    overall_risk_score DECIMAL(5, 2),
    risk_level VARCHAR(20), -- 'low', 'medium', 'high', 'critical'
    risk_factors JSONB,

    -- Behavioral patterns
    transaction_velocity_30d INTEGER,
    average_transaction_amount DECIMAL(15, 2),
    transaction_pattern_score DECIMAL(5, 2),

    -- KYC/CDD status
    kyc_status VARCHAR(50),
    kyc_last_updated TIMESTAMP,
    enhanced_due_diligence BOOLEAN DEFAULT FALSE,

    -- Geographic risk
    primary_country VARCHAR(2),
    high_risk_jurisdictions VARCHAR(2)[],

    -- Alerts history
    total_alerts INTEGER DEFAULT 0,
    critical_alerts INTEGER DEFAULT 0,
    resolved_alerts INTEGER DEFAULT 0,

    -- Sanctions screening
    sanctions_screened_at TIMESTAMP,
    sanctions_match BOOLEAN DEFAULT FALSE,

    last_calculated_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Feature Store (Simplified version)
CREATE TABLE feature_values (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL, -- 'transaction', 'user', 'session'
    entity_id VARCHAR(255) NOT NULL,

    -- Feature data
    feature_name VARCHAR(255) NOT NULL,
    feature_value JSONB NOT NULL,
    feature_type VARCHAR(50), -- 'numeric', 'categorical', 'boolean', 'text'

    -- Metadata
    calculated_at TIMESTAMP NOT NULL,
    version INTEGER DEFAULT 1,

    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_feature_lookup ON feature_values(entity_type, entity_id, feature_name);
```

#### 1.2 Transaction Ingestion API

**API Endpoints:**
```python
# /backend/src/api/transactions.py

@router.post("/transactions/ingest")
async def ingest_transaction(
    transaction: TransactionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Ingest transaction for real-time monitoring.
    Triggers risk scoring and rule evaluation.
    """
    # 1. Store transaction
    db_transaction = Transaction(**transaction.dict())
    db.add(db_transaction)
    db.commit()

    # 2. Trigger async risk assessment
    background_tasks.add_task(
        assess_transaction_risk,
        db_transaction.id
    )

    return {"status": "accepted", "transaction_id": db_transaction.transaction_id}

@router.post("/transactions/batch")
async def ingest_batch(
    transactions: List[TransactionCreate],
    db: Session = Depends(get_db)
):
    """
    Batch transaction ingestion for historical analysis.
    """
    pass

@router.get("/transactions/{transaction_id}/risk")
def get_transaction_risk(
    transaction_id: str,
    db: Session = Depends(get_db)
):
    """
    Get risk assessment for a transaction.
    """
    pass
```

#### 1.3 Basic Rules Engine

**Implementation:**
```python
# /backend/src/monitoring/rules_engine.py

class RulesEngine:
    """
    Simple rules engine for transaction monitoring.
    Sardine-inspired but adapted for regulatory context.
    """

    def __init__(self, db: Session):
        self.db = db
        self.rules = self._load_active_rules()

    def evaluate_transaction(
        self,
        transaction: Transaction,
        user_profile: UserRiskProfile
    ) -> List[Alert]:
        """
        Evaluate transaction against all active rules.
        Returns list of triggered alerts.
        """
        alerts = []

        for rule in self.rules:
            if self._check_rule(transaction, user_profile, rule):
                alert = self._create_alert(transaction, rule)
                alerts.append(alert)

        return alerts

    def _check_rule(
        self,
        transaction: Transaction,
        user_profile: UserRiskProfile,
        rule: MonitoringRule
    ) -> bool:
        """
        Check if transaction matches rule conditions.
        Uses JSON-based rule DSL.
        """
        conditions = rule.conditions

        # Example: Velocity check
        if conditions.get("type") == "velocity":
            threshold = conditions["threshold"]
            timeframe = conditions["timeframe_minutes"]

            recent_count = self._count_recent_transactions(
                transaction.user_id,
                timeframe
            )

            return recent_count > threshold

        # Example: Amount threshold
        elif conditions.get("type") == "amount_threshold":
            return transaction.amount > conditions["max_amount"]

        # Example: Geographic risk
        elif conditions.get("type") == "geographic_risk":
            high_risk_countries = conditions["countries"]
            return transaction.country_code in high_risk_countries

        return False

    def _create_alert(
        self,
        transaction: Transaction,
        rule: MonitoringRule
    ) -> Alert:
        """
        Create alert with regulatory context (Yufeed innovation).
        """
        alert = Alert(
            alert_type=rule.category,
            severity=rule.severity,
            transaction_id=transaction.id,
            user_id=transaction.user_id,
            rule_id=rule.rule_id,
            description=f"Rule triggered: {rule.name}",
            matched_rules=[rule.rule_id]
        )

        # YUFEED INNOVATION: Add regulatory context
        if rule.regulatory_source:
            alert.related_regulations = [rule.regulatory_source]
            alert.regulation_context = self._generate_regulatory_context(
                rule.regulatory_source,
                rule.regulation_article
            )

        self.db.add(alert)
        self.db.commit()

        return alert
```

#### 1.4 Pre-built Rules Library

**Categories (500+ rules like Sardine):**

1. **Velocity Rules** (100 rules)
   - Transaction count per hour/day/week
   - Amount velocity (total $ per timeframe)
   - Login velocity
   - Account changes velocity

2. **Structuring Rules** (80 rules)
   - Amounts just below reporting thresholds
   - Multiple round-number transactions
   - Layering patterns

3. **Unusual Behavior** (120 rules)
   - Dormant account suddenly active
   - Geographic impossibility
   - Unusual transaction time/day
   - Device changes

4. **Sanctions & Watchlist** (50 rules)
   - OFAC screening
   - EU sanctions lists
   - PEP screening
   - Adverse media

5. **Regulatory-Specific Rules** (150 rules)
   - AML6D Article 7 (Enhanced Due Diligence)
   - MiCA crypto asset rules
   - GDPR data transfer monitoring
   - Travel Rule compliance

**Rule Template Example:**
```json
{
  "rule_id": "AML6D_ART7_HIGH_RISK_JURISDICTION",
  "name": "Transaction from High-Risk Jurisdiction (AML6D Article 7)",
  "description": "Detect transactions originating from FATF high-risk jurisdictions requiring enhanced due diligence",
  "category": "geographic_risk",
  "severity": "high",
  "regulatory_source": 12345,  // LegalDocument ID for AML6D
  "regulation_article": "Article 7",
  "regulatory_requirement": "Enhanced due diligence required for transactions from high-risk third countries",
  "conditions": {
    "type": "geographic_risk",
    "countries": ["IR", "KP", "MM"],  // Iran, North Korea, Myanmar
    "apply_if": {
      "amount_threshold": 1000,
      "transaction_types": ["deposit", "withdrawal", "transfer"]
    }
  },
  "alert_template": {
    "description": "Transaction from {country_name} requires enhanced due diligence per AML6D Article 7",
    "recommended_actions": [
      "Perform enhanced CDD",
      "Review source of funds",
      "Document risk assessment",
      "Consider SAR filing if suspicious"
    ]
  }
}
```

### PHASE 2: AI & Automation (Months 3-4)

**Goal:** Add AI agents for alert triage and case management

#### 2.1 AI Alert Triage Agent

**Implementation:**
```python
# /backend/src/ai/alert_agent.py

class AlertTriageAgent:
    """
    AI agent for automated alert triage.
    Sardine-inspired but using Claude instead of proprietary models.
    """

    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    async def triage_alert(self, alert_id: int, db: Session) -> dict:
        """
        Automatically triage an alert.

        Returns:
            - disposition: 'auto_close', 'escalate', 'needs_review'
            - confidence: 0.0-1.0
            - reasoning: Explanation
            - recommended_actions: List of next steps
        """
        alert = db.query(Alert).filter(Alert.id == alert_id).first()

        # Gather context
        transaction = alert.transaction
        user_profile = self._get_user_profile(alert.user_id, db)
        historical_alerts = self._get_user_alert_history(alert.user_id, db)
        regulatory_context = self._get_regulatory_context(alert, db)

        # Build triage prompt
        prompt = self._build_triage_prompt(
            alert, transaction, user_profile,
            historical_alerts, regulatory_context
        )

        # Get AI decision
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse response
        decision = self._parse_triage_decision(response.content[0].text)

        # Update alert
        alert.status = decision["disposition"]
        alert.resolution_notes = decision["reasoning"]
        db.commit()

        return decision

    def _build_triage_prompt(
        self, alert, transaction, user_profile,
        historical_alerts, regulatory_context
    ) -> str:
        """
        Build triage prompt with full context.
        """
        return f"""You are an AML compliance officer reviewing an alert.

ALERT DETAILS:
- Type: {alert.alert_type}
- Severity: {alert.severity}
- Description: {alert.description}

TRANSACTION:
- Amount: {transaction.amount} {transaction.currency}
- Type: {transaction.transaction_type}
- From: {transaction.user_id}
- To: {transaction.counterparty_id}
- Country: {transaction.country_code}
- Time: {transaction.timestamp}

USER PROFILE:
- Risk Score: {user_profile.overall_risk_score}
- 30-day Transaction Velocity: {user_profile.transaction_velocity_30d}
- Previous Alerts: {user_profile.total_alerts}
- Critical Alerts: {user_profile.critical_alerts}
- KYC Status: {user_profile.kyc_status}

REGULATORY CONTEXT:
{regulatory_context}

HISTORICAL BEHAVIOR:
- Previous similar alerts: {len(historical_alerts)}
- Resolution pattern: {self._summarize_resolutions(historical_alerts)}

Based on this information, make a triage decision:

1. Should this alert be:
   a) AUTO_CLOSE (clearly false positive)
   b) NEEDS_REVIEW (requires human judgment)
   c) ESCALATE (high risk, immediate attention)

2. Confidence level (0.0-1.0)

3. Reasoning (2-3 sentences)

4. Recommended actions (if escalating)

5. Regulatory considerations (cite specific articles if applicable)

Return your response in JSON format:
{{
    "disposition": "...",
    "confidence": 0.X,
    "reasoning": "...",
    "recommended_actions": ["...", "..."],
    "regulatory_notes": "..."
}}
"""
```

#### 2.2 SAR Narrative Generation Agent

**Implementation:**
```python
# /backend/src/ai/sar_agent.py

class SARNarrativeAgent:
    """
    AI agent for generating SAR narrative sections.
    Based on Sardine's approach but with regulatory intelligence.
    """

    def generate_sar_narrative(
        self,
        case: Case,
        alerts: List[Alert],
        transactions: List[Transaction],
        db: Session
    ) -> dict:
        """
        Generate comprehensive SAR narrative with regulatory citations.

        Returns structured SAR with all required sections.
        """
        # Gather all evidence
        evidence = self._compile_evidence(case, alerts, transactions, db)

        # Get regulatory citations
        regulations = self._get_cited_regulations(case, db)

        # Generate narrative sections
        prompt = f"""Generate a Suspicious Activity Report (SAR) narrative based on this case.

CASE SUMMARY:
{case.summary}

SUBJECT INFORMATION:
- User ID: {case.subject_id}
- Account Type: {evidence['user_type']}

SUSPICIOUS ACTIVITY:
{self._format_suspicious_activity(alerts, transactions)}

REGULATORY VIOLATIONS:
{self._format_regulatory_violations(case, regulations)}

TIMELINE:
{self._format_timeline(transactions)}

Generate a complete SAR narrative including:
1. Subject Information
2. Suspicious Activity Description
3. Activity Timeline
4. Regulatory Basis (cite specific EU regulations)
5. Investigation Actions Taken
6. Supporting Documentation

Use professional compliance language. Cite specific regulation articles where applicable.
"""

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )

        narrative = response.content[0].text

        return {
            "narrative": narrative,
            "cited_regulations": [reg.celex for reg in regulations],
            "evidence_count": len(alerts) + len(transactions),
            "generated_at": datetime.utcnow().isoformat()
        }
```

#### 2.3 Automated Workflow System

**Workflow Engine:**
```python
# /backend/src/workflows/engine.py

class WorkflowEngine:
    """
    Automated workflow system for alert handling.
    Sardine-inspired workflow automation.
    """

    def __init__(self, db: Session):
        self.db = db
        self.workflows = self._load_workflows()

    async def process_alert(self, alert: Alert):
        """
        Process alert through automated workflow.
        """
        workflow = self._get_workflow_for_alert(alert)

        for step in workflow.steps:
            result = await self._execute_step(step, alert)

            if result.action == "halt":
                break
            elif result.action == "escalate":
                await self._escalate_alert(alert, result.reason)
                break

    async def _execute_step(self, step: WorkflowStep, alert: Alert):
        """
        Execute individual workflow step.
        """
        if step.type == "ai_triage":
            agent = AlertTriageAgent()
            return await agent.triage_alert(alert.id, self.db)

        elif step.type == "auto_resolve":
            # Check auto-resolution criteria
            if self._meets_auto_resolution_criteria(alert):
                alert.status = "resolved"
                alert.resolution_status = "false_positive"
                self.db.commit()
                return {"action": "halt", "reason": "auto_resolved"}

        elif step.type == "assign_analyst":
            # Route to appropriate analyst queue
            analyst = self._assign_to_analyst(alert)
            alert.assigned_to = analyst
            self.db.commit()

        elif step.type == "create_case":
            # Create investigation case
            case = self._create_case_from_alert(alert)
            alert.status = "in_review"
            self.db.commit()
```

### PHASE 3: Advanced Features (Months 5-6)

#### 3.1 Feature Engineering Pipeline

**Feature Store Implementation:**
```python
# /backend/src/monitoring/features.py

class FeatureStore:
    """
    Feature warehouse for risk scoring.
    Inspired by Sardine's 4,800+ features.
    """

    # Feature categories
    FEATURE_CATEGORIES = {
        "velocity": 50,
        "amount_patterns": 80,
        "geographic": 40,
        "temporal": 60,
        "network": 70,
        "behavioral": 90,
        "device": 45,  # If we add device intelligence
        "regulatory": 100  # Yufeed-specific
    }

    def calculate_features(
        self,
        entity_type: str,
        entity_id: str,
        db: Session
    ) -> dict:
        """
        Calculate all features for an entity.
        """
        features = {}

        if entity_type == "transaction":
            features.update(self._transaction_features(entity_id, db))
        elif entity_type == "user":
            features.update(self._user_features(entity_id, db))

        return features

    def _transaction_features(self, transaction_id: str, db: Session) -> dict:
        """
        Calculate 200+ transaction-level features.
        """
        txn = db.query(Transaction).filter(...).first()

        return {
            # Amount features
            "amount": txn.amount,
            "amount_rounded": self._is_round_number(txn.amount),
            "amount_percentile": self._get_amount_percentile(txn, db),
            "amount_vs_user_avg": self._compare_to_user_avg(txn, db),

            # Velocity features
            "txn_count_1h": self._count_recent_transactions(txn.user_id, 60, db),
            "txn_count_24h": self._count_recent_transactions(txn.user_id, 1440, db),
            "txn_count_7d": self._count_recent_transactions(txn.user_id, 10080, db),
            "amount_sum_24h": self._sum_recent_amount(txn.user_id, 1440, db),

            # Temporal features
            "hour_of_day": txn.timestamp.hour,
            "day_of_week": txn.timestamp.weekday(),
            "is_weekend": txn.timestamp.weekday() in [5, 6],
            "is_business_hours": 9 <= txn.timestamp.hour <= 17,

            # Geographic features
            "country_risk_score": self._get_country_risk(txn.country_code),
            "cross_border": txn.country_code != self._get_user_country(txn.user_id),
            "distance_from_home": self._calculate_distance(txn, db),

            # REGULATORY FEATURES (Yufeed innovation)
            "triggered_regulations": self._get_applicable_regulations(txn, db),
            "aml6d_risk_factors": self._check_aml6d_factors(txn, db),
            "travel_rule_applicable": txn.amount >= 1000,

            # Pattern features
            "similar_txn_count": self._count_similar_transactions(txn, db),
            "counterparty_risk": self._assess_counterparty_risk(txn, db),

            # ... 200+ more features
        }
```

#### 3.2 Network Graph Analysis

**Graph Database Integration:**
```python
# /backend/src/monitoring/network_graph.py

class NetworkAnalyzer:
    """
    Network graph analysis for detecting fraud rings.
    Sardine's "Connections Graph" feature.
    """

    def __init__(self):
        # Could use Neo4j, NetworkX, or build custom
        self.graph = networkx.DiGraph()

    def build_network_graph(
        self,
        user_id: str,
        depth: int = 2,
        db: Session
    ):
        """
        Build network graph for a user.

        Nodes: Users, Devices, IP Addresses, Bank Accounts
        Edges: Transactions, Shared Devices, Shared IPs
        """
        # Get user's transactions
        transactions = db.query(Transaction).filter(
            (Transaction.user_id == user_id) |
            (Transaction.counterparty_id == user_id)
        ).all()

        # Build graph
        for txn in transactions:
            self.graph.add_edge(
                txn.user_id,
                txn.counterparty_id,
                weight=txn.amount,
                timestamp=txn.timestamp,
                txn_id=txn.transaction_id
            )

        # Add device/IP connections
        # ...

    def detect_fraud_ring(
        self,
        min_participants: int = 3,
        min_connections: int = 5
    ) -> List[dict]:
        """
        Detect potential fraud rings using community detection.
        """
        # Use Louvain or other community detection algorithm
        communities = community.louvain_communities(self.graph)

        suspicious_rings = []
        for comm in communities:
            if len(comm) >= min_participants:
                # Analyze ring characteristics
                ring_metrics = self._analyze_ring(comm)
                if ring_metrics["suspicion_score"] > 0.7:
                    suspicious_rings.append({
                        "participants": list(comm),
                        "metrics": ring_metrics,
                        "visualization": self._generate_graph_viz(comm)
                    })

        return suspicious_rings
```

#### 3.3 Risk Scoring ML Models

**Model Training Pipeline:**
```python
# /backend/src/ml/risk_models.py

class RiskScoringModel:
    """
    ML models for transaction risk scoring.
    Trained on features from feature store.
    """

    def __init__(self):
        self.model = None  # XGBoost, Random Forest, etc.
        self.feature_importance = {}

    def train(
        self,
        training_data: pd.DataFrame,
        labels: pd.DataFrame
    ):
        """
        Train risk scoring model on historical data.
        """
        import xgboost as xgb

        # Feature engineering
        X = self._prepare_features(training_data)
        y = labels["is_fraudulent"]

        # Train model
        self.model = xgb.XGBClassifier(
            max_depth=6,
            learning_rate=0.1,
            n_estimators=100,
            objective="binary:logistic"
        )

        self.model.fit(X, y)

        # Calculate feature importance
        self.feature_importance = dict(zip(
            X.columns,
            self.model.feature_importances_
        ))

    def predict_risk(
        self,
        transaction_features: dict
    ) -> dict:
        """
        Predict risk score for a transaction.
        """
        X = pd.DataFrame([transaction_features])

        risk_score = self.model.predict_proba(X)[0][1]

        # Explain prediction using SHAP
        explanation = self._explain_prediction(X)

        return {
            "risk_score": risk_score,
            "risk_level": self._classify_risk(risk_score),
            "top_factors": explanation["top_factors"],
            "confidence": explanation["confidence"]
        }
```

### PHASE 4: Reporting & Compliance (Months 7-8)

#### 4.1 SAR/UAR Filing System

**Implementation:**
```python
# /backend/src/compliance/sar_filing.py

class SARFilingSystem:
    """
    Suspicious Activity Report filing system.
    Integrates with FinCEN (US) and goAML (international).
    """

    def prepare_sar(
        self,
        case_id: int,
        db: Session
    ) -> dict:
        """
        Prepare SAR from case investigation.
        """
        case = db.query(Case).filter(Case.id == case_id).first()

        # Generate narrative using AI agent
        sar_agent = SARNarrativeAgent()
        narrative = sar_agent.generate_sar_narrative(
            case,
            case.related_alerts,
            case.related_transactions,
            db
        )

        # Structure SAR data
        sar = {
            "filing_institution": self._get_institution_info(),
            "subject_information": self._get_subject_info(case, db),
            "suspicious_activity": {
                "narrative": narrative["narrative"],
                "activity_dates": self._get_activity_dates(case),
                "total_amount": self._calculate_total_amount(case, db),
                "transaction_count": len(case.related_transactions)
            },
            "regulatory_basis": {
                "cited_regulations": narrative["cited_regulations"],
                "violations": case.regulatory_violations
            },
            "supporting_documents": self._gather_documents(case, db)
        }

        return sar

    def file_sar(
        self,
        sar_data: dict,
        jurisdiction: str = "EU"
    ) -> dict:
        """
        File SAR with appropriate authority.
        """
        if jurisdiction == "US":
            return self._file_with_fincen(sar_data)
        elif jurisdiction == "EU":
            return self._file_with_fiu(sar_data)  # National FIU
        else:
            return self._file_with_goaml(sar_data)
```

#### 4.2 Regulatory Reporting Dashboard

**Analytics & Reporting:**
```python
# /backend/src/api/reporting.py

@router.get("/reporting/dashboard")
def get_reporting_dashboard(
    date_from: datetime,
    date_to: datetime,
    db: Session = Depends(get_db)
):
    """
    Compliance reporting dashboard.
    """
    return {
        "alert_metrics": {
            "total_alerts": get_alert_count(date_from, date_to, db),
            "by_severity": get_alerts_by_severity(date_from, date_to, db),
            "by_type": get_alerts_by_type(date_from, date_to, db),
            "resolution_time_avg": get_avg_resolution_time(date_from, date_to, db)
        },
        "case_metrics": {
            "open_cases": get_open_case_count(db),
            "closed_cases": get_closed_case_count(date_from, date_to, db),
            "sar_filed": get_sar_count(date_from, date_to, db)
        },
        "regulatory_coverage": {
            "monitored_regulations": get_monitored_regulation_count(db),
            "rules_derived_from_regs": get_rule_coverage(db),
            "recent_regulatory_updates": get_recent_updates(date_from, db)
        },
        "risk_metrics": {
            "high_risk_users": get_high_risk_user_count(db),
            "transaction_volume": get_transaction_volume(date_from, date_to, db),
            "average_risk_score": get_avg_risk_score(date_from, date_to, db)
        }
    }
```

### PHASE 5: User Interface (Months 8-9)

#### 5.1 Transaction Monitoring Dashboard

**New Frontend Pages:**

```typescript
// /frontend/src/app/monitoring/page.tsx

export default function MonitoringDashboard() {
  return (
    <div className="monitoring-dashboard">
      <h1>Transaction Monitoring</h1>

      {/* Real-time metrics */}
      <div className="metrics-row">
        <MetricCard
          title="Active Alerts"
          value={activeAlerts}
          trend="+12%"
          icon={<AlertCircle />}
        />
        <MetricCard
          title="Pending Reviews"
          value={pendingReviews}
          icon={<Clock />}
        />
        <MetricCard
          title="High Risk Transactions"
          value={highRiskCount}
          icon={<AlertTriangle />}
        />
      </div>

      {/* Alert queue */}
      <AlertQueue
        alerts={alerts}
        onAlertClick={handleAlertClick}
        onBulkAction={handleBulkAction}
      />

      {/* Real-time transaction feed */}
      <TransactionFeed
        transactions={realtimeTransactions}
        highlightRisky={true}
      />
    </div>
  );
}
```

#### 5.2 Case Management Interface

```typescript
// /frontend/src/app/cases/[caseId]/page.tsx

export default function CaseDetailPage({ params }: { params: { caseId: string } }) {
  return (
    <div className="case-detail">
      <CaseHeader case={caseData} />

      {/* Investigation timeline */}
      <InvestigationTimeline events={caseData.events} />

      {/* Related alerts */}
      <RelatedAlerts alerts={caseData.alerts} />

      {/* Transaction analysis */}
      <TransactionAnalysis transactions={caseData.transactions} />

      {/* REGULATORY CONTEXT (Yufeed Innovation) */}
      <RegulatoryContext
        regulations={caseData.applicable_regulations}
        violations={caseData.regulatory_violations}
      />

      {/* Network graph visualization */}
      <NetworkGraphView userId={caseData.subject_id} />

      {/* SAR preparation */}
      {caseData.outcome === "sar_required" && (
        <SARPreparationPanel
          caseId={caseData.id}
          onGenerateNarrative={handleGenerateNarrative}
          onFileSAR={handleFileSAR}
        />
      )}

      {/* Action buttons */}
      <CaseActions
        onEscalate={handleEscalate}
        onClose={handleClose}
        onReassign={handleReassign}
      />
    </div>
  );
}
```

#### 5.3 Rules Configuration UI

```typescript
// /frontend/src/app/rules/page.tsx

export default function RulesManagement() {
  return (
    <div className="rules-management">
      <h1>Monitoring Rules</h1>

      {/* Rule library */}
      <RuleLibrary
        rules={rules}
        categories={ruleCategories}
        onToggleRule={handleToggleRule}
        onEditRule={handleEditRule}
      />

      {/* Rule builder (no-code) */}
      <RuleBuilder
        onSaveRule={handleSaveRule}
        featureOptions={availableFeatures}
        regulatoryContext={regulations}
      />

      {/* Rule performance */}
      <RulePerformance
        rules={rules}
        metrics={{
          alert_count: true,
          true_positive_rate: true,
          false_positive_rate: true
        }}
      />

      {/* YUFEED INNOVATION: Auto-generate rules from regulations */}
      <RegulationBasedRuleGenerator
        regulation={selectedRegulation}
        onGenerateRules={handleGenerateRules}
      />
    </div>
  );
}
```

---

## PART 5: IMPLEMENTATION ROADMAP

### Timeline & Resources

| Phase | Duration | Team Size | Key Deliverables |
|-------|----------|-----------|------------------|
| **Phase 1: Foundation** | 2 months | 2 engineers | Transaction DB, ingestion API, basic rules engine |
| **Phase 2: AI & Automation** | 2 months | 2 engineers + 1 ML | AI agents, workflows, alert automation |
| **Phase 3: Advanced Features** | 2 months | 3 engineers + 1 ML | Feature store, ML models, network analysis |
| **Phase 4: Reporting** | 1 month | 1 engineer | SAR filing, regulatory reports |
| **Phase 5: UI** | 1 month | 1 frontend engineer | Dashboards, case management UI |
| **Testing & QA** | 1 month | 2 QA + all engineers | Load testing, security, compliance validation |

**Total: 9 months, Team of 4-5 engineers**

### Budget Estimate

| Category | Cost |
|----------|------|
| **Engineering** (4 engineers × 9 months) | $360,000 - $540,000 |
| **Infrastructure** (Cloud, DB, AI APIs) | $10,000 - $20,000/mo |
| **Third-party Data** (If adding data enrichment) | $5,000 - $15,000/mo |
| **Compliance/Legal Review** | $20,000 - $40,000 |
| **Total (9 months)** | **$500,000 - $700,000** |

---

## PART 6: YUFEED'S COMPETITIVE ADVANTAGE

### What Makes Yufeed + Sardine Features Unique?

**1. Regulatory Intelligence + Transaction Monitoring**
```
Sardine: "This transaction is suspicious"
Yufeed 2.0: "This transaction violates AML6D Article 7(a)(ii)
             enacted on [date] with deadline [date]"
```

**2. Auto-Generated Rules from Regulations**
```
When new EU regulation published:
1. Yufeed extracts obligations
2. AI generates monitoring rules
3. Rules auto-activate with regulatory citations
4. Compliance teams see "why" behind every alert
```

**3. Context-Aware Case Management**
```
Every alert includes:
- Transaction analysis (Sardine-style)
- Applicable regulations (Yufeed)
- Recent regulatory changes
- Impact assessment
- SAR narrative with regulatory citations
```

**4. Unified Compliance Platform**
```
Single Platform:
- Document monitoring (existing)
- Transaction monitoring (new)
- Case management (new)
- Regulatory reporting (enhanced)
```

---

## PART 7: RISKS & MITIGATION

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Real-time processing performance** | HIGH | MEDIUM | Use Redis/Kafka for streaming, optimize DB queries |
| **False positive rate too high** | HIGH | HIGH | Implement feedback loop, continuous model tuning |
| **ML model accuracy** | MEDIUM | MEDIUM | Start with rules-based, add ML incrementally |
| **Data privacy (GDPR)** | HIGH | LOW | Implement data minimization, encryption at rest |
| **Integration complexity** | MEDIUM | HIGH | Build API-first, modular architecture |

### Business Risks

| Risk | Mitigation |
|------|------------|
| **Scope creep** | Strict phase gates, MVP approach |
| **Regulatory compliance** | Early legal review, compliance officer input |
| **Market competition** | Focus on unique value (regulatory intelligence) |
| **Customer adoption** | Beta program with existing Yufeed customers |

---

## PART 8: SUCCESS METRICS

### Phase 1 Success Criteria (Months 1-2)
- [ ] Ingest 10,000+ transactions
- [ ] 500+ monitoring rules active
- [ ] Generate 100+ alerts
- [ ] Alert-to-review latency < 5 minutes

### Phase 2 Success Criteria (Months 3-4)
- [ ] AI agent triages 70%+ of alerts automatically
- [ ] False positive rate < 30%
- [ ] Case creation time < 2 minutes
- [ ] SAR narrative generation < 30 seconds

### Phase 3 Success Criteria (Months 5-6)
- [ ] Risk scoring latency < 500ms
- [ ] 1,000+ features calculated per transaction
- [ ] Fraud ring detection on 10,000+ user network
- [ ] ML model accuracy > 85%

### Phase 4-5 Success Criteria (Months 7-9)
- [ ] 10+ SARs filed successfully
- [ ] Compliance dashboard live
- [ ] User satisfaction score > 8/10
- [ ] Time to investigate case reduced by 50%

---

## PART 9: NEXT STEPS

### Immediate Actions (This Week)

1. **Stakeholder Buy-in**
   - Present this plan to leadership
   - Get budget approval
   - Align on timeline

2. **Technical Validation**
   - Prototype transaction ingestion API
   - Test rule evaluation performance
   - Validate AI agent approach with Claude API

3. **Requirements Gathering**
   - Interview compliance officers
   - Document exact SAR/UAR requirements
   - Define rule prioritization

### Month 1 Kickoff

1. **Team Formation**
   - Hire/assign 2 backend engineers
   - Engage ML consultant
   - Onboard compliance SME

2. **Technical Setup**
   - Set up development environment
   - Design database schema
   - Create project repository

3. **Phase 1 Sprint Planning**
   - Break down into 2-week sprints
   - Define user stories
   - Set up CI/CD pipeline

---

## CONCLUSION

Integrating Sardine.ai-inspired features into Yufeed creates a **unique competitive position**:

> **"The world's first compliance platform that monitors regulations AND enforces them through real-time transaction surveillance"**

**Key Innovations:**
1. **Regulation-to-Rule Automation** - Auto-generate monitoring rules from EU regulations
2. **Context-Enriched Alerts** - Every alert cites specific legal requirements
3. **AI-Powered SAR Writing** - Generate reports with regulatory citations
4. **Unified Compliance View** - Single platform for documents + transactions

**Timeline:** 9 months
**Investment:** $500K-$700K
**ROI:** Premium AML platform in growing €50B+ RegTech market

---

## APPENDICES

### Appendix A: API Examples

**Transaction Ingestion:**
```bash
POST /api/transactions/ingest
{
  "transaction_id": "TXN-123456",
  "user_id": "USER-789",
  "amount": 9500.00,
  "currency": "EUR",
  "transaction_type": "wire_transfer",
  "counterparty_id": "USER-456",
  "country_code": "IR",
  "timestamp": "2026-01-08T10:30:00Z"
}
```

**Get Alert Queue:**
```bash
GET /api/alerts?status=pending&severity=high&limit=50
```

**Trigger AI Triage:**
```bash
POST /api/alerts/123/triage
{
  "agent_type": "auto_triage",
  "auto_resolve": true
}
```

### Appendix B: Rule DSL Example

```json
{
  "rule_id": "STRUCTURING_MULTIPLE_BELOW_THRESHOLD",
  "conditions": {
    "type": "aggregate",
    "timeframe": "24h",
    "filters": {
      "amount": {"gte": 8000, "lt": 10000},
      "user_id": "{current_user}"
    },
    "aggregation": {
      "function": "count",
      "threshold": 3
    }
  },
  "actions": [
    {
      "type": "create_alert",
      "severity": "high",
      "description": "Multiple transactions just below €10,000 threshold"
    },
    {
      "type": "flag_user",
      "risk_increase": 20
    }
  ]
}
```

### Appendix C: Data Flow Diagram

```
┌─────────────┐
│ Client App  │
│ (Bank UI)   │
└──────┬──────┘
       │ Transaction Event
       ▼
┌─────────────┐
│ Ingestion   │
│ API         │◀─── Batch upload also supported
└──────┬──────┘
       │
       ▼
┌─────────────┐    ┌──────────────┐
│ Transaction │───▶│ Feature      │
│ DB          │    │ Calculation  │
└─────────────┘    └──────┬───────┘
                          │
                          ▼
                   ┌──────────────┐
                   │ Rules Engine │◀─── Yufeed regulations DB
                   └──────┬───────┘
                          │
                          ▼
                   ┌──────────────┐
                   │ Alerts       │
                   └──────┬───────┘
                          │
                          ▼
                   ┌──────────────┐
                   │ AI Agent     │
                   │ Triage       │
                   └──────┬───────┘
                          │
              ┌───────────┴───────────┐
              │                       │
              ▼                       ▼
       ┌────────────┐         ┌─────────────┐
       │ Auto-Close │         │ Case        │
       └────────────┘         │ Management  │
                              └─────────────┘
```

---

**Document End**

**Sources:**
- [Sardine.ai Platform](https://www.sardine.ai/platform)
- [Sardine AML Compliance](https://www.sardine.ai/aml-compliance)
- [Real-time AI Transaction Monitoring](https://www.sardine.ai/blog/real-time-ai-and-machine-learning-for-transaction-monitoring)
- [Device Intelligence & Behavioral Biometrics](https://www.sardine.ai/device-and-behavior)
- [Machine Learning Feature Store](https://www.sardine.ai/blog/machine-learning-feature-store-for-fraud-and-compliance)
- [Case Management Workflow Automation](https://www.sardine.ai/blog/series-c-announcement)
- [2025 Fraud & Compliance Predictions](https://www.sardine.ai/blog/2025-fraud-compliance-predictions)
