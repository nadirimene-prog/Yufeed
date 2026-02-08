"use client";

import { useState } from "react";
import Link from "next/link";
import { useAMLScope } from "@/hooks/queries/useSpecializedData";
import { LoadingBoundary } from "@/components/shared/LoadingBoundary";

interface AMLScopeItem {
  jurisdiction: string;
  total: number;
  approved: number;
  in_review: number;
  draft: number;
  rejected: number;
  covered: number;
  policy_mapped: number;
  coverage_pct: number;
  policy_mapping_pct: number;
}

interface AMLScopeGapItem {
  id: number;
  obligation_id: string;
  status: string;
  obligation_text: string;
  updated_at?: string | null;
  document: {
    celex?: string | null;
    title?: string | null;
    jurisdiction?: string | null;
  };
}

interface AMLScopeResponse {
  as_of: string;
  jurisdiction?: string | null;
  scope?: string | null;
  total_obligations: number;
  status_counts: Record<string, number>;
  coverage: {
    covered: number;
    coverage_pct: number;
    policy_mapped: number;
    policy_mapping_pct: number;
  };
  by_jurisdiction: AMLScopeItem[];
  gap_items: AMLScopeGapItem[];
}

const formatDate = (value?: string | null) => {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return parsed.toLocaleDateString();
};

export default function AmlScopePage() {
  const { data, isLoading, error } = useAMLScope();
  const [jurisdiction, setJurisdiction] = useState("all");
  const [scopeFilter, setScopeFilter] = useState("all");

  const total = data?.total_obligations ?? 0;
  const covered = data?.coverage.covered ?? 0;
  const coveragePct = data?.coverage.coverage_pct ?? 0;
  const policyPct = data?.coverage.policy_mapping_pct ?? 0;
  const gaps = total - covered;
  const isEmpty = !data || total === 0;

  return (
    <LoadingBoundary
      loading={isLoading}
      error={error}
      isEmpty={!data || total === 0}
      emptyMessage="No AML scope data available"
    >
      <div className="p-8 max-w-6xl mx-auto space-y-6">
        <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
              AML Scope Coverage
            </h1>
            <p className="text-sm text-gray-500">
              Regulatory obligations mapped to internal controls and policies.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <label className="text-xs uppercase tracking-wide text-gray-500">
              Jurisdiction
            </label>
            <select
              value={jurisdiction}
              onChange={(event) => setJurisdiction(event.target.value)}
              className="rounded-md border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
            >
              <option value="all">All</option>
              <option value="EU">EU</option>
              <option value="UK">UK</option>
              <option value="US">US</option>
              <option value="FR">FR</option>
              <option value="unknown">Unknown</option>
            </select>
            <label className="text-xs uppercase tracking-wide text-gray-500">
              Scope
            </label>
            <select
              value={scopeFilter}
              onChange={(event) => setScopeFilter(event.target.value)}
              className="rounded-md border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300"
            >
              <option value="all">All</option>
              <option value="psp,eme,vasp">PSP / EMI / VASP</option>
              <option value="psp">PSP</option>
              <option value="eme">EMI</option>
              <option value="vasp">VASP</option>
            </select>
          </div>
        </header>

        {isLoading ? (
          <div className="text-sm text-gray-500">Loading AML scope…</div>
        ) : (
          <>
            {isEmpty && (
              <div className="rounded-lg border border-dashed border-gray-200 bg-white p-5 text-sm text-gray-600 shadow-sm dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300">
                <div className="text-sm font-semibold text-gray-900 dark:text-white">
                  No AML obligations found yet
                </div>
                <p className="mt-2 text-xs text-gray-500">
                  Run ingestion or backfill obligations from existing documents
                  to populate coverage metrics.
                </p>
                <div className="mt-3 flex flex-wrap gap-2 text-xs">
                  <Link
                    href="/compliance/obligations"
                    className="font-semibold text-indigo-600 hover:text-indigo-500"
                  >
                    Review obligations
                  </Link>
                </div>
              </div>
            )}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
                <div className="text-xs uppercase text-gray-500">
                  Total obligations
                </div>
                <div className="text-2xl font-semibold text-gray-900 dark:text-white mt-2">
                  {total}
                </div>
              </div>
              <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
                <div className="text-xs uppercase text-gray-500">
                  Coverage %
                </div>
                <div className="text-2xl font-semibold text-gray-900 dark:text-white mt-2">
                  {coveragePct}%
                </div>
              </div>
              <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
                <div className="text-xs uppercase text-gray-500">
                  Policy mapped %
                </div>
                <div className="text-2xl font-semibold text-gray-900 dark:text-white mt-2">
                  {policyPct}%
                </div>
              </div>
              <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
                <div className="text-xs uppercase text-gray-500">
                  Coverage gaps
                </div>
                <div className="text-2xl font-semibold text-gray-900 dark:text-white mt-2">
                  {gaps}
                </div>
              </div>
            </div>

            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
              <div className="text-sm font-semibold text-gray-900 dark:text-white">
                Jurisdiction coverage
              </div>
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs uppercase text-gray-500">
                      <th className="py-2 pr-4">Jurisdiction</th>
                      <th className="py-2 pr-4">Total</th>
                      <th className="py-2 pr-4">Approved</th>
                      <th className="py-2 pr-4">In review</th>
                      <th className="py-2 pr-4">Draft</th>
                      <th className="py-2 pr-4">Covered</th>
                      <th className="py-2">Coverage %</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-slate-800">
                    {data?.by_jurisdiction?.length ? (
                      data.by_jurisdiction.map((row: AMLScopeItem) => (
                        <tr
                          key={row.jurisdiction}
                          className="text-gray-700 dark:text-gray-300"
                        >
                          <td className="py-3 pr-4 font-medium">
                            {row.jurisdiction.toUpperCase()}
                          </td>
                          <td className="py-3 pr-4">{row.total}</td>
                          <td className="py-3 pr-4">{row.approved}</td>
                          <td className="py-3 pr-4">{row.in_review}</td>
                          <td className="py-3 pr-4">{row.draft}</td>
                          <td className="py-3 pr-4">{row.covered}</td>
                          <td className="py-3">{row.coverage_pct}%</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td className="py-3 text-gray-500" colSpan={7}>
                          {isEmpty
                            ? "No obligations yet. Run ingestion or backfill to populate scope."
                            : "No data"}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold text-gray-900 dark:text-white">
                    Coverage gaps
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Obligations without internal controls.
                  </p>
                </div>
                <Link
                  href="/compliance/obligations"
                  className="text-xs font-semibold text-indigo-600 hover:text-indigo-500"
                >
                  Review obligations
                </Link>
              </div>
              <div className="mt-4 space-y-3">
                {data?.gap_items?.length ? (
                  data.gap_items.map((item: AMLScopeGapItem) => (
                    <Link
                      key={item.id}
                      href={`/compliance/obligations/${item.id}`}
                      className="block rounded-lg border border-gray-100 bg-gray-50/60 p-4 text-sm text-gray-700 hover:border-gray-200 dark:border-slate-800 dark:bg-slate-800/40 dark:text-gray-200"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="font-semibold">
                          {item.obligation_id}
                        </div>
                        <div className="text-xs text-gray-500">
                          {formatDate(item.updated_at)}
                        </div>
                      </div>
                      <div className="mt-2 text-xs text-gray-500 line-clamp-2">
                        {item.obligation_text}
                      </div>
                      <div className="mt-2 text-[11px] text-gray-400">
                        {item.document?.celex || "—"} •{" "}
                        {item.document?.jurisdiction || "EU"}
                      </div>
                    </Link>
                  ))
                ) : (
                  <div className="text-sm text-gray-500">
                    {isEmpty
                      ? "No obligations yet. Ingest documents to see coverage gaps."
                      : "No gaps detected."}
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </LoadingBoundary>
  );
}
