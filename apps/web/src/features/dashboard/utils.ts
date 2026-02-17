import { DashboardTimeRange, DashboardView } from "./types";

const VALID_VIEWS: DashboardView[] = ["operations", "compliance", "monitoring"];
const VALID_TIME_RANGES: DashboardTimeRange[] = ["24h", "7d", "30d"];

export function resolveDashboardView(value?: string | null): DashboardView {
  if (!value) return "operations";
  return VALID_VIEWS.includes(value as DashboardView)
    ? (value as DashboardView)
    : "operations";
}

export function resolveDashboardTimeRange(
  value?: string | null,
): DashboardTimeRange {
  if (!value) return "7d";
  return VALID_TIME_RANGES.includes(value as DashboardTimeRange)
    ? (value as DashboardTimeRange)
    : "7d";
}

export function severityBadgeClass(severity: string): string {
  const value = severity.toLowerCase();
  if (value === "critical") {
    return "bg-risk-critical-soft text-risk-critical border border-risk-critical/30";
  }
  if (value === "high") {
    return "bg-risk-high-soft text-risk-high border border-risk-high/30";
  }
  if (value === "medium") {
    return "bg-risk-medium-soft text-risk-medium border border-risk-medium/30";
  }
  return "bg-risk-low-soft text-risk-low border border-risk-low/30";
}

export function formatRangeLabel(range: DashboardTimeRange): string {
  if (range === "24h") return "Last 24 hours";
  if (range === "7d") return "Last 7 days";
  return "Last 30 days";
}
