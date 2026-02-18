"use client";

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/http";
import { dashboardKeys } from "@/lib/queryKeys";
import {
  WorkItemDetailResponse,
  WorkItemKind,
} from "@/features/dashboard/types";

export function useWorkItemDetail(
  kind: WorkItemKind | null,
  itemId: string | null,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey:
      kind && itemId
        ? dashboardKeys.workItem(kind, itemId)
        : ["dashboard", "work-item", "disabled"],
    queryFn: async () => {
      if (!kind || !itemId) {
        throw new Error("Missing work-item selection");
      }
      const response = await apiClient.get<WorkItemDetailResponse>(
        `/api/dashboard/work-items/${kind}/${itemId}`,
      );
      return response.data;
    },
    staleTime: 10_000,
    enabled: Boolean(kind && itemId && (options?.enabled ?? true)),
  });
}
