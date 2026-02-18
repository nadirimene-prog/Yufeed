import {
  DashboardTimeRange,
  DashboardView,
  DashboardWorkQueueItem,
  WorkItemSlaStatus,
} from "./types";

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

export function slaBadgeClass(status: WorkItemSlaStatus): string {
  if (status === "breached") {
    return "bg-risk-critical-soft text-risk-critical border border-risk-critical/30";
  }
  if (status === "warning") {
    return "bg-risk-high-soft text-risk-high border border-risk-high/30";
  }
  if (status === "ok") {
    return "bg-risk-clear-soft text-risk-clear border border-risk-clear/30";
  }
  return "bg-risk-low-soft text-risk-low border border-risk-low/30";
}

export function formatRangeLabel(range: DashboardTimeRange): string {
  if (range === "24h") return "Last 24 hours";
  if (range === "7d") return "Last 7 days";
  return "Last 30 days";
}

export function formatAgeMinutes(minutes: number): string {
  if (minutes < 60) return `${minutes}m`;
  if (minutes < 60 * 24) return `${Math.floor(minutes / 60)}h`;
  return `${Math.floor(minutes / (60 * 24))}d`;
}

function severityRank(severity: string): number {
  const value = severity.toLowerCase();
  if (value === "critical") return 4;
  if (value === "high") return 3;
  if (value === "medium") return 2;
  if (value === "low") return 1;
  return 0;
}

function slaRank(status: WorkItemSlaStatus): number {
  if (status === "breached") return 4;
  if (status === "warning") return 3;
  if (status === "ok") return 2;
  return 1;
}

export function rankQueueItems(
  items: DashboardWorkQueueItem[],
): DashboardWorkQueueItem[] {
  return [...items].sort((a, b) => {
    const slaDelta = slaRank(b.sla_status) - slaRank(a.sla_status);
    if (slaDelta !== 0) return slaDelta;

    const severityDelta = severityRank(b.severity) - severityRank(a.severity);
    if (severityDelta !== 0) return severityDelta;

    const riskDelta = b.risk_score - a.risk_score;
    if (riskDelta !== 0) return riskDelta;

    return b.age_minutes - a.age_minutes;
  });
}
