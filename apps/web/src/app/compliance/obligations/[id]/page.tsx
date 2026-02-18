"use client";

export const dynamic = "force-dynamic";

import { useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { handleApiError } from "@/lib/api-error-handler";
import { getAuthUserProfile } from "@/lib/auth";
import ObligationApprovalModal from "@/components/compliance/ObligationApprovalModal";
import type { Obligation } from "@/types/compliance";
import { getPolicies, getPolicySections } from "@/lib/compliance-api";
import { complianceKeys } from "@/lib/queryKeys";
import {
  useObligation,
  useUpdateObligationStatus,
} from "@/hooks/queries/useComplianceData";
import {
  useCreateComplianceInternalRule,
  useCreateComplianceInternalRuleMapping,
  useObligationInternalRules,
} from "@/hooks/queries/useComplianceWorkflowData";
import ObligationHeader from "@/app/compliance/obligations/[id]/components/ObligationHeader";
import ObligationSummary from "@/app/compliance/obligations/[id]/components/ObligationSummary";
import ObligationReview from "@/app/compliance/obligations/[id]/components/ObligationReview";
import InternalRulesManager from "@/app/compliance/obligations/[id]/components/InternalRulesManager";
import LinkedPolicyCard from "@/app/compliance/obligations/[id]/components/LinkedPolicyCard";
import LinkedRisksList from "@/app/compliance/obligations/[id]/components/LinkedRisksList";
import type { InternalRuleMappingCreatePayload } from "@/types/compliance-workflow";
import { logger } from "@/lib/logger";

const POLICIES_PARAMS = { skip: 0, limit: 200 } as const;
const DISABLED_POLICY_SECTIONS_KEY = [
  "compliance",
  "policies",
  "sections",
  "disabled",
] as const;

export default function ObligationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const idParam = Array.isArray(params?.id) ? params.id[0] : params?.id;

  // Robust ID parsing: checks if it's a valid number
  const parsedId = Number(idParam);
  const obligationId = !isNaN(parsedId) && parsedId > 0 ? parsedId : null;

  const queryClient = useQueryClient();
  const obligationQuery = useObligation(obligationId);
  const obligation = obligationQuery.data ?? null;

  const internalRulesQuery = useObligationInternalRules(obligationId);
  const internalRules = internalRulesQuery.data?.items ?? [];
  const rulesLoading = internalRulesQuery.isLoading;

  const updateObligationStatusMutation = useUpdateObligationStatus();
  const createInternalRuleMutation =
    useCreateComplianceInternalRule(obligationId);
  const createMappingMutation =
    useCreateComplianceInternalRuleMapping(obligationId);

  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [reviewNote, setReviewNote] = useState("");
  const [ruleForm, setRuleForm] = useState({
    name: "",
    description: "",
    control_owner: "",
    status: "draft",
    policy_id: "",
    policy_section_id: "",
  });
  const [mappingForm, setMappingForm] = useState<
    Record<number, { target: string; mappingType: string }>
  >({});
  const [rulesActionLoading, setRulesActionLoading] = useState<string | null>(
    null,
  );
  const [showApprovalModal, setShowApprovalModal] = useState(false);
  const currentUser = useMemo(() => getAuthUserProfile(), []);

  const policiesQuery = useQuery({
    queryKey: complianceKeys.policiesList(POLICIES_PARAMS),
    queryFn: () => getPolicies(POLICIES_PARAMS),
  });

  const policies = policiesQuery.data?.items ?? [];
  const policiesLoading = policiesQuery.isLoading;

  const selectedPolicyId = ruleForm.policy_id
    ? Number(ruleForm.policy_id)
    : null;
  const policySectionsQuery = useQuery({
    queryKey:
      typeof selectedPolicyId === "number"
        ? complianceKeys.policySections(selectedPolicyId)
        : DISABLED_POLICY_SECTIONS_KEY,
    queryFn: () => {
      if (typeof selectedPolicyId !== "number") {
        throw new Error("Policy id is required");
      }
      return getPolicySections(selectedPolicyId);
    },
    enabled: typeof selectedPolicyId === "number",
  });

  const sections =
    typeof selectedPolicyId === "number"
      ? (policySectionsQuery.data?.items ?? [])
      : [];
  const sectionsLoading =
    typeof selectedPolicyId === "number"
      ? policySectionsQuery.isLoading
      : false;

  const createInternalRule = async () => {
    if (typeof obligationId !== "number" || !ruleForm.name.trim()) return;
    setRulesActionLoading("create");
    try {
      await createInternalRuleMutation.mutateAsync({
        name: ruleForm.name.trim(),
        description: ruleForm.description.trim() || undefined,
        control_owner: ruleForm.control_owner.trim() || undefined,
        status: ruleForm.status,
        policy_section_id: ruleForm.policy_section_id
          ? Number(ruleForm.policy_section_id)
          : undefined,
      });
      setRuleForm({
        name: "",
        description: "",
        control_owner: "",
        status: "draft",
        policy_id: ruleForm.policy_id,
        policy_section_id: "",
      });
    } catch (err) {
      handleApiError(err, {
        context: "Create internal rule",
        customMessage: "Failed to create internal rule",
      });
    } finally {
      setRulesActionLoading(null);
    }
  };

  const addMapping = async (ruleId: number) => {
    const mapping = mappingForm[ruleId];
    if (!mapping?.target.trim()) return;
    setRulesActionLoading(`map-${ruleId}`);
    try {
      const trimmed = mapping.target.trim();
      const payload: InternalRuleMappingCreatePayload = {
        mapping_type: mapping.mappingType || "transaction_monitoring",
      };
      if (/^\\d+$/.test(trimmed)) {
        payload.monitoring_rule_id = Number(trimmed);
      } else {
        payload.monitoring_rule_rule_id = trimmed;
      }
      await createMappingMutation.mutateAsync({
        internalRuleId: ruleId,
        payload,
      });
      setMappingForm((prev) => ({
        ...prev,
        [ruleId]: { ...prev[ruleId], target: "" },
      }));
    } catch (err) {
      handleApiError(err, {
        context: "Create mapping",
        customMessage: "Failed to add monitoring rule mapping",
      });
    } finally {
      setRulesActionLoading(null);
    }
  };

  const updateStatus = async (status: string) => {
    if (typeof obligationId !== "number") return;
    setActionLoading(status);
    try {
      await updateObligationStatusMutation.mutateAsync({
        id: obligationId,
        status,
        note: reviewNote.trim() ? reviewNote.trim() : undefined,
      });
      setReviewNote("");
    } catch (err) {
      handleApiError(err, { context: "Update obligation status" });
    } finally {
      setActionLoading(null);
    }
  };

  const isCurrentUserCreator = (createdBy?: string | null) => {
    const actor = createdBy?.trim().toLowerCase();
    if (!actor) return false;
    const aliases = [currentUser?.email, currentUser?.userId]
      .filter((value): value is string => typeof value === "string")
      .map((value) => value.trim().toLowerCase())
      .filter(Boolean);
    return aliases.includes(actor);
  };

  const actionsFor = (status?: string, createdBy?: string | null) => {
    const normalized = (status ?? "draft").toLowerCase();
    if (normalized === "draft") {
      return [
        { label: "Send to review", status: "in_review" },
        { label: "Reject", status: "rejected" },
      ];
    }
    if (normalized === "in_review") {
      const actions = [{ label: "Reject", status: "rejected" }];
      if (!isCurrentUserCreator(createdBy)) {
        actions.unshift({ label: "Approve", status: "approved" });
      }
      return actions;
    }
    if (normalized === "rejected") {
      return [{ label: "Reopen", status: "draft" }];
    }
    return [];
  };

  const handleApprovalSuccess = (updatedObligation: Obligation) => {
    queryClient.setQueryData(
      complianceKeys.obligationDetail(updatedObligation.id),
      updatedObligation,
    );
    queryClient.invalidateQueries({ queryKey: complianceKeys.obligations() });
    queryClient.invalidateQueries({
      queryKey: complianceKeys.obligationInternalRules(updatedObligation.id),
    });
  };

  const canUseEnhancedApproval = ["draft", "in_review"].includes(
    (obligation?.status || "").toLowerCase(),
  );

  if (obligationId === null) {
    return <div className="text-sm text-gray-500">Invalid obligation id.</div>;
  }

  if (obligationQuery.isLoading) {
    return <div className="text-sm text-gray-500">Loading obligation…</div>;
  }

  if (obligationQuery.isError) {
    logger.error("Failed to load obligation detail", obligationQuery.error);
    return (
      <div className="text-sm text-gray-500">Failed to load obligation.</div>
    );
  }

  if (!obligation) {
    return <div className="text-sm text-gray-500">Obligation not found.</div>;
  }

  const actions = actionsFor(obligation.status, obligation.created_by);

  return (
    <div className="space-y-6">
      <ObligationHeader
        obligationId={obligation.obligation_id}
        title={obligation.document.title}
        celex={obligation.document.celex ?? null}
        jurisdiction={obligation.document.jurisdiction ?? null}
        sourceSystem={obligation.document.source_system ?? null}
        status={obligation.status}
      />

      <ObligationSummary
        obligationText={obligation.obligation_text}
        articleRef={obligation.article_ref ?? null}
        applicability={obligation.applicability ?? null}
        effectiveDate={obligation.effective_date ?? null}
        updatedAt={obligation.updated_at ?? null}
      />

      <ObligationReview
        reviewNotes={obligation.review_notes || null}
        reviewNote={reviewNote}
        onReviewNoteChange={setReviewNote}
        canUseEnhancedApproval={canUseEnhancedApproval}
        onEnhancedApproval={() => setShowApprovalModal(true)}
        actions={actions}
        actionLoading={actionLoading}
        onUpdateStatus={updateStatus}
        onViewSourceDoc={() => {
          if (obligation.document.celex) {
            router.push(`/doc/${obligation.document.celex}`);
          }
        }}
        createdBy={obligation.created_by ?? null}
        reviewedBy={obligation.reviewed_by ?? null}
        approvedBy={obligation.approved_by ?? null}
        approvedAt={obligation.approved_at ?? null}
      />

      <InternalRulesManager
        internalRules={internalRules}
        rulesLoading={rulesLoading}
        rulesActionLoading={rulesActionLoading}
        mappingForm={mappingForm}
        setMappingForm={setMappingForm}
        onAddMapping={addMapping}
        ruleForm={ruleForm}
        setRuleForm={setRuleForm}
        policies={policies}
        policiesLoading={policiesLoading}
        sections={sections}
        sectionsLoading={sectionsLoading}
        onCreateInternalRule={createInternalRule}
      />

      {obligation.linked_policy ? (
        <LinkedPolicyCard policy={obligation.linked_policy} />
      ) : null}

      {obligation.linked_risks && obligation.linked_risks.length > 0 ? (
        <LinkedRisksList linkedRisks={obligation.linked_risks} />
      ) : null}

      {/* Enhanced Approval Modal */}
      <ObligationApprovalModal
        open={showApprovalModal}
        onOpenChange={setShowApprovalModal}
        obligation={obligation}
        onSuccess={handleApprovalSuccess}
      />
    </div>
  );
}
