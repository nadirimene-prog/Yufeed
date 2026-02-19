"use client";

import { useMemo, useRef, useState } from "react";
import Link from "next/link";
import { ChevronDown, FileWarning, ListFilter, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ExportButton } from "@/components/ui/export-button";
import { cn } from "@/lib/utils";
import { useWorkspaceUsers } from "@/hooks/queries/useSpecializedData";
import {
  DashboardQueueFilter,
  DashboardSavedView,
  DashboardSeverityFilter,
  DashboardSlaFilter,
  DashboardWorkQueueItem,
  DashboardWorkQueueParams,
  WorkItemActionType,
} from "@/features/dashboard/types";
import {
  formatAgeMinutes,
  severityBadgeClass,
  slaBadgeClass,
} from "@/features/dashboard/utils";

interface UnifiedWorkQueueProps {
  data: {
    items: DashboardWorkQueueItem[];
    page: number;
    page_size: number;
    total: number;
  } | null;
  filters: DashboardWorkQueueParams;
  loading?: boolean;
  error?: string | null;
  selectedItemId: string | null;
  onSelectItem: (item: DashboardWorkQueueItem) => void;
  onFiltersChange: (patch: Partial<DashboardWorkQueueParams>) => void;
  onRefresh: () => void;
  onBulkAction?: (
    items: DashboardWorkQueueItem[],
    action: Exclude<WorkItemActionType, "create_case" | "close">,
    assignee?: string,
  ) => void;
}

const QUEUE_OPTIONS: Array<{ value: DashboardQueueFilter; label: string }> = [
  { value: "all", label: "All" },
  { value: "alerts", label: "Alerts" },
  { value: "cases", label: "Cases" },
  { value: "approvals", label: "Approvals" },
  { value: "reg_tasks", label: "Reg Tasks" },
];

const SAVED_VIEW_OPTIONS: Array<{ value: DashboardSavedView; label: string }> =
  [
    { value: "all", label: "All" },
    { value: "my_queue", label: "My Queue" },
    { value: "team_queue", label: "Team Queue" },
    { value: "escalations", label: "Escalations" },
  ];

const SEVERITY_OPTIONS: Array<{
  value: DashboardSeverityFilter;
  label: string;
}> = [
  { value: "all", label: "All severities" },
  { value: "critical", label: "Critical" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];

const SLA_OPTIONS: Array<{ value: DashboardSlaFilter; label: string }> = [
  { value: "all", label: "All SLA" },
  { value: "breached", label: "Breached" },
  { value: "warning", label: "Warning" },
  { value: "ok", label: "On track" },
  { value: "none", label: "No SLA" },
];

type QueueSort = "default" | "severity" | "age" | "risk";

function severityRank(severity: string) {
  const normalized = severity.toLowerCase();
  if (normalized === "critical") return 4;
  if (normalized === "high") return 3;
  if (normalized === "medium") return 2;
  if (normalized === "low") return 1;
  return 0;
}

function riskToneClass(score: number) {
  if (score >= 70) return "text-risk-critical";
  if (score >= 40) return "text-risk-high";
  return "text-risk-low";
}

export function UnifiedWorkQueue({
  data,
  filters,
  loading = false,
  error = null,
  selectedItemId,
  onSelectItem,
  onFiltersChange,
  onRefresh,
  onBulkAction,
}: UnifiedWorkQueueProps) {
  const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set());
  const [sortBy, setSortBy] = useState<QueueSort>("default");
  const [bulkAssignee, setBulkAssignee] = useState("");
  const rowRefs = useRef<Array<HTMLDivElement | null>>([]);
  const workspaceUsersQuery = useWorkspaceUsers();

  const items = useMemo(() => data?.items ?? [], [data?.items]);

  const sortedItems = useMemo(() => {
    const copy = [...items];
    if (sortBy === "severity") {
      copy.sort((a, b) => severityRank(b.severity) - severityRank(a.severity));
    } else if (sortBy === "age") {
      copy.sort((a, b) => b.age_minutes - a.age_minutes);
    } else if (sortBy === "risk") {
      copy.sort((a, b) => b.risk_score - a.risk_score);
    }
    return copy;
  }, [items, sortBy]);

  const selectedItems = useMemo(
    () => sortedItems.filter((item) => selectedRows.has(item.item_id)),
    [selectedRows, sortedItems],
  );

  const canBulkAction = selectedItems.length > 0 && Boolean(onBulkAction);
  const page = data?.page ?? filters.page;
  const pageSize = data?.page_size ?? filters.pageSize;
  const total = data?.total ?? 0;
  const from = total > 0 ? (page - 1) * pageSize + 1 : 0;
  const to = total > 0 ? Math.min(page * pageSize, total) : 0;

  const allSelectedOnPage =
    sortedItems.length > 0 &&
    sortedItems.every((item) => selectedRows.has(item.item_id));

  const toggleSelectAllOnPage = (checked: boolean) => {
    setSelectedRows((current) => {
      const next = new Set(current);
      if (checked) {
        sortedItems.forEach((item) => next.add(item.item_id));
      } else {
        sortedItems.forEach((item) => next.delete(item.item_id));
      }
      return next;
    });
  };

  const toggleSelected = (itemId: string, checked: boolean) => {
    setSelectedRows((current) => {
      const next = new Set(current);
      if (checked) next.add(itemId);
      else next.delete(itemId);
      return next;
    });
  };

  const runBulkAction = (
    action: Exclude<WorkItemActionType, "create_case" | "close">,
    label: string,
  ) => {
    if (!onBulkAction || selectedItems.length === 0) return;
    const confirmed = window.confirm(
      `Apply '${label}' to ${selectedItems.length} item(s)?`,
    );
    if (!confirmed) return;
    onBulkAction(selectedItems, action, bulkAssignee || undefined);
  };

  return (
    <section className="glass-surface flex h-full min-h-0 flex-col rounded-2xl border border-white/10 p-3 sm:p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-white">
            Unified Work Queue
          </h2>
          <p className="text-xs text-white/60">
            Prioritized triage queue grouped for analyst action.
          </p>
        </div>
        <Button
          variant="glass"
          size="sm"
          onClick={onRefresh}
          disabled={loading}
        >
          <RefreshCw
            className={cn("mr-1.5 h-3.5 w-3.5", loading && "animate-spin")}
          />
          Refresh
        </Button>
      </div>

      <div className="mb-2 grid grid-cols-1 gap-2 xl:grid-cols-2">
        <div className="grid grid-cols-2 gap-2">
          <select
            value={filters.queue}
            onChange={(event) =>
              onFiltersChange({
                queue: event.target.value as DashboardQueueFilter,
                page: 1,
              })
            }
            className="h-9 rounded-lg border border-white/10 bg-white/5 px-2 text-xs text-white"
            aria-label="Queue selector"
          >
            {QUEUE_OPTIONS.map((option) => (
              <option
                key={option.value}
                value={option.value}
                className="bg-[#0b1020]"
              >
                {option.label}
              </option>
            ))}
          </select>

          <select
            value={filters.savedView}
            onChange={(event) =>
              onFiltersChange({
                savedView: event.target.value as DashboardSavedView,
                page: 1,
              })
            }
            className="h-9 rounded-lg border border-white/10 bg-white/5 px-2 text-xs text-white"
            aria-label="Saved queue view"
          >
            {SAVED_VIEW_OPTIONS.map((option) => (
              <option
                key={option.value}
                value={option.value}
                className="bg-[#0b1020]"
              >
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-3 gap-2">
          <select
            value={filters.severity}
            onChange={(event) =>
              onFiltersChange({
                severity: event.target.value as DashboardSeverityFilter,
                page: 1,
              })
            }
            className="h-9 rounded-lg border border-white/10 bg-white/5 px-2 text-xs text-white"
            aria-label="Severity filter"
          >
            {SEVERITY_OPTIONS.map((option) => (
              <option
                key={option.value}
                value={option.value}
                className="bg-[#0b1020]"
              >
                {option.label}
              </option>
            ))}
          </select>

          <select
            value={filters.sla}
            onChange={(event) =>
              onFiltersChange({
                sla: event.target.value as DashboardSlaFilter,
                page: 1,
              })
            }
            className="h-9 rounded-lg border border-white/10 bg-white/5 px-2 text-xs text-white"
            aria-label="SLA filter"
          >
            {SLA_OPTIONS.map((option) => (
              <option
                key={option.value}
                value={option.value}
                className="bg-[#0b1020]"
              >
                {option.label}
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={() =>
              setSortBy((current) => {
                if (current === "default") return "severity";
                if (current === "severity") return "age";
                if (current === "age") return "risk";
                return "default";
              })
            }
            className="inline-flex h-9 items-center justify-center gap-1 rounded-lg border border-white/10 bg-white/5 px-2 text-[11px] uppercase tracking-wide text-white/80"
          >
            Sort
            <ChevronDown className="h-3.5 w-3.5" />
            <span className="text-white/50">{sortBy}</span>
          </button>
        </div>
      </div>

      <div className="mb-3 grid grid-cols-1 gap-2">
        <input
          value={filters.search}
          onChange={(event) =>
            onFiltersChange({ search: event.target.value, page: 1 })
          }
          placeholder="Entity / reference / typology"
          className="h-9 rounded-lg border border-white/10 bg-white/5 px-2 text-xs text-white placeholder:text-white/40"
          aria-label="Queue search"
        />
        <input
          value={filters.jurisdiction}
          onChange={(event) =>
            onFiltersChange({
              jurisdiction: event.target.value.toUpperCase(),
              page: 1,
            })
          }
          placeholder="Jurisdiction (e.g. US, FR, GB)"
          className="h-9 rounded-lg border border-white/10 bg-white/5 px-2 text-xs text-white placeholder:text-white/40"
          aria-label="Jurisdiction filter"
        />
      </div>

      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div
          className="inline-flex items-center gap-1 rounded-lg border border-white/10 bg-white/5 p-1 text-[11px] text-white/70"
          aria-live="polite"
        >
          <ListFilter className="h-3.5 w-3.5" />
          <span>
            Rows {total ? `${from}-${to}` : "0"} / {total}
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-1">
          <label className="inline-flex items-center gap-1 rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-[11px] text-white/70">
            <input
              type="checkbox"
              aria-label="Select all items on this page"
              checked={allSelectedOnPage}
              onChange={(event) => toggleSelectAllOnPage(event.target.checked)}
            />
            Select all
          </label>
          <select
            value={bulkAssignee}
            onChange={(event) => setBulkAssignee(event.target.value)}
            className="h-8 min-w-[150px] rounded-lg border border-white/10 bg-white/5 px-2 text-[11px] text-white"
            aria-label="Bulk assignment analyst"
          >
            <option value="">Assign to...</option>
            {(workspaceUsersQuery.data ?? []).map((user) => (
              <option
                key={user.user_id}
                value={user.user_id}
                className="bg-[#0b1020]"
              >
                {user.user_id}
              </option>
            ))}
          </select>
          <Button
            variant="glass"
            size="sm"
            onClick={() => runBulkAction("assign", "Bulk assign")}
            disabled={!canBulkAction || bulkAssignee.trim().length === 0}
          >
            Bulk assign
          </Button>
          <Button
            variant="glass"
            size="sm"
            onClick={() => runBulkAction("escalate", "Escalate")}
            disabled={!canBulkAction}
          >
            Escalate
          </Button>
          <Button
            variant="glass"
            size="sm"
            onClick={() =>
              runBulkAction("mark_in_progress", "Mark In Progress")
            }
            disabled={!canBulkAction}
          >
            In Progress
          </Button>
          <Button
            variant="glass"
            size="sm"
            disabled={selectedRows.size === 0}
            onClick={() => setSelectedRows(new Set())}
          >
            Clear
          </Button>
          <ExportButton
            data={sortedItems as unknown as Record<string, unknown>[]}
            filename="dashboard-work-queue"
            pdfTitle="Dashboard Work Queue"
            variant="glass"
            size="sm"
            loading={loading}
            columns={[
              { key: "ref_id", label: "Reference" },
              { key: "kind", label: "Kind" },
              { key: "severity", label: "Severity" },
              { key: "entity", label: "Entity" },
              { key: "jurisdiction", label: "Jurisdiction" },
              { key: "risk_score", label: "Risk Score" },
              { key: "status", label: "Status" },
            ]}
          />
        </div>
      </div>

      <div
        className="min-h-0 flex-1 overflow-auto"
        role="feed"
        aria-label="Unified work queue items"
      >
        {loading ? (
          <div className="rounded-xl border border-white/10 p-6 text-center text-sm text-white/50">
            Loading queue...
          </div>
        ) : error ? (
          <div className="rounded-xl border border-risk-critical/40 bg-risk-critical-soft p-4 text-sm text-risk-critical">
            {error}
          </div>
        ) : sortedItems.length === 0 ? (
          <div className="rounded-xl border border-white/10 p-6 text-center text-sm text-white/50">
            No queue items for current filters.
          </div>
        ) : (
          <div className="space-y-2">
            {sortedItems.map((item, index) => {
              const selected = selectedRows.has(item.item_id);

              return (
                <div
                  key={item.item_id}
                  ref={(element) => {
                    rowRefs.current[index] = element;
                  }}
                  tabIndex={0}
                  role="button"
                  onClick={() => onSelectItem(item)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onSelectItem(item);
                      return;
                    }
                    if (event.key === "ArrowDown") {
                      event.preventDefault();
                      rowRefs.current[index + 1]?.focus();
                      return;
                    }
                    if (event.key === "ArrowUp") {
                      event.preventDefault();
                      rowRefs.current[index - 1]?.focus();
                    }
                  }}
                  className={cn(
                    "w-full rounded-xl border p-3 text-left transition",
                    item.item_id === selectedItemId
                      ? "border-primary/60 bg-primary/10"
                      : "border-white/10 bg-white/[0.03] hover:border-white/20 hover:bg-white/[0.06]",
                  )}
                  aria-label={`Queue item ${item.ref_id}`}
                >
                  <div className="mb-1 flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={selected}
                        aria-label={`Select ${item.ref_id}`}
                        onClick={(event) => event.stopPropagation()}
                        onChange={(event) =>
                          toggleSelected(item.item_id, event.target.checked)
                        }
                      />
                      <span className="font-mono text-xs font-semibold text-white/90">
                        {item.ref_id}
                      </span>
                      {item.sar_required ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-risk-high-soft px-2 py-0.5 text-[10px] uppercase text-risk-high">
                          <FileWarning className="h-3 w-3" />
                          SAR Required
                        </span>
                      ) : null}
                    </div>
                    <span className="text-[11px] text-white/50">
                      {formatAgeMinutes(item.age_minutes)} ago
                    </span>
                  </div>

                  <div className="mb-1 flex flex-wrap items-center gap-1.5 text-[10px] uppercase tracking-wide text-white/50">
                    <span className="rounded-full bg-white/10 px-2 py-0.5">
                      {item.type_label}
                    </span>
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5",
                        severityBadgeClass(item.severity),
                      )}
                    >
                      {item.severity}
                    </span>
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5",
                        slaBadgeClass(item.sla_status),
                      )}
                    >
                      SLA {item.sla_status}
                    </span>
                    <span className="rounded-full bg-white/10 px-2 py-0.5">
                      {item.jurisdiction}
                    </span>
                  </div>

                  <p className="mb-1 truncate text-xs text-white/70">
                    {item.typology} ·{" "}
                    <Link
                      href={`/entities/user/${encodeURIComponent(item.entity)}`}
                      className="font-medium text-white/85 hover:text-primary hover:underline"
                      onClick={(event) => event.stopPropagation()}
                    >
                      {item.entity}
                    </Link>
                  </p>

                  <div className="flex items-center justify-between text-xs">
                    <span className="truncate text-white/60">
                      Owner: {item.owner ?? "Unassigned"}
                    </span>
                    <span
                      className={cn(
                        "font-mono font-semibold",
                        riskToneClass(item.risk_score),
                      )}
                    >
                      Risk {Math.round(item.risk_score)}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="mt-3 flex items-center justify-end gap-2">
        <Button
          variant="glass"
          size="sm"
          disabled={(data?.page ?? 1) <= 1 || loading}
          onClick={() =>
            onFiltersChange({ page: Math.max(1, filters.page - 1) })
          }
        >
          Previous
        </Button>
        <Button
          variant="glass"
          size="sm"
          disabled={
            !data || data.page * data.page_size >= data.total || loading
          }
          onClick={() => onFiltersChange({ page: filters.page + 1 })}
        >
          Next
        </Button>
      </div>
    </section>
  );
}

export default UnifiedWorkQueue;
