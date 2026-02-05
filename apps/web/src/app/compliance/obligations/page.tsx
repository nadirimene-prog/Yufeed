"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import apiClient from "@/lib/http";
import { handleApiError } from "@/lib/api-error-handler";

interface ObligationItem {
  id: number;
  obligation_id: string;
  status: string;
  article_ref?: string | null;
  obligation_text: string;
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
  return parsed.toLocaleDateString();
};

export default function ObligationsPage() {
  const [items, setItems] = useState<ObligationItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("pending");
  const [jurisdictionFilter, setJurisdictionFilter] = useState("all");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [scopeFilter, setScopeFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const pageSize = 20;

  const queryParams = useMemo(() => {
    const params = new URLSearchParams();
    if (statusFilter !== "all") {
      params.set("status", statusFilter === "pending" ? "draft,in_review" : statusFilter);
    }
    if (jurisdictionFilter !== "all") {
      params.set("jurisdiction", jurisdictionFilter);
    }
    if (sourceFilter !== "all") {
      params.set("source_system", sourceFilter);
    }
    if (scopeFilter !== "all") {
      params.set("scope", scopeFilter);
    }
    if (query.trim()) {
      params.set("q", query.trim());
    }
    params.set("skip", String(page * pageSize));
    params.set("limit", String(pageSize));
    return params.toString();
  }, [statusFilter, jurisdictionFilter, sourceFilter, scopeFilter, query, page]);

  useEffect(() => {
    let mounted = true;
    const fetchItems = async () => {
      setLoading(true);
      try {
        const response = await apiClient.get(`/api/obligations?${queryParams}`);
        if (!mounted) return;
        setItems(response.data.items || []);
        setTotal(response.data.total || 0);
      } catch (err) {
        handleApiError(err, { context: "Obligations list", customMessage: "Failed to load obligations" });
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };
    fetchItems();
    return () => {
      mounted = false;
    };
  }, [queryParams]);

  const updateStatus = async (id: number, status: string) => {
    setActionLoading(`${id}:${status}`);
    try {
      await apiClient.patch(`/api/obligations/${id}`, { status });
      const response = await apiClient.get(`/api/obligations?${queryParams}`);
      setItems(response.data.items || []);
      setTotal(response.data.total || 0);
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

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Regulatory obligations</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Track obligations extracted from EU/FR publications and validate them internally.
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
          onChange={(event) => {
            setQuery(event.target.value);
            setPage(0);
          }}
          placeholder="Search CELEX, title, obligation text..."
          className="min-w-[220px] rounded-full border border-gray-200 bg-white px-4 py-2 text-xs text-gray-700 shadow-sm focus:border-gray-300 focus:outline-none dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
        />
        <select
          value={statusFilter}
          onChange={(event) => {
            setStatusFilter(event.target.value);
            setPage(0);
          }}
          className="rounded-full border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-600 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
        >
          <option value="pending">Pending (draft + review)</option>
          <option value="draft">Draft</option>
          <option value="in_review">In review</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </select>
        <select
          value={jurisdictionFilter}
          onChange={(event) => {
            setJurisdictionFilter(event.target.value);
            setPage(0);
          }}
          className="rounded-full border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-600 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
        >
          <option value="all">All jurisdictions</option>
          <option value="EU">EU</option>
          <option value="FR">France</option>
        </select>
        <select
          value={sourceFilter}
          onChange={(event) => {
            setSourceFilter(event.target.value);
            setPage(0);
          }}
          className="rounded-full border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-600 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
        >
          <option value="all">All sources</option>
          <option value="eur-lex">EUR-Lex</option>
          <option value="legifrance">Légifrance</option>
        </select>
        <select
          value={scopeFilter}
          onChange={(event) => {
            setScopeFilter(event.target.value);
            setPage(0);
          }}
          className="rounded-full border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-600 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
        >
          <option value="psp,eme,vasp">PSP / EMI / VASP</option>
          <option value="all">All scopes</option>
          <option value="psp">PSP</option>
          <option value="eme">EMI</option>
          <option value="vasp">VASP</option>
        </select>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400">
          <div>
            {loading ? "Loading obligations…" : `${total} obligations`}
          </div>
          <div>
            Page {page + 1} / {totalPages}
          </div>
        </div>

        <div className="mt-4 space-y-4">
          {loading ? (
            <div className="text-sm text-gray-500">Loading...</div>
          ) : items.length ? (
            items.map((item) => (
              <div
                key={item.id}
                className="rounded-lg border border-gray-100 bg-gray-50/60 p-4 dark:border-slate-800 dark:bg-slate-800/40"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <Link href={`/compliance/obligations/${item.id}`} className="text-sm font-semibold text-gray-900 hover:underline dark:text-white">
                      {item.document.title}
                    </Link>
                    <div className="mt-1 text-xs text-gray-500">
                      {item.document.celex} • {item.document.jurisdiction || "EU"} • {item.document.source_system || "source"}
                    </div>
                    <p className="mt-2 text-xs text-gray-500 line-clamp-2 dark:text-gray-400">
                      {item.obligation_text}
                    </p>
                  </div>
                  <span className={"rounded-full px-3 py-1 text-[11px] font-semibold " + obligationStatusStyle(item.status)}>
                    {item.status.replace("_", " ")}
                  </span>
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-gray-400">
                  <span>{item.article_ref || "No article ref"}</span>
                  <span>•</span>
                  <span>Updated {formatDate(item.updated_at)}</span>
                </div>
                {actionsFor(item.status).length ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {actionsFor(item.status).map((action) => (
                      <button
                        key={action.status}
                        onClick={() => updateStatus(item.id, action.status)}
                        disabled={actionLoading === `${item.id}:${action.status}`}
                        className="rounded-full border border-gray-200 bg-white px-3 py-1 text-[11px] font-semibold text-gray-600 hover:border-gray-300 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-gray-300"
                      >
                        {action.label}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            ))
          ) : (
            <div className="text-sm text-gray-500">No obligations match your filters.</div>
          )}
        </div>

        <div className="mt-6 flex items-center justify-between">
          <button
            onClick={() => setPage((prev) => Math.max(0, prev - 1))}
            disabled={page === 0}
            className="rounded-full border border-gray-200 bg-white px-4 py-2 text-xs font-medium text-gray-600 disabled:opacity-50 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
          >
            Previous
          </button>
          <button
            onClick={() => setPage((prev) => Math.min(totalPages - 1, prev + 1))}
            disabled={page + 1 >= totalPages}
            className="rounded-full border border-gray-200 bg-white px-4 py-2 text-xs font-medium text-gray-600 disabled:opacity-50 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
