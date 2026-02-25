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
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <div className="text-sm font-semibold text-slate-900">
        Obligation summary
      </div>
      <div className="mt-3 text-sm text-slate-600 whitespace-pre-wrap">
        {obligationText}
      </div>

      <div className="mt-4 grid gap-3 text-xs text-slate-500 sm:grid-cols-2">
        <div>
          <div className="uppercase text-[11px] text-slate-400">
            Article reference
          </div>
          <div className="mt-1 text-sm text-slate-700">{articleRef ?? "—"}</div>
        </div>
        <div>
          <div className="uppercase text-[11px] text-slate-400">
            Applicability
          </div>
          <div className="mt-1 text-sm text-slate-700">
            {applicability ?? "—"}
          </div>
        </div>
        <div>
          <div className="uppercase text-[11px] text-slate-400">
            Effective date
          </div>
          <div className="mt-1 text-sm text-slate-700">
            {formatDate(effectiveDate)}
          </div>
        </div>
        <div>
          <div className="uppercase text-[11px] text-slate-400">Updated</div>
          <div className="mt-1 text-sm text-slate-700">
            {formatDate(updatedAt)}
          </div>
        </div>
      </div>
    </div>
  );
}
