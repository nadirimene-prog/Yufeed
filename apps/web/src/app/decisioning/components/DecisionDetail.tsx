"use client";

import { Download, Search } from "lucide-react";
import type { DecisionListItem } from "@/app/decisioning/components/types";

function formatDateTime(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export default function DecisionDetail({
  apiUrl,
  selectedDecision,
  decisionBadgeStyles,
  canReplayEvent,
  onLoadIntoSimulator,
  onReplayDecision,
}: {
  apiUrl: string;
  selectedDecision: DecisionListItem | null;
  decisionBadgeStyles: Record<string, string>;
  canReplayEvent: boolean;
  onLoadIntoSimulator: () => void;
  onReplayDecision: () => void;
}) {
  return (
    <div className="rounded-xl border border-slate-200  bg-white  p-5">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold text-slate-900  flex items-center gap-2">
          <Search className="h-4 w-4" />
          Decision Detail
        </div>
        {selectedDecision ? (
          <a
            href={`${apiUrl}/api/reporting/evidence/decision/${selectedDecision.decision_id}`}
            className="inline-flex items-center gap-2 text-xs text-blue-600 hover:text-blue-700"
          >
            <Download className="h-3.5 w-3.5" />
            Evidence bundle
          </a>
        ) : null}
      </div>

      {selectedDecision ? (
        <div className="mt-4 space-y-4 text-xs text-slate-600 ">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="rounded-lg border border-slate-200  p-3">
              <div className="text-[10px] uppercase tracking-wider text-slate-400">
                Decision
              </div>
              <div className="mt-2">
                <span
                  className={`inline-flex rounded-full px-2 py-1 text-[11px] font-semibold ${
                    decisionBadgeStyles[selectedDecision.decision] ||
                    "bg-slate-100 text-slate-700"
                  }`}
                >
                  {selectedDecision.decision}
                </span>
              </div>
            </div>
            <div className="rounded-lg border border-slate-200  p-3">
              <div className="text-[10px] uppercase tracking-wider text-slate-400">
                Created
              </div>
              <div className="mt-2 font-medium text-slate-900 ">
                {formatDateTime(selectedDecision.created_at)}
              </div>
            </div>
            <div className="rounded-lg border border-slate-200  p-3">
              <div className="text-[10px] uppercase tracking-wider text-slate-400">
                Reason Codes
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {(selectedDecision.reason_codes ?? []).length ? (
                  selectedDecision.reason_codes?.map((code) => (
                    <span
                      key={code}
                      className="rounded-full bg-slate-100 px-2 py-1 text-[11px] text-slate-700  "
                    >
                      {code}
                    </span>
                  ))
                ) : (
                  <span className="text-[11px] text-slate-500">None</span>
                )}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <div className="text-[10px] uppercase tracking-wider text-slate-400">
                Decision ID
              </div>
              <div className="font-medium text-slate-900 ">
                {selectedDecision.decision_id}
              </div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-slate-400">
                Event ID
              </div>
              <div className="font-medium text-slate-900 ">
                {selectedDecision.event_id ?? "-"}
              </div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-slate-400">
                Decision
              </div>
              <div className="font-medium text-slate-900 ">
                {selectedDecision.decision}
              </div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-slate-400">
                Event Type
              </div>
              <div className="font-medium text-slate-900 ">
                {selectedDecision.event_type ?? "-"}
              </div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-slate-400">
                Entity
              </div>
              <div className="font-medium text-slate-900 ">
                {selectedDecision.entity_id ?? "-"}
              </div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-slate-400">
                Rule Version
              </div>
              <div className="font-medium text-slate-900 ">
                {selectedDecision.rule_version ?? "-"}
              </div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-slate-400">
                Model Version
              </div>
              <div className="font-medium text-slate-900 ">
                {selectedDecision.model_version ?? "-"}
              </div>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              onClick={onLoadIntoSimulator}
              disabled={!canReplayEvent}
              className="rounded-md border border-slate-300  px-3 py-2 text-xs disabled:opacity-50"
            >
              Load into simulator
            </button>
            <button
              onClick={onReplayDecision}
              disabled={!canReplayEvent}
              className="rounded-md bg-slate-900 text-white px-3 py-2 text-xs disabled:opacity-50"
            >
              Replay decision
            </button>
          </div>
        </div>
      ) : (
        <div className="mt-4 text-xs text-slate-500">
          Select a decision to view details.
        </div>
      )}
    </div>
  );
}
