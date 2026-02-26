"use client";

import {
  AlertTriangle,
  Database,
  FileJson,
  History,
  PlayCircle,
  Sparkles,
} from "lucide-react";
import type {
  DecisionResponse,
  EventResponse,
  FeatureSetResponse,
  TransactionResponse,
} from "@/app/decisioning/components/types";
import FeatureStorePanel from "@/app/decisioning/components/FeatureStorePanel";

export default function DecisionSimulator({
  apiUrl,
  autoRun,
  onAutoRunChange,
  eventType,
  onEventTypeChange,
  transactionId,
  onTransactionIdChange,
  entityType,
  onEntityTypeChange,
  entityId,
  onEntityIdChange,
  source,
  onSourceChange,
  payload,
  onPayloadChange,
  context,
  onContextChange,
  error,
  loading,
  transactionLoading,
  onIngestEvent,
  onCreateTransaction,
  onRunDecision,
  featureEntityType,
  onFeatureEntityTypeChange,
  featureEntityId,
  onFeatureEntityIdChange,
  featuresJson,
  onFeaturesJsonChange,
  featureLoading,
  featureResponse,
  onSetFeatures,
  onLoadFeatures,
  eventResult,
  transactionResult,
  decisionResult,
  auditLoading,
  eventRecord,
  decisionRecord,
  auditLogs,
}: {
  apiUrl: string;
  autoRun: boolean;
  onAutoRunChange: (value: boolean) => void;
  eventType: string;
  onEventTypeChange: (value: string) => void;
  transactionId: string;
  onTransactionIdChange: (value: string) => void;
  entityType: string;
  onEntityTypeChange: (value: string) => void;
  entityId: string;
  onEntityIdChange: (value: string) => void;
  source: string;
  onSourceChange: (value: string) => void;
  payload: string;
  onPayloadChange: (value: string) => void;
  context: string;
  onContextChange: (value: string) => void;
  error: string | null;
  loading: boolean;
  transactionLoading: boolean;
  onIngestEvent: () => void;
  onCreateTransaction: () => void;
  onRunDecision: () => void;
  featureEntityType: string;
  onFeatureEntityTypeChange: (value: string) => void;
  featureEntityId: string;
  onFeatureEntityIdChange: (value: string) => void;
  featuresJson: string;
  onFeaturesJsonChange: (value: string) => void;
  featureLoading: boolean;
  featureResponse: FeatureSetResponse | null;
  onSetFeatures: () => void;
  onLoadFeatures: () => void;
  eventResult: EventResponse | null;
  transactionResult: TransactionResponse | null;
  decisionResult: DecisionResponse | null;
  auditLoading: boolean;
  eventRecord: Record<string, unknown> | null;
  decisionRecord: Record<string, unknown> | null;
  auditLogs: Record<string, unknown>[];
}) {
  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-slate-200  bg-white  p-4 flex items-center justify-between">
        <div className="text-sm text-slate-600  flex items-center gap-2">
          <Sparkles className="h-4 w-4" />
          Auto-run sample decision on load
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={autoRun}
            onChange={(e) => onAutoRunChange(e.target.checked)}
          />
          Enable
        </label>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="rounded-xl border border-slate-200  bg-white  p-6 shadow-sm space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-slate-600 ">
                  Event Type
                </label>
                <input
                  value={eventType}
                  onChange={(event) => onEventTypeChange(event.target.value)}
                  className="mt-1 w-full rounded-md border border-slate-300  bg-white  px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 ">
                  Transaction ID (optional)
                </label>
                <input
                  value={transactionId}
                  onChange={(event) =>
                    onTransactionIdChange(event.target.value)
                  }
                  className="mt-1 w-full rounded-md border border-slate-300  bg-white  px-3 py-2 text-sm"
                  placeholder="Numeric ID"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 ">
                  Entity Type
                </label>
                <input
                  value={entityType}
                  onChange={(event) => onEntityTypeChange(event.target.value)}
                  className="mt-1 w-full rounded-md border border-slate-300  bg-white  px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 ">
                  Entity ID
                </label>
                <input
                  value={entityId}
                  onChange={(event) => onEntityIdChange(event.target.value)}
                  className="mt-1 w-full rounded-md border border-slate-300  bg-white  px-3 py-2 text-sm"
                  placeholder="TXN-0001"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 ">
                  Source
                </label>
                <input
                  value={source}
                  onChange={(event) => onSourceChange(event.target.value)}
                  className="mt-1 w-full rounded-md border border-slate-300  bg-white  px-3 py-2 text-sm"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-600 ">
                Payload (JSON)
              </label>
              <textarea
                value={payload}
                onChange={(event) => onPayloadChange(event.target.value)}
                rows={8}
                className="mt-1 w-full rounded-md border border-slate-300  bg-slate-950 text-slate-100 font-mono text-xs p-3"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-600 ">
                Context (JSON)
              </label>
              <textarea
                value={context}
                onChange={(event) => onContextChange(event.target.value)}
                rows={6}
                className="mt-1 w-full rounded-md border border-slate-300  bg-slate-950 text-slate-100 font-mono text-xs p-3"
              />
            </div>

            {error ? (
              <div className="rounded-md border border-red-200 bg-red-50 text-red-700    px-3 py-2 text-xs flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" />
                {error}
              </div>
            ) : null}

            <div className="flex flex-wrap gap-3">
              <button
                onClick={onIngestEvent}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 rounded-md bg-white  border border-slate-300  text-sm disabled:opacity-60"
              >
                <Database className="h-4 w-4" />
                Ingest Event
              </button>
              <button
                onClick={onCreateTransaction}
                disabled={transactionLoading}
                className="flex items-center gap-2 px-4 py-2 rounded-md bg-white  border border-slate-300  text-sm disabled:opacity-60"
              >
                <FileJson className="h-4 w-4" />
                {transactionLoading ? "Creating..." : "Create Transaction"}
              </button>
              <button
                onClick={onRunDecision}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 rounded-md bg-slate-900 text-white text-sm hover:bg-slate-800 disabled:opacity-60"
              >
                <PlayCircle className="h-4 w-4" />
                Run Decision
              </button>
            </div>
          </div>

          <FeatureStorePanel
            featureEntityType={featureEntityType}
            setFeatureEntityType={onFeatureEntityTypeChange}
            featureEntityId={featureEntityId}
            setFeatureEntityId={onFeatureEntityIdChange}
            featuresJson={featuresJson}
            setFeaturesJson={onFeaturesJsonChange}
            featureLoading={featureLoading}
            featureResponse={featureResponse}
            onSetFeatures={onSetFeatures}
            onLoadFeatures={onLoadFeatures}
          />
        </div>

        <div className="space-y-6">
          <div className="rounded-xl border border-slate-200  bg-white  p-6 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-900 ">
              Event Response
            </h2>
            <div className="mt-3 text-xs text-slate-600 ">
              {eventResult ? (
                <pre className="bg-slate-950 text-slate-100 p-3 rounded-md overflow-auto max-h-72">
                  {JSON.stringify(eventResult, null, 2)}
                </pre>
              ) : (
                "No event ingested yet."
              )}
            </div>
          </div>

          <div className="rounded-xl border border-slate-200  bg-white  p-6 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-900 ">
              Transaction
            </h2>
            <div className="mt-3 text-xs text-slate-600 ">
              {transactionResult ? (
                <pre className="bg-slate-950 text-slate-100 p-3 rounded-md overflow-auto max-h-72">
                  {JSON.stringify(transactionResult, null, 2)}
                </pre>
              ) : (
                "No transaction created yet."
              )}
            </div>
          </div>

          <div className="rounded-xl border border-slate-200  bg-white  p-6 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-900 ">
              Decision Result
            </h2>
            <div className="mt-3 text-xs text-slate-600 ">
              {decisionResult ? (
                <div className="space-y-3">
                  <pre className="bg-slate-950 text-slate-100 p-3 rounded-md overflow-auto max-h-72">
                    {JSON.stringify(decisionResult, null, 2)}
                  </pre>
                  {decisionResult.reason_codes?.length ? (
                    <div className="rounded-md border border-slate-200  p-3 text-xs text-slate-600 ">
                      <div className="font-semibold mb-2">Rules Triggered</div>
                      <div className="flex flex-wrap gap-2">
                        {decisionResult.reason_codes.map((code) => (
                          <a
                            key={code}
                            href="/transaction-monitoring/rules"
                            className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-700  "
                          >
                            {code}
                          </a>
                        ))}
                      </div>
                    </div>
                  ) : null}
                  {decisionResult.alerts?.length ? (
                    <div className="rounded-md border border-slate-200  p-3 text-xs text-slate-600 ">
                      <div className="font-semibold mb-2">Alerts</div>
                      <div className="flex flex-wrap gap-2">
                        {decisionResult.alerts.map((alertId) => (
                          <span
                            key={alertId}
                            className="rounded-full bg-orange-100 px-2 py-1 text-xs text-orange-700  "
                          >
                            {alertId}
                          </span>
                        ))}
                      </div>
                    </div>
                  ) : null}
                  <a
                    href={`${apiUrl}/api/reporting/evidence/decision/${decisionResult.decision_id}`}
                    className="text-xs text-blue-600 hover:text-blue-700"
                  >
                    Download decision evidence
                  </a>
                </div>
              ) : (
                "No decision run yet."
              )}
            </div>
          </div>

          <div className="rounded-xl border border-slate-200  bg-white  p-6 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-900  flex items-center gap-2">
              <History className="h-4 w-4" />
              Decision Timeline
            </h2>
            {auditLoading ? (
              <div className="text-xs text-slate-500 mt-3">Loading...</div>
            ) : (
              <div className="mt-3 space-y-3 text-xs text-slate-600 ">
                {eventRecord ? (
                  <pre className="bg-slate-950 text-slate-100 p-3 rounded-md overflow-auto max-h-40">
                    {JSON.stringify(eventRecord, null, 2)}
                  </pre>
                ) : null}
                {decisionRecord ? (
                  <pre className="bg-slate-950 text-slate-100 p-3 rounded-md overflow-auto max-h-40">
                    {JSON.stringify(decisionRecord, null, 2)}
                  </pre>
                ) : null}
                {auditLogs?.length ? (
                  <pre className="bg-slate-950 text-slate-100 p-3 rounded-md overflow-auto max-h-40">
                    {JSON.stringify(auditLogs, null, 2)}
                  </pre>
                ) : (
                  <div>No audit logs yet.</div>
                )}
              </div>
            )}
          </div>

          <div className="rounded-xl border border-dashed border-slate-300  bg-white/60  p-5 text-xs text-slate-600 ">
            <div className="flex items-center gap-2 text-slate-700  font-medium mb-2">
              <FileJson className="h-4 w-4" />
              Quick tips
            </div>
            <ul className="space-y-2">
              <li>
                Use transaction_id to attach decisions to stored transactions.
              </li>
              <li>Use /api/features to add online features before deciding.</li>
              <li>Events are immutable and show in the Audit Trail.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
