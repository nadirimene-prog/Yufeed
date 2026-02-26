"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import AuditFilters, { AuditFilters as Filters } from "./audit-filters";
import AuditTable, { AuditLog } from "./audit-table";
import AuditDetail from "./audit-detail";
import { TableSkeleton } from "@/components/ui/skeleton";
import { fetchWithAuth } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/apiBaseUrl";

const API_URL = getApiBaseUrl();

const DEFAULT_FILTERS: Filters = {
  search: "",
  action: "all",
  entityType: "all",
  entityId: "",
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
  const [caseId, setCaseId] = useState("");
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const searchParams = useSearchParams();

  useEffect(() => {
    fetchLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters, page]);

  useEffect(() => {
    const entityType = searchParams.get("entity_type");
    const entityId = searchParams.get("entity_id");
    const action = searchParams.get("action");
    const actorId = searchParams.get("actor_id");
    const search = searchParams.get("search");

    if (entityType || entityId || action || actorId || search) {
      setFilters((prev) => ({
        ...prev,
        entityType: entityType || prev.entityType,
        entityId: entityId || prev.entityId,
        action: action || prev.action,
        actorId: actorId || prev.actorId,
        search: search || prev.search,
      }));
      setPage(0);
    }
  }, [searchParams]);

  const fetchLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        skip: String(page * pageSize),
        limit: String(pageSize),
      });
      if (filters.action !== "all") params.set("action", filters.action);
      if (filters.entityType !== "all")
        params.set("entity_type", filters.entityType);
      if (filters.entityId) params.set("entity_id", filters.entityId);
      if (filters.actorId) params.set("actor_id", filters.actorId);

      const res = await fetchWithAuth(
        `${API_URL}/api/audit/logs?${params.toString()}`,
      );
      if (!res.ok) throw new Error(`Failed to load logs (${res.status})`);
      const data = await res.json();
      setLogs(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load audit logs",
      );
    } finally {
      setLoading(false);
    }
  };

  const exportCaseEvidence = async () => {
    const trimmed = caseId.trim();
    if (!trimmed) {
      setExportError("Enter a case ID to export evidence.");
      return;
    }
    setExporting(true);
    setExportError(null);
    try {
      const res = await fetchWithAuth(
        `${API_URL}/api/reporting/evidence/case/${trimmed}`,
      );
      if (!res.ok) {
        throw new Error(`Evidence export failed (${res.status})`);
      }
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `case-evidence-${trimmed}.json`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setExportError(
        err instanceof Error ? err.message : "Failed to export evidence",
      );
    } finally {
      setExporting(false);
    }
  };

  const filteredLogs = useMemo(() => {
    if (!filters.search) return logs;
    const query = filters.search.toLowerCase();
    return logs.filter((log) =>
      [log.audit_id, log.actor_email, log.actor_id, log.entity_id, log.path]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(query)),
    );
  }, [logs, filters.search]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900 ">
            Audit Trail
          </h1>
          <p className="text-sm text-slate-600 ">
            Immutable audit logs for compliance evidence and replay.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchLogs()}
            className="px-3 py-2 text-sm rounded-md border border-slate-300  bg-white  text-slate-900 "
          >
            Refresh
          </button>
        </div>
      </div>

      <div className="rounded-md border border-slate-200  bg-white  p-4">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-900 ">
              Evidence Export
            </h2>
            <p className="text-xs text-slate-600 ">
              Download an immutable evidence bundle for a case.
            </p>
          </div>
          <div className="flex flex-col sm:flex-row sm:items-center gap-2">
            <input
              value={caseId}
              onChange={(event) => setCaseId(event.target.value)}
              placeholder="Case ID"
              className="px-3 py-2 text-sm rounded-md border border-slate-300  bg-white  text-slate-900  w-full sm:w-64"
            />
            <button
              onClick={exportCaseEvidence}
              disabled={exporting}
              className="px-3 py-2 text-sm rounded-md border border-slate-300  bg-slate-900 text-white disabled:opacity-60"
            >
              {exporting ? "Preparing..." : "Download JSON"}
            </button>
          </div>
        </div>
        {exportError ? (
          <div className="mt-3 text-xs text-red-600 ">{exportError}</div>
        ) : null}
      </div>

      <AuditFilters filters={filters} onChange={setFilters} />

      {loading ? (
        <TableSkeleton rows={6} />
      ) : error ? (
        <div className="rounded-md border border-red-200 bg-red-50 text-red-700    p-4">
          {error}
        </div>
      ) : (
        <>
          <AuditTable logs={filteredLogs} onSelect={setSelectedLog} />
          <div className="flex items-center justify-between">
            <div className="text-sm text-slate-500 ">Page {page + 1}</div>
            <div className="space-x-2">
              <button
                className="px-3 py-2 text-sm rounded-md border border-slate-300  bg-white  text-slate-900  disabled:opacity-50"
                disabled={page === 0}
                onClick={() => setPage((p) => Math.max(0, p - 1))}
              >
                Previous
              </button>
              <button
                className="px-3 py-2 text-sm rounded-md border border-slate-300  bg-white  text-slate-900 "
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
