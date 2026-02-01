# Regulatory Intelligence Pipeline - Implementation Status

**Date:** January 29, 2026  
**Status:** In Progress (Partial implementation in codebase)

## Status by Epic (per epic scheme)

| Epic | Status | Notes |
|------|--------|-------|
| EPIC-000 Sprint 0 - Product Development Rules | Partial | Sprint 0 technical foundation mostly present (prompts, migrations, env vars); policy template seeding not wired on startup. |
| EPIC-001 Regulatory Document Ingestion | Partial | Weekly RSS/search/Legifrance ingestion implemented; OJ sync + content backfill services exist; ingestion status surfaced in Compliance Dashboard. |
| EPIC-002 AI Analysis & Obligation Extraction | Partial | Analyzer runs for content + metadata-only docs; subject tags + scope tags expanded; obligation IDs now CELEX+article but accuracy/volume validation missing. RAG chunk indexing + hybrid retrieval added for semantic query coverage. |
| EPIC-003 Regulatory Alert Pipeline | Implemented | Alerts + API in `apps/api/src/compliance/regulatory_alerts.py` and `apps/api/src/api/regulatory_alerts.py`. |
| EPIC-004 Policy Management & AI Writer | Implemented | Policy CRUD + templates + AI policy section generation (feature-flagged). |
| EPIC-005 Internal Rules & System Enforcement | Partial | Internal rules + mappings API exist; monitoring rule suggestion UI added (feature-flagged); internal rule status updates + auto-implemented checks wired on policy link/internal rule updates; enforcement integration still pending. |
| EPIC-006 Impact Assessment & Action Items | Implemented | Auto-create impact assessments during analysis with action items; impact/action APIs + UI wired. |
| EPIC-007 Deadline Monitoring | Implemented | Celery beat schedules wired via config; deadlines UI added in compliance dashboard. |
| EPIC-008 Audit Trail & RBAC | Partial | RBAC enforced; explicit audit events added for workflow actions. |
| EPIC-009 Sentinel Dashboard Integration | Partial | AML Officer proactive alerts wired with filters + resolve actions; Policies UI uses `/api/policies` with export + compliance matrix summary; Obligations list supports status tabs, policy linking, and bulk actions. |
| EPIC-010 Operational Excellence (Optional) | Partial | AI feedback reporting endpoint exists; performance indexes already created in migrations; no UI for feedback review. |

## Evidence (codebase pointers)
- Sprint 0 foundations: `apps/api/src/ai/prompts/`, `apps/api/alembic/versions/i3j4k5l6m7n8_add_regulatory_pipeline_tables.py`, `apps/api/.env.example`, `apps/api/scripts/seed_policy_templates.py`.
- Ingestion + OJ sync + backfill: `apps/api/src/ingestion/`, `apps/api/src/worker.py`.
- Workflow models + migrations: `apps/api/src/models/compliance_workflow.py`, `apps/api/alembic/versions/6c9d1a2b3c4d_regulatory_sources_and_obligations.py`.
- AI analysis: `apps/api/src/ai/analyzer.py`, `apps/api/src/services/obligation_service.py`.
- Alerts + APIs: `apps/api/src/compliance/regulatory_alerts.py`, `apps/api/src/api/regulatory_alerts.py`.
- Policies + obligations + rules APIs: `apps/api/src/api/obligations.py`, `apps/api/src/api/policies.py`, `apps/api/src/api/compliance_workflow.py`.

## Story-Level Status (EPIC-001)

| Story | Status | Notes |
|-------|--------|-------|
| US-001 EUR-Lex RSS Feed Ingestion | Implemented | Weekly schedule configurable via `INGESTION_WEEKLY_SCHEDULE`; RSS fetches via CELLAR ingestion feed (OJ filter). |
| US-002 EUR-Lex Search Ingestion | Implemented | Search ingestion runs weekly via `IngestionManager` using configured EN/FR/DE terms; dedupe handled by CELEX uniqueness. |
| US-003 OJ Act-by-Act Metadata Extraction | Partial | SPARQL sync implemented; stores `official_journal_acts` and links to docs when possible. |
| US-004 Content Backfill | Implemented | Backfill service + re-analysis exist; schedule configurable via `CONTENT_BACKFILL_SCHEDULE` (default monthly). |
| US-005 Légifrance Feed Integration | Implemented | RSS ingestion filtered by AML/financial keywords; CELEX references linked to EU docs when detected. |
| US-006 Ingestion Manager Orchestration | Implemented | `run_all()` and source disable config exist; CLI uses `python -m src.ingestion.manager --run-all` (with `PYTHONPATH=apps/api`); status visible in Compliance Dashboard via ingestion APIs. |

## Story-Level Status (EPIC-002)

| Story | Status | Notes |
|-------|--------|-------|
| US-007 Trigger AI Analysis for New Documents | Implemented | Analysis runs for content + metadata-only docs; idempotency via `analyzed_at`; failures logged. |
| US-008 Obligation Extraction from Regulatory Text | Partial | Obligations extracted + stored; `obligation_id` uses CELEX+article; accuracy/volume validation still missing. |
| US-012A RAG Chunk Indexing & Retrieval | Implemented | LegalChunk model + OpenSearch hybrid (BM25 + vector) retrieval; indexing wired into ingestion/backfill and batch script available. |
| US-009 Document Classification and Risk Scoring | Partial | Compliance domain + expanded risk levels stored; subject-matter tags inferred; doc type inferred via CELLAR or AI/heuristics. |
| US-010 Scope Tag Inference | Implemented | Scope tags inferred and stored; expanded to credit_institution/insurance; filterable in dashboard. |
| US-011 Effective Date Parsing | Implemented | Rule-based parsing supports ISO dates and relative timelines (e.g., “X months after publication”). |
| US-012 Analysis Cost Monitoring | Implemented | Usage persisted via `ai/cost_tracker.py`; daily/weekly summaries via `/api/ai/costs/*`; daily threshold check scheduled in Celery. |

## Next steps by Epic
- EPIC-002: Validate obligation extraction accuracy/volume and add subject-matter QA checks.
- EPIC-003: Add tests around alert creation and resolution workflows.
- EPIC-005: Wire enforcement integration (TM system hooks) + expand internal rule status workflow.
- EPIC-008: Expand audit coverage to policy deletions and template operations.
- EPIC-006: Improve action-item quality/target dates and add gap review UX.
