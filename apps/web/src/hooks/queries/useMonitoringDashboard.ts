import { useDashboardOverview } from "@/features/dashboard/useDashboardOverview";

/**
 * Backward-compatible hook that now resolves through the unified dashboard API.
 */
export function useMonitoringDashboard() {
  return useDashboardOverview("monitoring", "7d");
}
