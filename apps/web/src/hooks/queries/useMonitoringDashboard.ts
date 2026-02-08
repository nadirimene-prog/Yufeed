/**
 * React Query hooks for Monitoring Dashboard
 * Combines multiple queries for dashboard view
 */

import { useQueries } from "@tanstack/react-query";
import { monitoringKeys } from "@/lib/queryKeys";
import apiClient from "@/lib/http";

export function useMonitoringDashboard() {
  return useQueries({
    queries: [
      {
        queryKey: monitoringKeys.alertsList({ limit: 10, status: "pending" }),
        queryFn: async () => {
          const response = await apiClient.get("/api/alerts", {
            params: { limit: 10, status: "pending" },
          });
          return response.data;
        },
      },
      {
        queryKey: monitoringKeys.casesList({ limit: 10, status: "open" }),
        queryFn: async () => {
          const response = await apiClient.get("/api/cases", {
            params: { limit: 10, status: "open" },
          });
          return response.data;
        },
      },
      {
        queryKey: monitoringKeys.metrics(),
        queryFn: async () => {
          const response = await apiClient.get("/api/monitoring/metrics");
          return response.data;
        },
      },
      {
        queryKey: monitoringKeys.dashboard(),
        queryFn: async () => {
          const response = await apiClient.get("/api/monitoring/dashboard");
          return response.data;
        },
      },
    ],
    combine: (results) => ({
      data: {
        alerts: results[0].data,
        cases: results[1].data,
        metrics: results[2].data,
        dashboard: results[3].data,
      },
      isLoading: results.some((r) => r.isLoading),
      isError: results.some((r) => r.isError),
      errors: results.filter((r) => r.error).map((r) => r.error),
    }),
  });
}
