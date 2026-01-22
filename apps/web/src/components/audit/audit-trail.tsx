"use client";

import { useEffect, useMemo, useState } from "react";
import AuditFilters, { AuditFilters as Filters } from "./audit-filters";
import AuditTable, { AuditLog } from "./audit-table";
import AuditDetail from "./audit-detail";
import { TableSkeleton } from "@/components/ui/skeleton";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const DEFAULT_FILTERS: Filters = {
  search: "",
  action: "all",
  entityType: "all",
  actorId: "",
};

export default function AuditTrail() {
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const pageSize = 25;
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

  useEffect(() => {
    fetchLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters, page]);

  const fetchLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        skip: String(page * pageSize),
        limit: String(pageSize),
      });
      if (filters.action !== "all") params.set("action", filters.action);
      if (filters.entityType !== "all") params.set("entity_type", filters.entityType);
      if (filters.actorId) params.set("actor_id", filters.actorId);

      const res = await fetch(`${API_URL}/api/audit/logs?${params.toString()}`);
      if (!res.ok) throw new Error(`Failed to load logs (${res.status})`);
      const data = await res.json();
      setLogs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load audit logs");
    } finally {
      setLoading(false);
    }
  };

  const filteredLogs = useMemo(() => {
    if (!filters.search) return logs;
    const query = filters.search.toLowerCase();
    return logs.filter((log) =>
      [
        log.audit_id,
        log.actor_email,
        log.actor_id,
        log.entity_id,
        log.path,
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(query))
    );
  }, [logs, filters.search]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
            Audit Trail
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Immutable audit logs for compliance evidence and replay.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchLogs()}
            className="px-3 py-2 text-sm rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-100"
          >
            Refresh
          </button>
        </div>
      </div>

      <AuditFilters filters={filters} onChange={setFilters} />

      {loading ? (
        <TableSkeleton rows={6} />
      ) : error ? (
        <div className="rounded-md border border-red-200 bg-red-50 text-red-700 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-200 p-4">
          {error}
        </div>
      ) : (
        <>
          <AuditTable logs={filteredLogs} onSelect={setSelectedLog} />
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Page {page + 1}
            </div>
            <div className="space-x-2">
              <button
                className="px-3 py-2 text-sm rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-100 disabled:opacity-50"
                disabled={page === 0}
                onClick={() => setPage((p) => Math.max(0, p - 1))}
              >
                Previous
              </button>
              <button
                className="px-3 py-2 text-sm rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-100"
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}

      <AuditDetail
        open={!!selectedLog}
        onOpenChange={(open) => !open && setSelectedLog(null)}
        log={selectedLog}
      />
    </div>
  );
}
