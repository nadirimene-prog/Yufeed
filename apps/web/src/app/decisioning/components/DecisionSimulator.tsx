"use client";

import {
  AlertTriangle,
  Database,
  FileJson,
  History,
  PlayCircle,
  Sparkles,
} from "lucide-react";
import type { DecisionResponse, EventResponse, FeatureSetResponse, TransactionResponse } from "@/app/decisioning/components/types";
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
      <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 p-4 flex items-center justify-between">
        <div className="text-sm text-gray-600 dark:text-gray-400 flex items-center gap-2">
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
          <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 p-6 shadow-sm space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-gray-600 dark:text-gray-400">
                  Event Type
                </label>
                <input
                  value={eventType}
                  onChange={(event) => onEventTypeChange(event.target.value)}
                  className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600 dark:text-gray-400">
                  Transaction ID (optional)
                </label>
                <input
                  value={transactionId}
                  onChange={(event) => onTransactionIdChange(event.target.value)}
                  className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm"
                  placeholder="Numeric ID"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600 dark:text-gray-400">
                  Entity Type
                </label>
                <input
                  value={entityType}
                  onChange={(event) => onEntityTypeChange(event.target.value)}
                  className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600 dark:text-gray-400">
                  Entity ID
                </label>
                <input
                  value={entityId}
                  onChange={(event) => onEntityIdChange(event.target.value)}
                  className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm"
                  placeholder="TXN-0001"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600 dark:text-gray-400">Source</label>
                <input
                  value={source}
                  onChange={(event) => onSourceChange(event.target.value)}
                  className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-medium text-gray-600 dark:text-gray-400">
                Payload (JSON)
              </label>
              <textarea
                value={payload}
                onChange={(event) => onPayloadChange(event.target.value)}
                rows={8}
                className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-gray-950 text-gray-100 font-mono text-xs p-3"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-gray-600 dark:text-gray-400">
                Context (JSON)
              </label>
              <textarea
                value={context}
                onChange={(event) => onContextChange(event.target.value)}
                rows={6}
                className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-gray-950 text-gray-100 font-mono text-xs p-3"
              />
            </div>

            {error ? (
              <div className="rounded-md border border-red-200 bg-red-50 text-red-700 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-200 px-3 py-2 text-xs flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" />
                {error}
              </div>
            ) : null}

            <div className="flex flex-wrap gap-3">
              <button
                onClick={onIngestEvent}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 rounded-md bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 text-sm disabled:opacity-60"
              >
                <Database className="h-4 w-4" />
                Ingest Event
              </button>
              <button
                onClick={onCreateTransaction}
                disabled={transactionLoading}
                className="flex items-center gap-2 px-4 py-2 rounded-md bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 text-sm disabled:opacity-60"
              >
                <FileJson className="h-4 w-4" />
                {transactionLoading ? "Creating..." : "Create Transaction"}
              </button>
              <button
                onClick={onRunDecision}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 rounded-md bg-gray-900 text-white text-sm hover:bg-gray-800 disabled:opacity-60"
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
          <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 p-6 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Event Response</h2>
            <div className="mt-3 text-xs text-gray-600 dark:text-gray-400">
              {eventResult ? (
                <pre className="bg-gray-950 text-gray-100 p-3 rounded-md overflow-auto max-h-72">
                  {JSON.stringify(eventResult, null, 2)}
                </pre>
              ) : (
                "No event ingested yet."
              )}
            </div>
          </div>

          <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 p-6 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Transaction</h2>
            <div className="mt-3 text-xs text-gray-600 dark:text-gray-400">
              {transactionResult ? (
                <pre className="bg-gray-950 text-gray-100 p-3 rounded-md overflow-auto max-h-72">
                  {JSON.stringify(transactionResult, null, 2)}
                </pre>
              ) : (
                "No transaction created yet."
              )}
            </div>
          </div>

          <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 p-6 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Decision Result</h2>
            <div className="mt-3 text-xs text-gray-600 dark:text-gray-400">
              {decisionResult ? (
                <div className="space-y-3">
                  <pre className="bg-gray-950 text-gray-100 p-3 rounded-md overflow-auto max-h-72">
                    {JSON.stringify(decisionResult, null, 2)}
                  </pre>
                  {decisionResult.reason_codes?.length ? (
                    <div className="rounded-md border border-gray-200 dark:border-gray-800 p-3 text-xs text-gray-600 dark:text-gray-300">
                      <div className="font-semibold mb-2">Rules Triggered</div>
                      <div className="flex flex-wrap gap-2">
                        {decisionResult.reason_codes.map((code) => (
                          <a
                            key={code}
                            href="/transaction-monitoring/rules"
                            className="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-700 dark:bg-gray-800 dark:text-gray-200"
                          >
                            {code}
                          </a>
                        ))}
                      </div>
                    </div>
                  ) : null}
                  {decisionResult.alerts?.length ? (
                    <div className="rounded-md border border-gray-200 dark:border-gray-800 p-3 text-xs text-gray-600 dark:text-gray-300">
                      <div className="font-semibold mb-2">Alerts</div>
                      <div className="flex flex-wrap gap-2">
                        {decisionResult.alerts.map((alertId) => (
                          <span
                            key={alertId}
                            className="rounded-full bg-orange-100 px-2 py-1 text-xs text-orange-700 dark:bg-orange-900/30 dark:text-orange-200"
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

          <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 p-6 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
              <History className="h-4 w-4" />
              Decision Timeline
            </h2>
            {auditLoading ? (
              <div className="text-xs text-gray-500 mt-3">Loading...</div>
            ) : (
              <div className="mt-3 space-y-3 text-xs text-gray-600 dark:text-gray-400">
                {eventRecord ? (
                  <pre className="bg-gray-950 text-gray-100 p-3 rounded-md overflow-auto max-h-40">
                    {JSON.stringify(eventRecord, null, 2)}
                  </pre>
                ) : null}
                {decisionRecord ? (
                  <pre className="bg-gray-950 text-gray-100 p-3 rounded-md overflow-auto max-h-40">
                    {JSON.stringify(decisionRecord, null, 2)}
                  </pre>
                ) : null}
                {auditLogs?.length ? (
                  <pre className="bg-gray-950 text-gray-100 p-3 rounded-md overflow-auto max-h-40">
                    {JSON.stringify(auditLogs, null, 2)}
                  </pre>
                ) : (
                  <div>No audit logs yet.</div>
                )}
              </div>
            )}
          </div>

          <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-white/60 dark:bg-gray-950/50 p-5 text-xs text-gray-600 dark:text-gray-400">
            <div className="flex items-center gap-2 text-gray-700 dark:text-gray-200 font-medium mb-2">
              <FileJson className="h-4 w-4" />
              Quick tips
            </div>
            <ul className="space-y-2">
              <li>Use transaction_id to attach decisions to stored transactions.</li>
              <li>Use /api/features to add online features before deciding.</li>
              <li>Events are immutable and show in the Audit Trail.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

