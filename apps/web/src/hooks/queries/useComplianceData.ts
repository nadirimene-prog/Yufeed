"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  approveObligation,
  getObligation,
  getObligations,
  getPolicies,
  getRiskMap,
  updateObligationStatus,
} from "@/lib/compliance-api";
import { complianceKeys, dashboardKeys } from "@/lib/queryKeys";
import type { ObligationsListResponse } from "@/lib/compliance-api";
import type { DashboardOverviewResponse } from "@/features/dashboard/types";
import apiClient from "@/lib/http";

const DASHBOARD_OBLIGATIONS_PARAMS = {
  limit: 10,
  include_status_counts: true,
} as const;
const DASHBOARD_POLICIES_PARAMS = { limit: 10 } as const;

export function useComplianceDashboard() {
  const overviewQuery = useQuery({
    queryKey: dashboardKeys.overview("compliance", "7d"),
    queryFn: async () => {
      const response = await apiClient.get<DashboardOverviewResponse>(
        "/api/dashboard/overview",
        {
          params: { view: "compliance", time_range: "7d" },
        },
      );
      return response.data;
    },
  });

  const obligationsQuery = useQuery({
    queryKey: complianceKeys.obligationsList(DASHBOARD_OBLIGATIONS_PARAMS),
    queryFn: () => getObligations(DASHBOARD_OBLIGATIONS_PARAMS),
  });

  const policiesQuery = useQuery({
    queryKey: complianceKeys.policiesList(DASHBOARD_POLICIES_PARAMS),
    queryFn: () => getPolicies(DASHBOARD_POLICIES_PARAMS),
  });

  const riskMapQuery = useQuery({
    queryKey: complianceKeys.riskMap(),
    queryFn: () => getRiskMap(),
  });

  const errors = [
    overviewQuery.error,
    obligationsQuery.error,
    policiesQuery.error,
    riskMapQuery.error,
  ].filter(Boolean) as Error[];

  return {
    data: {
      overview: overviewQuery.data,
      obligations: obligationsQuery.data,
      policies: policiesQuery.data,
      riskMap: riskMapQuery.data,
    },
    isLoading:
      overviewQuery.isLoading ||
      obligationsQuery.isLoading ||
      policiesQuery.isLoading ||
      riskMapQuery.isLoading,
    isError:
      overviewQuery.isError ||
      obligationsQuery.isError ||
      policiesQuery.isError ||
      riskMapQuery.isError,
    errors,
    queries: {
      overviewQuery,
      obligationsQuery,
      policiesQuery,
      riskMapQuery,
    },
  };
}

export function useObligation(id: number | null) {
  return useQuery({
    queryKey:
      typeof id === "number"
        ? complianceKeys.obligationDetail(id)
        : ["compliance", "obligations", "detail", "disabled"],
    queryFn: () => {
      if (typeof id !== "number") {
        throw new Error("Obligation id is required");
      }
      return getObligation(id);
    },
    enabled: typeof id === "number",
  });
}

export function useObligationsList(params: {
  status?: string;
  jurisdiction?: string;
  source_system?: string;
  scope?: string;
  q?: string;
  include_status_counts?: boolean;
  skip?: number;
  limit?: number;
}): {
  data: ObligationsListResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
} {
  const query = useQuery({
    queryKey: complianceKeys.obligationsList(params),
    queryFn: () => getObligations(params),
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    error: (query.error as Error | null) ?? null,
  };
}

export function useApproveObligation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: number;
      data: Parameters<typeof approveObligation>[1];
    }) => approveObligation(id, data),
    onSuccess: (updated) => {
      queryClient.setQueryData(
        complianceKeys.obligationDetail(updated.id),
        updated,
      );
      queryClient.invalidateQueries({ queryKey: complianceKeys.obligations() });
    },
  });
}

export function useUpdateObligationStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      status,
      note,
    }: {
      id: number;
      status: string;
      note?: string;
    }) => updateObligationStatus(id, { status, note }),
    onSuccess: (updated) => {
      queryClient.setQueryData(
        complianceKeys.obligationDetail(updated.id),
        updated,
      );
      queryClient.invalidateQueries({ queryKey: complianceKeys.obligations() });
    },
  });
}
