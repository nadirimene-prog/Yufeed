/**
 * React Query hooks for specialized features
 * (Onchain Risk, Travel Rule, Model Registry, etc.)
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { modelRegistryKeys } from "@/lib/queryKeys";
import apiClient from "@/lib/http";

// ============================================================================
// Onchain Risk
// ============================================================================

const onchainRiskKeys = {
  all: ["onchain-risk"] as const,
  analysis: (params: Record<string, unknown>) =>
    [...onchainRiskKeys.all, "analysis", params] as const,
};

export function useOnchainRisk(params?: { address?: string; chain?: string }) {
  return useQuery({
    queryKey: onchainRiskKeys.analysis(params || {}),
    queryFn: async () => {
      const response = await apiClient.get("/api/onchain-risk", { params });
      return response.data;
    },
    enabled: !!params?.address,
  });
}

// ============================================================================
// Travel Rule
// ============================================================================

const travelRuleKeys = {
  all: ["travel-rule"] as const,
  transfers: (params: Record<string, unknown>) =>
    [...travelRuleKeys.all, "transfers", params] as const,
};

export function useTravelRuleTransfers(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: travelRuleKeys.transfers(params || {}),
    queryFn: async () => {
      const response = await apiClient.get("/api/travel-rule/transfers", {
        params,
      });
      return response.data;
    },
  });
}

export function useCreateTravelRuleTransfer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: any) => {
      const response = await apiClient.post("/api/travel-rule/transfers", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: travelRuleKeys.all });
    },
  });
}

// ============================================================================
// Model Registry
// ============================================================================

export function useModelRegistry(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: modelRegistryKeys.modelsList(params || {}),
    queryFn: async () => {
      const response = await apiClient.get("/api/model-registry/models", {
        params,
      });
      return response.data;
    },
  });
}

export function useModel(id: string) {
  return useQuery({
    queryKey: modelRegistryKeys.modelDetail(id),
    queryFn: async () => {
      const response = await apiClient.get(`/api/model-registry/models/${id}`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useRegisterModel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: any) => {
      const response = await apiClient.post("/api/model-registry/models", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: modelRegistryKeys.models() });
    },
  });
}

// ============================================================================
// AML Scope Analysis
// ============================================================================

const amlScopeKeys = {
  all: ["aml-scope"] as const,
  analysis: () => [...amlScopeKeys.all, "analysis"] as const,
};

export function useAMLScope() {
  return useQuery({
    queryKey: amlScopeKeys.analysis(),
    queryFn: async () => {
      const response = await apiClient.get("/api/compliance/aml-scope");
      return response.data;
    },
  });
}

// ============================================================================
// Compliance Reports
// ============================================================================

const complianceReportKeys = {
  all: ["compliance-reports"] as const,
  report: (params: Record<string, unknown>) =>
    [...complianceReportKeys.all, "report", params] as const,
};

export function useComplianceReport(params?: {
  type?: string;
  period?: string;
}) {
  return useQuery({
    queryKey: complianceReportKeys.report(params || {}),
    queryFn: async () => {
      const response = await apiClient.get("/api/compliance/reports", {
        params,
      });
      return response.data;
    },
  });
}

export function useGenerateComplianceReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: any) => {
      const response = await apiClient.post("/api/compliance/reports", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: complianceReportKeys.all });
    },
  });
}

// ============================================================================
// SAR Preparation
// ============================================================================

const sarKeys = {
  all: ["sar"] as const,
  draft: (id: string) => [...sarKeys.all, "draft", id] as const,
  templates: () => [...sarKeys.all, "templates"] as const,
};

export function useSARDraft(id?: string) {
  return useQuery({
    queryKey: sarKeys.draft(id || "new"),
    queryFn: async () => {
      if (!id) return null;
      const response = await apiClient.get(`/api/sar/drafts/${id}`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useSARTemplates() {
  return useQuery({
    queryKey: sarKeys.templates(),
    queryFn: async () => {
      const response = await apiClient.get("/api/sar/templates");
      return response.data;
    },
  });
}

export function useCreateSARDraft() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: any) => {
      const response = await apiClient.post("/api/sar/drafts", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sarKeys.all });
    },
  });
}

export function useUpdateSARDraft() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: any }) => {
      const response = await apiClient.put(`/api/sar/drafts/${id}`, data);
      return response.data;
    },
    onSuccess: (updated: unknown, variables: { id: string; data: unknown }) => {
      queryClient.setQueryData(sarKeys.draft(variables.id), updated);
    },
  });
}

export function useSubmitSAR() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const response = await apiClient.post(`/api/sar/drafts/${id}/submit`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sarKeys.all });
    },
  });
}
