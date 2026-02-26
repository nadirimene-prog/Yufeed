"use client";

export type DashboardTelemetryEventName =
  | "dashboard_filter_apply"
  | "dashboard_row_select"
  | "dashboard_action_submit"
  | "dashboard_action_next"
  | "dashboard_shortcut_used"
  | "dashboard_autosave_result";

export type DashboardTelemetryPayload = Record<string, unknown>;

declare global {
  interface WindowEventMap {
    "dashboard:telemetry": CustomEvent<{
      event: DashboardTelemetryEventName;
      payload: DashboardTelemetryPayload;
      at: string;
    }>;
  }
}

export function trackDashboardEvent(
  event: DashboardTelemetryEventName,
  payload: DashboardTelemetryPayload = {},
) {
  if (typeof window === "undefined") return;
  if (process.env.NODE_ENV === "test") return;

  const detail = {
    event,
    payload,
    at: new Date().toISOString(),
  };

  window.dispatchEvent(new CustomEvent("dashboard:telemetry", { detail }));

  if (process.env.NODE_ENV === "development") {
    console.debug("[dashboard-telemetry]", detail);
  }
}

export default trackDashboardEvent;
