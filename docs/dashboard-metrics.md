# AMLCO Dashboard Metrics Definition (v1)

## Purpose
Canonical metric definitions for the AMLCO dashboard so frontend comparisons, backend aggregations, and compliance reviews use the same formulas.

## Scope
- Dashboard overview metrics
- Throughput comparisons/history
- Governance/compliance quality indicators
- KPI baselining for pilot rollout

## Global Rules (Locked)
- Storage time: UTC
- Display time: user locale / tenant timezone
- Comparison window: immediately preceding window of equal duration (`24h`, `7d`, `30d`)
- Missing source data: return `null` (not `0`)
- Percent denominator zero: return `null`
- Freshness thresholds:
  - overview: `120s`
  - queue: `60s`
  - detail: `30s`

## Ownership
- Compliance owner: AMLCO / compliance manager
- Backend owner: API dashboard maintainers
- Frontend owner: dashboard UX team
- QA owner: release QA / pilot QA

## Core Throughput Metrics

### `median_time_to_first_action_minutes`
- Definition: Median elapsed minutes from alert creation (`Alert.created_at`) to first analyst state change (`Alert.updated_at`) within the selected window.
- Inclusion:
  - alerts with `created_at` in window
  - `updated_at` present
  - non-negative elapsed time
- Exclusion:
  - missing timestamps
  - negative elapsed deltas (clock skew / data corruption)

### `median_case_resolution_hours`
- Definition: Median elapsed hours from case open (`Case.opened_at`) to close (`Case.closed_at`) for cases closed within the selected window.
- Inclusion:
  - `Case.status == "closed"`
  - `closed_at` in window
  - `opened_at` present
- Exclusion:
  - missing timestamps
  - negative elapsed deltas

### Comparison Fields
- `median_time_to_first_action_delta_minutes`
  - Current window median minus previous equal-length window median
- `median_case_resolution_delta_hours`
  - Current window median minus previous equal-length window median
- Positive/negative interpretation:
  - Lower is better for both metrics (UI presentation should not imply positive delta is good)

### History Arrays
- `*_history`
  - Fixed bucket series over the selected window (default 7 buckets)
  - Sparse buckets may be `0` or `null` based on backend implementation; frontend must handle either

## Queue / Triage Metrics

### `alerts_open`
- Count of alerts in active triage states (`pending`, `in_review`)

### `cases_open`
- Count of cases in active states (`open`, `in_progress`)

### `approvals_pending`
- Count of case decisions awaiting maker-checker approval

### `reg_tasks_due`
- Count of regulatory task-like work items due or represented in queue logic

## Critical Decision Bar Metrics

### `p1_sla_breaches`
- Count of critical-severity items currently past SLA

### `p2_sla_breaches`
- Count of high-severity items currently past SLA

### `sanctions_hits_unreviewed`
- Count of sanctions/PEP alerts not yet reviewed/dispositioned

### `sar_due_24h`
- Count of SAR filing-related tasks due within next 24h

### `high_risk_cases_unassigned`
- Count of high-risk cases without an owner

### `ingestion_lag_minutes`
- Current pipeline lag (processing watermark gap) in minutes

## Governance Metrics

### `rule_drift_score`
- Composite drift proxy score for detection/ruleset behavior
- Unit: score (0-100 preferred)

### `alert_to_case_rate`
- `cases_created / alerts_reviewed` over selected window
- Denominator zero => `null`

### `fp_proxy_rate`
- Proxy false-positive rate based on closed/no-action outcomes (implementation-defined)
- Denominator zero => `null`

### `audit_completeness_rate`
- Percentage of reviewed/closed items with required audit fields completed
- Denominator zero => `null`

### Governance Histories
- `rule_drift_score_history`
- `alert_to_case_rate_history`
- `fp_proxy_rate_history`
- `audit_completeness_rate_history`

## Review / Auditability Metrics (Pilot KPIs)

### `review_return_rate`
- Returned reviews / total reviews over selected period

### `audit_completeness_rate`
- See governance metric above; also tracked as pilot KPI

## UX / Throughput Pilot KPIs (Tracked outside overview payload if needed)
- Median time to first action
- Median case resolution time
- P1/P2 SLA breach rate
- Analyst actions/hour
- Review return rate
- Audit completeness rate
- Queue abandonment/context-switch rate
- Dashboard interaction latency (filter apply, row select, action submit, queue render, detail refresh)

## Validation Checklist (Before Pilot)
- Compliance sign-off on formula text and inclusion/exclusion rules
- Backend test fixtures cover:
  - sparse windows
  - zero denominators
  - timezone boundary crossings
  - null/missing timestamps
- Frontend confirms:
  - no fake trend fallbacks
  - stale/freshness labeling matches thresholds
