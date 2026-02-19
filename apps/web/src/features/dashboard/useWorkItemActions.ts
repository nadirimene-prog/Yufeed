"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/http";
import { dashboardKeys } from "@/lib/queryKeys";
import {
  ReviewActionRequest,
  ReviewActionResponse,
  WorkItemActionType,
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

  const bulkAction = useMutation({
    mutationFn: async (payload: {
      items: Array<{ kind: WorkItemKind; record_id: string }>;
      action: Exclude<WorkItemActionType, "create_case" | "close">;
      assignee?: string;
    }) => {
      const requests = payload.items.map((item) =>
        apiClient.post(
          `/api/dashboard/work-items/${item.kind}/${item.record_id}/actions`,
          {
            action: payload.action,
            assignee:
              payload.action === "assign" ? payload.assignee : undefined,
          },
        ),
      );
      await Promise.all(requests);
      return {
        success: true,
        count: payload.items.length,
      };
    },
    onSuccess: async () => {
      await invalidateDashboard();
    },
  });

  const saveDraft = useMutation({
    mutationFn: async (payload: { narrative: string; notes: string }) => {
      if (!kind || !itemId) {
        throw new Error("No work item selected");
      }
      const response = await apiClient.patch(
        `/api/dashboard/work-items/${kind}/${itemId}`,
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
    bulkAction,
    saveDraft,
  };
}
