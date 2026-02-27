# AMLCO Dashboard Performance Gate (Sprint 5)

## Purpose
Define the measurement gate for queue virtualization and broader dashboard performance hardening decisions.

## Gate Decision (Locked)
Implement queue virtualization **only if either** threshold is exceeded in pilot-like conditions:

1. Queue render median (`p50`) > `150ms` at ~100 visible rows
2. Interaction latency median (`p50`) > `100ms` on analyst-grade hardware

If both remain below threshold, defer virtualization to avoid complexity and accessibility regression risk.

## Telemetry Inputs

### Frontend Telemetry Events
- `dashboard_filter_apply`
- `dashboard_row_select`
- `dashboard_action_submit`
- `dashboard_action_next`
- `dashboard_shortcut_used`
- `dashboard_autosave_result`
- `dashboard_ui_timing`
  - `metric = "queue_render_complete"`
  - `metric = "detail_refresh_complete"`

### Required Payload Fields (Performance-Relevant)
- `latency_ms`
- `success`
- `phase` (where applicable)
- queue render context: `visible_count`, `total`, `density`, `has_error`
- detail refresh context: `trigger`, `kind`, `has_error`

## Measurement Windows
- Baseline: 7 days pre-pilot (if available)
- Pilot: 2-week pilot period
- Post-pilot verification: first 7 days after wider rollout

## Test Conditions
- Desktop primary path (`>=1280px`)
- Analyst-grade machine profile (reference hardware documented by QA)
- Mixed queue states:
  - normal rows
  - degraded queue refresh with cached rows
  - stale overview/detail warnings present
- Long sessions (30+ minutes with repeated filter/select/action cycles)

## Evaluation Procedure
1. Collect telemetry from pilot users.
2. Segment by:
   - density mode (`comfortable` / `compact`)
   - queue size buckets
   - degraded vs healthy backend responses
3. Compute `p50`, `p95` for:
   - filter apply completion (`dashboard_filter_apply` completion phases)
   - detail load (`dashboard_row_select` completion phases)
   - action submit roundtrip (`dashboard_action_submit`)
   - queue render complete (`dashboard_ui_timing`)
   - detail refresh complete (`dashboard_ui_timing`)
4. Compare against thresholds.
5. Decide virtualization:
   - required
   - defer
   - reevaluate after backend optimization

## Optimization Order (Before Virtualization)
1. Backend query/index tuning
2. Caching of read-only overview panels (safe freshness bounds)
3. Frontend render reduction / state churn cleanup
4. Only then evaluate queue virtualization

## Output (Required for Sign-Off)
- One performance report with:
  - p50/p95 tables
  - sample sizes
  - environment notes
  - degraded-state observations
  - virtualization decision with rationale
