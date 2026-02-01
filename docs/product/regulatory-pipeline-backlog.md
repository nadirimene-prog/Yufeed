# Regulatory Intelligence Pipeline - Product Backlog

**Document Type:** Sprint Planning Backlog  
**Version:** 1.0  
**Date:** 2026-01-29  
**Prepared by:** Product Owner, Scrum Master, CTO Panel

---

## Panel Discussion Summary

### Participants

| Role | Perspective | Key Contributions |
|------|-------------|-------------------|
| **Product Owner (PO)** | Business value, customer needs | User stories, acceptance criteria, prioritization |
| **Scrum Master (SM)** | Process, impediments, team health | Sprint structure, DoD, velocity planning |
| **CTO** | Technical feasibility, architecture | Technical tasks, dependencies, risk flags |

### Panel Decisions

**Sprint Length:** 2 weeks  
**Team Capacity:** 40 story points/sprint (assuming 4 developers)  
**Total Estimated Points:** ~180 points across 10 sprints  
**Target Completion:** 20 weeks (with buffer for unforeseen issues)

---

## Epic Structure

```
EPIC-001: Regulatory Document Ingestion
EPIC-002: AI Analysis & Obligation Extraction
EPIC-003: Regulatory Alert Pipeline
EPIC-004: Policy Management & AI Writer
EPIC-005: Internal Rules & System Enforcement
EPIC-006: Impact Assessment & Action Items
EPIC-007: Deadline Monitoring
EPIC-008: Audit Trail & RBAC
EPIC-009: Sentinel Dashboard Integration
EPIC-010: Operational Excellence (Optional)
```

---

## Sprint Allocation Overview

| Sprint | Weeks | Epics | Focus | Points |
|--------|-------|-------|-------|--------|
| Sprint 1 | 1-2 | EPIC-001 | Ingestion Foundation | 34 |
| Sprint 2 | 3-4 | EPIC-002 | AI Analysis | 38 |
| Sprint 3 | 5-6 | EPIC-003 | Alert Pipeline | 32 |
| Sprint 4 | 7-8 | EPIC-004 | Policy Management | 42 |
| Sprint 5 | 9-10 | EPIC-005 | Internal Rules | 36 |
| Sprint 6 | 11-12 | EPIC-006, 007 | Impact + Deadlines | 34 |
| Sprint 7 | 13-14 | EPIC-008 | Audit & RBAC | 30 |
| Sprint 8 | 15-16 | EPIC-009 | Dashboard Integration | 28 |
| Sprint 9 | 17-18 | Bug fixes, polish | Stabilization | 20 |
| Sprint 10 | 19-20 | EPIC-010 | Operational Excellence | 24 |

---

## EPIC-001: Regulatory Document Ingestion

### US-001: EUR-Lex RSS Feed Ingestion
**As a** Compliance Officer  
**I want** EUR-Lex Official Journal entries to be automatically ingested weekly  
**So that** I don't miss new EU regulations

**Acceptance Criteria:**
- [ ] RSS fetcher retrieves entries from EUR-Lex OJ L-series feed
- [ ] Documents are deduplicated by CELEX number
- [ ] Ingestion runs on configurable schedule (default: weekly Sunday 3AM UTC)
- [ ] Failed ingestions create admin alert
- [ ] Ingestion run logged in `ingestion_runs` table

**Story Points:** 5  
**Sprint:** 1  
**Dependencies:** None  
**Tech Notes (CTO):** Extend existing `RSSFetcher` class

---

### US-002: EUR-Lex Search Ingestion
**As a** Compliance Officer  
**I want** EUR-Lex searched for AML/CFT/MiCA keywords weekly  
**So that** I capture regulations not published in OJ

**Acceptance Criteria:**
- [ ] Search queries configurable in `INGESTION_CONFIG`
- [ ] Supports EN, FR, DE language variants
- [ ] Results merged with RSS to avoid duplicates
- [ ] Search terms: "anti-money laundering", "crypto-asset", "MiCA", "PSD2"

**Story Points:** 8  
**Sprint:** 1  
**Dependencies:** US-001  
**Tech Notes (CTO):** Use `EurLexSearchFetcher` class

---

### US-003: OJ Act-by-Act Metadata Extraction
**As a** Compliance Officer  
**I want** Official Journal act-by-act records extracted via SPARQL  
**So that** I have granular act-level tracking

**Acceptance Criteria:**
- [ ] SPARQL queries CELLAR endpoint for OJ acts
- [ ] Extracts: act_id, signature_id, OJ reference, date
- [ ] Stores in `official_journal_acts` table
- [ ] Links to parent `legal_documents`

**Story Points:** 8  
**Sprint:** 1  
**Dependencies:** None  
**Tech Notes (CTO):** New `OJActFetcher` class, uses `CellarClient`

---

### US-004: Content Backfill for Metadata-Only Documents
**As a** System  
**I want** documents with missing full_text to be queued for content extraction  
**So that** AI analysis can run on complete documents

**Acceptance Criteria:**
- [ ] Monthly batch job identifies `full_text IS NULL` documents
- [ ] Fetches content from EUR-Lex/Légifrance
- [ ] Updates `legal_document_texts` table
- [ ] Marks document for re-analysis

**Story Points:** 8  
**Sprint:** 1  
**Dependencies:** US-001, US-002, US-003  
**Tech Notes (CTO):** New `BatchContentFetcher` class

---

### US-005: Légifrance Feed Integration
**As a** Compliance Officer  
**I want** French regulations from JORF ingested automatically  
**So that** I track France-specific AML requirements

**Acceptance Criteria:**
- [ ] Légifrance RSS feed parsed weekly
- [ ] Filtered for AML/financial services keywords
- [ ] French language documents stored with `language=fr`
- [ ] Links to parent EU regulations where applicable

**Story Points:** 5  
**Sprint:** 1  
**Dependencies:** US-001  
**Tech Notes (CTO):** Extend `LegifranceFetcher`

---

### US-006: Ingestion Manager Orchestration
**As a** System Administrator  
**I want** a unified ingestion manager that orchestrates all sources  
**So that** I can monitor and control the ingestion pipeline

**Acceptance Criteria:**
- [ ] `IngestionManager.run_all()` executes all configured sources
- [ ] Sources can be enabled/disabled via config
- [ ] Dashboard shows last run status per source
- [ ] CLI command: `python -m ingestion.manager --run-all`

**Story Points:** 5  
**Sprint:** 1  
**Dependencies:** US-001 through US-005  
**SM Notes:** This is the Sprint 1 demo story

---

## EPIC-002: AI Analysis & Obligation Extraction

### US-007: Trigger AI Analysis for New Documents
**As a** System  
**I want** newly ingested documents to automatically trigger AI analysis  
**So that** obligations are extracted without manual intervention

**Acceptance Criteria:**
- [ ] `processor.py` calls `analyzer.analyze_document()` for new docs
- [ ] Analysis runs even for metadata-only documents (title/CELEX)
- [ ] Analysis skipped if document already analyzed (idempotency)
- [ ] Failed analysis logged with error details

**Story Points:** 5  
**Sprint:** 2  
**Dependencies:** EPIC-001 complete  
**Tech Notes (CTO):** Modify `_handle_new_doc()` in processor.py

---

### US-008: Obligation Extraction from Regulatory Text
**As a** Compliance Officer  
**I want** AI to extract specific obligations from regulation articles  
**So that** I know exactly what compliance actions are required

**Acceptance Criteria:**
- [ ] AI extracts: obligation_text, article_ref, applicability, effective_date
- [ ] Each obligation gets unique `obligation_id` (CELEX + article)
- [ ] Stored in `regulatory_obligations` table
- [ ] Average 3-5 obligations per relevant document
- [ ] Extraction accuracy >80% (validated in Sprint 2 demo)

**Story Points:** 13  
**Sprint:** 2  
**Dependencies:** US-007  
**Tech Notes (CTO):** Uses Anthropic Claude, prompt in `analyzer.py`

---

### US-009: Document Classification and Risk Scoring
**As a** Compliance Officer  
**I want** documents classified by type and risk level  
**So that** I can prioritize my review queue

**Acceptance Criteria:**
- [ ] Classification: regulation, directive, decision, guideline
- [ ] Risk levels: critical, high, medium, low, minimal
- [ ] Subject matter tags: AML, MiCA, PSD2, GDPR, DORA
- [ ] Stored in `legal_documents` fields

**Story Points:** 8  
**Sprint:** 2  
**Dependencies:** US-007  
**Tech Notes (CTO):** Already exists in analyzer, verify working

---

### US-010: Scope Tag Inference
**As a** Compliance Officer  
**I want** obligations tagged with relevant scope  
**So that** I can filter by business area (PSP, EMI, CASP)

**Acceptance Criteria:**
- [ ] AI infers scope_tags from obligation text
- [ ] Tags: PSP, EMI, CASP, credit_institution, insurance
- [ ] Stored in `regulatory_obligations.scope_tags` (JSON array)
- [ ] Filterable in dashboard

**Story Points:** 5  
**Sprint:** 2  
**Dependencies:** US-008  
**Tech Notes (CTO):** Add to obligation extraction prompt

---

### US-011: Effective Date Parsing
**As a** Compliance Officer  
**I want** AI to extract and normalize effective dates  
**So that** I know when obligations become enforceable

**Acceptance Criteria:**
- [ ] Parses dates in various formats (relative, absolute)
- [ ] Handles "X months after publication" patterns
- [ ] Stored as `DateTime` in `effective_date` field
- [ ] Null if no date found (manual entry required)

**Story Points:** 5  
**Sprint:** 2  
**Dependencies:** US-008  
**Tech Notes (CTO):** NLP date parsing, handle EU date formats

---

### US-012: Analysis Cost Monitoring
**As a** System Administrator  
**I want** Anthropic API costs tracked per analysis  
**So that** I can monitor and control AI expenses

**Acceptance Criteria:**
- [ ] Token count logged per API call
- [ ] Cost calculated based on model pricing
- [ ] Daily/weekly cost summary available
- [ ] Alert if daily spend exceeds threshold

**Story Points:** 3  
**Sprint:** 2  
**Dependencies:** US-008  
**Tech Notes (CTO):** Add to analyzer, store in new `ai_usage_logs` table

---

### US-012A: RAG Chunk Indexing & Hybrid Retrieval
**As a** Compliance Officer  
**I want** regulatory text indexed into semantic chunks with hybrid retrieval  
**So that** I can ask natural language questions grounded in exact citations

**Acceptance Criteria:**
- [ ] Legal documents chunked into `legal_chunks` table (article-aware when possible)
- [ ] Chunks indexed into OpenSearch with vector + BM25 fields
- [ ] Hybrid retrieval supports compliance_domain/risk_level filters
- [ ] Ingestion + content backfill trigger RAG indexing automatically
- [ ] Batch script available to (re)index all documents

**Story Points:** 5  
**Sprint:** 2  
**Dependencies:** US-007, US-008  
**Tech Notes (CTO):** New `rag_indexer.py`, `search_rag_chunks`, `LegalChunk` model + migration

---

## EPIC-003: Regulatory Alert Pipeline

### US-013: Create Alert on Obligation Approval
**As a** Compliance Officer  
**I want** an alert created when I approve an obligation without a linked policy  
**So that** I remember to link it to the appropriate policy

**Acceptance Criteria:**
- [ ] Alert type: `policy_update_required`
- [ ] Created in `alerts` table when obligation approved with `linked_policy_id=NULL`
- [ ] Severity based on days until effective_date
- [ ] Alert resolved when policy linked

**Story Points:** 8  
**Sprint:** 3  
**Dependencies:** EPIC-002 complete  
**Tech Notes (CTO):** New `regulatory_alerts.py` module

---

### US-014: Regulatory Deadline Alert
**As a** Compliance Officer  
**I want** alerts for approaching regulatory deadlines  
**So that** I don't miss compliance dates

**Acceptance Criteria:**
- [ ] Alert type: `regulatory_deadline`
- [ ] Created when obligation has `effective_date` within 90 days
- [ ] Severity: low(90d), medium(60d), high(30d), critical(7d)
- [ ] One alert per obligation (deduplicated)

**Story Points:** 5  
**Sprint:** 3  
**Dependencies:** US-013  
**Tech Notes (CTO):** Part of `regulatory_alerts.py`

---

### US-015: Internal Rule Required Alert
**As a** Compliance Officer  
**I want** alerts when approved obligations lack internal rules  
**So that** I ensure policies are enforced operationally

**Acceptance Criteria:**
- [ ] Alert type: `internal_rule_required`
- [ ] Triggered when PolicySection approved but no InternalRule exists
- [ ] Includes obligation details and suggested MonitoringRule config
- [ ] Alert resolved when InternalRule created

**Story Points:** 5  
**Sprint:** 3  
**Dependencies:** US-013  
**Tech Notes (CTO):** Dependent on EPIC-005

---

### US-016: Alert Resolution Workflow
**As a** Compliance Officer  
**I want** to resolve alerts when actions are completed  
**So that** my alert queue stays clean

**Acceptance Criteria:**
- [ ] API: `POST /api/alerts/{id}/resolve`
- [ ] Auto-resolution on certain actions (policy link, rule creation)
- [ ] Resolution logged with user and timestamp
- [ ] Resolved alerts queryable with filter

**Story Points:** 5  
**Sprint:** 3  
**Dependencies:** US-013, US-014, US-015  

---

### US-017: AI Policy Suggestion in Alert
**As a** Compliance Officer  
**I want** the alert to suggest matching policies  
**So that** I can quickly link obligations to existing policies

**Acceptance Criteria:**
- [ ] Alert payload includes `suggested_policies` array
- [ ] Policies ranked by `match_score` (0-1)
- [ ] Match based on regulatory basis overlap + keyword similarity
- [ ] Top 3 suggestions shown

**Story Points:** 8  
**Sprint:** 3  
**Dependencies:** US-013  
**Tech Notes (CTO):** Semantic similarity using embeddings or keyword matching

---

## EPIC-004: Policy Management & AI Writer

### US-018: Standard Policy Template Library
**As a** Compliance Officer  
**I want** a library of standard EMI+CASP policy templates  
**So that** I don't create policies from scratch

**Acceptance Criteria:**
- [ ] 35-40 pre-seeded policy templates
- [ ] Categories: AML/CFT, EMI, CASP, Governance, GDPR, HR
- [ ] Each template has: name, owner, regulatory_basis, review_frequency
- [ ] API: `GET /api/policies/templates`

**Story Points:** 8  
**Sprint:** 4  
**Dependencies:** None  
**Tech Notes (CTO):** Seed script `seed_policy_templates.py`

---

### US-019: Instantiate Policy from Template
**As a** Compliance Officer  
**I want** to create a policy from a template  
**So that** I start with a standard structure

**Acceptance Criteria:**
- [ ] API: `POST /api/policies/from-template/{template_id}`
- [ ] Creates new `PolicyDocument` with template values
- [ ] Status: `draft`
- [ ] User can customize name, owner before creation

**Story Points:** 5  
**Sprint:** 4  
**Dependencies:** US-018  

---

### US-020: Link Obligation to Policy
**As a** Compliance Officer  
**I want** to link an approved obligation to an existing policy  
**So that** the policy addresses the regulatory requirement

**Acceptance Criteria:**
- [ ] API: `POST /api/policies/{id}/link-obligation/{obligation_id}`
- [ ] Updates `RegulatoryObligation.linked_policy_id`
- [ ] Triggers AI policy section generation (US-021)
- [ ] Resolves `policy_update_required` alert

**Story Points:** 5  
**Sprint:** 4  
**Dependencies:** US-019, US-013  

---

### US-021: AI-Generated Policy Section
**As a** Compliance Officer  
**I want** AI to draft a policy section when I link an obligation  
**So that** I have ready-to-review policy text

**Acceptance Criteria:**
- [ ] AI generates section title + content from obligation text
- [ ] Uses first-person voice ("We implement...", "Yufeed maintains...")
- [ ] Includes regulatory reference in section
- [ ] Status: `draft` (requires human approval)
- [ ] Matches tone of existing policy sections

**Story Points:** 13  
**Sprint:** 4  
**Dependencies:** US-020  
**Tech Notes (CTO):** New `policy_writer.py` module, uses Claude

---

### US-022: Edit AI-Generated Section
**As a** Compliance Officer  
**I want** to edit the AI-generated policy section  
**So that** I can correct or enhance the draft

**Acceptance Criteria:**
- [ ] API: `PATCH /api/policies/{id}/sections/{section_id}`
- [ ] Editable fields: title, content
- [ ] Version history preserved
- [ ] Last edited by/at tracked

**Story Points:** 5  
**Sprint:** 4  
**Dependencies:** US-021  

---

### US-023: Approve Policy Section
**As a** MLRO  
**I want** to approve a policy section for publication  
**So that** it becomes part of the official policy

**Acceptance Criteria:**
- [ ] API: `POST /api/policies/{id}/sections/{section_id}/approve`
- [ ] Changes status to `approved`
- [ ] Requires MLRO role (RBAC)
- [ ] Logs approval in audit trail
- [ ] Triggers internal rule check (US-015)

**Story Points:** 5  
**Sprint:** 4  
**Dependencies:** US-022, US-045 (RBAC)  

---

### US-024: Export Policy as Markdown
**As a** MLRO  
**I want** to export a policy as a formatted document  
**So that** I can share with supervisors

**Acceptance Criteria:**
- [ ] API: `GET /api/policies/{id}/export`
- [ ] Returns Markdown with full policy structure
- [ ] Includes compliance matrix (obligation → section mapping)
- [ ] Shows regulatory references per section
- [ ] Headers: Version, Owner, Last Reviewed, Next Review

**Story Points:** 8  
**Sprint:** 4  
**Dependencies:** US-023  
**SM Notes:** Sprint 4 demo deliverable

---

### US-025: Compliance Matrix View
**As a** Auditor  
**I want** to see which obligations are addressed by which policy sections  
**So that** I can verify compliance coverage

**Acceptance Criteria:**
- [ ] API: `GET /api/policies/{id}/compliance-matrix`
- [ ] Returns table: Obligation | Regulation | Article | Section | Status
- [ ] Coverage status: ✅ Addressed, ⚠️ Partial, ❌ Not Addressed
- [ ] Exportable as CSV

**Story Points:** 5  
**Sprint:** 4  
**Dependencies:** US-020  

---

## EPIC-005: Internal Rules & System Enforcement

### US-026: Create Internal Rule from Obligation
**As a** Compliance Officer  
**I want** to create an internal control rule from an obligation  
**So that** the policy is operationally enforced

**Acceptance Criteria:**
- [ ] API: `POST /api/internal-rules/`
- [ ] Links to: obligation_id, policy_section_id
- [ ] Fields: name, description, control_owner, status
- [ ] Status: `draft` → `in_review` → `approved` → `implemented`

**Story Points:** 5  
**Sprint:** 5  
**Dependencies:** US-023  

---

### US-027: AI Monitoring Rule Suggestion
**As a** Technology Officer  
**I want** AI to suggest monitoring rule configuration  
**So that** I know what parameters to set in the TM system

**Acceptance Criteria:**
- [ ] AI generates JSON config from obligation text
- [ ] Includes: conditions, thresholds, severity, alert_message
- [ ] Example: `{field: "transaction_count", operator: ">", value: 10, window: "1h"}`
- [ ] Displayed when creating internal rule

**Story Points:** 13  
**Sprint:** 5  
**Dependencies:** US-026  
**Tech Notes (CTO):** New `monitoring_rule_suggester.py`

---

### US-028: Map Internal Rule to Monitoring Rule
**As a** Technology Officer  
**I want** to link an internal rule to a monitoring rule ID  
**So that** the TM system enforces the regulation

**Acceptance Criteria:**
- [ ] API: `POST /api/internal-rules/{id}/mappings`
- [ ] Creates `InternalRuleMapping` with `monitoring_rule_id`
- [ ] Validates monitoring_rule_id exists
- [ ] Resolves `internal_rule_required` alert

**Story Points:** 5  
**Sprint:** 5  
**Dependencies:** US-027  

---

### US-029: Internal Rule Status Management
**As a** Compliance Officer  
**I want** to track internal rule implementation status  
**So that** I know what's pending

**Acceptance Criteria:**
- [ ] Status transitions: draft → in_review → approved → implemented → archived
- [ ] Each transition logged with user/timestamp
- [ ] Dashboard filter by status
- [ ] Bulk status updates supported

**Story Points:** 5  
**Sprint:** 5  
**Dependencies:** US-026  

---

### US-030: Auto-Transition to Implemented
**As a** System  
**I want** obligations to auto-transition to `implemented` status  
**So that** I have accurate compliance tracking

**Acceptance Criteria:**
- [ ] Triggered when all conditions met:
  - linked_policy_id IS NOT NULL
  - linked_policy.status = 'active'
  - InternalRule.status = 'implemented'
  - InternalRuleMapping exists
- [ ] Logged as `auto_implemented` in audit trail

**Story Points:** 8  
**Sprint:** 5  
**Dependencies:** US-028, US-026  
**Tech Notes (CTO):** `check_implementation_status()` function

---

## EPIC-006: Impact Assessment & Action Items

### US-031: Auto-Create Impact Assessment
**As a** System  
**I want** impact assessments created during document analysis  
**So that** I understand regulation effects immediately

**Acceptance Criteria:**
- [ ] Created in `impact_assessments` table
- [ ] Fields: overall_impact_level, affected_areas, requires_policy_updates
- [ ] Linked to `legal_documents.id`
- [ ] Impact level derived from AI risk classification

**Story Points:** 8  
**Sprint:** 6  
**Dependencies:** EPIC-002 complete  

---

### US-032: Generate Action Items from Obligations
**As a** Compliance Officer  
**I want** implementation tasks auto-generated from obligations  
**So that** I have a clear implementation checklist

**Acceptance Criteria:**
- [ ] AI generates 2-4 action items per obligation
- [ ] Fields: title, assigned_to, business_area, priority, target_date
- [ ] Target_date calculated from obligation effective_date
- [ ] Stored in `action_items` table

**Story Points:** 13  
**Sprint:** 6  
**Dependencies:** US-031  
**Tech Notes (CTO):** New `action_item_generator.py`

---

### US-033: Action Item Management
**As a** Compliance Officer  
**I want** to update action item status and assignment  
**So that** I can track implementation progress

**Acceptance Criteria:**
- [ ] API: `PATCH /api/actions/{id}`
- [ ] Status: not_started, in_progress, blocked, completed, deferred
- [ ] Reassignment to different owner
- [ ] Comments/notes on action items

**Story Points:** 5  
**Sprint:** 6  
**Dependencies:** US-032  

---

## EPIC-007: Deadline Monitoring

### US-034: Daily Deadline Check Job
**As a** System  
**I want** a daily job checking for approaching deadlines  
**So that** alerts are generated proactively

**Acceptance Criteria:**
- [ ] Celery task runs daily at 8:00 AM UTC
- [ ] Queries obligations with effective_date in next 90 days
- [ ] Creates alerts at 90, 60, 30, 7, 1 day thresholds
- [ ] Skips already-alerted obligations (idempotent)

**Story Points:** 8  
**Sprint:** 6  
**Dependencies:** US-014  
**Tech Notes (CTO):** New `deadline_monitor.py`

---

### US-035: Overdue Obligation Detection
**As a** MLRO  
**I want** critical alerts for overdue obligations  
**So that** I can address compliance failures urgently

**Acceptance Criteria:**
- [ ] Detects obligations where effective_date < NOW()
- [ ] Status not in ('implemented', 'rejected')
- [ ] Creates `regulatory_overdue` alert with critical severity
- [ ] Includes days_overdue in alert

**Story Points:** 5  
**Sprint:** 6  
**Dependencies:** US-034  

---

### US-036: Email Escalation for Overdue
**As a** MLRO  
**I want** email notifications for obligations >7 days overdue  
**So that** I'm aware even if not checking dashboard

**Acceptance Criteria:**
- [ ] Celery task: `escalate_critical_overdue()`
- [ ] Groups overdue by policy owner
- [ ] Sends email with list of overdue obligations
- [ ] Subject: "URGENT: X Overdue Regulatory Obligations"

**Story Points:** 5  
**Sprint:** 6 (or Sprint 10 as optional)  
**Dependencies:** US-035  
**Tech Notes (CTO):** Requires email service integration

---

## EPIC-008: Audit Trail & RBAC

### US-037: Audit Log Model
**As a** Auditor  
**I want** all compliance actions logged  
**So that** I can demonstrate supervisory compliance

**Acceptance Criteria:**
- [ ] `audit_logs` table with: entity_type, entity_id, action, user_email, user_role, timestamp, details
- [ ] Logged actions: create, update, approve, reject, link, resolve
- [ ] Immutable (no updates/deletes)
- [ ] Indexed for efficient querying

**Story Points:** 5  
**Sprint:** 7  
**Dependencies:** None  
**Tech Notes (CTO):** New `audit.py` model

---

### US-038: Audit Trail Query API
**As a** Auditor  
**I want** to query the audit trail for any entity  
**So that** I can review compliance history

**Acceptance Criteria:**
- [ ] API: `GET /api/obligations/{id}/audit-trail`
- [ ] API: `GET /api/policies/{id}/audit-trail`
- [ ] API: `GET /api/audit-logs?entity_type=X&start_date=Y`
- [ ] Returns chronological list of events
- [ ] Supports pagination

**Story Points:** 5  
**Sprint:** 7  
**Dependencies:** US-037  

---

### US-039: Role-Based Access Control Middleware
**As a** System  
**I want** role-based permissions on compliance actions  
**So that** only authorized users can approve/publish

**Acceptance Criteria:**
- [ ] Middleware: `require_any_role(["mlro", "head_of_compliance"])`
- [ ] Returns 403 if user lacks required role
- [ ] Roles stored in user profile/JWT
- [ ] Role check logged in audit

**Story Points:** 8  
**Sprint:** 7  
**Dependencies:** None  
**Tech Notes (CTO):** FastAPI dependency injection

---

### US-040: Permission Matrix Enforcement
**As a** System  
**I want** the following permissions enforced  
**So that** we have proper separation of duties

**Acceptance Criteria:**
- [ ] Approve Obligation: `mlro`, `head_of_compliance`
- [ ] Publish Policy Section: `mlro` only
- [ ] Create Internal Rule: `compliance_officer`, `mlro`
- [ ] Link Monitoring Rule: `admin`, `mlro`
- [ ] View Audit Trail: `mlro`, `head_of_compliance`, `auditor`

**Story Points:** 5  
**Sprint:** 7  
**Dependencies:** US-039  

---

### US-041: Obligation Rejection Workflow
**As a** Compliance Officer  
**I want** to reject invalid obligations with a reason  
**So that** AI extraction quality is tracked

**Acceptance Criteria:**
- [ ] API: `POST /api/obligations/{id}/reject`
- [ ] Requires: rejection_category, feedback_text (optional)
- [ ] Categories: not_applicable, duplicate, incorrect_parsing, wrong_article
- [ ] Logged in audit trail
- [ ] Stored in `obligation_rejections` table for AI improvement

**Story Points:** 5  
**Sprint:** 7  
**Dependencies:** US-037  

---

## EPIC-009: Sentinel Dashboard Integration

### US-042: Proactive Alerts Endpoint
**As a** Compliance Officer  
**I want** regulatory alerts in the Sentinel dashboard  
**So that** I see all compliance tasks in one place

**Acceptance Criteria:**
- [ ] API: `GET /api/aml-officer/alerts/proactive` returns real alerts
- [ ] Includes: regulatory_deadline, policy_update_required, internal_rule_required, regulatory_overdue
- [ ] Sorted by severity, then created_at
- [ ] Pagination supported

**Story Points:** 8  
**Sprint:** 8  
**Dependencies:** EPIC-003, EPIC-007  

---

### US-043: Alert Filtering in Dashboard
**As a** Compliance Officer  
**I want** to filter alerts by type, severity, and date  
**So that** I can focus on what matters

**Acceptance Criteria:**
- [ ] Filter by: alert_type, severity, status, date_range
- [ ] UI dropdowns in Sentinel
- [ ] Saved filter presets (optional)
- [ ] Count badges per category

**Story Points:** 5  
**Sprint:** 8  
**Dependencies:** US-042  

---

### US-044: Obligation Management View
**As a** Compliance Officer  
**I want** a dedicated view for managing obligations  
**So that** I can review, approve, and link them

**Acceptance Criteria:**
- [ ] Table view: CELEX, Title, Status, Effective Date, Policy Link
- [ ] Actions: Approve, Reject, Link Policy
- [ ] Bulk actions for multiple obligations
- [ ] Status filter tabs: Draft, In Review, Approved, Implemented

**Story Points:** 13  
**Sprint:** 8  
**Dependencies:** EPIC-002, EPIC-004  

---

### US-045: Policy Management View
**As a** MLRO  
**I want** a view for managing policies and sections  
**So that** I can review and publish policy content

**Acceptance Criteria:**
- [ ] Policy list with: Name, Version, Status, Linked Obligations count
- [ ] Section editor with AI-generated content
- [ ] Approve/Publish buttons
- [ ] Export to Markdown button
- [ ] Compliance matrix tab

**Story Points:** 13  
**Sprint:** 8  
**Dependencies:** EPIC-004  

---

## EPIC-010: Operational Excellence (Optional)

### US-046: AI Feedback Collection
**As a** System  
**I want** to collect structured feedback on AI extractions  
**So that** prompts can be improved over time

**Acceptance Criteria:**
- [ ] `obligation_rejections` table populated via US-041
- [ ] Quarterly report generating function
- [ ] Aggregates by rejection_category
- [ ] Exports examples for prompt engineering

**Story Points:** 5  
**Sprint:** 10  
**Dependencies:** US-041  

---

### US-047: Database Index Optimization
**As a** System Administrator  
**I want** optimal database indexes for deadline queries  
**So that** Celery jobs run efficiently at scale

**Acceptance Criteria:**
- [ ] Index: `idx_obligations_effective_date` on effective_date WHERE status NOT IN (rejected, deprecated)
- [ ] Index: `idx_obligations_linked_policy` on linked_policy_id
- [ ] Index: `idx_internal_rules_obligation` on (obligation_id, status)
- [ ] EXPLAIN ANALYZE confirms index usage

**Story Points:** 3  
**Sprint:** 10 (or Sprint 7)  
**Dependencies:** None  
**Tech Notes (CTO):** Database migration script

---

---

## Definition of Done (DoD)

**Scrum Master establishes the following DoD for all stories:**

- [ ] Code written and passes linting
- [ ] Unit tests written (>80% coverage for new code)
- [ ] Integration tests for API endpoints
- [ ] Code reviewed and approved by peer
- [ ] Documentation updated (API docs, README)
- [ ] Merged to `develop` branch
- [ ] Deployed to staging environment
- [ ] Product Owner accepts demo
- [ ] No critical/blocker bugs

---

## Sprint Ceremonies

**Scrum Master recommends:**

| Ceremony | Duration | Participants | Cadence |
|----------|----------|--------------|---------|
| Sprint Planning | 2 hours | PO, SM, Dev Team | Sprint start |
| Daily Standup | 15 min | SM, Dev Team | Daily |
| Sprint Review | 1 hour | PO, SM, Dev Team, Stakeholders | Sprint end |
| Sprint Retro | 1 hour | SM, Dev Team | Sprint end |
| Backlog Refinement | 1 hour | PO, SM, Dev Leads | Mid-sprint |

---

## Risk Register (CTO Input)

| Risk | Probability | Impact | Mitigation | Owner |
|------|-------------|--------|------------|-------|
| AI extraction <70% accuracy | Medium | High | Fallback to manual, iterate prompts | Engineering |
| EUR-Lex API downtime | Low | Medium | Retry logic, error alerting | Engineering |
| Team velocity lower than planned | Medium | Medium | Buffer sprint, scope reduction | SM |
| Anthropic costs exceed budget | Low | Low | Caching, rate limiting | Engineering |
| RBAC blocks user testing | Medium | Low | Testing role for QA | Engineering |
