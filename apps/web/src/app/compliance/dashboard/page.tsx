"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { getObligationCoverageStats } from "@/lib/compliance-api";

function metricCard(label: string, value: number, hint?: string) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
        {label}
      </div>
      <div className="mt-2 text-3xl font-semibold text-gray-900 dark:text-white">
        {value}
      </div>
      {hint ? (
        <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
          {hint}
        </div>
      ) : null}
    </div>
  );
}

export default function ComplianceDashboardPage() {
  const coverageQuery = useQuery({
    queryKey: ["compliance", "obligations", "coverage-stats"],
    queryFn: getObligationCoverageStats,
    refetchInterval: 30000,
  });

  const data = coverageQuery.data;

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
            Compliance Coverage
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Obligation to policy mapping coverage and AI suggestion confidence.
          </p>
        </div>
        <Link
          href="/compliance/obligations"
          className="inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white px-4 py-2 text-xs font-medium text-gray-600 hover:border-gray-300 dark:border-slate-700 dark:bg-slate-900 dark:text-gray-300"
        >
          Open obligations
        </Link>
      </header>

      {coverageQuery.isError ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900/40 dark:bg-rose-900/20 dark:text-rose-200">
          Failed to load coverage stats.
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
        {metricCard("Total Obligations", data?.total ?? 0)}
        {metricCard("Linked", data?.linked_count ?? 0)}
        {metricCard("Unlinked", data?.unlinked_count ?? 0)}
        {metricCard("AI Suggested", data?.ai_suggested_count ?? 0)}
        {metricCard(
          "Coverage Rate",
          data?.total ? Math.round((data.linked_count / data.total) * 100) : 0,
          "linked / total",
        )}
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
          Confidence Tiers
        </h2>
        <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
          {metricCard(
            "High",
            data?.confidence_tiers.high ?? 0,
            ">= high threshold",
          )}
          {metricCard(
            "Medium",
            data?.confidence_tiers.medium ?? 0,
            "between medium/high",
          )}
          {metricCard(
            "Low",
            data?.confidence_tiers.low ?? 0,
            "< medium threshold",
          )}
        </div>
      </div>
    </div>
  );
}
