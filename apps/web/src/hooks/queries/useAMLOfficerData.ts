/**
 * React Query hooks for AML Officer dashboard data
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { amlOfficerKeys } from '@/lib/queryKeys';
import { amlOfficerApi } from '@/lib/aml-officer-api';

export function useAMLOfficerBriefing() {
  return useQuery({
    queryKey: amlOfficerKeys.briefing(),
    queryFn: () => amlOfficerApi.getBriefing(),
    refetchInterval: 5 * 60 * 1000, // Refresh every 5 minutes
  });
}

export function useAMLOfficerAlerts(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: [...amlOfficerKeys.alerts(), params || {}],
    queryFn: () => amlOfficerApi.getAlerts(params),
  });
}

export function useSARReports(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: amlOfficerKeys.sarList(params || {}),
    queryFn: () => amlOfficerApi.getSARReports(params),
  });
}

export function useCreateSAR() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: any) => amlOfficerApi.createSAR(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: amlOfficerKeys.sar() });
      queryClient.invalidateQueries({ queryKey: amlOfficerKeys.briefing() });
    },
  });
}

export function useSanctionsCheck() {
  return useMutation({
    mutationFn: (data: { name: string; dob?: string; country?: string }) =>
      amlOfficerApi.checkSanctions(data),
  });
}

export function useAMLOfficerAsk() {
  return useMutation({
    mutationFn: (question: string) => amlOfficerApi.ask(question),
  });
}
