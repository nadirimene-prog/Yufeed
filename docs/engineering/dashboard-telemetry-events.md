# Dashboard Telemetry Events (AMLCO Command Center)

## Scope
Frontend telemetry for the AMLCO dashboard (`/dashboard`) to support UX KPI baselining and rollout monitoring.

Current implementation emits a browser `CustomEvent` (`dashboard:telemetry`) from:
- `/Users/imenenadir/Documents/Yufeed/apps/web/src/features/dashboard/telemetry.ts`

This is provider-agnostic. A later integration (PostHog/Segment/etc.) can subscribe and forward without changing dashboard feature code.

## Event Names (Baseline)

### `dashboard_filter_apply`
Emitted when queue filters/pagination are applied.

Typical payload:
- `source`: `"queue_controls" | "critical_tile" | "pagination"`
- `keys`: `string[]` changed filter keys
- `phase`: `"submitted" | "queue_loaded" | "queue_load_error"` (completion phase emitted after queue query resolves)
- `success`: boolean (completion phase only)
- `latency_ms`: number (completion phase only)
- `page` / `page_size` / `total` / `visible_count` (completion phase only)

### `dashboard_row_select`
Emitted when a user selects a queue item.

Typical payload:
- `source`: `"desktop_queue" | "mobile_queue"`
- `kind`: work item kind
- `severity`: work item severity
- `review_required`: boolean
- `phase`: `"selected" | "detail_loaded" | "detail_load_error"`
- `success`: boolean (detail load phases only)
- `latency_ms`: number (detail load phases only)

### `dashboard_action_submit`
Emitted for single, review, and bulk actions after success/failure.

Typical payload:
- `mode`: `"single" | "review" | "bulk"`
- `action` or `decision` / `proposed_action`
- `kind` (single/review)
- `count` (bulk)
- `success`: boolean
- `advance_to_next`: boolean (single/review only)
- `latency_ms`: number (roundtrip timing)

### `dashboard_action_next`
Emitted when an `+ Next` flow is attempted.

Typical payload:
- `initiator`: `"action" | "review"`
- `success`: boolean
- `moved_to_next`: boolean
- `used_backend_hint`: boolean

### `dashboard_shortcut_used`
Emitted for power-user keyboard shortcuts and queue-local shortcuts.

Typical payload:
- `shortcut`: string (`"?"`, `"mod+k"`, `"g q"`, `"j"`, `"k"`, `"x"`, etc.)

### `dashboard_autosave_result`
Emitted by workspace draft autosave/manual draft save path.

Typical payload:
- `source`: `"autosave" | "manual"`
- `result`: `"success" | "error" | "retrying"`
- `has_narrative`: boolean (when applicable)
- `has_notes`: boolean (when applicable)

## Privacy / Data Minimization
- Do not emit free-text narrative/notes content.
- Do not emit entity names, reference IDs, or analyst notes.
- Prefer counts, booleans, enums, and workflow metadata.

## Integration Notes
- Listener example:
  - `window.addEventListener("dashboard:telemetry", (e) => { ...forward(e.detail)... })`
- If a provider is added, keep these event names stable to preserve dashboard KPI continuity across releases.
