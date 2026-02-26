"use client";

import { Download, List, RefreshCw } from "lucide-react";
import type {
  DecisionEvidenceBundle,
  DecisionListItem,
  DecisionResponse,
  ReplayDiffRow,
} from "@/app/decisioning/components/types";
import {
  decisionsToCsv,
  downloadFile,
} from "@/app/decisioning/components/utils";
import DecisionDetail from "@/app/decisioning/components/DecisionDetail";
import EvidencePanel from "@/app/decisioning/components/EvidencePanel";
import ReplayComparison from "@/app/decisioning/components/ReplayComparison";

function formatDateTime(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function formatValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "-";
  return String(value);
}

type SetStateAction<T> = T | ((prev: T) => T);
type StateSetter<T> = (value: SetStateAction<T>) => void;

export default function DecisionLog({
  apiUrl,
  decisions,
  decisionTotal,
  decisionPage,
  setDecisionPage,
  decisionPageSize,
  setDecisionPageSize,
  decisionFilter,
  setDecisionFilter,
  eventTypeFilter,
  setEventTypeFilter,
  entityTypeFilter,
  setEntityTypeFilter,
  entityIdFilter,
  setEntityIdFilter,
  decisionIdFilter,
  setDecisionIdFilter,
  eventIdFilter,
  setEventIdFilter,
  fromFilter,
  setFromFilter,
  toFilter,
  setToFilter,
  decisionLoading,
  decisionError,
  selectedDecision,
  onSelectDecision,
  onRefresh,
  decisionBadgeStyles,
  evidenceBundle,
  evidenceLoading,
  onLoadReplayIntoSimulator,
  replaySourceDecisionId,
  replayResult,
}: {
  apiUrl: string;
  decisions: DecisionListItem[];
  decisionTotal: number;
  decisionPage: number;
  setDecisionPage: StateSetter<number>;
  decisionPageSize: number;
  setDecisionPageSize: StateSetter<number>;
  decisionFilter: string;
  setDecisionFilter: (value: string) => void;
  eventTypeFilter: string;
  setEventTypeFilter: (value: string) => void;
  entityTypeFilter: string;
  setEntityTypeFilter: (value: string) => void;
  entityIdFilter: string;
  setEntityIdFilter: (value: string) => void;
  decisionIdFilter: string;
  setDecisionIdFilter: (value: string) => void;
  eventIdFilter: string;
  setEventIdFilter: (value: string) => void;
  fromFilter: string;
  setFromFilter: (value: string) => void;
  toFilter: string;
  setToFilter: (value: string) => void;
  decisionLoading: boolean;
  decisionError: string | null;
  selectedDecision: DecisionListItem | null;
  onSelectDecision: (decision: DecisionListItem) => void;
  onRefresh: () => void;
  decisionBadgeStyles: Record<string, string>;
  evidenceBundle: DecisionEvidenceBundle | null;
  evidenceLoading: boolean;
  onLoadReplayIntoSimulator: (autoRunReplay: boolean) => void;
  replaySourceDecisionId: string | null;
  replayResult: DecisionResponse | null;
}) {
  const originalDecision: Record<string, unknown> = (evidenceBundle?.decision ??
    {}) as Record<string, unknown>;
  const originalEvidenceRaw = originalDecision["evidence"];
  const originalEvidence =
    typeof originalEvidenceRaw === "object" && originalEvidenceRaw !== null
      ? (originalEvidenceRaw as Record<string, unknown>)
      : {};

  const canCompare =
    Boolean(replayResult) &&
    Boolean(replaySourceDecisionId) &&
    replaySourceDecisionId === selectedDecision?.decision_id;

  const diffRows: ReplayDiffRow[] = [
    {
      label: "Decision",
      original: formatValue(originalDecision?.decision),
      replay: formatValue(replayResult?.decision),
    },
    {
      label: "Risk score",
      original: formatValue(originalEvidence?.risk_score),
      replay: formatValue(replayResult?.risk_score),
    },
    {
      label: "Risk level",
      original: formatValue(originalEvidence?.risk_level),
      replay: formatValue(replayResult?.risk_level),
    },
    {
      label: "Alerts",
      original: formatValue(
        Array.isArray(originalEvidence["alerts"])
          ? (originalEvidence["alerts"] as unknown[]).map(String).join(", ")
          : "",
      ),
      replay: formatValue(
        Array.isArray(replayResult?.alerts)
          ? replayResult.alerts.join(", ")
          : "",
      ),
    },
    {
      label: "Reason codes",
      original: formatValue(
        Array.isArray(originalDecision["reason_codes"])
          ? (originalDecision["reason_codes"] as unknown[])
              .map(String)
              .join(", ")
          : "",
      ),
      replay: formatValue(
        Array.isArray(replayResult?.reason_codes)
          ? replayResult.reason_codes.join(", ")
          : "",
      ),
    },
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-1 space-y-4">
        <div className="rounded-xl border border-slate-200  bg-white  p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="text-sm font-semibold text-slate-900  flex items-center gap-2">
              <List className="h-4 w-4" />
              Decision Log
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  const payload = JSON.stringify(decisions, null, 2);
                  downloadFile(
                    "decision-log-page.json",
                    payload,
                    "application/json",
                  );
                }}
                className="inline-flex items-center gap-2 text-xs text-slate-600 "
                title="Export JSON"
              >
                <Download className="h-3.5 w-3.5" />
                JSON
              </button>
              <button
                onClick={() => {
                  const payload = decisionsToCsv(decisions);
                  downloadFile("decision-log-page.csv", payload, "text/csv");
                }}
                className="inline-flex items-center gap-2 text-xs text-slate-600 "
                title="Export CSV"
              >
                <Download className="h-3.5 w-3.5" />
                CSV
              </button>
              <button
                onClick={onRefresh}
                className="inline-flex items-center gap-2 text-xs text-slate-600 "
                title="Refresh"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Refresh
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs">
            <select
              value={decisionFilter}
              onChange={(e) => setDecisionFilter(e.target.value)}
              className="rounded-md border border-slate-300  bg-white  px-2 py-1"
            >
              <option value="">Decision</option>
              <option value="allow">Allow</option>
              <option value="step-up">Step-up</option>
              <option value="step_up">Step up (legacy)</option>
              <option value="alert">Alert</option>
              <option value="block">Block</option>
            </select>
            <input
              value={eventTypeFilter}
              onChange={(e) => setEventTypeFilter(e.target.value)}
              placeholder="Event type"
              className="rounded-md border border-slate-300  bg-white  px-2 py-1"
            />
            <input
              value={entityTypeFilter}
              onChange={(e) => setEntityTypeFilter(e.target.value)}
              placeholder="Entity type"
              className="rounded-md border border-slate-300  bg-white  px-2 py-1"
            />
            <input
              value={entityIdFilter}
              onChange={(e) => setEntityIdFilter(e.target.value)}
              placeholder="Entity ID"
              className="rounded-md border border-slate-300  bg-white  px-2 py-1"
            />
            <input
              value={decisionIdFilter}
              onChange={(e) => setDecisionIdFilter(e.target.value)}
              placeholder="Decision ID"
              className="rounded-md border border-slate-300  bg-white  px-2 py-1"
            />
            <input
              value={eventIdFilter}
              onChange={(e) => setEventIdFilter(e.target.value)}
              placeholder="Event ID"
              className="rounded-md border border-slate-300  bg-white  px-2 py-1"
            />
            <input
              type="datetime-local"
              value={fromFilter}
              onChange={(e) => setFromFilter(e.target.value)}
              className="rounded-md border border-slate-300  bg-white  px-2 py-1"
            />
            <input
              type="datetime-local"
              value={toFilter}
              onChange={(e) => setToFilter(e.target.value)}
              className="rounded-md border border-slate-300  bg-white  px-2 py-1"
            />
          </div>
        </div>

        <div className="rounded-xl border border-slate-200  bg-white  p-4 space-y-3">
          {decisionLoading ? (
            <div className="text-xs text-slate-500">Loading decisions...</div>
          ) : decisionError ? (
            <div className="text-xs text-red-600">{decisionError}</div>
          ) : decisions.length === 0 ? (
            <div className="text-xs text-slate-500">No decisions found.</div>
          ) : (
            <div className="space-y-2 max-h-[520px] overflow-auto pr-2">
              {decisions.map((item) => (
                <button
                  key={item.decision_id}
                  onClick={() => onSelectDecision(item)}
                  className={`w-full text-left rounded-lg border px-3 py-2 text-xs transition ${
                    selectedDecision?.decision_id === item.decision_id
                      ? "border-slate-900  bg-slate-50 "
                      : "border-slate-200  hover:border-slate-400"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                        decisionBadgeStyles[item.decision] ||
                        "bg-slate-100 text-slate-700"
                      }`}
                    >
                      {item.decision}
                    </span>
                    <span className="text-[10px] text-slate-500">
                      {formatDateTime(item.created_at)}
                    </span>
                  </div>
                  <div className="mt-2 text-[11px] text-slate-600 ">
                    <div>Event: {item.event_type ?? "-"}</div>
                    <div>Entity: {item.entity_id ?? "-"}</div>
                  </div>
                </button>
              ))}
            </div>
          )}

          <div className="flex items-center justify-between text-[11px] text-slate-500">
            <div>
              {decisionTotal > 0
                ? `Showing ${decisionPage * decisionPageSize + 1}-${Math.min(
                    decisionTotal,
                    (decisionPage + 1) * decisionPageSize,
                  )} of ${decisionTotal}`
                : "No results"}
            </div>
            <div className="flex items-center gap-2">
              <select
                value={decisionPageSize}
                onChange={(e) => setDecisionPageSize(Number(e.target.value))}
                className="rounded-md border border-slate-300  bg-white  px-2 py-1"
              >
                {[10, 25, 50, 100].map((size) => (
                  <option key={size} value={size}>
                    {size}/page
                  </option>
                ))}
              </select>
              <button
                onClick={() => setDecisionPage((page) => Math.max(0, page - 1))}
                disabled={decisionPage === 0}
                className="rounded-md border border-slate-300  px-2 py-1 disabled:opacity-50"
              >
                Prev
              </button>
              <button
                onClick={() =>
                  setDecisionPage((page) =>
                    (page + 1) * decisionPageSize >= decisionTotal
                      ? page
                      : page + 1,
                  )
                }
                disabled={
                  (decisionPage + 1) * decisionPageSize >= decisionTotal
                }
                className="rounded-md border border-slate-300  px-2 py-1 disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="lg:col-span-2 space-y-4">
        <DecisionDetail
          apiUrl={apiUrl}
          selectedDecision={selectedDecision}
          decisionBadgeStyles={decisionBadgeStyles}
          canReplayEvent={Boolean(evidenceBundle?.event)}
          onLoadIntoSimulator={() => onLoadReplayIntoSimulator(false)}
          onReplayDecision={() => onLoadReplayIntoSimulator(true)}
        />

        <EvidencePanel
          evidenceLoading={evidenceLoading}
          evidenceBundle={evidenceBundle}
        />

        <ReplayComparison canCompare={canCompare} diffRows={diffRows} />
      </div>
    </div>
  );
}
