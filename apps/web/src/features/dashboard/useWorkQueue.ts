"use client";

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/http";
import { dashboardKeys } from "@/lib/queryKeys";
import {
  DashboardWorkQueueParams,
  DashboardWorkQueueResponse,
} from "@/features/dashboard/types";

function toApiParams(params: DashboardWorkQueueParams) {
  return {
    page: params.page,
    page_size: params.pageSize,
    queue: params.queue,
    severity: params.severity === "all" ? undefined : params.severity,
    jurisdiction:
      params.jurisdiction.trim().length > 0
        ? params.jurisdiction.trim()
        : undefined,
    sla: params.sla === "all" ? undefined : params.sla,
    search: params.search.trim().length > 0 ? params.search.trim() : undefined,
    saved_view: params.savedView === "all" ? undefined : params.savedView,
  };
}

export function useWorkQueue(
  params: DashboardWorkQueueParams,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: dashboardKeys.workQueue(params),
    queryFn: async () => {
      const response = await apiClient.get<DashboardWorkQueueResponse>(
        "/api/dashboard/work-queue",
        {
          params: toApiParams(params),
        },
      );
      return response.data;
    },
    staleTime: 20_000,
    refetchInterval: 45_000,
    enabled: options?.enabled ?? true,
  });
}
