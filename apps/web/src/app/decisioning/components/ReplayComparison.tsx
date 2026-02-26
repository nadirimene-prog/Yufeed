"use client";

import { Sparkles } from "lucide-react";
import type { ReplayDiffRow } from "@/app/decisioning/components/types";

export default function ReplayComparison({
  canCompare,
  diffRows,
}: {
  canCompare: boolean;
  diffRows: ReplayDiffRow[];
}) {
  return (
    <div className="rounded-xl border border-slate-200  bg-white  p-5 space-y-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 ">
        <Sparkles className="h-4 w-4" />
        Replay Comparison
      </div>
      {canCompare ? (
        <div className="space-y-2 text-xs">
          {diffRows.map((row) => {
            const match =
              String(row.original ?? "") === String(row.replay ?? "");
            return (
              <div
                key={row.label}
                className={`rounded-md border px-3 py-2 ${
                  match
                    ? "border-emerald-200 bg-emerald-50/50 text-emerald-700   "
                    : "border-amber-200 bg-amber-50/60 text-amber-700   "
                }`}
              >
                <div className="text-[10px] uppercase tracking-wider">
                  {row.label}
                </div>
                <div className="mt-1 grid grid-cols-1 md:grid-cols-2 gap-2">
                  <div>
                    <div className="text-[10px] text-slate-500">Original</div>
                    <div className="font-medium">{row.original || "-"}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-slate-500">Replay</div>
                    <div className="font-medium">{row.replay || "-"}</div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-xs text-slate-500">
          Replay a decision to compare outcomes.
        </div>
      )}
    </div>
  );
}
