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
import { complianceKeys } from "@/lib/queryKeys";

const DASHBOARD_OBLIGATIONS_PARAMS = { limit: 10, include_status_counts: true } as const;
const DASHBOARD_POLICIES_PARAMS = { limit: 10 } as const;

export function useComplianceDashboard() {
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

  const errors = [obligationsQuery.error, policiesQuery.error, riskMapQuery.error].filter(
    Boolean
  ) as Error[];

  return {
    data: {
      obligations: obligationsQuery.data,
      policies: policiesQuery.data,
      riskMap: riskMapQuery.data,
    },
    isLoading: obligationsQuery.isLoading || policiesQuery.isLoading || riskMapQuery.isLoading,
    isError: obligationsQuery.isError || policiesQuery.isError || riskMapQuery.isError,
    errors,
    queries: {
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

export function useApproveObligation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Parameters<typeof approveObligation>[1] }) =>
      approveObligation(id, data),
    onSuccess: (updated) => {
      queryClient.setQueryData(complianceKeys.obligationDetail(updated.id), updated);
      queryClient.invalidateQueries({ queryKey: complianceKeys.obligations() });
    },
  });
}

export function useUpdateObligationStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, status, note }: { id: number; status: string; note?: string }) =>
      updateObligationStatus(id, { status, note }),
    onSuccess: (updated) => {
      queryClient.setQueryData(complianceKeys.obligationDetail(updated.id), updated);
      queryClient.invalidateQueries({ queryKey: complianceKeys.obligations() });
    },
  });
}
