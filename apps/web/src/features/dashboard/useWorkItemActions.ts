"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/http";
import { dashboardKeys } from "@/lib/queryKeys";
import {
  ReviewActionRequest,
  ReviewActionResponse,
  WorkItemActionRequest,
  WorkItemActionResponse,
  WorkItemKind,
} from "@/features/dashboard/types";

export function useWorkItemActions(
  kind: WorkItemKind | null,
  itemId: string | null,
) {
  const queryClient = useQueryClient();

  const invalidateDashboard = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: dashboardKeys.all }),
      kind && itemId
        ? queryClient.invalidateQueries({
            queryKey: dashboardKeys.workItem(kind, itemId),
          })
        : Promise.resolve(),
    ]);
  };

  const performAction = useMutation({
    mutationFn: async (payload: WorkItemActionRequest) => {
      if (!kind || !itemId) {
        throw new Error("No work item selected");
      }
      const response = await apiClient.post<WorkItemActionResponse>(
        `/api/dashboard/work-items/${kind}/${itemId}/actions`,
        payload,
      );
      return response.data;
    },
    onSuccess: async () => {
      await invalidateDashboard();
    },
  });

  const reviewAction = useMutation({
    mutationFn: async (payload: ReviewActionRequest) => {
      if (!kind || !itemId) {
        throw new Error("No work item selected");
      }
      const response = await apiClient.post<ReviewActionResponse>(
        `/api/dashboard/work-items/${kind}/${itemId}/review`,
        payload,
      );
      return response.data;
    },
    onSuccess: async () => {
      await invalidateDashboard();
    },
  });

  return {
    performAction,
    reviewAction,
  };
}
