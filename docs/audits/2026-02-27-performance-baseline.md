# YuFeed Performance Baseline (2026-02-27)

## Scope

- Obligations list endpoint query count/latency
- Dashboard work queue query count/latency
- Dashboard frontend render/profile baseline
- Build output and bundle baseline
- DB slow query and connection baseline

## Backend Baseline

- Environment: pending capture in target environment
- Obligations list (`/api/obligations`) query count: pending
- Obligations list p50/p95 latency: pending
- Dashboard queue (`/api/dashboard/work-queue`) query count: pending
- Dashboard queue p50/p95 latency: pending
- DB active connections baseline: pending
- Slow query sample (`log_min_duration_statement`): pending

## Frontend Baseline

- `npm run build` summary: pending
- Dashboard profiler (`/dashboard`) render counts:
  - insights toggle path: pending
  - 30s freshness timer path: pending
  - queue selection path: pending

## Notes

- This file is created as the baseline artifact required by the remediation program.
- Capture values before merging additional performance PRs into protected branches.
