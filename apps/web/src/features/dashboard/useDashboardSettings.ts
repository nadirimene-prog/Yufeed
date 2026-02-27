"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/http";
import { dashboardKeys } from "@/lib/queryKeys";
import type {
  DashboardPreferencesResponse,
  DashboardPreferencesUpdateRequest,
  DashboardSavedViewCreateRequest,
  DashboardSavedViewRecord,
  DashboardSavedViewsResponse,
  DashboardSavedViewUpdateRequest,
} from "@/features/dashboard/types";

export function useDashboardSavedViews(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: dashboardKeys.savedViews(),
    queryFn: async () => {
      const response = await apiClient.get<DashboardSavedViewsResponse>(
        "/api/dashboard/views",
      );
      return response.data;
    },
    staleTime: 30_000,
    refetchInterval: 60_000,
    enabled: options?.enabled ?? true,
  });
}

export function useDashboardPreferences(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: dashboardKeys.preferences(),
    queryFn: async () => {
      const response = await apiClient.get<DashboardPreferencesResponse>(
        "/api/dashboard/preferences",
      );
      return response.data;
    },
    staleTime: 30_000,
    refetchInterval: 60_000,
    enabled: options?.enabled ?? true,
  });
}

export function useDashboardSavedViewMutations() {
  const queryClient = useQueryClient();

  const invalidate = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: dashboardKeys.savedViews() }),
      queryClient.invalidateQueries({ queryKey: dashboardKeys.preferences() }),
    ]);
  };

  const createSavedView = useMutation({
    mutationFn: async (payload: DashboardSavedViewCreateRequest) => {
      const response = await apiClient.post<DashboardSavedViewRecord>(
        "/api/dashboard/views",
        payload,
      );
      return response.data;
    },
    onSuccess: invalidate,
  });

  const updateSavedView = useMutation({
    mutationFn: async (payload: {
      id: string;
      patch: DashboardSavedViewUpdateRequest;
    }) => {
      const response = await apiClient.patch<DashboardSavedViewRecord>(
        `/api/dashboard/views/${encodeURIComponent(payload.id)}`,
        payload.patch,
      );
      return response.data;
    },
    onSuccess: invalidate,
  });

  const deleteSavedView = useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/api/dashboard/views/${encodeURIComponent(id)}`);
      return { id };
    },
    onSuccess: invalidate,
  });

  return {
    createSavedView,
    updateSavedView,
    deleteSavedView,
  };
}

export function useDashboardPreferencesMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: DashboardPreferencesUpdateRequest) => {
      const response = await apiClient.patch<DashboardPreferencesResponse>(
        "/api/dashboard/preferences",
        payload,
      );
      return response.data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: dashboardKeys.preferences(),
      });
      await queryClient.invalidateQueries({
        queryKey: dashboardKeys.savedViews(),
      });
    },
  });
}
