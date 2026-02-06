"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import apiClient from "@/lib/http";
import { handleApiError } from "@/lib/api-error-handler";
import ObligationApprovalModal from "@/components/compliance/ObligationApprovalModal";
import type { Obligation, Policy, PolicySection } from "@/types/compliance";
import { getPolicies, getPolicySections } from "@/lib/compliance-api";
import ObligationHeader from "@/app/compliance/obligations/[id]/components/ObligationHeader";
import ObligationSummary from "@/app/compliance/obligations/[id]/components/ObligationSummary";
import ObligationReview from "@/app/compliance/obligations/[id]/components/ObligationReview";
import InternalRulesManager from "@/app/compliance/obligations/[id]/components/InternalRulesManager";
import LinkedPolicyCard from "@/app/compliance/obligations/[id]/components/LinkedPolicyCard";
import LinkedRisksList from "@/app/compliance/obligations/[id]/components/LinkedRisksList";
import type { InternalRule } from "@/app/compliance/obligations/[id]/components/types";

export default function ObligationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = Array.isArray(params?.id) ? params.id[0] : params?.id;
  const [data, setData] = useState<Obligation | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [policiesLoading, setPoliciesLoading] = useState(true);
  const [sections, setSections] = useState<PolicySection[]>([]);
  const [sectionsLoading, setSectionsLoading] = useState(false);
  const [internalRules, setInternalRules] = useState<InternalRule[]>([]);
  const [rulesLoading, setRulesLoading] = useState(true);
  const [reviewNote, setReviewNote] = useState("");
  const [ruleForm, setRuleForm] = useState({
    name: "",
    description: "",
    control_owner: "",
    status: "draft",
    policy_id: "",
    policy_section_id: "",
  });
  const [mappingForm, setMappingForm] = useState<Record<number, { target: string; mappingType: string }>>({});
  const [rulesActionLoading, setRulesActionLoading] = useState<string | null>(null);
  const [showApprovalModal, setShowApprovalModal] = useState(false);

  useEffect(() => {
    let mounted = true;
    const fetchDetail = async () => {
      if (!id) return;
      setLoading(true);
      try {
        const response = await apiClient.get(`/api/obligations/${id}`);
        if (mounted) {
          setData(response.data);
        }
      } catch (err) {
        handleApiError(err, { context: "Obligation detail", customMessage: "Failed to load obligation" });
      } finally {
        if (mounted) setLoading(false);
      }
    };
    fetchDetail();
    return () => {
      mounted = false;
    };
  }, [id]);

  useEffect(() => {
    let mounted = true;
    const fetchPolicies = async () => {
      setPoliciesLoading(true);
      try {
        const response = await getPolicies({ skip: 0, limit: 200 });
        if (!mounted) return;
        setPolicies(response.items || []);
      } catch (err) {
        handleApiError(err, { context: "Policies list", customMessage: "Failed to load policies" });
      } finally {
        if (mounted) {
          setPoliciesLoading(false);
        }
      }
    };
    fetchPolicies();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!ruleForm.policy_id) {
      setSections([]);
      setSectionsLoading(false);
      return;
    }
    let mounted = true;
    const fetchSections = async () => {
      setSectionsLoading(true);
      try {
        const response = await getPolicySections(Number(ruleForm.policy_id));
        if (!mounted) return;
        setSections(response.items || []);
      } catch (err) {
        handleApiError(err, { context: "Policy sections", customMessage: "Failed to load policy sections" });
      } finally {
        if (mounted) setSectionsLoading(false);
      }
    };
    fetchSections();
    return () => {
      mounted = false;
    };
  }, [ruleForm.policy_id]);

  const fetchInternalRules = async () => {
    if (!id) return;
    setRulesLoading(true);
    try {
      const response = await apiClient.get(`/api/compliance/obligations/${id}/internal-rules`);
      setInternalRules(response.data.items || []);
    } catch (err) {
      handleApiError(err, { context: "Internal rules", customMessage: "Failed to load internal rules" });
    } finally {
      setRulesLoading(false);
    }
  };

  useEffect(() => {
    fetchInternalRules();
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  const createInternalRule = async () => {
    if (!id || !ruleForm.name.trim()) return;
    setRulesActionLoading("create");
    try {
      const payload: Record<string, unknown> = {
        name: ruleForm.name.trim(),
        description: ruleForm.description.trim() || undefined,
        control_owner: ruleForm.control_owner.trim() || undefined,
        status: ruleForm.status,
      };
      if (ruleForm.policy_section_id) {
        payload.policy_section_id = Number(ruleForm.policy_section_id);
      }
      await apiClient.post(`/api/compliance/obligations/${id}/internal-rules`, payload);
      setRuleForm({
        name: "",
        description: "",
        control_owner: "",
        status: "draft",
        policy_id: ruleForm.policy_id,
        policy_section_id: "",
      });
      await fetchInternalRules();
    } catch (err) {
      handleApiError(err, { context: "Create internal rule", customMessage: "Failed to create internal rule" });
    } finally {
      setRulesActionLoading(null);
    }
  };

  const addMapping = async (ruleId: number) => {
    const mapping = mappingForm[ruleId];
    if (!mapping || !mapping.target.trim()) return;
    setRulesActionLoading(`map-${ruleId}`);
    try {
      const trimmed = mapping.target.trim();
      const payload: Record<string, unknown> = {
        mapping_type: mapping.mappingType || "transaction_monitoring",
      };
      if (/^\\d+$/.test(trimmed)) {
        payload.monitoring_rule_id = Number(trimmed);
      } else {
        payload.monitoring_rule_rule_id = trimmed;
      }
      await apiClient.post(`/api/compliance/internal-rules/${ruleId}/mappings`, payload);
      setMappingForm((prev) => ({ ...prev, [ruleId]: { ...prev[ruleId], target: "" } }));
      await fetchInternalRules();
    } catch (err) {
      handleApiError(err, { context: "Create mapping", customMessage: "Failed to add monitoring rule mapping" });
    } finally {
      setRulesActionLoading(null);
    }
  };

  const updateStatus = async (status: string) => {
    if (!id) return;
    setActionLoading(status);
    try {
      const payload: Record<string, unknown> = { status };
      if (reviewNote.trim()) {
        payload.note = reviewNote.trim();
      }
      const response = await apiClient.patch(`/api/obligations/${id}`, payload);
      setData(response.data);
      setReviewNote("");
    } catch (err) {
      handleApiError(err, { context: "Update obligation status" });
    } finally {
      setActionLoading(null);
    }
  };

  const actionsFor = (status?: string) => {
    const normalized = (status || "draft").toLowerCase();
    if (normalized === "draft") {
      return [
        { label: "Send to review", status: "in_review" },
        { label: "Reject", status: "rejected" },
      ];
    }
    if (normalized === "in_review") {
      return [
        { label: "Approve", status: "approved" },
        { label: "Reject", status: "rejected" },
      ];
    }
    if (normalized === "rejected") {
      return [{ label: "Reopen", status: "draft" }];
    }
    return [];
  };

  const handleApprovalSuccess = (updatedObligation: Obligation) => {
    setData((prev) => {
      if (!prev) return updatedObligation;
      return {
        ...prev,
        status: updatedObligation.status,
        review_notes: updatedObligation.review_notes ?? prev.review_notes,
        reviewed_by: updatedObligation.reviewed_by ?? prev.reviewed_by,
        approved_by: updatedObligation.approved_by ?? prev.approved_by,
        approved_at: updatedObligation.approved_at ?? prev.approved_at,
        linked_policy_id: updatedObligation.linked_policy_id,
        linked_policy: updatedObligation.linked_policy,
        linked_risks: updatedObligation.linked_risks,
        linked_risks_count: updatedObligation.linked_risks_count,
        internal_rules_count: updatedObligation.internal_rules_count,
      };
    });
    fetchInternalRules(); // Refresh internal rules in case one was created
  };

  const canUseEnhancedApproval = ["draft", "in_review"].includes((data?.status || "").toLowerCase());

  if (loading) {
    return <div className="text-sm text-gray-500">Loading obligation…</div>;
  }

  if (!data) {
    return <div className="text-sm text-gray-500">Obligation not found.</div>;
  }

  const actions = actionsFor(data.status);

  return (
    <div className="space-y-6">
      <ObligationHeader
        obligationId={data.obligation_id}
        title={data.document.title}
        celex={data.document.celex || null}
        jurisdiction={data.document.jurisdiction || null}
        sourceSystem={data.document.source_system || null}
        status={data.status}
      />

      <ObligationSummary
        obligationText={data.obligation_text}
        articleRef={data.article_ref || null}
        applicability={data.applicability || null}
        effectiveDate={data.effective_date || null}
        updatedAt={data.updated_at || null}
      />

      <ObligationReview
        reviewNotes={data.review_notes || null}
        reviewNote={reviewNote}
        onReviewNoteChange={setReviewNote}
        canUseEnhancedApproval={canUseEnhancedApproval}
        onEnhancedApproval={() => setShowApprovalModal(true)}
        actions={actions}
        actionLoading={actionLoading}
        onUpdateStatus={updateStatus}
        onViewSourceDoc={() => {
          if (data.document.celex) {
            router.push(`/doc/${data.document.celex}`);
          }
        }}
        createdBy={data.created_by || null}
        reviewedBy={data.reviewed_by || null}
        approvedBy={data.approved_by || null}
        approvedAt={data.approved_at || null}
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

      {data.linked_policy ? <LinkedPolicyCard policy={data.linked_policy} /> : null}

      {data.linked_risks && data.linked_risks.length > 0 ? (
        <LinkedRisksList linkedRisks={data.linked_risks} />
      ) : null}

      {/* Enhanced Approval Modal */}
      <ObligationApprovalModal
        open={showApprovalModal}
        onOpenChange={setShowApprovalModal}
        obligation={data}
        onSuccess={handleApprovalSuccess}
      />
    </div>
  );
}
