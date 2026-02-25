"use client";

export const dynamic = "force-dynamic";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import { handleApiError } from "@/lib/api-error-handler";
import { getAuthUserProfile } from "@/lib/auth";
import { bulkApproveObligations } from "@/lib/compliance-api";
import { complianceKeys } from "@/lib/queryKeys";
import {
  useObligationsList,
  useUpdateObligationStatus,
} from "@/hooks/queries/useComplianceData";
import type { Obligation } from "@/types/compliance";

const obligationStatusStyle = (status?: string) => {
  const value = (status ?? "draft").toLowerCase();
  if (value === "approved") return "bg-emerald-50 text-emerald-700";
  if (value === "in_review") return "bg-blue-50 text-blue-700";
  if (value === "rejected") return "bg-rose-50 text-rose-700";
  return "bg-amber-50 text-amber-700";
};

const formatDate = (value?: string | null) => {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return parsed.toLocaleDateString();
};

export default function ObligationsPage() {
  const [statusFilter, setStatusFilter] = useState("pending");
  const [jurisdictionFilter, setJurisdictionFilter] = useState("all");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [scopeFilter, setScopeFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [bulkLoading, setBulkLoading] = useState(false);
  const [selectedObligationIds, setSelectedObligationIds] = useState<number[]>(
    [],
  );
  const currentUser = useMemo(() => getAuthUserProfile(), []);
  const queryClient = useQueryClient();

  const pageSize = 20;

  const listParams = useMemo(() => {
    const status =
      statusFilter === "pending" ? "draft,in_review" : statusFilter;
    return {
      ...(statusFilter !== "all" ? { status } : {}),
      ...(jurisdictionFilter !== "all"
        ? { jurisdiction: jurisdictionFilter }
        : {}),
      ...(sourceFilter !== "all" ? { source_system: sourceFilter } : {}),
      ...(scopeFilter !== "all" ? { scope: scopeFilter } : {}),
      ...(query.trim() ? { q: query.trim() } : {}),
      skip: page * pageSize,
      limit: pageSize,
    };
  }, [
    statusFilter,
    jurisdictionFilter,
    sourceFilter,
    scopeFilter,
    query,
    page,
  ]);

  const obligationsQuery = useObligationsList(listParams);
  const updateStatusMutation = useUpdateObligationStatus();

  const items: Obligation[] = useMemo(
    () => obligationsQuery.data?.items ?? [],
    [obligationsQuery.data?.items],
  );
  const total = obligationsQuery.data?.total ?? 0;
  const loading = obligationsQuery.isLoading;
  const pageItemIds = useMemo(() => items.map((item) => item.id), [items]);
  const allPageSelected =
    pageItemIds.length > 0 &&
    pageItemIds.every((id) => selectedObligationIds.includes(id));

  const updateStatus = async (id: number, status: string) => {
    setActionLoading(`${id}:${status}`);
    try {
      await updateStatusMutation.mutateAsync({ id, status });
    } catch (err) {
      handleApiError(err, { context: "Update obligation status" });
    } finally {
      setActionLoading(null);
    }
  };

  const toggleItemSelection = (id: number) => {
    setSelectedObligationIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  };

  const togglePageSelection = () => {
    setSelectedObligationIds((prev) => {
      if (allPageSelected) {
        return prev.filter((id) => !pageItemIds.includes(id));
      }
      const merged = new Set([...prev, ...pageItemIds]);
      return Array.from(merged);
    });
  };

  const handleBulkApprove = async () => {
    if (!selectedObligationIds.length) return;
    setBulkLoading(true);
    try {
      await bulkApproveObligations({
        obligation_ids: selectedObligationIds,
        status: "approved",
        note: "bulk review",
        auto_link_best_suggestion: true,
        create_internal_rule: true,
      });
      setSelectedObligationIds([]);
      await queryClient.invalidateQueries({
        queryKey: complianceKeys.obligations(),
      });
    } catch (err) {
      handleApiError(err, { context: "Bulk approve obligations" });
    } finally {
      setBulkLoading(false);
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

  const actionsFor = (item: Obligation) => {
    const status = item.status;
    const normalized = (status ?? "draft").toLowerCase();
    if (normalized === "draft") {
      return [
        { label: "Send to review", status: "in_review" },
        { label: "Reject", status: "rejected" },
      ];
    }
    if (normalized === "in_review") {
      const actions = [{ label: "Reject", status: "rejected" }];
      if (!isCurrentUserCreator(item.created_by)) {
        actions.unshift({ label: "Approve", status: "approved" });
      }
      return actions;
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
          <h1 className="text-2xl font-semibold text-slate-900">
            Regulatory obligations
          </h1>
          <p className="text-sm text-slate-500">
            Track obligations extracted from EU/FR publications and validate
            them internally.
          </p>
        </div>
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-medium text-slate-600 hover:border-slate-300"
        >
          Back to dashboard
        </Link>
      </header>

      {obligationsQuery.isError && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          Failed to load obligations.
        </div>
      )}

      <div className="flex flex-wrap gap-3 text-xs text-slate-500">
        <input
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setPage(0);
          }}
          placeholder="Search CELEX, title, obligation text..."
          className="min-w-[220px] rounded-full border border-slate-200 bg-white px-4 py-2 text-xs text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none"
        />
        <select
          value={statusFilter}
          onChange={(event) => {
            setStatusFilter(event.target.value);
            setPage(0);
          }}
          className="rounded-full border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600"
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
          className="rounded-full border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600"
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
          className="rounded-full border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600"
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
          className="rounded-full border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-600"
        >
          <option value="psp,eme,vasp">PSP / EMI / VASP</option>
          <option value="all">All scopes</option>
          <option value="psp">PSP</option>
          <option value="eme">EMI</option>
          <option value="vasp">VASP</option>
        </select>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between text-sm text-slate-500">
          <div>{loading ? "Loading obligations…" : `${total} obligations`}</div>
          <div className="flex items-center gap-2">
            <button
              onClick={togglePageSelection}
              disabled={loading || !pageItemIds.length}
              className="rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-semibold text-slate-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {allPageSelected ? "Unselect page" : "Select page"}
            </button>
            <button
              onClick={handleBulkApprove}
              disabled={bulkLoading || selectedObligationIds.length === 0}
              className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-[11px] font-semibold text-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {bulkLoading
                ? "Approving..."
                : `Bulk approve (${selectedObligationIds.length})`}
            </button>
            <div>
              Page {page + 1} / {totalPages}
            </div>
          </div>
        </div>

        <div className="mt-4 space-y-4">
          {loading ? (
            <div className="text-sm text-slate-500">Loading...</div>
          ) : items.length ? (
            items.map((item) => (
              <div
                key={item.id}
                className="rounded-lg border border-slate-100 bg-slate-50/60 p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 gap-3">
                    <input
                      type="checkbox"
                      checked={selectedObligationIds.includes(item.id)}
                      onChange={() => toggleItemSelection(item.id)}
                      className="mt-1 h-4 w-4 rounded border-slate-300 bg-white text-emerald-600 focus:ring-emerald-500"
                    />
                    <div className="min-w-0">
                      <Link
                        href={`/compliance/obligations/${item.id}`}
                        className="text-sm font-semibold text-slate-900 hover:underline"
                      >
                        {item.document.title}
                      </Link>
                      <div className="mt-1 text-xs text-slate-500">
                        {item.document.celex} •{""}
                        {item.document.jurisdiction ?? "EU"} •{""}
                        {item.document.source_system ?? "source"}
                      </div>
                      <p className="mt-2 text-xs text-slate-500 line-clamp-2">
                        {item.obligation_text}
                      </p>
                    </div>
                  </div>
                  <span
                    className={
                      "rounded-full px-3 py-1 text-[11px] font-semibold" +
                      obligationStatusStyle(item.status)
                    }
                  >
                    {item.status.replace("_", "")}
                  </span>
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-slate-400">
                  <span>{item.article_ref || "No article ref"}</span>
                  <span>•</span>
                  <span>Updated {formatDate(item.updated_at)}</span>
                </div>
                {actionsFor(item).length ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {actionsFor(item).map((action) => (
                      <button
                        key={action.status}
                        onClick={() => updateStatus(item.id, action.status)}
                        disabled={
                          actionLoading === `${item.id}:${action.status}`
                        }
                        className="rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-semibold text-slate-600 hover:border-slate-300 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {action.label}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            ))
          ) : (
            <div className="text-sm text-slate-500">
              No obligations match your filters.
            </div>
          )}
        </div>

        <div className="mt-6 flex items-center justify-between">
          <button
            onClick={() => setPage((prev) => Math.max(0, prev - 1))}
            disabled={page === 0}
            className="rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-medium text-slate-600 disabled:opacity-50"
          >
            Previous
          </button>
          <button
            onClick={() =>
              setPage((prev) => Math.min(totalPages - 1, prev + 1))
            }
            disabled={page + 1 >= totalPages}
            className="rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-medium text-slate-600 disabled:opacity-50"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
