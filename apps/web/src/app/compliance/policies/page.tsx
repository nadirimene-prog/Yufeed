"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { handleApiError } from "@/lib/api-error-handler";
import {
  createPolicy,
  createPolicyFromTemplate,
  createPolicySection,
  getPolicies,
  getPolicySections,
  getPolicyTemplates,
} from "@/lib/compliance-api";
import type {
  PolicyCreate,
  PolicyStatus,
  PolicyTemplate,
} from "@/types/compliance";

interface Policy {
  id: number;
  policy_id: string;
  name: string;
  owner?: string | null;
  status?: string | null;
  language?: string | null;
  effective_date?: string | null;
  last_reviewed_at?: string | null;
  source_url?: string | null;
  updated_at?: string | null;
}

interface PolicySection {
  id: number;
  policy_id: number;
  section_ref?: string | null;
  title?: string | null;
  status?: string | null;
  version?: string | null;
  updated_at?: string | null;
}

const policyStatusStyle = (status?: string | null) => {
  const value = (status || "draft").toLowerCase();
  if (value === "active")
    return "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300";
  if (value === "approved")
    return "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300";
  if (value === "in_review")
    return "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300";
  if (value === "retired")
    return "bg-rose-50 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300";
  return "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300";
};

const useDebouncedValue = <T,>(value: T, delayMs: number) => {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const handle = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(handle);
  }, [value, delayMs]);

  return debounced;
};

const formatDate = (value?: string | null) => {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return parsed.toLocaleDateString();
};

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [policyPage, setPolicyPage] = useState(1);
  const policyPageSize = 20;
  const [templates, setTemplates] = useState<PolicyTemplate[]>([]);
  const [templatesTotal, setTemplatesTotal] = useState(0);
  const [templatesLoading, setTemplatesLoading] = useState(true);
  const [templateQuery, setTemplateQuery] = useState("");
  const [templateCategory, setTemplateCategory] = useState("all");
  const [templateActionLoading, setTemplateActionLoading] = useState<
    string | null
  >(null);
  const [templatePage, setTemplatePage] = useState(1);
  const templatePageSize = 9;
  const [sections, setSections] = useState<PolicySection[]>([]);
  const [sectionsLoading, setSectionsLoading] = useState(false);
  const [selectedPolicyId, setSelectedPolicyId] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<PolicyStatus | "all">("all");
  const [policyForm, setPolicyForm] = useState<
    PolicyCreate & {
      owner: string;
      status: PolicyStatus;
      language: string;
      source_url: string;
    }
  >({
    name: "",
    owner: "",
    status: "draft",
    language: "en",
    source_url: "",
  });
  const [sectionForm, setSectionForm] = useState({
    section_ref: "",
    title: "",
    status: "draft",
    version: "",
    content: "",
  });
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const templateCategories = useMemo(() => {
    return Array.from(new Set(templates.map((item) => item.category)));
  }, [templates]);

  const debouncedQuery = useDebouncedValue(query, 300);
  const debouncedTemplateQuery = useDebouncedValue(templateQuery, 300);

  const loadPolicies = async () => {
    setLoading(true);
    try {
      const response = await getPolicies({
        status: statusFilter !== "all" ? statusFilter : undefined,
        q: debouncedQuery.trim() || undefined,
        skip: (policyPage - 1) * policyPageSize,
        limit: policyPageSize,
      });
      const items = response.items || [];
      setPolicies(items);
      setTotal(response.total || 0);
      if (items.length) {
        const nextSelected =
          items.find((item: Policy) => item.id === selectedPolicyId)?.id ||
          items[0].id;
        setSelectedPolicyId(nextSelected);
      } else {
        setSelectedPolicyId(null);
        setSections([]);
      }
    } catch (err) {
      handleApiError(err, {
        context: "Policies list",
        customMessage: "Failed to load policies",
      });
    } finally {
      setLoading(false);
    }
  };

  const loadTemplates = async () => {
    setTemplatesLoading(true);
    try {
      const response = await getPolicyTemplates({
        category: templateCategory !== "all" ? templateCategory : undefined,
        q: debouncedTemplateQuery.trim() || undefined,
        skip: (templatePage - 1) * templatePageSize,
        limit: templatePageSize,
      });
      setTemplates(response.items || []);
      setTemplatesTotal(response.total || 0);
    } catch (err) {
      handleApiError(err, {
        context: "Policy templates",
        customMessage: "Failed to load policy templates",
      });
    } finally {
      setTemplatesLoading(false);
    }
  };

  const loadSections = async (policyId: number) => {
    setSectionsLoading(true);
    try {
      const response = await getPolicySections(policyId);
      setSections(response.items || []);
    } catch (err) {
      handleApiError(err, {
        context: "Policy sections",
        customMessage: "Failed to load policy sections",
      });
    } finally {
      setSectionsLoading(false);
    }
  };

  useEffect(() => {
    setPolicyPage(1);
  }, [debouncedQuery, statusFilter]);

  useEffect(() => {
    loadPolicies();
  }, [debouncedQuery, statusFilter, policyPage]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    setTemplatePage(1);
  }, [debouncedTemplateQuery, templateCategory]);

  useEffect(() => {
    loadTemplates();
  }, [debouncedTemplateQuery, templateCategory, templatePage]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (selectedPolicyId) {
      loadSections(selectedPolicyId);
    }
  }, [selectedPolicyId]);

  const handleCreatePolicy = async () => {
    if (!policyForm.name.trim()) return;
    setActionLoading("policy");
    try {
      const payload: PolicyCreate = {
        name: policyForm.name.trim(),
        owner: policyForm.owner.trim() || undefined,
        status: policyForm.status,
        language: policyForm.language,
        source_url: policyForm.source_url.trim() || undefined,
      };
      const response = await createPolicy(payload);
      setPolicyForm({
        name: "",
        owner: "",
        status: "draft",
        language: "en",
        source_url: "",
      });
      await loadPolicies();
      if (response?.id) {
        setSelectedPolicyId(response.id);
      }
    } catch (err) {
      handleApiError(err, {
        context: "Create policy",
        customMessage: "Failed to create policy",
      });
    } finally {
      setActionLoading(null);
    }
  };

  const handleCreateFromTemplate = async (template: PolicyTemplate) => {
    setTemplateActionLoading(template.template_id);
    try {
      const response = await createPolicyFromTemplate(template.template_id);
      await loadPolicies();
      if (response?.id) {
        setSelectedPolicyId(response.id);
      }
    } catch (err) {
      handleApiError(err, {
        context: "Create policy from template",
        customMessage: "Failed to create policy from template",
      });
    } finally {
      setTemplateActionLoading(null);
    }
  };

  const createSection = async () => {
    if (!selectedPolicyId) return;
    if (!sectionForm.title.trim() && !sectionForm.section_ref.trim()) return;
    setActionLoading("section");
    try {
      const payload = {
        section_ref: sectionForm.section_ref.trim() || undefined,
        title: sectionForm.title.trim() || undefined,
        status: sectionForm.status,
        version: sectionForm.version.trim() || undefined,
        content: sectionForm.content.trim() || undefined,
      };
      await createPolicySection(selectedPolicyId, payload);
      setSectionForm({
        section_ref: "",
        title: "",
        status: "draft",
        version: "",
        content: "",
      });
      await loadSections(selectedPolicyId);
    } catch (err) {
      handleApiError(err, {
        context: "Create policy section",
        customMessage: "Failed to create policy section",
      });
    } finally {
      setActionLoading(null);
    }
  };

  const selectedPolicy =
    policies.find((policy) => policy.id === selectedPolicyId) || null;

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
            Policy library
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Capture YuFeed internal policies and map them to compliance
            obligations.
          </p>
        </div>
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white px-4 py-2 text-xs font-medium text-gray-600 hover:border-gray-300 dark:border-slate-700 dark:bg-slate-900 dark:text-gray-300"
        >
          Back to dashboard
        </Link>
      </header>

      <div className="flex flex-wrap gap-3 text-xs text-gray-500">
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search policy ID or name..."
          className="min-w-[220px] rounded-full border border-gray-200 bg-white px-4 py-2 text-xs text-gray-700 shadow-sm focus:border-gray-300 focus:outline-none dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
        />
        <select
          value={statusFilter}
          onChange={(event) =>
            setStatusFilter(event.target.value as PolicyStatus | "all")
          }
          className="rounded-full border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-600 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
        >
          <option value="all">All statuses</option>
          <option value="draft">Draft</option>
          <option value="in_review">In review</option>
          <option value="approved">Approved</option>
          <option value="active">Active</option>
          <option value="retired">Retired</option>
        </select>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="text-sm font-semibold text-gray-900 dark:text-white">
              Master policies
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Seeded master policy library for compliance obligations. These are
              the canonical policies used for mapping.
            </p>
          </div>
          <div className="text-xs text-gray-500">
            {templatesLoading
              ? "Loading master policies…"
              : `${templatesTotal} policies`}
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-3 text-xs text-gray-500">
          <input
            value={templateQuery}
            onChange={(event) => setTemplateQuery(event.target.value)}
            placeholder="Search master policies..."
            className="min-w-[220px] rounded-full border border-gray-200 bg-white px-4 py-2 text-xs text-gray-700 shadow-sm focus:border-gray-300 focus:outline-none dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
          />
          <select
            value={templateCategory}
            onChange={(event) => setTemplateCategory(event.target.value)}
            className="rounded-full border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-600 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
          >
            <option value="all">All categories</option>
            {templateCategories.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {templatesLoading ? (
            <div className="text-sm text-gray-500">
              Loading master policies...
            </div>
          ) : templates.length ? (
            templates.map((template) => (
              <div
                key={template.template_id}
                className="rounded-lg border border-gray-100 bg-gray-50/60 p-4 text-xs text-gray-600 dark:border-slate-800 dark:bg-slate-800/40"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-sm font-semibold text-gray-900 dark:text-white">
                      {template.name}
                    </div>
                    <div className="mt-1 text-[11px] text-gray-500">
                      {template.template_id}
                    </div>
                  </div>
                  <span className="rounded-full bg-indigo-50 px-2 py-1 text-[10px] font-semibold text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">
                    {template.category}
                  </span>
                </div>
                {template.regulatory_basis?.length ? (
                  <div className="mt-2 text-[11px] text-gray-500">
                    {template.regulatory_basis.join(" • ")}
                  </div>
                ) : null}
                <button
                  onClick={() => handleCreateFromTemplate(template)}
                  disabled={templateActionLoading === template.template_id}
                  className="mt-3 w-full rounded-full border border-gray-200 bg-white px-3 py-2 text-[11px] font-semibold text-gray-600 hover:border-gray-300 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-gray-300"
                >
                  {templateActionLoading === template.template_id
                    ? "Opening..."
                    : "Open policy"}
                </button>
              </div>
            ))
          ) : (
            <div className="text-sm text-gray-500">No templates found.</div>
          )}
        </div>

        <div className="mt-4 flex items-center justify-between text-xs text-gray-500">
          <span>
            Page {templatePage} of{" "}
            {Math.max(1, Math.ceil(templatesTotal / templatePageSize))}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setTemplatePage((prev) => Math.max(1, prev - 1))}
              disabled={templatePage === 1}
              className="rounded-full border border-gray-200 bg-white px-3 py-1 text-[11px] font-semibold text-gray-600 hover:border-gray-300 disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-gray-300"
            >
              Prev
            </button>
            <button
              onClick={() =>
                setTemplatePage((prev) =>
                  prev >= Math.ceil(templatesTotal / templatePageSize)
                    ? prev
                    : prev + 1,
                )
              }
              disabled={
                templatePage >= Math.ceil(templatesTotal / templatePageSize)
              }
              className="rounded-full border border-gray-200 bg-white px-3 py-1 text-[11px] font-semibold text-gray-600 hover:border-gray-300 disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-gray-300"
            >
              Next
            </button>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,360px)]">
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400">
            <div>{loading ? "Loading policies…" : `${total} policies`}</div>
            <div>
              Active:{" "}
              {
                policies.filter((item) => (item.status || "draft") === "active")
                  .length
              }
            </div>
          </div>

          <div className="mt-4 space-y-3">
            {loading ? (
              <div className="text-sm text-gray-500">Loading...</div>
            ) : policies.length ? (
              policies.map((policy) => (
                <button
                  key={policy.id}
                  onClick={() => setSelectedPolicyId(policy.id)}
                  className={`w-full rounded-lg border px-4 py-3 text-left transition ${
                    selectedPolicyId === policy.id
                      ? "border-indigo-200 bg-indigo-50/60 dark:border-indigo-500/40 dark:bg-indigo-950/20"
                      : "border-gray-100 bg-gray-50/60 hover:border-gray-200 dark:border-slate-800 dark:bg-slate-800/40"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-sm font-semibold text-gray-900 dark:text-white">
                      {policy.name}
                    </div>
                    <span
                      className={`rounded-full px-2 py-1 text-[10px] font-semibold ${policyStatusStyle(policy.status)}`}
                    >
                      {(policy.status || "draft").replace("_", " ")}
                    </span>
                  </div>
                  <div className="mt-1 text-xs text-gray-500">
                    {policy.policy_id} •{" "}
                    {policy.language?.toUpperCase() || "EN"}
                  </div>
                  <div className="mt-1 text-xs text-gray-400">
                    Updated {formatDate(policy.updated_at)}
                  </div>
                </button>
              ))
            ) : (
              <div className="text-sm text-gray-500">
                No policies found yet.
              </div>
            )}
          </div>

          <div className="mt-4 flex items-center justify-between text-xs text-gray-500">
            <span>
              Page {policyPage} of{" "}
              {Math.max(1, Math.ceil(total / policyPageSize))}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPolicyPage((prev) => Math.max(1, prev - 1))}
                disabled={policyPage === 1}
                className="rounded-full border border-gray-200 bg-white px-3 py-1 text-[11px] font-semibold text-gray-600 hover:border-gray-300 disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-gray-300"
              >
                Prev
              </button>
              <button
                onClick={() =>
                  setPolicyPage((prev) =>
                    prev >= Math.ceil(total / policyPageSize) ? prev : prev + 1,
                  )
                }
                disabled={policyPage >= Math.ceil(total / policyPageSize)}
                className="rounded-full border border-gray-200 bg-white px-3 py-1 text-[11px] font-semibold text-gray-600 hover:border-gray-300 disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-gray-300"
              >
                Next
              </button>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="text-sm font-semibold text-gray-900 dark:text-white">
              Create policy
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Capture internal policy documents and assign ownership + language.
            </p>
            <div className="mt-4 space-y-3 text-xs text-gray-600">
              <input
                value={policyForm.name}
                onChange={(event) =>
                  setPolicyForm({ ...policyForm, name: event.target.value })
                }
                placeholder="Policy name"
                className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
              />
              <input
                value={policyForm.owner}
                onChange={(event) =>
                  setPolicyForm({ ...policyForm, owner: event.target.value })
                }
                placeholder="Owner (Head of Compliance)"
                className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
              />
              <div className="grid gap-3 sm:grid-cols-2">
                <select
                  value={policyForm.status}
                  onChange={(event) =>
                    setPolicyForm({
                      ...policyForm,
                      status: event.target.value as PolicyStatus,
                    })
                  }
                  className="rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
                >
                  <option value="draft">Draft</option>
                  <option value="in_review">In review</option>
                  <option value="approved">Approved</option>
                  <option value="active">Active</option>
                  <option value="retired">Retired</option>
                </select>
                <select
                  value={policyForm.language}
                  onChange={(event) =>
                    setPolicyForm({
                      ...policyForm,
                      language: event.target.value,
                    })
                  }
                  className="rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
                >
                  <option value="en">English</option>
                  <option value="fr">French</option>
                </select>
              </div>
              <input
                value={policyForm.source_url}
                onChange={(event) =>
                  setPolicyForm({
                    ...policyForm,
                    source_url: event.target.value,
                  })
                }
                placeholder="Source URL (optional)"
                className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
              />
              <button
                onClick={handleCreatePolicy}
                disabled={actionLoading === "policy"}
                className="w-full rounded-full border border-gray-200 bg-white px-4 py-2 text-xs font-semibold text-gray-600 hover:border-gray-300 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-gray-300"
              >
                {actionLoading === "policy" ? "Saving..." : "Add policy"}
              </button>
            </div>
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="text-sm font-semibold text-gray-900 dark:text-white">
              Policy sections
            </div>
            <p className="mt-1 text-xs text-gray-500">
              {selectedPolicy
                ? `Sections for ${selectedPolicy.name}.`
                : "Select a policy to manage sections."}
            </p>

            <div className="mt-4 space-y-3 text-xs text-gray-600">
              {selectedPolicy ? (
                <>
                  <div className="space-y-2">
                    {sectionsLoading ? (
                      <div className="text-sm text-gray-500">
                        Loading sections...
                      </div>
                    ) : sections.length ? (
                      sections.map((section) => (
                        <div
                          key={section.id}
                          className="rounded-md border border-gray-100 bg-gray-50/60 px-3 py-2 dark:border-slate-800 dark:bg-slate-800/40"
                        >
                          <div className="flex items-center justify-between">
                            <div className="text-xs font-semibold text-gray-800 dark:text-gray-100">
                              {section.title ||
                                section.section_ref ||
                                "Untitled section"}
                            </div>
                            <span
                              className={`rounded-full px-2 py-1 text-[10px] font-semibold ${policyStatusStyle(section.status)}`}
                            >
                              {(section.status || "draft").replace("_", " ")}
                            </span>
                          </div>
                          <div className="mt-1 text-[11px] text-gray-500">
                            {section.section_ref || "No ref"} • v
                            {section.version || "1"}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-sm text-gray-500">
                        No sections yet.
                      </div>
                    )}
                  </div>

                  <div className="border-t border-gray-100 pt-4 dark:border-slate-800">
                    <div className="text-xs font-semibold text-gray-600 dark:text-gray-300">
                      Add a section
                    </div>
                    <div className="mt-2 space-y-2">
                      <input
                        value={sectionForm.section_ref}
                        onChange={(event) =>
                          setSectionForm({
                            ...sectionForm,
                            section_ref: event.target.value,
                          })
                        }
                        placeholder="Section ref (ex: POL-1.2)"
                        className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
                      />
                      <input
                        value={sectionForm.title}
                        onChange={(event) =>
                          setSectionForm({
                            ...sectionForm,
                            title: event.target.value,
                          })
                        }
                        placeholder="Section title"
                        className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
                      />
                      <div className="grid gap-3 sm:grid-cols-2">
                        <select
                          value={sectionForm.status}
                          onChange={(event) =>
                            setSectionForm({
                              ...sectionForm,
                              status: event.target.value,
                            })
                          }
                          className="rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
                        >
                          <option value="draft">Draft</option>
                          <option value="in_review">In review</option>
                          <option value="approved">Approved</option>
                        </select>
                        <input
                          value={sectionForm.version}
                          onChange={(event) =>
                            setSectionForm({
                              ...sectionForm,
                              version: event.target.value,
                            })
                          }
                          placeholder="Version"
                          className="rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
                        />
                      </div>
                      <textarea
                        value={sectionForm.content}
                        onChange={(event) =>
                          setSectionForm({
                            ...sectionForm,
                            content: event.target.value,
                          })
                        }
                        placeholder="Section content (optional)"
                        rows={3}
                        className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
                      />
                      <button
                        onClick={createSection}
                        disabled={actionLoading === "section"}
                        className="w-full rounded-full border border-gray-200 bg-white px-4 py-2 text-xs font-semibold text-gray-600 hover:border-gray-300 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-gray-300"
                      >
                        {actionLoading === "section"
                          ? "Saving..."
                          : "Add section"}
                      </button>
                    </div>
                  </div>
                </>
              ) : (
                <div className="text-sm text-gray-500">
                  Select a policy from the list to manage sections.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
