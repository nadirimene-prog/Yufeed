"use client";

import { useMemo, useState } from "react";
import { Filter, ListFilter, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
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
  rankQueueItems,
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
    { value: "all", label: "Team queue" },
    { value: "my_queue", label: "My queue" },
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
  const [selectedRows, setSelectedRows] = useState<Record<string, boolean>>({});

  const items = useMemo(() => rankQueueItems(data?.items ?? []), [data?.items]);
  const selectedItems = items.filter((item) => selectedRows[item.item_id]);

  const canBulkAction = selectedItems.length > 0 && Boolean(onBulkAction);
  const page = data?.page ?? filters.page;
  const pageSize = data?.page_size ?? filters.pageSize;
  const total = data?.total ?? 0;
  const from = total > 0 ? (page - 1) * pageSize + 1 : 0;
  const to = total > 0 ? Math.min(page * pageSize, total) : 0;

  return (
    <section className="glass-surface rounded-2xl border border-white/10 p-3 sm:p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-white">
            Unified Work Queue
          </h2>
          <p className="text-xs text-white/60">
            Triage ordered by SLA, severity, risk, and age.
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

      <div className="mb-3 grid grid-cols-1 gap-2 lg:grid-cols-2">
        <div className="grid grid-cols-2 gap-2">
          <label className="sr-only" htmlFor="queue-selector">
            Queue selector
          </label>
          <select
            id="queue-selector"
            value={filters.queue}
            onChange={(event) =>
              onFiltersChange({
                queue: event.target.value as DashboardQueueFilter,
                page: 1,
              })
            }
            className="h-9 rounded-lg border border-white/10 bg-white/5 px-2 text-xs text-white"
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
          <input
            value={filters.search}
            onChange={(event) =>
              onFiltersChange({ search: event.target.value, page: 1 })
            }
            placeholder="Entity / ref / typology"
            className="h-9 rounded-lg border border-white/10 bg-white/5 px-2 text-xs text-white placeholder:text-white/40"
            aria-label="Queue search"
          />
        </div>
      </div>

      <div className="mb-2 flex items-center justify-between">
        <div className="inline-flex items-center gap-1 rounded-lg border border-white/10 bg-white/5 p-1 text-[11px] text-white/70">
          <ListFilter className="h-3.5 w-3.5" />
          <span>
            Rows {data?.total ? `${from}-${to}` : "0"} / {data?.total ?? 0}
          </span>
        </div>

        <div className="flex items-center gap-1">
          <Button
            variant="glass"
            size="sm"
            disabled={!canBulkAction}
            onClick={() => onBulkAction?.(selectedItems, "assign")}
          >
            Bulk assign
          </Button>
          <Button
            variant="glass"
            size="sm"
            disabled={!canBulkAction}
            onClick={() => onBulkAction?.(selectedItems, "escalate")}
          >
            Escalate
          </Button>
          <Button
            variant="glass"
            size="sm"
            disabled={!canBulkAction}
            onClick={() => onBulkAction?.(selectedItems, "mark_in_progress")}
          >
            In Progress
          </Button>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-white/10">
        <div className="max-h-[50vh] overflow-auto">
          <table className="w-full min-w-[960px] border-separate border-spacing-0 text-xs text-white/85">
            <thead className="sticky top-0 z-10 bg-[#0d1324] text-white/60">
              <tr>
                <th className="px-3 py-2 text-left">
                  <Filter className="h-3.5 w-3.5" />
                </th>
                <th className="px-3 py-2 text-left font-semibold">Type</th>
                <th className="px-3 py-2 text-left font-semibold">Severity</th>
                <th className="px-3 py-2 text-left font-semibold">Entity</th>
                <th className="px-3 py-2 text-left font-semibold">Typology</th>
                <th className="px-3 py-2 text-left font-semibold">
                  Jurisdiction
                </th>
                <th className="px-3 py-2 text-left font-semibold">Age</th>
                <th className="px-3 py-2 text-left font-semibold">SLA</th>
                <th className="px-3 py-2 text-left font-semibold">Owner</th>
                <th className="px-3 py-2 text-left font-semibold">
                  Next Action
                </th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td
                    colSpan={10}
                    className="px-3 py-6 text-center text-white/50"
                  >
                    Loading queue...
                  </td>
                </tr>
              ) : error ? (
                <tr>
                  <td
                    colSpan={10}
                    className="px-3 py-6 text-center text-risk-critical"
                  >
                    {error}
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td
                    colSpan={10}
                    className="px-3 py-6 text-center text-white/50"
                  >
                    No queue items for the current filters.
                  </td>
                </tr>
              ) : (
                items.map((item) => (
                  <tr
                    key={item.item_id}
                    onClick={() => onSelectItem(item)}
                    className={cn(
                      "cursor-pointer border-t border-white/5 transition-colors hover:bg-white/5",
                      item.item_id === selectedItemId && "bg-aurora-500/10",
                    )}
                  >
                    <td
                      className="px-3 py-2"
                      onClick={(event) => event.stopPropagation()}
                    >
                      <input
                        type="checkbox"
                        checked={Boolean(selectedRows[item.item_id])}
                        onChange={(event) =>
                          setSelectedRows((current) => ({
                            ...current,
                            [item.item_id]: event.target.checked,
                          }))
                        }
                        aria-label={`Select ${item.ref_id}`}
                      />
                    </td>
                    <td className="px-3 py-2">{item.type_label}</td>
                    <td className="px-3 py-2">
                      <span
                        className={cn(
                          "rounded-full px-2 py-1 text-[10px] uppercase",
                          severityBadgeClass(item.severity),
                        )}
                      >
                        {item.severity}
                      </span>
                    </td>
                    <td className="max-w-[140px] truncate px-3 py-2">
                      {item.entity}
                    </td>
                    <td className="max-w-[160px] truncate px-3 py-2">
                      {item.typology}
                    </td>
                    <td className="px-3 py-2">{item.jurisdiction}</td>
                    <td className="px-3 py-2">
                      {formatAgeMinutes(item.age_minutes)}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={cn(
                          "rounded-full px-2 py-1 text-[10px] uppercase",
                          slaBadgeClass(item.sla_status),
                        )}
                      >
                        {item.sla_status}
                      </span>
                    </td>
                    <td className="max-w-[110px] truncate px-3 py-2">
                      {item.owner ?? "Unassigned"}
                    </td>
                    <td className="max-w-[180px] truncate px-3 py-2">
                      {item.next_action}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
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
