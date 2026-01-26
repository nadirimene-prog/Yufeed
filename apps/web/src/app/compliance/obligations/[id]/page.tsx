"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import apiClient from "@/lib/http";
import { handleApiError } from "@/lib/api-error-handler";

interface ObligationDetail {
  id: number;
  obligation_id: string;
  status: string;
  article_ref?: string | null;
  obligation_text: string;
  applicability?: string | null;
  effective_date?: string | null;
  created_by?: string | null;
  reviewed_by?: string | null;
  approved_by?: string | null;
  approved_at?: string | null;
  review_notes?: string | null;
  updated_at?: string | null;
  document: {
    id: number;
    celex: string;
    title: string;
    jurisdiction?: string | null;
    source_system?: string | null;
    publication_date?: string | null;
  };
}

interface Policy {
  id: number;
  policy_id: string;
  name: string;
  status?: string | null;
  language?: string | null;
}

interface PolicySection {
  id: number;
  policy_id: number;
  section_ref?: string | null;
  title?: string | null;
  status?: string | null;
  version?: string | null;
}

interface InternalRuleMapping {
  id: number;
  internal_rule_id: number;
  monitoring_rule_id?: number | null;
  mapping_type?: string | null;
  monitoring_rule?: {
    id: number;
    rule_id: string;
    name: string;
    severity?: string | null;
    enabled?: boolean | null;
  } | null;
}

interface InternalRule {
  id: number;
  internal_rule_id: string;
  obligation_id: number;
  policy_section_id?: number | null;
  name: string;
  description?: string | null;
  control_owner?: string | null;
  status?: string | null;
  policy_section?: PolicySection | null;
  mappings?: InternalRuleMapping[];
}

const obligationStatusStyle = (status?: string) => {
  const value = (status || "draft").toLowerCase();
  if (value === "approved") return "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300";
  if (value === "in_review") return "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300";
  if (value === "rejected") return "bg-rose-50 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300";
  return "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300";
};

const formatDate = (value?: string | null) => {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return parsed.toLocaleString();
};

export default function ObligationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = Array.isArray(params?.id) ? params.id[0] : params?.id;
  const [data, setData] = useState<ObligationDetail | null>(null);
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
        const response = await apiClient.get("/api/compliance/policies?skip=0&limit=200");
        if (!mounted) return;
        setPolicies(response.data.items || []);
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
        const response = await apiClient.get(`/api/compliance/policies/${ruleForm.policy_id}/sections`);
        if (!mounted) return;
        setSections(response.data.items || []);
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
  }, [id]);

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

  if (loading) {
    return <div className="text-sm text-gray-500">Loading obligation…</div>;
  }

  if (!data) {
    return <div className="text-sm text-gray-500">Obligation not found.</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="text-xs text-gray-500">Obligation {data.obligation_id}</div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">{data.document.title}</h1>
          <div className="mt-2 flex flex-wrap gap-2 text-xs text-gray-500">
            <span>{data.document.celex}</span>
            <span>•</span>
            <span>{data.document.jurisdiction || "EU"}</span>
            <span>•</span>
            <span>{data.document.source_system || "source"}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={"rounded-full px-3 py-1 text-xs font-semibold " + obligationStatusStyle(data.status)}>
            {data.status.replace("_", " ")}
          </span>
          <Link
            href="/compliance/obligations"
            className="rounded-full border border-gray-200 bg-white px-4 py-2 text-xs font-medium text-gray-600 hover:border-gray-300 dark:border-slate-700 dark:bg-slate-900 dark:text-gray-300"
          >
            Back
          </Link>
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="text-sm font-semibold text-gray-900 dark:text-white">Obligation summary</div>
        <div className="mt-3 text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap">
          {data.obligation_text}
        </div>

        <div className="mt-4 grid gap-3 text-xs text-gray-500 sm:grid-cols-2">
          <div>
            <div className="uppercase text-[11px] text-gray-400">Article reference</div>
            <div className="mt-1 text-sm text-gray-700 dark:text-gray-300">{data.article_ref || "—"}</div>
          </div>
          <div>
            <div className="uppercase text-[11px] text-gray-400">Applicability</div>
            <div className="mt-1 text-sm text-gray-700 dark:text-gray-300">{data.applicability || "—"}</div>
          </div>
          <div>
            <div className="uppercase text-[11px] text-gray-400">Effective date</div>
            <div className="mt-1 text-sm text-gray-700 dark:text-gray-300">{formatDate(data.effective_date)}</div>
          </div>
          <div>
            <div className="uppercase text-[11px] text-gray-400">Updated</div>
            <div className="mt-1 text-sm text-gray-700 dark:text-gray-300">{formatDate(data.updated_at)}</div>
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="text-sm font-semibold text-gray-900 dark:text-white">Head of compliance validation</div>
        <p className="mt-1 text-xs text-gray-500">
          Mark the obligation as reviewed/approved or send back for changes.
        </p>

        <div className="mt-4">
          <div className="text-xs font-semibold text-gray-600 dark:text-gray-300">Review notes</div>
          {data.review_notes ? (
            <div className="mt-2 rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-xs text-gray-600 whitespace-pre-wrap dark:border-slate-800 dark:bg-slate-800/40 dark:text-gray-300">
              {data.review_notes}
            </div>
          ) : (
            <div className="mt-2 text-xs text-gray-500">No notes yet.</div>
          )}
          <textarea
            value={reviewNote}
            onChange={(event) => setReviewNote(event.target.value)}
            placeholder="Add a review note (optional)"
            rows={3}
            className="mt-3 w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
          />
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {actionsFor(data.status).map((action) => (
            <button
              key={action.status}
              onClick={() => updateStatus(action.status)}
              disabled={actionLoading === action.status}
              className="rounded-full border border-gray-200 bg-white px-4 py-2 text-xs font-semibold text-gray-600 hover:border-gray-300 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-gray-300"
            >
              {action.label}
            </button>
          ))}
          <button
            onClick={() => router.push(`/doc/${data.document.celex}`)}
            className="rounded-full border border-gray-200 bg-white px-4 py-2 text-xs font-semibold text-gray-600 hover:border-gray-300 dark:border-slate-700 dark:bg-slate-900 dark:text-gray-300"
          >
            View source document
          </button>
        </div>

        <div className="mt-4 grid gap-2 text-xs text-gray-500">
          <div>Created by: {data.created_by || "—"}</div>
          <div>Reviewed by: {data.reviewed_by || "—"}</div>
          <div>Approved by: {data.approved_by || "—"}</div>
          <div>Approved at: {formatDate(data.approved_at)}</div>
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="text-sm font-semibold text-gray-900 dark:text-white">Internal rules & mappings</div>
        <p className="mt-1 text-xs text-gray-500">
          Define the internal controls required by this obligation and map them to monitoring rules.
        </p>

        <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,320px)]">
          <div className="space-y-3">
            {rulesLoading ? (
              <div className="text-sm text-gray-500">Loading internal rules...</div>
            ) : internalRules.length ? (
              internalRules.map((rule) => (
                <div
                  key={rule.id}
                  className="rounded-lg border border-gray-100 bg-gray-50/60 p-4 dark:border-slate-800 dark:bg-slate-800/40"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="text-sm font-semibold text-gray-900 dark:text-white">
                        {rule.name}
                      </div>
                      <div className="mt-1 text-xs text-gray-500">
                        {rule.internal_rule_id} • {rule.control_owner || "Owner TBD"}
                      </div>
                    </div>
                    <span className={"rounded-full px-2 py-1 text-[10px] font-semibold " + obligationStatusStyle(rule.status ?? undefined)}>
                      {(rule.status || "draft").replace("_", " ")}
                    </span>
                  </div>
                  {rule.description && (
                    <div className="mt-2 text-xs text-gray-600 dark:text-gray-300">{rule.description}</div>
                  )}
                  {rule.policy_section && (
                    <div className="mt-2 text-[11px] text-gray-500">
                      Policy section: {rule.policy_section.section_ref || "—"}{" "}
                      {rule.policy_section.title ? `• ${rule.policy_section.title}` : ""}
                    </div>
                  )}

                  <div className="mt-4 border-t border-gray-100 pt-3 dark:border-slate-800">
                    <div className="text-[11px] font-semibold text-gray-500">Mapped monitoring rules</div>
                    <div className="mt-2 space-y-2">
                      {rule.mappings && rule.mappings.length ? (
                        rule.mappings.map((mapping) => (
                          <div key={mapping.id} className="rounded-md border border-gray-100 bg-white px-3 py-2 text-xs dark:border-slate-800 dark:bg-slate-900">
                            <div className="flex items-center justify-between">
                              <div className="text-xs font-semibold text-gray-800 dark:text-gray-200">
                                {mapping.monitoring_rule?.name || "Monitoring rule"}
                              </div>
                              <div className="text-[10px] text-gray-500">
                                {mapping.monitoring_rule?.rule_id || mapping.monitoring_rule_id || "—"}
                              </div>
                            </div>
                            <div className="mt-1 text-[11px] text-gray-500">
                              {mapping.mapping_type || "transaction_monitoring"} •{" "}
                              {mapping.monitoring_rule?.severity || "severity ?"}
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="text-xs text-gray-500">No monitoring rules linked yet.</div>
                      )}
                    </div>

                    <div className="mt-3 flex flex-col gap-2 text-xs text-gray-600">
                      <input
                        value={mappingForm[rule.id]?.target || ""}
                        onChange={(event) =>
                          setMappingForm((prev) => ({
                            ...prev,
                            [rule.id]: { ...(prev[rule.id] || { mappingType: "transaction_monitoring" }), target: event.target.value },
                          }))
                        }
                        placeholder="Monitoring rule ID or rule_id"
                        className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
                      />
                      <div className="flex gap-2">
                        <select
                          value={mappingForm[rule.id]?.mappingType || "transaction_monitoring"}
                          onChange={(event) =>
                            setMappingForm((prev) => ({
                              ...prev,
                              [rule.id]: { ...(prev[rule.id] || { target: "" }), mappingType: event.target.value },
                            }))
                          }
                          className="flex-1 rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
                        >
                          <option value="transaction_monitoring">Transaction monitoring</option>
                          <option value="sanctions">Sanctions</option>
                          <option value="fraud">Fraud</option>
                        </select>
                        <button
                          onClick={() => addMapping(rule.id)}
                          disabled={rulesActionLoading === `map-${rule.id}`}
                          className="rounded-md border border-gray-200 bg-white px-3 py-2 text-xs font-semibold text-gray-600 hover:border-gray-300 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-gray-300"
                        >
                          {rulesActionLoading === `map-${rule.id}` ? "Saving..." : "Add mapping"}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-sm text-gray-500">No internal rules linked yet.</div>
            )}
          </div>

          <div className="rounded-lg border border-gray-100 bg-gray-50/60 p-4 text-xs text-gray-600 dark:border-slate-800 dark:bg-slate-800/40">
            <div className="text-xs font-semibold text-gray-700 dark:text-gray-200">Create internal rule</div>
            <div className="mt-3 space-y-2">
              <input
                value={ruleForm.name}
                onChange={(event) => setRuleForm({ ...ruleForm, name: event.target.value })}
                placeholder="Rule name"
                className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
              />
              <input
                value={ruleForm.control_owner}
                onChange={(event) => setRuleForm({ ...ruleForm, control_owner: event.target.value })}
                placeholder="Control owner"
                className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
              />
              <textarea
                value={ruleForm.description}
                onChange={(event) => setRuleForm({ ...ruleForm, description: event.target.value })}
                placeholder="Rule description"
                rows={3}
                className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
              />
              <select
                value={ruleForm.status}
                onChange={(event) => setRuleForm({ ...ruleForm, status: event.target.value })}
                className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
              >
                <option value="draft">Draft</option>
                <option value="in_review">In review</option>
                <option value="approved">Approved</option>
              </select>
              <select
                value={ruleForm.policy_id}
                onChange={(event) => setRuleForm({ ...ruleForm, policy_id: event.target.value, policy_section_id: "" })}
                className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
              >
                <option value="">Policy (optional)</option>
                {policiesLoading ? (
                  <option>Loading policies...</option>
                ) : (
                  policies.map((policy) => (
                    <option key={policy.id} value={policy.id}>
                      {policy.policy_id} • {policy.name}
                    </option>
                  ))
                )}
              </select>
              <select
                value={ruleForm.policy_section_id}
                onChange={(event) => setRuleForm({ ...ruleForm, policy_section_id: event.target.value })}
                disabled={!ruleForm.policy_id}
                className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 disabled:opacity-60 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
              >
                <option value="">Policy section (optional)</option>
                {sectionsLoading ? (
                  <option>Loading sections...</option>
                ) : (
                  sections.map((section) => (
                    <option key={section.id} value={section.id}>
                      {section.section_ref || "Section"} {section.title ? `• ${section.title}` : ""}
                    </option>
                  ))
                )}
              </select>
              <button
                onClick={createInternalRule}
                disabled={rulesActionLoading === "create"}
                className="w-full rounded-full border border-gray-200 bg-white px-4 py-2 text-xs font-semibold text-gray-600 hover:border-gray-300 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-gray-300"
              >
                {rulesActionLoading === "create" ? "Saving..." : "Add internal rule"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
