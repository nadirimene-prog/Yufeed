"use client";

import { ChevronDown, ListFilter, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ExportButton } from "@/components/ui/export-button";
import { cn } from "@/lib/utils";
import DataFreshnessBadge from "@/features/dashboard/components/DataFreshnessBadge";
import {
  DashboardFreshnessMeta,
  DashboardQueueFilter,
  DashboardSavedView,
  DashboardSeverityFilter,
  DashboardSlaFilter,
  DashboardWorkQueueItem,
  DashboardWorkQueueParams,
} from "@/features/dashboard/types";

export type QueueSort = "default" | "severity" | "age" | "risk";
export type QueueDensity = "comfortable" | "compact";

interface QueueFilterBarProps {
  filters: DashboardWorkQueueParams;
  searchDraft: string;
  jurisdictionDraft: string;
  density: QueueDensity;
  sortBy: QueueSort;
  advancedFiltersOpen: boolean;
  loading?: boolean;
  freshness?: DashboardFreshnessMeta | null;
  nowMs?: number | null;
  canExport?: boolean;
  total: number;
  from: number;
  to: number;
  sortedItems: DashboardWorkQueueItem[];
  onSearchDraftChange: (value: string) => void;
  onJurisdictionDraftChange: (value: string) => void;
  onCommitSearch: () => void;
  onCommitJurisdiction: () => void;
  onFiltersChange: (patch: Partial<DashboardWorkQueueParams>) => void;
  onDensityChange: (value: QueueDensity) => void;
  onToggleAdvancedFilters: () => void;
  onCycleSort: () => void;
  onRefresh: () => void;
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

export function QueueFilterBar({
  filters,
  searchDraft,
  jurisdictionDraft,
  density,
  sortBy,
  advancedFiltersOpen,
  loading = false,
  freshness = null,
  nowMs = null,
  canExport = false,
  total,
  from,
  to,
  sortedItems,
  onSearchDraftChange,
  onJurisdictionDraftChange,
  onCommitSearch,
  onCommitJurisdiction,
  onFiltersChange,
  onDensityChange,
  onToggleAdvancedFilters,
  onCycleSort,
  onRefresh,
}: QueueFilterBarProps) {
  return (
    <>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-sm font-semibold text-foreground">
              Unified Work Queue
            </h2>
            <DataFreshnessBadge
              freshness={freshness}
              label="Queue"
              compact
              nowMs={nowMs}
            />
          </div>
          <p className="text-xs text-muted-foreground">
            Prioritized triage queue grouped for analyst action.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          <div
            className="inline-flex items-center gap-1 rounded-lg border border-border bg-slate-50 p-1"
            role="group"
            aria-label="Queue density"
          >
            <button
              type="button"
              onClick={() => onDensityChange("comfortable")}
              className={cn(
                "rounded-md px-2 py-1 text-[11px] font-medium transition",
                density === "comfortable"
                  ? "bg-white text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              )}
              aria-pressed={density === "comfortable"}
            >
              Comfortable
            </button>
            <button
              type="button"
              onClick={() => onDensityChange("compact")}
              className={cn(
                "rounded-md px-2 py-1 text-[11px] font-medium transition",
                density === "compact"
                  ? "bg-white text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              )}
              aria-pressed={density === "compact"}
            >
              Compact
            </button>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={onToggleAdvancedFilters}
            aria-expanded={advancedFiltersOpen}
            aria-controls="queue-advanced-filters"
          >
            Advanced filters
            <ChevronDown
              className={cn(
                "h-3.5 w-3.5 transition-transform",
                advancedFiltersOpen && "rotate-180",
              )}
            />
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            disabled={loading}
          >
            <RefreshCw
              className={cn(
                "mr-1.5 h-3.5 w-3.5 text-muted-foreground",
                loading && "animate-spin",
              )}
            />
            Refresh
          </Button>
        </div>
      </div>

      <div className="mb-2 grid grid-cols-1 gap-2 xl:grid-cols-[minmax(0,1fr)_140px_160px_auto] xl:items-center">
        <input
          id="dashboard-queue-search-input"
          data-dashboard-queue-search-input
          value={searchDraft}
          onChange={(event) => onSearchDraftChange(event.target.value)}
          onBlur={onCommitSearch}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              onCommitSearch();
            }
          }}
          placeholder="Entity / reference / typology"
          className="h-9 rounded-lg border border-border bg-white px-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
          aria-label="Queue search"
        />

        <select
          value={filters.queue}
          onChange={(event) =>
            onFiltersChange({
              queue: event.target.value as DashboardQueueFilter,
              page: 1,
            })
          }
          className="h-9 rounded-lg border border-border bg-slate-50 px-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
          aria-label="Queue selector"
        >
          {QUEUE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
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
          className="h-9 rounded-lg border border-border bg-slate-50 px-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
          aria-label="Saved queue view"
        >
          {SAVED_VIEW_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        <div
          className="inline-flex h-9 items-center gap-1 rounded-lg border border-border bg-slate-50 px-2 text-[11px] text-muted-foreground"
          aria-live="polite"
        >
          <ListFilter className="h-3.5 w-3.5" />
          <span>
            Rows {total ? `${from}-${to}` : "0"} / {total}
          </span>
        </div>
      </div>

      {advancedFiltersOpen ? (
        <div id="queue-advanced-filters" className="mb-2">
          <div className="rounded-xl border border-border bg-slate-50 p-2">
            <div className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-3">
              <select
                value={filters.severity}
                onChange={(event) =>
                  onFiltersChange({
                    severity: event.target.value as DashboardSeverityFilter,
                    page: 1,
                  })
                }
                className="h-9 rounded-lg border border-border bg-white px-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
                aria-label="Severity filter"
              >
                {SEVERITY_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
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
                className="h-9 rounded-lg border border-border bg-white px-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
                aria-label="SLA filter"
              >
                {SLA_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>

              <input
                value={jurisdictionDraft}
                onChange={(event) =>
                  onJurisdictionDraftChange(event.target.value.toUpperCase())
                }
                onBlur={onCommitJurisdiction}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    onCommitJurisdiction();
                  }
                }}
                placeholder="Jurisdiction (e.g. US, FR, GB)"
                className="h-9 rounded-lg border border-border bg-white px-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
                aria-label="Jurisdiction filter"
              />
            </div>

            <div className="mt-2 flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={onCycleSort}
                className="inline-flex h-9 items-center justify-center gap-1 rounded-lg border border-border bg-white px-2 text-[11px] uppercase tracking-wide text-muted-foreground transition-colors hover:bg-slate-100"
              >
                Sort
                <ChevronDown className="h-3.5 w-3.5" />
                <span className="text-foreground">{sortBy}</span>
              </button>

              {canExport ? (
                <ExportButton
                  data={sortedItems as unknown as Record<string, unknown>[]}
                  filename="dashboard-work-queue"
                  pdfTitle="Dashboard Work Queue"
                  variant="outline"
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
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}

export default QueueFilterBar;
