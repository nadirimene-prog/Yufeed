"use client";

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/http";
import { dashboardKeys } from "@/lib/queryKeys";
import { AiUsageSummaryResponse } from "@/features/dashboard/types";

export function useAiUsageSummary(days = 30, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: dashboardKeys.aiUsageSummary(days),
    queryFn: async () => {
      const response = await apiClient.get<AiUsageSummaryResponse>(
        "/api/ai-costs/usage-summary",
        {
          params: { days },
        },
      );
      return response.data;
    },
    staleTime: 30_000,
    refetchInterval: 60_000,
    enabled: options?.enabled ?? true,
  });
}
