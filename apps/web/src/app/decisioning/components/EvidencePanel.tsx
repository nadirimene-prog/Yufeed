"use client";

import { History } from "lucide-react";
import type { DecisionEvidenceBundle } from "@/app/decisioning/components/types";

export default function EvidencePanel({
  evidenceLoading,
  evidenceBundle,
}: {
  evidenceLoading: boolean;
  evidenceBundle: DecisionEvidenceBundle | null;
}) {
  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 p-5 space-y-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
        <History className="h-4 w-4" />
        Evidence & Audit Trail
      </div>
      {evidenceLoading ? (
        <div className="text-xs text-gray-500">Loading evidence...</div>
      ) : evidenceBundle ? (
        <div className="space-y-3 text-xs text-gray-600 dark:text-gray-400">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-3">
              <div className="text-[10px] uppercase text-gray-400">Risk Score</div>
              <div className="mt-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
                {evidenceBundle.decision?.evidence?.risk_score ?? "-"}
              </div>
            </div>
            <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-3">
              <div className="text-[10px] uppercase text-gray-400">Risk Level</div>
              <div className="mt-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
                {evidenceBundle.decision?.evidence?.risk_level ?? "-"}
              </div>
            </div>
            <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-3">
              <div className="text-[10px] uppercase text-gray-400">Alerts</div>
              <div className="mt-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
                {Array.isArray(evidenceBundle.decision?.evidence?.alerts)
                  ? evidenceBundle.decision?.evidence?.alerts.length
                  : "-"}
              </div>
            </div>
            <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-3">
              <div className="text-[10px] uppercase text-gray-400">On-chain</div>
              <div className="mt-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
                {evidenceBundle.decision?.evidence?.onchain?.risk_level ?? "-"}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="rounded-md border border-gray-200 dark:border-gray-800 p-3">
              <div className="text-[10px] uppercase text-gray-400">Decision</div>
              <pre className="mt-2 max-h-40 overflow-auto bg-gray-950 text-gray-100 p-2 rounded">
                {JSON.stringify(evidenceBundle.decision, null, 2)}
              </pre>
            </div>
            <div className="rounded-md border border-gray-200 dark:border-gray-800 p-3">
              <div className="text-[10px] uppercase text-gray-400">Event</div>
              <pre className="mt-2 max-h-40 overflow-auto bg-gray-950 text-gray-100 p-2 rounded">
                {JSON.stringify(evidenceBundle.event ?? {}, null, 2)}
              </pre>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="rounded-md border border-gray-200 dark:border-gray-800 p-3">
              <div className="text-[10px] uppercase text-gray-400">Transaction</div>
              <pre className="mt-2 max-h-40 overflow-auto bg-gray-950 text-gray-100 p-2 rounded">
                {JSON.stringify(evidenceBundle.transaction ?? {}, null, 2)}
              </pre>
            </div>
            <div className="rounded-md border border-gray-200 dark:border-gray-800 p-3">
              <div className="text-[10px] uppercase text-gray-400">Alerts</div>
              <pre className="mt-2 max-h-40 overflow-auto bg-gray-950 text-gray-100 p-2 rounded">
                {JSON.stringify(evidenceBundle.alerts ?? [], null, 2)}
              </pre>
            </div>
          </div>

          <div className="rounded-md border border-gray-200 dark:border-gray-800 p-3">
            <div className="text-[10px] uppercase text-gray-400">Audit Logs</div>
            <pre className="mt-2 max-h-56 overflow-auto bg-gray-950 text-gray-100 p-2 rounded">
              {JSON.stringify(evidenceBundle.audit_logs ?? [], null, 2)}
            </pre>
          </div>
        </div>
      ) : (
        <div className="text-xs text-gray-500">No evidence loaded.</div>
      )}
    </div>
  );
}

