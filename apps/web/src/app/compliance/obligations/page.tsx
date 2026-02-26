"use client";

export const dynamic = "force-dynamic";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import { handleApiError } from "@/lib/api-error-handler";
import { getAuthUserProfile } from "@/lib/auth";
import {
  analyzeDocument,
  bulkApproveObligations,
  getRegulationObligationCoverage,
} from "@/lib/compliance-api";
import { complianceKeys } from "@/lib/queryKeys";
import {
  useObligationsByRegulationList,
  useObligationsList,
  useUpdateObligationStatus,
} from "@/hooks/queries/useComplianceData";
import type {
  Obligation,
  ObligationsByRegulationGroup,
  RegulationObligationCoverageSummary,
} from "@/types/compliance";

type ObligationsViewMode = "regulation" | "obligation";
type ReanalyzeFeedback = { kind: "success" | "error"; message: string };

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

const articleBucketLabel = (obligation: Obligation) => {
  return (obligation.article_ref || "").trim() || "No article ref";
};

const articleBucketSortKey = (label: string) => {
  if (label === "No article ref") return { bucket: 2, number: Number.MAX_SAFE_INTEGER };
  const match = label.match(/(?:Article|Art\.?)\s*(\d+)/i);
  if (match) return { bucket: 0, number: Number(match[1]) };
  return { bucket: 1, number: Number.MAX_SAFE_INTEGER };
};

const groupObligationsByArticle = (obligations: Obligation[]) => {
  const grouped = new Map<string, Obligation[]>();
  for (const obligation of obligations) {
    const label = articleBucketLabel(obligation);
    const existing = grouped.get(label);
    if (existing) existing.push(obligation);
    else grouped.set(label, [obligation]);
  }
  return Array.from(grouped.entries())
    .sort(([a], [b]) => {
      const aKey = articleBucketSortKey(a);
      const bKey = articleBucketSortKey(b);
      if (aKey.bucket !== bKey.bucket) return aKey.bucket - bKey.bucket;
      if (aKey.number !== bKey.number) return aKey.number - bKey.number;
      return a.localeCompare(b);
    })
    .map(([label, items]) => ({ label, items }));
};

const coverageRatio = (coverage?: RegulationObligationCoverageSummary | null) => {
  if (!coverage) return null;
  return `${coverage.covered_signal_article_count}/${coverage.articles_with_obligation_signal}`;
};

export default function ObligationsPage() {
  const [viewMode, setViewMode] = useState<ObligationsViewMode>("regulation");
  const [statusFilter, setStatusFilter] = useState("pending");
  const [jurisdictionFilter, setJurisdictionFilter] = useState("all");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [scopeFilter, setScopeFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [bulkLoading, setBulkLoading] = useState(false);
  const [reanalyzingDocIds, setReanalyzingDocIds] = useState<number[]>([]);
  const [reanalyzeFeedbackByDoc, setReanalyzeFeedbackByDoc] = useState<
    Record<number, ReanalyzeFeedback>
  >({});
  const [selectedObligationIds, setSelectedObligationIds] = useState<number[]>(
    [],
  );
  const currentUser = useMemo(() => getAuthUserProfile(), []);
  const isAdminUser = (currentUser?.role ?? "").toLowerCase() === "admin";
  const queryClient = useQueryClient();

  const pageSize = 20;

  const baseFilters = useMemo(() => {
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
    };
  }, [statusFilter, jurisdictionFilter, sourceFilter, scopeFilter, query]);

  const flatListParams = useMemo(
    () => ({
      ...baseFilters,
      skip: page * pageSize,
      limit: pageSize,
    }),
    [baseFilters, page],
  );

  const groupedListParams = useMemo(
    () => ({
      ...baseFilters,
      include_coverage: true,
      include_status_counts: true,
      skip: page * pageSize,
      limit: pageSize,
    }),
    [baseFilters, page],
  );

  const obligationsQuery = useObligationsList(flatListParams, {
    enabled: viewMode === "obligation",
  });
  const groupedObligationsQuery = useObligationsByRegulationList(
    groupedListParams,
    { enabled: viewMode === "regulation" },
  );
  const updateStatusMutation = useUpdateObligationStatus();

  const flatItems: Obligation[] = useMemo(
    () => obligationsQuery.data?.items ?? [],
    [obligationsQuery.data?.items],
  );
  const regulationGroups: ObligationsByRegulationGroup[] = useMemo(
    () => groupedObligationsQuery.data?.items ?? [],
    [groupedObligationsQuery.data?.items],
  );

  const loading =
    viewMode === "regulation"
      ? groupedObligationsQuery.isLoading
      : obligationsQuery.isLoading;
  const activeIsError =
    viewMode === "regulation"
      ? groupedObligationsQuery.isError
      : obligationsQuery.isError;

  const total =
    viewMode === "regulation"
      ? groupedObligationsQuery.data?.total_regulations ?? 0
      : obligationsQuery.data?.total ?? 0;
  const groupedTotalObligations = groupedObligationsQuery.data?.total_obligations ?? 0;

  const pageItemIds = useMemo(() => {
    if (viewMode === "regulation") {
      return regulationGroups.flatMap((group) =>
        group.obligations.map((obligation) => obligation.id),
      );
    }
    return flatItems.map((item) => item.id);
  }, [viewMode, regulationGroups, flatItems]);

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

  const handleReanalyzeRegulation = async (group: ObligationsByRegulationGroup) => {
    const docId = group.document.id;
    const celex = group.document.celex?.trim();
    if (!celex) {
      setReanalyzeFeedbackByDoc((prev) => ({
        ...prev,
        [docId]: {
          kind: "error",
          message: "Cannot re-analyze this regulation because the CELEX identifier is missing.",
        },
      }));
      return;
    }

    setReanalyzingDocIds((prev) =>
      prev.includes(docId) ? prev : [...prev, docId],
    );
    setReanalyzeFeedbackByDoc((prev) => {
      const next = { ...prev };
      delete next[docId];
      return next;
    });

    const beforeCoverage = group.coverage ?? null;

    try {
      const response = await analyzeDocument(celex, true);
      const freshCoverage = await getRegulationObligationCoverage(docId);
      const afterCoverage = freshCoverage.coverage ?? null;

      let message = "Re-analysis complete.";
      if (beforeCoverage && afterCoverage) {
        const beforeRatio = coverageRatio(beforeCoverage);
        const afterRatio = coverageRatio(afterCoverage);
        const uncoveredDelta =
          afterCoverage.uncovered_signal_article_count -
          beforeCoverage.uncovered_signal_article_count;
        if (beforeRatio && afterRatio) {
          message = `Re-analysis complete. Coverage ${beforeRatio} -> ${afterRatio} signal articles.`;
        }
        if (uncoveredDelta !== 0) {
          message += ` Uncovered signal articles ${
            uncoveredDelta < 0 ? "decreased" : "increased"
          } by ${Math.abs(uncoveredDelta)}.`;
        }
      }

      const extractedCandidates = Array.isArray(response?.results?.obligations_json)
        ? response.results.obligations_json.length
        : null;
      if (typeof extractedCandidates === "number") {
        message += ` Extracted ${extractedCandidates} candidates.`;
      }

      setReanalyzeFeedbackByDoc((prev) => ({
        ...prev,
        [docId]: { kind: "success", message },
      }));

      await queryClient.invalidateQueries({ queryKey: complianceKeys.obligations() });
    } catch (err) {
      handleApiError(err, { context: `Re-analyze regulation ${celex}` });
      setReanalyzeFeedbackByDoc((prev) => ({
        ...prev,
        [docId]: {
          kind: "error",
          message:
            "Re-analysis failed. Check permissions (admin only) or review backend logs.",
        },
      }));
    } finally {
      setReanalyzingDocIds((prev) => prev.filter((id) => id !== docId));
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
    const normalized = (item.status ?? "draft").toLowerCase();
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

  const renderObligationRow = (item: Obligation) => (
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
              {item.document.celex} • {item.document.jurisdiction ?? "EU"} •{" "}
              {item.document.source_system ?? "source"}
            </div>
            <p className="mt-2 text-xs text-slate-500 line-clamp-2">
              {item.obligation_text}
            </p>
          </div>
        </div>
        <span
          className={
            "rounded-full px-3 py-1 text-[11px] font-semibold " +
            obligationStatusStyle(item.status)
          }
        >
          {item.status.replace("_", " ")}
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
              disabled={actionLoading === `${item.id}:${action.status}`}
              className="rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-semibold text-slate-600 hover:border-slate-300 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {action.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );

  const headerSummaryText = loading
    ? "Loading obligations…"
    : viewMode === "regulation"
      ? `${total} regulations • ${groupedTotalObligations} obligations`
      : `${total} obligations`;

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">
            Regulatory obligations
          </h1>
          <p className="text-sm text-slate-500">
            Review obligations by regulation and article, then validate them
            internally.
          </p>
        </div>
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-medium text-slate-600 hover:border-slate-300"
        >
          Back to dashboard
        </Link>
      </header>

      {activeIsError && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          Failed to load obligations.
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
        <div className="inline-flex rounded-full border border-slate-200 bg-white p-1 shadow-sm">
          <button
            onClick={() => {
              setViewMode("regulation");
              setPage(0);
            }}
            className={
              "rounded-full px-3 py-1 text-xs font-semibold " +
              (viewMode === "regulation"
                ? "bg-slate-900 text-white"
                : "text-slate-600 hover:bg-slate-100")
            }
          >
            By regulation
          </button>
          <button
            onClick={() => {
              setViewMode("obligation");
              setPage(0);
            }}
            className={
              "rounded-full px-3 py-1 text-xs font-semibold " +
              (viewMode === "obligation"
                ? "bg-slate-900 text-white"
                : "text-slate-600 hover:bg-slate-100")
            }
          >
            By obligation
          </button>
        </div>

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
          <option value="all">All statuses</option>
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
          <option value="esma">ESMA</option>
          <option value="amla">AMLA</option>
          <option value="tracfin">TRACFIN</option>
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
          <div>{headerSummaryText}</div>
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
          ) : viewMode === "obligation" ? (
            flatItems.length ? (
              flatItems.map(renderObligationRow)
            ) : (
              <div className="text-sm text-slate-500">
                No obligations match your filters.
              </div>
            )
          ) : regulationGroups.length ? (
            regulationGroups.map((group) => {
              const articleBuckets = groupObligationsByArticle(group.obligations);
              const pendingCount =
                (group.obligation_counts.draft ?? 0) +
                (group.obligation_counts.in_review ?? 0);
              const totalCount = group.obligation_counts.total ?? 0;
              const coverage = group.coverage;
              const isReanalyzing = reanalyzingDocIds.includes(group.document.id);
              const reanalyzeFeedback = reanalyzeFeedbackByDoc[group.document.id];
              return (
                <details
                  key={group.document.id}
                  open
                  className="rounded-xl border border-slate-200 bg-slate-50/50"
                >
                  <summary className="cursor-pointer list-none p-4">
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="rounded-full bg-slate-900 px-2 py-0.5 text-[10px] font-semibold text-white">
                            {group.document.celex || "Document"}
                          </span>
                          <span className="text-[11px] text-slate-500">
                            {group.document.jurisdiction ?? "EU"} •{" "}
                            {group.document.source_system ?? "source"} • Pub.{" "}
                            {formatDate(group.document.publication_date)}
                          </span>
                        </div>
                        <h2 className="mt-2 text-sm font-semibold text-slate-900">
                          {group.document.title}
                        </h2>
                        <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-slate-500">
                          <span className="rounded-full border border-slate-200 bg-white px-2 py-1">
                            Filtered: {group.filtered_obligation_count}
                          </span>
                          <span className="rounded-full border border-slate-200 bg-white px-2 py-1">
                            Total: {totalCount}
                          </span>
                          <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-1 text-amber-700">
                            Pending: {pendingCount}
                          </span>
                          <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-1 text-emerald-700">
                            Approved: {group.obligation_counts.approved ?? 0}
                          </span>
                          <span className="rounded-full border border-rose-200 bg-rose-50 px-2 py-1 text-rose-700">
                            Rejected: {group.obligation_counts.rejected ?? 0}
                          </span>
                        </div>
                        {coverage ? (
                          <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-slate-500">
                            <span className="rounded-full border border-blue-200 bg-blue-50 px-2 py-1 text-blue-700">
                              Coverage: {coverage.covered_signal_article_count}/
                              {coverage.articles_with_obligation_signal} signal
                              articles
                            </span>
                            <span className="rounded-full border border-slate-200 bg-white px-2 py-1">
                              Articles parsed: {coverage.article_count}
                            </span>
                            {coverage.uncovered_signal_article_count > 0 ? (
                              <span className="rounded-full border border-orange-200 bg-orange-50 px-2 py-1 text-orange-700">
                                Uncovered signal articles:{" "}
                                {coverage.uncovered_signal_article_count}
                              </span>
                            ) : null}
                            {coverage.obligations_without_article_ref > 0 ? (
                              <span className="rounded-full border border-slate-200 bg-white px-2 py-1">
                                No article ref:{" "}
                                {coverage.obligations_without_article_ref}
                              </span>
                            ) : null}
                          </div>
                        ) : null}
                      </div>
                      <div className="flex flex-col items-start gap-2 text-[11px] text-slate-400 lg:items-end">
                        <div>
                          Updated {formatDate(group.document.last_obligation_updated_at)}
                        </div>
                        {isAdminUser && group.document.celex ? (
                          <button
                            type="button"
                            onClick={(event) => {
                              event.preventDefault();
                              event.stopPropagation();
                              void handleReanalyzeRegulation(group);
                            }}
                            disabled={isReanalyzing}
                            className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-[11px] font-semibold text-blue-700 hover:border-blue-300 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            {isReanalyzing ? "Re-analyzing..." : "Re-analyze regulation"}
                          </button>
                        ) : null}
                      </div>
                    </div>
                  </summary>

                  <div className="border-t border-slate-200 px-4 py-4">
                    <div className="space-y-4">
                      {reanalyzeFeedback ? (
                        <div
                          className={
                            "rounded-lg border px-3 py-2 text-xs " +
                            (reanalyzeFeedback.kind === "success"
                              ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                              : "border-rose-200 bg-rose-50 text-rose-800")
                          }
                        >
                          {reanalyzeFeedback.message}
                        </div>
                      ) : null}
                      {articleBuckets.map((bucket) => (
                        <details
                          key={`${group.document.id}-${bucket.label}`}
                          open={bucket.label !== "No article ref"}
                          className="rounded-lg border border-slate-200 bg-white"
                        >
                          <summary className="cursor-pointer list-none px-4 py-3">
                            <div className="flex items-center justify-between gap-3">
                              <div className="text-xs font-semibold text-slate-700">
                                {bucket.label}
                              </div>
                              <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[10px] font-semibold text-slate-600">
                                {bucket.items.length} obligation
                                {bucket.items.length > 1 ? "s" : ""}
                              </span>
                            </div>
                          </summary>
                          <div className="border-t border-slate-100 px-3 py-3">
                            <div className="space-y-3">
                              {bucket.items.map(renderObligationRow)}
                            </div>
                          </div>
                        </details>
                      ))}
                    </div>
                  </div>
                </details>
              );
            })
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
            onClick={() => setPage((prev) => Math.min(totalPages - 1, prev + 1))}
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
