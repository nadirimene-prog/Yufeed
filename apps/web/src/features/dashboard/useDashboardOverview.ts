"use client";

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/http";
import { dashboardKeys } from "@/lib/queryKeys";
import {
  DashboardOverviewResponse,
  DashboardTimeRange,
  DashboardView,
} from "@/features/dashboard/types";

export function useDashboardOverview(
  view: DashboardView,
  timeRange: DashboardTimeRange,
) {
  return useQuery({
    queryKey: dashboardKeys.overview(view, timeRange),
    queryFn: async () => {
      const response = await apiClient.get<DashboardOverviewResponse>(
        "/api/dashboard/overview",
        {
          params: { view, time_range: timeRange },
        },
      );
      return response.data;
    },
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}
