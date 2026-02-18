# API Compatibility and Deprecations

Last updated: 2026-02-17

This document tracks endpoint aliases and behavior differences that exist for backward compatibility.

## Monitoring Rules

Canonical prefix:
- `/api/monitoring-rules`

Legacy alias prefix:
- `/api/rules`

Current alias coverage:
- `POST /api/rules` -> forwards to `POST /api/monitoring-rules`
- `GET /api/rules` -> forwards to `GET /api/monitoring-rules`
- `GET /api/rules/{rule_id}` -> forwards to `GET /api/monitoring-rules/{rule_id}`

Compatibility behavior:
- Responses from `/api/rules*` include header `X-Deprecated: true`.
- Legacy payload keys accepted on create: `conditions_json` maps to `conditions`; `aggregation_json` maps to `thresholds`.
- Create response includes legacy fields (`rule_id`, `conditions_json`, `aggregation_json`) to avoid breaking older clients.

Migration target:
- Move all clients to `/api/monitoring-rules*`.
- Use canonical request keys (`conditions`, `thresholds`) and canonical response contract.

## Compliance Workflow

Prefix:
- `/api/compliance`

Compatibility and contract notes:
- `POST /api/compliance/policies` returns `201 Created`.
- `POST /api/compliance/policies/{policy_id}/extract-obligations` is available for end-to-end flow compatibility and returns `201 Created`.
- `GET /api/compliance/policies/{policy_id}/obligations` returns obligations linked to the policy.
- `POST /api/compliance/obligations/{obligation_id}/approve` supports approval in workflow integrations.
- The following create endpoints return `201 Created`: `POST /api/compliance/policies/{policy_id}/sections`, `POST /api/compliance/obligations/{obligation_id}/internal-rules`, `POST /api/compliance/internal-rules/{internal_rule_id}/mappings`.
- Compatibility identifiers: policy, obligation, and internal-rule path parameters accept either numeric DB IDs or business IDs (`policy_id`, `obligation_id`, `internal_rule_id`).

Tenant behavior:
- Compliance policy visibility is filtered by tenant metadata.
- In `dev` and `test`, tenant overrides from `X-Tenant-ID` or `tenant_id` query parameter are allowed for integration testing.

## Alerts

Prefix:
- `/api/alerts`

New endpoint:
- `POST /api/alerts/{alert_id}/notes` returns `201 Created`

Behavior:
- Appends note entries to alert evidence metadata (`evidence.notes`) and emits an audit event.

## Migration Checklist

1. Replace `/api/rules*` usage with `/api/monitoring-rules*`.
2. Replace legacy request fields (`conditions_json`, `aggregation_json`) with canonical fields (`conditions`, `thresholds`).
3. Ensure clients accept `201 Created` for compliance and alerts create operations listed above.
4. Send tenant context explicitly (`X-Tenant-ID`) in automated integration tests for deterministic isolation.
