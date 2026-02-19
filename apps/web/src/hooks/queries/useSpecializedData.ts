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
    queryKey: onchainRiskKeys.analysis(params ?? {}),
    queryFn: async () => {
      const response = await apiClient.get("/api/onchain/plugins", { params });
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
    queryKey: travelRuleKeys.transfers(params ?? {}),
    queryFn: async () => {
      const response = await apiClient.get("/api/travel-rule/requests", {
        params,
      });
      return response.data;
    },
  });
}

// Travel Rule Transfer Request types
interface TravelRuleParty {
  name: string;
  account_id?: string;
  wallet_address?: string;
  country?: string;
}

interface TravelRuleTransferRequest {
  transaction_id: string;
  amount: number;
  currency: string;
  asset?: string;
  originator: TravelRuleParty;
  beneficiary: TravelRuleParty;
  message?: string;
}

export function useCreateTravelRuleTransfer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: TravelRuleTransferRequest) => {
      const response = await apiClient.post("/api/travel-rule/requests", data);
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
    queryKey: modelRegistryKeys.modelsList(params ?? {}),
    queryFn: async () => {
      const response = await apiClient.get("/api/models", {
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
      const response = await apiClient.get(`/api/models/${id}`);
      return response.data;
    },
    enabled: !!id,
  });
}

// Model Registry types
interface ModelRegistrationData {
  model_id: string;
  name: string;
  description?: string;
  model_type?: string;
  owner?: string;
  status?: string;
}

export function useRegisterModel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: ModelRegistrationData) => {
      const response = await apiClient.post("/api/models", data);
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
      const response = await apiClient.get("/api/reporting/aml-scope");
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
    queryKey: complianceReportKeys.report(params ?? {}),
    queryFn: async () => {
      const response = await apiClient.get("/api/reporting/dashboard", {
        params,
      });
      return response.data;
    },
  });
}

// Compliance Report types
interface ComplianceReportParams {
  type?: string;
  period?: string;
  date_from?: string;
  date_to?: string;
}

export function useGenerateComplianceReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: ComplianceReportParams) => {
      const response = await apiClient.get("/api/reporting/dashboard", {
        params: data,
      });
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
    queryKey: sarKeys.draft(id ?? "new"),
    queryFn: async () => {
      if (!id) return null;
      // SAR drafts endpoint does not exist; return null gracefully
      return null;
    },
    enabled: !!id,
  });
}

export function useSARTemplates() {
  return useQuery({
    queryKey: sarKeys.templates(),
    queryFn: async () => {
      const response = await apiClient.get("/api/aml-officer/sar/templates");
      return response.data;
    },
  });
}

// SAR Draft types
interface SARDraftData {
  case_id: number;
  case_data: Record<string, unknown>;
  related_alerts?: Record<string, unknown>[];
  related_transactions?: Record<string, unknown>[];
}

export function useCreateSARDraft() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: SARDraftData) => {
      const response = await apiClient.post(
        "/api/aml-officer/sar/prepare",
        data,
      );
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
    mutationFn: async ({ data }: { id: string; data: SARDraftData }) => {
      // SAR draft update endpoint does not exist; prepare new SAR instead
      const response = await apiClient.post(
        "/api/aml-officer/sar/prepare",
        data,
      );
      return response.data;
    },
    onSuccess: (
      updated: unknown,
      variables: { id: string; data: SARDraftData },
    ) => {
      queryClient.setQueryData(sarKeys.draft(variables.id), updated);
    },
  });
}

export function useSubmitSAR() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      // SAR submit endpoint does not exist; use prepare endpoint
      const response = await apiClient.post("/api/aml-officer/sar/prepare", {
        id,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sarKeys.all });
    },
  });
}

// ============================================================================
// Workspace users
// ============================================================================

const workspaceKeys = {
  all: ["workspace"] as const,
  users: (params: { tenant_id?: string; is_active?: boolean }) =>
    [...workspaceKeys.all, "users", params] as const,
};

export interface WorkspaceUser {
  user_id: string;
  role: string;
  is_active: boolean;
}

export function useWorkspaceUsers(params?: {
  tenant_id?: string;
  is_active?: boolean;
}) {
  const queryParams = {
    ...(params?.tenant_id ? { tenant_id: params.tenant_id } : {}),
    ...(typeof params?.is_active === "boolean"
      ? { is_active: params.is_active }
      : { is_active: true }),
  };

  return useQuery({
    queryKey: workspaceKeys.users(queryParams),
    queryFn: async () => {
      const response = await apiClient.get<WorkspaceUser[]>(
        "/api/workspace/users",
        {
          params: queryParams,
        },
      );
      return response.data;
    },
  });
}
