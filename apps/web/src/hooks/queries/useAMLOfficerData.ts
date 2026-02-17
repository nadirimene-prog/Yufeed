/**
 * React Query hooks for AML Officer dashboard data
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { amlOfficerKeys } from "@/lib/queryKeys";
import { amlOfficerApi } from "@/lib/aml-officer-api";

export function useAMLOfficerBriefing() {
  return useQuery({
    queryKey: amlOfficerKeys.briefing(),
    queryFn: () => amlOfficerApi.getDailyBriefing(),
    refetchInterval: 5 * 60 * 1000, // Refresh every 5 minutes
  });
}

export function useAMLOfficerAlerts() {
  return useQuery({
    queryKey: amlOfficerKeys.alerts(),
    queryFn: () => amlOfficerApi.getProactiveAlerts(),
  });
}

export function useSARTemplates() {
  return useQuery({
    queryKey: amlOfficerKeys.sar(),
    queryFn: () => amlOfficerApi.getSARTemplates(),
  });
}

export function usePrepareSAR() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      caseId: number;
      caseData: Record<string, unknown>;
      relatedAlerts?: Record<string, unknown>[];
      relatedTransactions?: Record<string, unknown>[];
    }) =>
      amlOfficerApi.prepareSAR(
        data.caseId,
        data.caseData,
        data.relatedAlerts,
        data.relatedTransactions,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: amlOfficerKeys.sar() });
      queryClient.invalidateQueries({ queryKey: amlOfficerKeys.briefing() });
    },
  });
}

export function useSanctionsCheck() {
  return useMutation({
    mutationFn: (data: { name: string; dob?: string; country?: string }) =>
      amlOfficerApi.screenSanctions({
        name: data.name,
        birth_date: data.dob,
        nationality: data.country,
      }),
  });
}

export function useAMLOfficerAsk() {
  return useMutation({
    mutationFn: (question: string) => amlOfficerApi.askQuestion({ question }),
  });
}

export function useInvestigateAlert() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      alertId: number;
      alertData: Record<string, unknown>;
      relatedTransactions?: Record<string, unknown>[];
      relatedRegulations?: Record<string, unknown>[];
    }) =>
      amlOfficerApi.investigateAlert({
        alert_id: data.alertId,
        alert_data: data.alertData,
        related_transactions: data.relatedTransactions,
        related_regulations: data.relatedRegulations,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: amlOfficerKeys.briefing() });
    },
  });
}

export function useBatchInvestigate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      alerts: Record<string, unknown>[];
      maxConcurrent?: number;
    }) => amlOfficerApi.batchInvestigate(data.alerts, data.maxConcurrent),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: amlOfficerKeys.briefing() });
    },
  });
}
