"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createComplianceInternalRule,
  createComplianceInternalRuleMapping,
  getObligationInternalRules,
} from "@/lib/compliance-api";
import { complianceKeys } from "@/lib/queryKeys";
import type {
  InternalRuleCreatePayload,
  InternalRuleMappingCreatePayload,
} from "@/types/compliance-workflow";

const DISABLED_INTERNAL_RULES_KEY = [
  "compliance",
  "obligations",
  "internal_rules",
  "disabled",
] as const;

export function useObligationInternalRules(obligationId: number | null) {
  return useQuery({
    queryKey:
      typeof obligationId === "number"
        ? complianceKeys.obligationInternalRules(obligationId)
        : DISABLED_INTERNAL_RULES_KEY,
    queryFn: () => {
      if (typeof obligationId !== "number") {
        throw new Error("Obligation id is required");
      }
      return getObligationInternalRules(obligationId);
    },
    enabled: typeof obligationId === "number",
  });
}

export function useCreateComplianceInternalRule(obligationId: number | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: InternalRuleCreatePayload) => {
      if (typeof obligationId !== "number") {
        throw new Error("Obligation id is required");
      }
      return createComplianceInternalRule(obligationId, payload);
    },
    onSuccess: () => {
      if (typeof obligationId === "number") {
        queryClient.invalidateQueries({
          queryKey: complianceKeys.obligationInternalRules(obligationId),
        });
        queryClient.invalidateQueries({
          queryKey: complianceKeys.obligationDetail(obligationId),
        });
        queryClient.invalidateQueries({
          queryKey: complianceKeys.obligations(),
        });
      }
    },
  });
}

export function useCreateComplianceInternalRuleMapping(
  obligationId: number | null,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      internalRuleId,
      payload,
    }: {
      internalRuleId: number;
      payload: InternalRuleMappingCreatePayload;
    }) => createComplianceInternalRuleMapping(internalRuleId, payload),
    onSuccess: () => {
      if (typeof obligationId === "number") {
        queryClient.invalidateQueries({
          queryKey: complianceKeys.obligationInternalRules(obligationId),
        });
        queryClient.invalidateQueries({
          queryKey: complianceKeys.obligationDetail(obligationId),
        });
      }
    },
  });
}
