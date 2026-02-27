# AMLCO Dashboard Pilot Rollout Checklist (Sprint 6)

## Scope
Controlled rollout of the AMLCO dashboard best-in-class workstation features to a pilot group (5-10 users).

## Feature Flags (Locked)
- `dashboard_trusted_metrics_v1`
- `dashboard_power_user_shortcuts_v1`
- `dashboard_action_next_v1`
- `dashboard_decision_trace_v1`
- `dashboard_saved_views_server_v1`

## Pre-Pilot Readiness

### Product / Compliance
- [ ] `docs/dashboard-metrics.md` reviewed and signed off by compliance owner
- [ ] Decision trace / review provenance labels approved
- [ ] Override-reason policy behavior reviewed for affected workflows

### Backend
- [ ] `/api/dashboard/overview` freshness and comparison fields enabled
- [ ] `/api/dashboard/work-queue` freshness metadata enabled
- [ ] `/api/dashboard/work-items/...` freshness + provenance + decision trace enabled
- [ ] `/api/dashboard/views` CRUD endpoints enabled
- [ ] `/api/dashboard/preferences` get/patch endpoints enabled
- [ ] telemetry ingestion endpoint enabled (`/api/dashboard/telemetry/events`)

### Frontend
- [ ] Saved views dialog reachable from dashboard header (`Views`)
- [ ] Role/user default saved view auto-apply verified
- [ ] Queue density and insights/default-tab server preference sync verified
- [ ] Keyboard shortcuts + command palette verified
- [ ] Autosave + action-next flows verified
- [ ] Partial outage/degraded states verified (overview/queue/detail)

### QA / Automation
- [ ] Dashboard unit tests green
- [ ] Dashboard API unit tests green
- [ ] Playwright visual snapshots green (desktop/mobile)
- [ ] Manual compliance QA scenarios completed

## Pilot Launch Steps
1. Enable flags for internal QA users.
2. Enable flags for pilot cohort (5-10 users, mixed analyst/reviewer/manager).
3. Confirm telemetry ingestion volume and no endpoint errors.
4. Capture baseline KPI snapshot before pilot starts.

## Pilot Monitoring (2 Weeks)

### KPIs to Track
- Median time to first action
- Median case resolution time
- P1/P2 SLA breach rate
- Analyst actions/hour
- Review return rate
- Audit completeness rate
- Queue abandonment/context-switch rate
- Dashboard interaction latency (p50/p95)

### Health Checks
- [ ] Frontend error rate stable
- [ ] Backend dashboard endpoint latency stable
- [ ] Freshness lag within expected range
- [ ] No critical auditability defects reported

## Acceptance Thresholds (Locked)
- [ ] No increase in P1/P2 SLA breach rate
- [ ] Median time to first action improves by >=10% OR analyst actions/hour improves by >=10%
- [ ] No critical auditability defects
- [ ] Dashboard error-rate spike <= +2% over baseline

## Post-Pilot Decision
- [ ] Broader rollout approved
- [ ] Additional hardening required (document blockers)
- [ ] Rollback / partial disable plan documented if thresholds fail
