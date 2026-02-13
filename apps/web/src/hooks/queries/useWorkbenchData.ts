"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getFindings,
  getFinding,
  closeFinding,
  escalateFinding,
  acknowledgeFinding,
  getCaseDecisions,
  createCaseDecision,
  submitCaseDecision,
  approveCaseDecision,
  rejectCaseDecision,
  getEvidencePacks,
  getEvidencePackDetail,
  createEvidencePack,
} from "@/lib/workbench-api";
import { workbenchKeys } from "@/lib/queryKeys";
import type { FindingListParams, DecisionListParams } from "@/types/workbench";

// ─── Finding Queries ────────────────────────────────────────────
export function useFindings(params?: FindingListParams) {
  const queryParams = {
    limit: params?.limit ?? 50,
    ...(params?.status != null && params.status.length > 0
      ? { status: params.status }
      : {}),
    ...(params?.severity != null && params.severity.length > 0
      ? { severity: params.severity }
      : {}),
    ...(params?.finding_type != null && params.finding_type.length > 0
      ? { finding_type: params.finding_type }
      : {}),
    ...(params?.assigned_to != null && params.assigned_to.length > 0
      ? { assigned_to: params.assigned_to }
      : {}),
  };

  return useQuery({
    queryKey: workbenchKeys.findingsList(queryParams),
    queryFn: () => getFindings(queryParams),
  });
}

export function useFinding(id: number) {
  return useQuery({
    queryKey: workbenchKeys.findingDetail(id),
    queryFn: () => getFinding(id),
    enabled: id > 0,
  });
}

// ─── Finding Mutations ──────────────────────────────────────────
export function useCloseFinding() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      reason,
      comment,
    }: {
      id: number;
      reason: string;
      comment: string;
    }) => closeFinding(id, { closed_reason: reason, closed_comment: comment }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workbenchKeys.findings() });
    },
  });
}

export function useEscalateFinding() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, case_id }: { id: number; case_id: string }) =>
      escalateFinding(id, { existing_case_id: case_id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workbenchKeys.findings() });
    },
  });
}

export function useAcknowledgeFinding() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => acknowledgeFinding(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workbenchKeys.findings() });
    },
  });
}

// ─── Decision Queries ───────────────────────────────────────────
export function useCaseDecisions(caseId: string, params?: DecisionListParams) {
  const queryParams = {
    limit: params?.limit ?? 50,
    ...(params?.status != null && params.status.length > 0
      ? { status: params.status }
      : {}),
  };

  return useQuery({
    queryKey: workbenchKeys.decisionsList(caseId, queryParams),
    queryFn: () => getCaseDecisions(caseId, queryParams),
    enabled: caseId.length > 0,
  });
}

// ─── Decision Mutations ─────────────────────────────────────────
export function useCreateDecision(caseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { disposition: string; rationale: string }) =>
      createCaseDecision(caseId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: workbenchKeys.decisions(caseId),
      });
    },
  });
}

export function useSubmitDecision(caseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      decisionId,
      rationale,
    }: {
      decisionId: number;
      rationale: string;
    }) => submitCaseDecision(caseId, decisionId, { rationale }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: workbenchKeys.decisions(caseId),
      });
    },
  });
}

export function useApproveDecision(caseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      decisionId,
      comment,
    }: {
      decisionId: number;
      comment?: string;
    }) =>
      approveCaseDecision(
        caseId,
        decisionId,
        comment != null && comment.length > 0 ? { comment } : undefined,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: workbenchKeys.decisions(caseId),
      });
    },
  });
}

export function useRejectDecision(caseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      decisionId,
      reason,
    }: {
      decisionId: number;
      reason: string;
    }) => rejectCaseDecision(caseId, decisionId, { rejection_reason: reason }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: workbenchKeys.decisions(caseId),
      });
    },
  });
}

// ─── Evidence Pack Queries ──────────────────────────────────────
export function useEvidencePacks(caseId: string) {
  return useQuery({
    queryKey: workbenchKeys.evidencePacksList(caseId, {}),
    queryFn: () => getEvidencePacks(caseId),
    enabled: caseId.length > 0,
  });
}

export function useEvidencePackDetail(caseId: string, packId: string) {
  return useQuery({
    queryKey: workbenchKeys.evidencePackDetail(caseId, packId),
    queryFn: () => getEvidencePackDetail(caseId, packId),
    enabled: caseId.length > 0 && packId.length > 0,
  });
}

export function useCreateEvidencePack(caseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (format: string = "json") =>
      createEvidencePack(caseId, { format }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: workbenchKeys.evidencePacks(caseId),
      });
    },
  });
}
