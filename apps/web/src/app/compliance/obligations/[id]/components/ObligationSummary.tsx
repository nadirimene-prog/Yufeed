"use client";

import { formatDate } from "@/app/compliance/obligations/[id]/components/utils";

export default function ObligationSummary({
  obligationText,
  articleRef,
  applicability,
  effectiveDate,
  updatedAt,
}: {
  obligationText: string;
  articleRef?: string | null;
  applicability?: string | null;
  effectiveDate?: string | null;
  updatedAt?: string | null;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="text-sm font-semibold text-gray-900 dark:text-white">
        Obligation summary
      </div>
      <div className="mt-3 text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap">
        {obligationText}
      </div>

      <div className="mt-4 grid gap-3 text-xs text-gray-500 sm:grid-cols-2">
        <div>
          <div className="uppercase text-[11px] text-gray-400">
            Article reference
          </div>
          <div className="mt-1 text-sm text-gray-700 dark:text-gray-300">
            {articleRef ?? "—"}
          </div>
        </div>
        <div>
          <div className="uppercase text-[11px] text-gray-400">
            Applicability
          </div>
          <div className="mt-1 text-sm text-gray-700 dark:text-gray-300">
            {applicability ?? "—"}
          </div>
        </div>
        <div>
          <div className="uppercase text-[11px] text-gray-400">
            Effective date
          </div>
          <div className="mt-1 text-sm text-gray-700 dark:text-gray-300">
            {formatDate(effectiveDate)}
          </div>
        </div>
        <div>
          <div className="uppercase text-[11px] text-gray-400">Updated</div>
          <div className="mt-1 text-sm text-gray-700 dark:text-gray-300">
            {formatDate(updatedAt)}
          </div>
        </div>
      </div>
    </div>
  );
}
