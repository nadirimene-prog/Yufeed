"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { FileWarning } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { useWorkspaceUsers } from "@/hooks/queries/useSpecializedData";
import {
  DashboardFreshnessMeta,
  DashboardWorkQueueItem,
  DashboardWorkQueueParams,
  WorkItemActionType,
} from "@/features/dashboard/types";
import {
  formatAgeMinutes,
  severityBadgeClass,
  slaBadgeClass,
} from "@/features/dashboard/utils";
import QueueBulkActionBar from "@/features/dashboard/components/QueueBulkActionBar";
import QueueFilterBar, {
  QueueDensity,
  QueueSort,
} from "@/features/dashboard/components/QueueFilterBar";
import { isDashboardShortcutTargetBlocked } from "@/features/dashboard/hooks/useDashboardShortcuts";
import trackDashboardEvent from "@/features/dashboard/telemetry";

interface UnifiedWorkQueueProps {
  data: {
    items: DashboardWorkQueueItem[];
    page: number;
    page_size: number;
    total: number;
    freshness?: DashboardFreshnessMeta | null;
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

type PendingBulkAction = {
  action: Exclude<WorkItemActionType, "create_case" | "close">;
  label: string;
} | null;

const QUEUE_ADVANCED_PREF_KEY = "dashboard:queue-advanced-open";
const QUEUE_DENSITY_PREF_KEY = "dashboard:queue-density";

function readBooleanPref(key: string, fallback: boolean) {
  if (typeof window === "undefined") return fallback;
  const raw = window.localStorage.getItem(key);
  if (raw === "1") return true;
  if (raw === "0") return false;
  return fallback;
}

function readDensityPref(fallback: QueueDensity): QueueDensity {
  if (typeof window === "undefined") return fallback;
  const raw = window.localStorage.getItem(QUEUE_DENSITY_PREF_KEY);
  return raw === "compact" || raw === "comfortable" ? raw : fallback;
}

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
  const [advancedFiltersOpen, setAdvancedFiltersOpen] = useState(() =>
    readBooleanPref(QUEUE_ADVANCED_PREF_KEY, false),
  );
  const [density, setDensity] = useState<QueueDensity>(() =>
    readDensityPref("comfortable"),
  );
  const [searchDraft, setSearchDraft] = useState(() => filters.search);
  const [jurisdictionDraft, setJurisdictionDraft] = useState(
    () => filters.jurisdiction,
  );
  const [pendingBulkAction, setPendingBulkAction] =
    useState<PendingBulkAction>(null);
  const rowRefs = useRef<Array<HTMLDivElement | null>>([]);
  const searchDebounceRef = useRef<number | null>(null);
  const jurisdictionDebounceRef = useRef<number | null>(null);
  const workspaceUsersQuery = useWorkspaceUsers();

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(
      QUEUE_ADVANCED_PREF_KEY,
      advancedFiltersOpen ? "1" : "0",
    );
  }, [advancedFiltersOpen]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(QUEUE_DENSITY_PREF_KEY, density);
  }, [density]);

  useEffect(() => {
    queueMicrotask(() => {
      setSearchDraft(filters.search);
    });
  }, [filters.search]);

  useEffect(() => {
    queueMicrotask(() => {
      setJurisdictionDraft(filters.jurisdiction);
    });
  }, [filters.jurisdiction]);

  useEffect(() => {
    if (searchDraft === filters.search) return;
    if (searchDebounceRef.current) {
      window.clearTimeout(searchDebounceRef.current);
    }
    searchDebounceRef.current = window.setTimeout(() => {
      onFiltersChange({ search: searchDraft, page: 1 });
      searchDebounceRef.current = null;
    }, 300);
    return () => {
      if (searchDebounceRef.current) {
        window.clearTimeout(searchDebounceRef.current);
        searchDebounceRef.current = null;
      }
    };
  }, [filters.search, onFiltersChange, searchDraft]);

  useEffect(() => {
    if (jurisdictionDraft === filters.jurisdiction) return;
    if (jurisdictionDebounceRef.current) {
      window.clearTimeout(jurisdictionDebounceRef.current);
    }
    jurisdictionDebounceRef.current = window.setTimeout(() => {
      onFiltersChange({ jurisdiction: jurisdictionDraft, page: 1 });
      jurisdictionDebounceRef.current = null;
    }, 300);
    return () => {
      if (jurisdictionDebounceRef.current) {
        window.clearTimeout(jurisdictionDebounceRef.current);
        jurisdictionDebounceRef.current = null;
      }
    };
  }, [filters.jurisdiction, jurisdictionDraft, onFiltersChange]);

  const items = useMemo(() => data?.items ?? [], [data?.items]);

  useEffect(() => {
    queueMicrotask(() => {
      setSelectedRows((current) => {
        if (current.size === 0) return current;
        const visibleIds = new Set(items.map((item) => item.item_id));
        let changed = false;
        const next = new Set<string>();
        for (const id of current) {
          if (visibleIds.has(id)) {
            next.add(id);
          } else {
            changed = true;
          }
        }
        return changed ? next : current;
      });
    });
  }, [items]);

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

  const toggleSelected = (itemId: string, checked: boolean) => {
    setSelectedRows((current) => {
      const next = new Set(current);
      if (checked) next.add(itemId);
      else next.delete(itemId);
      return next;
    });
  };

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.metaKey || event.ctrlKey || event.altKey || event.shiftKey) {
        return;
      }
      if (isDashboardShortcutTargetBlocked(event.target)) {
        return;
      }
      if (document.querySelector("[role='dialog']")) {
        return;
      }
      if (sortedItems.length === 0) {
        return;
      }

      const lowerKey = event.key.toLowerCase();
      if (lowerKey !== "j" && lowerKey !== "k" && lowerKey !== "x") {
        return;
      }

      const currentIndex = selectedItemId
        ? sortedItems.findIndex((item) => item.item_id === selectedItemId)
        : -1;

      if (lowerKey === "j" || lowerKey === "k") {
        event.preventDefault();
        trackDashboardEvent("dashboard_shortcut_used", { shortcut: lowerKey });
        const nextIndex =
          lowerKey === "j"
            ? Math.min(
                sortedItems.length - 1,
                currentIndex >= 0 ? currentIndex + 1 : 0,
              )
            : Math.max(0, currentIndex >= 0 ? currentIndex - 1 : 0);
        const nextItem = sortedItems[nextIndex];
        if (!nextItem) return;
        onSelectItem(nextItem);
        window.requestAnimationFrame(() => {
          rowRefs.current[nextIndex]?.focus();
        });
        return;
      }

      const targetItem =
        (currentIndex >= 0 ? sortedItems[currentIndex] : sortedItems[0]) ??
        null;
      if (!targetItem) return;

      event.preventDefault();
      trackDashboardEvent("dashboard_shortcut_used", { shortcut: "x" });
      const isCurrentlySelected = selectedRows.has(targetItem.item_id);
      toggleSelected(targetItem.item_id, !isCurrentlySelected);
      window.requestAnimationFrame(() => {
        const focusIndex = sortedItems.findIndex(
          (item) => item.item_id === targetItem.item_id,
        );
        if (focusIndex >= 0) {
          rowRefs.current[focusIndex]?.focus();
        }
      });
    };

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [onSelectItem, selectedItemId, selectedRows, sortedItems]);

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

  const runBulkAction = (
    action: Exclude<WorkItemActionType, "create_case" | "close">,
    label: string,
  ) => {
    if (!onBulkAction || selectedItems.length === 0) return;
    setPendingBulkAction({ action, label });
  };

  const confirmBulkAction = () => {
    if (!onBulkAction || selectedItems.length === 0 || !pendingBulkAction) {
      setPendingBulkAction(null);
      return;
    }
    onBulkAction(
      selectedItems,
      pendingBulkAction.action,
      bulkAssignee || undefined,
    );
    setPendingBulkAction(null);
  };

  const commitSearch = () => {
    if (searchDebounceRef.current) {
      window.clearTimeout(searchDebounceRef.current);
      searchDebounceRef.current = null;
    }
    if (searchDraft === filters.search) return;
    onFiltersChange({ search: searchDraft, page: 1 });
  };

  const commitJurisdiction = () => {
    if (jurisdictionDebounceRef.current) {
      window.clearTimeout(jurisdictionDebounceRef.current);
      jurisdictionDebounceRef.current = null;
    }
    if (jurisdictionDraft === filters.jurisdiction) return;
    onFiltersChange({ jurisdiction: jurisdictionDraft, page: 1 });
  };

  const compactRows = density === "compact";

  return (
    <section className="flex h-full min-h-0 flex-col rounded-2xl border border-border bg-white p-3 shadow-sm sm:p-4">
      <QueueFilterBar
        filters={filters}
        searchDraft={searchDraft}
        jurisdictionDraft={jurisdictionDraft}
        density={density}
        sortBy={sortBy}
        advancedFiltersOpen={advancedFiltersOpen}
        loading={loading}
        freshness={data?.freshness ?? null}
        total={total}
        from={from}
        to={to}
        sortedItems={sortedItems}
        onSearchDraftChange={setSearchDraft}
        onJurisdictionDraftChange={setJurisdictionDraft}
        onCommitSearch={commitSearch}
        onCommitJurisdiction={commitJurisdiction}
        onFiltersChange={onFiltersChange}
        onDensityChange={setDensity}
        onToggleAdvancedFilters={() =>
          setAdvancedFiltersOpen((current) => !current)
        }
        onCycleSort={() =>
          setSortBy((current) => {
            if (current === "default") return "severity";
            if (current === "severity") return "age";
            if (current === "age") return "risk";
            return "default";
          })
        }
        onRefresh={onRefresh}
      />

      <QueueBulkActionBar
        selectedCount={selectedItems.length}
        allSelectedOnPage={allSelectedOnPage}
        bulkAssignee={bulkAssignee}
        users={workspaceUsersQuery.data ?? []}
        canBulkAction={canBulkAction}
        onToggleSelectAllOnPage={toggleSelectAllOnPage}
        onBulkAssigneeChange={setBulkAssignee}
        onRunBulkAction={runBulkAction}
        onClear={() => setSelectedRows(new Set())}
      />

      <div
        className="min-h-0 flex-1 overflow-auto"
        role="feed"
        aria-label="Unified work queue items"
      >
        {loading ? (
          <div className="rounded-xl border border-border bg-slate-50 p-6 text-center text-sm text-muted-foreground">
            Loading queue...
          </div>
        ) : error ? (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-600">
            {error}
          </div>
        ) : sortedItems.length === 0 ? (
          <div className="rounded-xl border border-border bg-slate-50 p-6 text-center text-sm text-muted-foreground">
            No queue items for current filters.
          </div>
        ) : (
          <div className={cn("space-y-2", compactRows && "space-y-1")}>
            {sortedItems.map((item, index) => {
              const selected = selectedRows.has(item.item_id);
              const rowSelected = item.item_id === selectedItemId;

              return (
                <div
                  key={item.item_id}
                  ref={(element) => {
                    rowRefs.current[index] = element;
                  }}
                  data-dashboard-queue-row
                  data-queue-item-id={item.item_id}
                  tabIndex={0}
                  role="button"
                  onClick={() => onSelectItem(item)}
                  onKeyDown={(event) => {
                    if (event.target !== event.currentTarget) {
                      return;
                    }
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
                    "w-full rounded-xl border text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20",
                    compactRows ? "px-2.5 py-2" : "p-3",
                    rowSelected
                      ? "border-primary/50 bg-primary/5 shadow-sm"
                      : "border-border bg-white hover:border-border/60 hover:shadow-sm",
                  )}
                  aria-pressed={rowSelected}
                  aria-label={`Queue item ${item.ref_id}`}
                >
                  <div
                    className={cn(
                      "flex items-start justify-between gap-2",
                      compactRows ? "mb-1" : "mb-1.5",
                    )}
                  >
                    <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                      <input
                        type="checkbox"
                        checked={selected}
                        data-dashboard-queue-checkbox
                        data-queue-item-id={item.item_id}
                        aria-label={`Select ${item.ref_id}`}
                        onClick={(event) => event.stopPropagation()}
                        onKeyDown={(event) => event.stopPropagation()}
                        onChange={(event) =>
                          toggleSelected(item.item_id, event.target.checked)
                        }
                        className="rounded border-border focus:ring-primary text-primary"
                      />
                      <span className="font-mono text-xs font-semibold text-foreground">
                        {item.ref_id}
                      </span>
                      {item.sar_required ? (
                        <span className="inline-flex items-center gap-1 rounded-full border border-red-100 bg-red-50 px-2 py-0.5 text-[10px] uppercase text-red-600">
                          <FileWarning className="h-3 w-3" />
                          SAR Required
                        </span>
                      ) : null}
                      <span
                        className={cn(
                          "rounded-full border border-border/50 px-2 py-0.5 text-[10px] uppercase tracking-wide",
                          severityBadgeClass(item.severity),
                          compactRows && "px-1.5",
                        )}
                      >
                        {item.severity}
                      </span>
                      <span
                        className={cn(
                          "rounded-full border border-border/50 px-2 py-0.5 text-[10px] uppercase tracking-wide",
                          slaBadgeClass(item.sla_status),
                          compactRows && "px-1.5 opacity-80",
                        )}
                      >
                        SLA {item.sla_status}
                      </span>
                    </div>

                    <span className="shrink-0 text-[11px] text-muted-foreground">
                      {formatAgeMinutes(item.age_minutes)} ago
                    </span>
                  </div>

                  <div
                    className={cn(
                      "flex flex-wrap items-center gap-x-2 gap-y-1 text-xs",
                      compactRows && "text-[11px]",
                      compactRows ? "mb-1" : "mb-1.5",
                    )}
                  >
                    <span
                      className={cn(
                        compactRows
                          ? "text-muted-foreground"
                          : "rounded-full border border-border/50 bg-slate-100 px-2 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground",
                      )}
                    >
                      {item.type_label}
                    </span>
                    <span
                      className={cn(
                        compactRows
                          ? "text-muted-foreground"
                          : "rounded-full border border-border/50 bg-slate-100 px-2 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground",
                      )}
                    >
                      {item.jurisdiction}
                    </span>
                    <Link
                      href={`/entities/user/${encodeURIComponent(item.entity)}`}
                      className="min-w-0 truncate font-medium text-foreground hover:text-primary hover:underline"
                      onClick={(event) => event.stopPropagation()}
                    >
                      {item.entity}
                    </Link>
                    <span className="text-muted-foreground">
                      Owner: {item.owner ?? "Unassigned"}
                    </span>
                  </div>

                  <div className="flex items-center justify-between gap-2 text-xs">
                    <p className="truncate text-muted-foreground">
                      {item.typology}
                    </p>
                    <span
                      className={cn(
                        "shrink-0 font-mono font-semibold",
                        compactRows ? "text-[11px]" : "text-xs",
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
          variant="outline"
          size="sm"
          disabled={(data?.page ?? 1) <= 1 || loading}
          onClick={() =>
            onFiltersChange({ page: Math.max(1, filters.page - 1) })
          }
        >
          Previous
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={
            !data || data.page * data.page_size >= data.total || loading
          }
          onClick={() => onFiltersChange({ page: filters.page + 1 })}
        >
          Next
        </Button>
      </div>

      <Dialog
        open={Boolean(pendingBulkAction)}
        onOpenChange={(open) => {
          if (!open) setPendingBulkAction(null);
        }}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Confirm Bulk Action</DialogTitle>
            <DialogDescription>
              {pendingBulkAction
                ? `Apply '${pendingBulkAction.label}' to ${selectedItems.length} selected item(s)?`
                : "Review the bulk action before continuing."}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              type="button"
              onClick={() => setPendingBulkAction(null)}
            >
              Cancel
            </Button>
            <Button type="button" onClick={confirmBulkAction}>
              Confirm
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}

export default UnifiedWorkQueue;
