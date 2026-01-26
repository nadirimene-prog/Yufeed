"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import apiClient from "@/lib/http";
import { handleApiError } from "@/lib/api-error-handler";

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
  if (value === "approved") return "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300";
  if (value === "in_review") return "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300";
  if (value === "archived") return "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300";
  return "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300";
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
  const [sections, setSections] = useState<PolicySection[]>([]);
  const [sectionsLoading, setSectionsLoading] = useState(false);
  const [selectedPolicyId, setSelectedPolicyId] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [policyForm, setPolicyForm] = useState({
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

  const queryParams = useMemo(() => {
    const params = new URLSearchParams();
    if (statusFilter !== "all") {
      params.set("status", statusFilter);
    }
    if (query.trim()) {
      params.set("q", query.trim());
    }
    params.set("skip", "0");
    params.set("limit", "200");
    return params.toString();
  }, [query, statusFilter]);

  const loadPolicies = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get(`/api/compliance/policies?${queryParams}`);
      const items = response.data.items || [];
      setPolicies(items);
      setTotal(response.data.total || 0);
      if (items.length) {
        const nextSelected = items.find((item: Policy) => item.id === selectedPolicyId)?.id || items[0].id;
        setSelectedPolicyId(nextSelected);
      } else {
        setSelectedPolicyId(null);
        setSections([]);
      }
    } catch (err) {
      handleApiError(err, { context: "Policies list", customMessage: "Failed to load policies" });
    } finally {
      setLoading(false);
    }
  };

  const loadSections = async (policyId: number) => {
    setSectionsLoading(true);
    try {
      const response = await apiClient.get(`/api/compliance/policies/${policyId}/sections`);
      setSections(response.data.items || []);
    } catch (err) {
      handleApiError(err, { context: "Policy sections", customMessage: "Failed to load policy sections" });
    } finally {
      setSectionsLoading(false);
    }
  };

  useEffect(() => {
    loadPolicies();
  }, [queryParams]);

  useEffect(() => {
    if (selectedPolicyId) {
      loadSections(selectedPolicyId);
    }
  }, [selectedPolicyId]);

  const createPolicy = async () => {
    if (!policyForm.name.trim()) return;
    setActionLoading("policy");
    try {
      const payload = {
        name: policyForm.name.trim(),
        owner: policyForm.owner.trim() || undefined,
        status: policyForm.status,
        language: policyForm.language,
        source_url: policyForm.source_url.trim() || undefined,
      };
      const response = await apiClient.post("/api/compliance/policies", payload);
      setPolicyForm({ name: "", owner: "", status: "draft", language: "en", source_url: "" });
      await loadPolicies();
      if (response?.data?.id) {
        setSelectedPolicyId(response.data.id);
      }
    } catch (err) {
      handleApiError(err, { context: "Create policy", customMessage: "Failed to create policy" });
    } finally {
      setActionLoading(null);
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
      await apiClient.post(`/api/compliance/policies/${selectedPolicyId}/sections`, payload);
      setSectionForm({ section_ref: "", title: "", status: "draft", version: "", content: "" });
      await loadSections(selectedPolicyId);
    } catch (err) {
      handleApiError(err, { context: "Create policy section", customMessage: "Failed to create policy section" });
    } finally {
      setActionLoading(null);
    }
  };

  const selectedPolicy = policies.find((policy) => policy.id === selectedPolicyId) || null;

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Policy library</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Capture YuFeed internal policies and map them to compliance obligations.
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
          onChange={(event) => setStatusFilter(event.target.value)}
          className="rounded-full border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-600 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
        >
          <option value="all">All statuses</option>
          <option value="draft">Draft</option>
          <option value="in_review">In review</option>
          <option value="approved">Approved</option>
          <option value="archived">Archived</option>
        </select>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,360px)]">
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400">
            <div>{loading ? "Loading policies…" : `${total} policies`}</div>
            <div>Active: {policies.filter((item) => (item.status || "draft") !== "archived").length}</div>
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
                    <span className={`rounded-full px-2 py-1 text-[10px] font-semibold ${policyStatusStyle(policy.status)}`}>
                      {(policy.status || "draft").replace("_", " ")}
                    </span>
                  </div>
                  <div className="mt-1 text-xs text-gray-500">
                    {policy.policy_id} • {policy.language?.toUpperCase() || "EN"}
                  </div>
                  <div className="mt-1 text-xs text-gray-400">
                    Updated {formatDate(policy.updated_at)}
                  </div>
                </button>
              ))
            ) : (
              <div className="text-sm text-gray-500">No policies found yet.</div>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="text-sm font-semibold text-gray-900 dark:text-white">Create policy</div>
            <p className="mt-1 text-xs text-gray-500">
              Capture internal policy documents and assign ownership + language.
            </p>
            <div className="mt-4 space-y-3 text-xs text-gray-600">
              <input
                value={policyForm.name}
                onChange={(event) => setPolicyForm({ ...policyForm, name: event.target.value })}
                placeholder="Policy name"
                className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
              />
              <input
                value={policyForm.owner}
                onChange={(event) => setPolicyForm({ ...policyForm, owner: event.target.value })}
                placeholder="Owner (Head of Compliance)"
                className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
              />
              <div className="grid gap-3 sm:grid-cols-2">
                <select
                  value={policyForm.status}
                  onChange={(event) => setPolicyForm({ ...policyForm, status: event.target.value })}
                  className="rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
                >
                  <option value="draft">Draft</option>
                  <option value="in_review">In review</option>
                  <option value="approved">Approved</option>
                  <option value="archived">Archived</option>
                </select>
                <select
                  value={policyForm.language}
                  onChange={(event) => setPolicyForm({ ...policyForm, language: event.target.value })}
                  className="rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
                >
                  <option value="en">English</option>
                  <option value="fr">French</option>
                </select>
              </div>
              <input
                value={policyForm.source_url}
                onChange={(event) => setPolicyForm({ ...policyForm, source_url: event.target.value })}
                placeholder="Source URL (optional)"
                className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
              />
              <button
                onClick={createPolicy}
                disabled={actionLoading === "policy"}
                className="w-full rounded-full border border-gray-200 bg-white px-4 py-2 text-xs font-semibold text-gray-600 hover:border-gray-300 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-gray-300"
              >
                {actionLoading === "policy" ? "Saving..." : "Add policy"}
              </button>
            </div>
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="text-sm font-semibold text-gray-900 dark:text-white">Policy sections</div>
            <p className="mt-1 text-xs text-gray-500">
              {selectedPolicy ? `Sections for ${selectedPolicy.name}.` : "Select a policy to manage sections."}
            </p>

            <div className="mt-4 space-y-3 text-xs text-gray-600">
              {selectedPolicy ? (
                <>
                  <div className="space-y-2">
                    {sectionsLoading ? (
                      <div className="text-sm text-gray-500">Loading sections...</div>
                    ) : sections.length ? (
                      sections.map((section) => (
                        <div
                          key={section.id}
                          className="rounded-md border border-gray-100 bg-gray-50/60 px-3 py-2 dark:border-slate-800 dark:bg-slate-800/40"
                        >
                          <div className="flex items-center justify-between">
                            <div className="text-xs font-semibold text-gray-800 dark:text-gray-100">
                              {section.title || section.section_ref || "Untitled section"}
                            </div>
                            <span className={`rounded-full px-2 py-1 text-[10px] font-semibold ${policyStatusStyle(section.status)}`}>
                              {(section.status || "draft").replace("_", " ")}
                            </span>
                          </div>
                          <div className="mt-1 text-[11px] text-gray-500">
                            {section.section_ref || "No ref"} • v{section.version || "1"}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-sm text-gray-500">No sections yet.</div>
                    )}
                  </div>

                  <div className="border-t border-gray-100 pt-4 dark:border-slate-800">
                    <div className="text-xs font-semibold text-gray-600 dark:text-gray-300">Add a section</div>
                    <div className="mt-2 space-y-2">
                      <input
                        value={sectionForm.section_ref}
                        onChange={(event) => setSectionForm({ ...sectionForm, section_ref: event.target.value })}
                        placeholder="Section ref (ex: POL-1.2)"
                        className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
                      />
                      <input
                        value={sectionForm.title}
                        onChange={(event) => setSectionForm({ ...sectionForm, title: event.target.value })}
                        placeholder="Section title"
                        className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
                      />
                      <div className="grid gap-3 sm:grid-cols-2">
                        <select
                          value={sectionForm.status}
                          onChange={(event) => setSectionForm({ ...sectionForm, status: event.target.value })}
                          className="rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
                        >
                          <option value="draft">Draft</option>
                          <option value="in_review">In review</option>
                          <option value="approved">Approved</option>
                        </select>
                        <input
                          value={sectionForm.version}
                          onChange={(event) => setSectionForm({ ...sectionForm, version: event.target.value })}
                          placeholder="Version"
                          className="rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
                        />
                      </div>
                      <textarea
                        value={sectionForm.content}
                        onChange={(event) => setSectionForm({ ...sectionForm, content: event.target.value })}
                        placeholder="Section content (optional)"
                        rows={3}
                        className="w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
                      />
                      <button
                        onClick={createSection}
                        disabled={actionLoading === "section"}
                        className="w-full rounded-full border border-gray-200 bg-white px-4 py-2 text-xs font-semibold text-gray-600 hover:border-gray-300 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-gray-300"
                      >
                        {actionLoading === "section" ? "Saving..." : "Add section"}
                      </button>
                    </div>
                  </div>
                </>
              ) : (
                <div className="text-sm text-gray-500">Select a policy from the list to manage sections.</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
