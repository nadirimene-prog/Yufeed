/**
 * React Query hooks for Monitoring Rules data management
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { monitoringKeys } from "@/lib/queryKeys";
import apiClient from "@/lib/http";

export function useRules(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: monitoringKeys.rulesList(params || {}),
    queryFn: async () => {
      const response = await apiClient.get("/api/monitoring_rules", { params });
      return response.data;
    },
  });
}

export function useRule(id: string) {
  return useQuery({
    queryKey: monitoringKeys.ruleDetail(id),
    queryFn: async () => {
      const response = await apiClient.get(`/api/monitoring_rules/${id}`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateRule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: any) => {
      const response = await apiClient.post("/api/monitoring_rules", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: monitoringKeys.rules() });
    },
  });
}

export function useUpdateRule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: any }) => {
      const response = await apiClient.put(`/api/monitoring_rules/${id}`, data);
      return response.data;
    },
    onSuccess: (updated, variables) => {
      queryClient.setQueryData(
        monitoringKeys.ruleDetail(variables.id),
        updated,
      );
      queryClient.invalidateQueries({ queryKey: monitoringKeys.rules() });
    },
  });
}

export function useDeleteRule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const response = await apiClient.delete(`/api/monitoring_rules/${id}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: monitoringKeys.rules() });
    },
  });
}

export function useToggleRule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, enabled }: { id: string; enabled: boolean }) => {
      const response = await apiClient.patch(`/api/monitoring_rules/${id}`, {
        enabled,
      });
      return response.data;
    },
    onSuccess: (updated, variables) => {
      queryClient.setQueryData(
        monitoringKeys.ruleDetail(variables.id),
        updated,
      );
      queryClient.invalidateQueries({ queryKey: monitoringKeys.rules() });
    },
  });
}
