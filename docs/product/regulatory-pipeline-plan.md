# Regulatory Intelligence Pipeline - Implementation Plan

**Version:** 1.0  
**Date:** January 29, 2026  
**Status:** Approved - Ready for Sprint 1 Kickoff

---

## Executive Summary

This document outlines the end-to-end **Regulatory Intelligence Pipeline** for YuFeed's Sentinel dashboard. The pipeline transforms ingested EU/FR regulatory documents into actionable compliance insights with automated policy generation and system enforcement.

**Investment:** 20 weeks (10 sprints)  
**Team:** 4-5 developers  
**Outcome:** 80% reduction in manual compliance tracking time

---

## Business Value

| Capability | Current State | With Pipeline |
|------------|---------------|---------------|
| Track new regulations | Manual EUR-Lex searches | Automated weekly ingestion |
| Write policy sections | 2-3 hours per obligation | AI draft in 30 seconds |
| Prove compliance | 2 days to compile | 5-minute export |
| Configure monitoring | Manual, disconnected | Policy → TM rule mapping |
| Track deadlines | Calendar reminders | Automated 90/60/30/7-day alerts |

---

## Epic Overview

| Epic | Description | Sprints | Stories |
|------|-------------|---------|---------|
| EPIC-001 | Document Ingestion Enhancement | 1 | 6 |
| EPIC-002 | AI Analysis & Obligation Extraction | 2 | 6 |
| EPIC-003 | Regulatory Alert Pipeline | 3 | 5 |
| EPIC-004 | Policy Management & AI Writer | 4 | 8 |
| EPIC-005 | Internal Rules & System Enforcement | 5 | 5 |
| EPIC-006 | Impact Assessment & Action Items | 6 | 3 |
| EPIC-007 | Deadline Monitoring | 6 | 3 |
| EPIC-008 | Audit Trail & RBAC | 7 | 5 |
| EPIC-009 | Sentinel Dashboard Integration | 8 | 4 |
| EPIC-010 | Operational Excellence (Optional) | 10 | 2 |

**Total:** 47 User Stories, ~320 story points

---

## Architecture

### Data Flow

```
EUR-Lex RSS/Search → legal_documents → AI Analysis → regulatory_obligations
                                                          ↓
                                        policy_documents ← linked_policy_id
                                              ↓
                                        policy_sections (AI-generated)
                                              ↓
                                        internal_rules
                                              ↓
                                        internal_rule_mappings → monitoring_rules
```

### New Components

| Component | Purpose | Location |
|-----------|---------|----------|
| `OJActFetcher` | Ingest OJ Act-by-Act metadata | `src/ingestion/oj_acts.py` |
| `BatchContentFetcher` | Backfill empty full_text | `src/ingestion/batch.py` |
| `regulatory_alerts.py` | Bridge obligations → alerts | `src/compliance/` |
| `policy_writer.py` | AI policy section generation | `src/ai/` |
| `monitoring_rule_suggester.py` | AI monitoring rule config | `src/ai/` |
| `deadline_monitor.py` | Celery deadline checks | `src/compliance/` |
| `AuditLog` model | Compliance audit trail | `src/models/audit.py` |

### Database Changes

**New Tables:**
- `obligation_rejections` - AI feedback tracking
- `audit_logs` - Compliance event logging

**Modified Tables:**
- `regulatory_obligations` - Add `implemented` status
- `policy_documents` - Add template seeding
- `internal_rules` - Add mapping to monitoring rules

**New Indexes:**
```sql
CREATE INDEX idx_obligations_effective_date ON regulatory_obligations(effective_date);
CREATE INDEX idx_obligations_linked_policy ON regulatory_obligations(linked_policy_id);
CREATE INDEX idx_internal_rules_obligation ON internal_rules(obligation_id, status);
```

---

## API Endpoints

### Obligations
```
GET  /api/obligations/                          # List all obligations
GET  /api/obligations/{id}                      # Get obligation details
POST /api/obligations/{id}/approve              # Approve obligation (RBAC)
POST /api/obligations/{id}/reject               # Reject with reason
GET  /api/obligations/{id}/audit-trail          # Get audit history
```

### Policies
```
GET  /api/policies/templates                    # List policy templates
POST /api/policies/from-template/{template_id}  # Create from template
POST /api/policies/{id}/link-obligation/{obl_id} # Link obligation (triggers AI)
PATCH /api/policies/{id}/sections/{section_id}  # Edit section
POST /api/policies/{id}/sections/{id}/approve   # Approve section (MLRO)
GET  /api/policies/{id}/export                  # Export as Markdown
GET  /api/policies/{id}/compliance-matrix       # Get coverage matrix
```

### Internal Rules
```
POST /api/internal-rules/                       # Create internal rule
POST /api/internal-rules/{id}/mappings          # Map to monitoring rule
GET  /api/internal-rules/?obligation_id=X       # Query by obligation
```

### Alerts
```
GET  /api/aml-officer/alerts/proactive          # Regulatory alerts
POST /api/alerts/{id}/resolve                   # Resolve alert
```

---

## Rollout Strategy

### Phase Groups

| Group | Weeks | Epics | Release To |
|-------|-------|-------|------------|
| A: Foundation | 1-4 | 1-3, 5 | 3 design partners |
| B: Enforcement | 5-6 | 4, 6, 8 | 10 beta customers |
| C: Compliance | 7-8 | 7, 9 | All customers (GA) |
| D: Excellence | 9+ | 10 | All customers |

### Feature Flags

| Flag | Default | Description |
|------|---------|-------------|
| `regulatory_ai_policy_writer` | OFF | AI section generation |
| `regulatory_rule_suggestions` | OFF | AI monitoring rule suggestions |
| `regulatory_deadline_alerts` | ON | Deadline tracking |
| `regulatory_audit_trail` | ON | Audit logging |

---

## Success Metrics

### Core Pipeline (Phases 1-5)
- ✅ Ingestion: All 3 source types run automatically
- ✅ Content Coverage: >90% of documents have full_text
- ✅ Obligation Extraction: 3-5 obligations per document
- ✅ Policy Coverage: Obligations linked within 2 weeks

### System Enforcement (Phase 6)
- ✅ Internal Rules: >80% of sections have linked rules
- ✅ Monitoring Rules: High-risk obligations mapped to TM

### Compliance Management (Phases 7-9)
- ✅ Impact Assessments: Auto-created for all regulations
- ✅ Deadline Tracking: Zero overdue without alerts
- ✅ Audit Trail: 100% of state changes logged

---

## RBAC Permissions

| Action | Allowed Roles |
|--------|---------------|
| Approve Obligation | `mlro`, `head_of_compliance` |
| Reject Obligation | `mlro`, `head_of_compliance` |
| Create Policy | `mlro`, `compliance_officer` |
| Publish Policy Section | `mlro` only |
| Create Internal Rule | `compliance_officer`, `mlro` |
| Link to Monitoring Rule | `admin`, `mlro` |
| View Audit Trail | `mlro`, `head_of_compliance`, `auditor` |

---

## Dependencies

### External
- Anthropic Claude API (AI analysis, policy writing)
- EUR-Lex SPARQL endpoint
- Légifrance RSS/API

### Internal
- Sentinel Dashboard (deployed)
- Alert model extension
- RBAC middleware
- Email service (for escalation)

---

## Related Documentation

- Product Backlog: `docs/product/regulatory-pipeline-backlog.md`
- Policy Taxonomy: `docs/product/policy-taxonomy.md`
- Rollout Validation: `docs/product/regulatory-pipeline-rollout.md`
- Development Rules: `docs/engineering/product-development-rules.md`

---

## Contacts

- **Product Owner:** [Name]
- **Engineering Lead:** [Name]
- **Scrum Master:** [Name]
- **Compliance SME:** [Name]
