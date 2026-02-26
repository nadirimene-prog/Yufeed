"use client";

import { startTransition, useEffect, useId, useMemo, useState } from "react";
import axios from "axios";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { AlertTriangle, PanelRight, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StatusIndicator } from "@/components/ui/status-indicator";
import { Card, CardContent } from "@/components/ui/card";
import { getAuthToken, getAuthUserProfile } from "@/lib/auth";
import { cn } from "@/lib/utils";
import {
  DashboardQueueFilter,
  DashboardSavedView,
  DashboardSeverityFilter,
  DashboardSlaFilter,
  DashboardTimeRange,
  DashboardView,
  DashboardWorkQueueItem,
  DashboardWorkQueueParams,
  WorkspaceMessage,
} from "@/features/dashboard/types";
import { useDashboardOverview } from "@/features/dashboard/useDashboardOverview";
import { useWorkQueue } from "@/features/dashboard/useWorkQueue";
import { useWorkItemDetail } from "@/features/dashboard/useWorkItemDetail";
import { useWorkItemActions } from "@/features/dashboard/useWorkItemActions";
import {
  formatRangeLabel,
  resolveDashboardTimeRange,
  resolveDashboardView,
} from "@/features/dashboard/utils";
import CriticalDecisionBar, {
  CriticalTileFilter,
} from "@/features/dashboard/components/CriticalDecisionBar";
import UnifiedWorkQueue from "@/features/dashboard/components/UnifiedWorkQueue";
import InvestigationWorkspace from "@/features/dashboard/components/InvestigationWorkspace";
import GovernancePanel from "@/features/dashboard/components/GovernancePanel";
import InsightsPanel from "@/features/dashboard/components/InsightsPanel";
import TrendStrip from "@/features/dashboard/components/TrendStrip";
import DataFreshnessBadge from "@/features/dashboard/components/DataFreshnessBadge";
import CommandPalette, {
  DashboardCommandAction,
} from "@/features/dashboard/components/CommandPalette";
import ShortcutHelpDialog from "@/features/dashboard/components/ShortcutHelpDialog";
import { useDashboardShortcuts } from "@/features/dashboard/hooks/useDashboardShortcuts";
import { useDashboardTelemetryBridge } from "@/features/dashboard/hooks/useDashboardTelemetryBridge";
import trackDashboardEvent from "@/features/dashboard/telemetry";

const VIEW_OPTIONS: Array<{ key: DashboardView; label: string }> = [
  { key: "operations", label: "Operations" },
  { key: "compliance", label: "Compliance" },
  { key: "monitoring", label: "Monitoring" },
];

const RANGE_OPTIONS: DashboardTimeRange[] = ["24h", "7d", "30d"];
const DASHBOARD_V3_ENABLED =
  process.env.NEXT_PUBLIC_DASHBOARD_AMLCO_V3 !== "false";
const INSIGHTS_PREF_KEY = "dashboard:insights-open";

const QUEUE_FILTER_OPTIONS: DashboardQueueFilter[] = [
  "all",
  "alerts",
  "cases",
  "approvals",
  "reg_tasks",
];
const SEVERITY_FILTER_OPTIONS: DashboardSeverityFilter[] = [
  "all",
  "low",
  "medium",
  "high",
  "critical",
];
const SLA_FILTER_OPTIONS: DashboardSlaFilter[] = [
  "all",
  "breached",
  "warning",
  "ok",
  "none",
];
const SAVED_VIEW_OPTIONS: DashboardSavedView[] = [
  "all",
  "my_queue",
  "team_queue",
  "escalations",
];

function defaultQueueFilters(): DashboardWorkQueueParams {
  return {
    page: 1,
    pageSize: 50,
    queue: "all",
    severity: "all",
    jurisdiction: "",
    sla: "all",
    search: "",
    savedView: "all",
  };
}

function parseErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (
      detail &&
      typeof detail === "object" &&
      typeof detail.message === "string"
    ) {
      return detail.message;
    }
    if (typeof error.message === "string" && error.message.trim().length > 0) {
      return error.message;
    }
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

function coerceNumber(value: string | null, fallback: number) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) return fallback;
  return Math.floor(parsed);
}

function coerceEnum<T extends string>(
  value: string | null,
  options: readonly T[],
  fallback: T,
): T {
  if (!value) return fallback;
  return options.includes(value as T) ? (value as T) : fallback;
}

function parseFilters(params: URLSearchParams): DashboardWorkQueueParams {
  const defaults = defaultQueueFilters();
  return {
    page: coerceNumber(params.get("page"), defaults.page),
    pageSize: coerceNumber(params.get("pageSize"), defaults.pageSize),
    queue: coerceEnum(
      params.get("queue"),
      QUEUE_FILTER_OPTIONS,
      defaults.queue,
    ),
    severity: coerceEnum(
      params.get("severity"),
      SEVERITY_FILTER_OPTIONS,
      defaults.severity,
    ),
    jurisdiction: params.get("jurisdiction") ?? defaults.jurisdiction,
    sla: coerceEnum(params.get("sla"), SLA_FILTER_OPTIONS, defaults.sla),
    search: params.get("search") ?? defaults.search,
    savedView: coerceEnum(
      params.get("savedView"),
      SAVED_VIEW_OPTIONS,
      defaults.savedView,
    ),
  };
}

function setParam(
  params: URLSearchParams,
  key: string,
  value: string | number,
  defaultValue: string | number,
) {
  if (`${value}` === `${defaultValue}` || `${value}`.trim().length === 0) {
    params.delete(key);
    return;
  }
  params.set(key, String(value));
}

function isPaginationOnlyPatch(patch: Partial<DashboardWorkQueueParams>) {
  const keys = Object.keys(patch);
  if (keys.length === 0) return false;
  return keys.every((key) => key === "page" || key === "pageSize");
}

export function DashboardHub() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const profile = getAuthUserProfile();

  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [workspaceMessage, setWorkspaceMessage] =
    useState<WorkspaceMessage | null>(null);
  const [mobileWorkspaceOpen, setMobileWorkspaceOpen] = useState(false);
  const [mobilePanel, setMobilePanel] = useState<"queue" | "governance">(
    "queue",
  );
  const [shortcutHelpOpen, setShortcutHelpOpen] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [insightsOpen, setInsightsOpen] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return window.localStorage.getItem(INSIGHTS_PREF_KEY) === "1";
  });
  const dashboardTabsId = useId();

  const view = resolveDashboardView(searchParams.get("view"));
  const range = resolveDashboardTimeRange(searchParams.get("range"));
  const filters = useMemo(
    () => parseFilters(new URLSearchParams(searchParams.toString())),
    [searchParams],
  );

  const hasToken = Boolean(getAuthToken());
  const dashboardEnabled = hasToken && DASHBOARD_V3_ENABLED;

  useDashboardTelemetryBridge({ enabled: dashboardEnabled });

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(INSIGHTS_PREF_KEY, insightsOpen ? "1" : "0");
  }, [insightsOpen]);

  const overviewQuery = useDashboardOverview(view, range, {
    enabled: dashboardEnabled,
  });
  const queueQuery = useWorkQueue(filters, {
    enabled: dashboardEnabled,
  });

  const selectedItem = useMemo(() => {
    const items = queueQuery.data?.items ?? [];
    if (items.length === 0) return null;
    if (!selectedItemId) return items[0];
    return items.find((item) => item.item_id === selectedItemId) ?? items[0];
  }, [queueQuery.data?.items, selectedItemId]);

  const detailQuery = useWorkItemDetail(
    selectedItem?.kind ?? null,
    selectedItem?.record_id ?? null,
    {
      enabled: dashboardEnabled && Boolean(selectedItem),
    },
  );

  const { performAction, reviewAction, bulkAction, saveDraft, snoozeAlert } =
    useWorkItemActions(
      selectedItem?.kind ?? null,
      selectedItem?.record_id ?? null,
    );

  const activeViewPanelId = `dashboard-view-panel-${dashboardTabsId}-${view}`;
  const overviewFreshness = overviewQuery.data?.freshness ?? null;
  const overviewIsStale = (() => {
    if (!overviewFreshness?.generated_at) return false;
    const generatedAt = new Date(overviewFreshness.generated_at);
    if (Number.isNaN(generatedAt.valueOf())) return false;
    const staleAfter = Math.max(1, overviewFreshness.stale_after_seconds ?? 120);
    return Date.now() - generatedAt.getTime() > staleAfter * 1000;
  })();

  const updateSearch = (patch: Partial<DashboardWorkQueueParams>) => {
    const defaults = defaultQueueFilters();
    const next = { ...filters, ...patch };
    const params = new URLSearchParams(searchParams.toString());

    params.set("view", view);
    params.set("range", range);

    setParam(params, "page", next.page, defaults.page);
    setParam(params, "pageSize", next.pageSize, defaults.pageSize);
    setParam(params, "queue", next.queue, defaults.queue);
    setParam(params, "severity", next.severity, defaults.severity);
    setParam(params, "sla", next.sla, defaults.sla);
    setParam(params, "search", next.search, defaults.search);
    setParam(params, "jurisdiction", next.jurisdiction, defaults.jurisdiction);
    setParam(params, "savedView", next.savedView, defaults.savedView);

    startTransition(() => {
      router.replace(`${pathname}?${params.toString()}`);
    });
  };

  const updateViewRange = (
    nextView: DashboardView = view,
    nextRange: DashboardTimeRange = range,
  ) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("view", nextView);
    params.set("range", nextRange);
    startTransition(() => {
      router.replace(`${pathname}?${params.toString()}`);
    });
  };

  const applyQueueFilterPatch = (
    patch: Partial<DashboardWorkQueueParams>,
    source: "queue_controls" | "critical_tile" | "pagination" = "queue_controls",
  ) => {
    trackDashboardEvent("dashboard_filter_apply", {
      source,
      keys: Object.keys(patch).sort(),
    });
    updateSearch(patch);
  };

  const applyCriticalFilter = (patch: CriticalTileFilter) => {
    applyQueueFilterPatch(
      {
      page: 1,
      queue: (patch.queue ?? filters.queue) as DashboardQueueFilter,
      severity: (patch.severity ?? filters.severity) as DashboardSeverityFilter,
      sla: (patch.sla ?? filters.sla) as DashboardSlaFilter,
      savedView: (patch.savedView ?? filters.savedView) as DashboardSavedView,
      search: patch.search ?? filters.search,
      },
      "critical_tile",
    );
  };

  const openWorkspaceActionsTab = () => {
    if (typeof document === "undefined") return;
    const actionTab = Array.from(
      document.querySelectorAll<HTMLElement>("[role='tab']"),
    ).find((node) => node.textContent?.trim() === "Actions");
    actionTab?.click();
  };

  const focusQueueSearchInput = () => {
    if (typeof document === "undefined") return;
    const input = document.querySelector<HTMLInputElement>(
      "[data-dashboard-queue-search-input]",
    );
    if (!input) return;
    input.focus();
    input.select();
  };

  const focusWorkspacePanel = () => {
    if (typeof document === "undefined") return;
    const panel = document.querySelector<HTMLElement>(
      "[data-dashboard-workspace-panel]",
    );
    panel?.focus();
  };

  const focusWorkspaceAssignee = () => {
    openWorkspaceActionsTab();
    window.requestAnimationFrame(() => {
      const input = document.querySelector<HTMLInputElement>(
        "[data-dashboard-assignee-input]",
      );
      input?.focus();
      input?.select();
    });
  };

  const clickWorkspaceAction = (action: string) => {
    openWorkspaceActionsTab();
    window.requestAnimationFrame(() => {
      const button = document.querySelector<HTMLButtonElement>(
        `[data-dashboard-action="${action}"]:not([disabled])`,
      );
      button?.click();
    });
  };

  const clickActionNext = () => {
    openWorkspaceActionsTab();
    window.requestAnimationFrame(() => {
      const primary = document.querySelector<HTMLButtonElement>(
        "[data-dashboard-action-next-primary='true']:not([disabled])",
      );
      if (primary) {
        primary.click();
        return;
      }
      const fallback = document.querySelector<HTMLButtonElement>(
        "[data-dashboard-action-next]:not([disabled])",
      );
      fallback?.click();
    });
  };

  const selectNextQueueItem = (preferredItemId?: string | null) => {
    const items = queueQuery.data?.items ?? [];
    if (items.length === 0 || !selectedItem) return false;

    if (preferredItemId) {
      const preferred = items.find((item) => item.item_id === preferredItemId);
      if (preferred && preferred.item_id !== selectedItem.item_id) {
        setSelectedItemId(preferred.item_id);
        return true;
      }
    }

    const currentIndex = items.findIndex(
      (item) => item.item_id === selectedItem.item_id,
    );
    if (currentIndex === -1) return false;
    const fallback = items[currentIndex + 1] ?? items[currentIndex - 1];
    if (!fallback || fallback.item_id === selectedItem.item_id) return false;
    setSelectedItemId(fallback.item_id);
    return true;
  };

  const executeAction = async (
    payload: {
      action:
        | "assign"
        | "escalate"
        | "mark_in_progress"
        | "create_case"
        | "close";
      assignee?: string;
      notes?: string;
      sar_required?: boolean;
    },
    options?: { advanceToNext?: boolean },
  ) => {
    setWorkspaceMessage(null);
    try {
      const result = await performAction.mutateAsync(payload);
      const movedToNext = options?.advanceToNext
        ? selectNextQueueItem(result.next_recommended_item_id)
        : false;
      trackDashboardEvent("dashboard_action_submit", {
        mode: "single",
        kind: selectedItem?.kind ?? null,
        action: payload.action,
        success: true,
        advance_to_next: Boolean(options?.advanceToNext),
      });
      if (options?.advanceToNext) {
        trackDashboardEvent("dashboard_action_next", {
          initiator: "action",
          success: true,
          moved_to_next: movedToNext,
          used_backend_hint: Boolean(result.next_recommended_item_id),
        });
      }
      if (result.created_case_id) {
        setWorkspaceMessage({
          text: `Case created: ${result.created_case_id}${movedToNext ? " • Opened next item." : ""}`,
          type: "success",
        });
      } else {
        setWorkspaceMessage({
          text: `${result.message}${movedToNext ? " • Opened next item." : ""}`,
          type: "success",
        });
      }
    } catch (error) {
      trackDashboardEvent("dashboard_action_submit", {
        mode: "single",
        kind: selectedItem?.kind ?? null,
        action: payload.action,
        success: false,
        advance_to_next: Boolean(options?.advanceToNext),
      });
      if (options?.advanceToNext) {
        trackDashboardEvent("dashboard_action_next", {
          initiator: "action",
          success: false,
          moved_to_next: false,
          used_backend_hint: false,
        });
      }
      setWorkspaceMessage({
        text: parseErrorMessage(error, "Failed to execute action"),
        type: "error",
      });
    }
  };

  const runAction = async (payload: {
    action:
      | "assign"
      | "escalate"
      | "mark_in_progress"
      | "create_case"
      | "close";
    assignee?: string;
    notes?: string;
    sar_required?: boolean;
  }) => {
    await executeAction(payload, { advanceToNext: false });
  };

  const runActionAndNext = async (payload: {
    action:
      | "assign"
      | "escalate"
      | "mark_in_progress"
      | "create_case"
      | "close";
    assignee?: string;
    notes?: string;
    sar_required?: boolean;
  }) => {
    await executeAction(payload, { advanceToNext: true });
  };

  const executeReview = async (
    payload: {
      proposed_action: "close" | "approve";
      decision: "approve" | "return";
      submitted_by: string;
      review_notes?: string;
      sar_required?: boolean;
    },
    options?: { advanceToNext?: boolean },
  ) => {
    setWorkspaceMessage(null);
    try {
      const result = await reviewAction.mutateAsync(payload);
      const movedToNext = options?.advanceToNext
        ? selectNextQueueItem(result.next_recommended_item_id)
        : false;
      trackDashboardEvent("dashboard_action_submit", {
        mode: "review",
        kind: selectedItem?.kind ?? null,
        decision: payload.decision,
        proposed_action: payload.proposed_action,
        success: true,
        advance_to_next: Boolean(options?.advanceToNext),
      });
      if (options?.advanceToNext) {
        trackDashboardEvent("dashboard_action_next", {
          initiator: "review",
          success: true,
          moved_to_next: movedToNext,
          used_backend_hint: Boolean(result.next_recommended_item_id),
        });
      }
      setWorkspaceMessage({
        text: `${result.message}${movedToNext ? " • Opened next item." : ""}`,
        type: "success",
      });
    } catch (error) {
      trackDashboardEvent("dashboard_action_submit", {
        mode: "review",
        kind: selectedItem?.kind ?? null,
        decision: payload.decision,
        proposed_action: payload.proposed_action,
        success: false,
        advance_to_next: Boolean(options?.advanceToNext),
      });
      if (options?.advanceToNext) {
        trackDashboardEvent("dashboard_action_next", {
          initiator: "review",
          success: false,
          moved_to_next: false,
          used_backend_hint: false,
        });
      }
      setWorkspaceMessage({
        text: parseErrorMessage(error, "Failed to submit review action"),
        type: "error",
      });
    }
  };

  const runReview = async (payload: {
    proposed_action: "close" | "approve";
    decision: "approve" | "return";
    submitted_by: string;
    review_notes?: string;
    sar_required?: boolean;
  }) => {
    await executeReview(payload, { advanceToNext: false });
  };

  const runReviewAndNext = async (payload: {
    proposed_action: "close" | "approve";
    decision: "approve" | "return";
    submitted_by: string;
    review_notes?: string;
    sar_required?: boolean;
  }) => {
    await executeReview(payload, { advanceToNext: true });
  };

  const runBulkAction = async (
    items: DashboardWorkQueueItem[],
    action: "assign" | "escalate" | "mark_in_progress",
    assignee?: string,
  ) => {
    if (items.length === 0) return;

    const fallbackAssignee =
      assignee ?? profile?.userId ?? selectedItem?.owner ?? "";

    try {
      await bulkAction.mutateAsync({
        items: items.map((item) => ({
          kind: item.kind,
          record_id: item.record_id,
        })),
        action,
        assignee: fallbackAssignee,
      });
      trackDashboardEvent("dashboard_action_submit", {
        mode: "bulk",
        action,
        count: items.length,
        success: true,
      });
      setWorkspaceMessage({
        text: `${items.length} item(s) updated.`,
        type: "success",
      });
    } catch (error) {
      trackDashboardEvent("dashboard_action_submit", {
        mode: "bulk",
        action,
        count: items.length,
        success: false,
      });
      setWorkspaceMessage({
        text: parseErrorMessage(error, "Bulk action failed"),
        type: "error",
      });
    }
  };

  const runSaveDraft = async (payload: {
    narrative: string;
    notes: string;
  }, options?: { silent?: boolean; source?: "manual" | "autosave" }) => {
    if (!selectedItem) return;
    try {
      await saveDraft.mutateAsync(payload);
      if (!options?.silent) {
        setWorkspaceMessage({ text: "Draft saved.", type: "success" });
      }
    } catch (error) {
      if (!options?.silent) {
        setWorkspaceMessage({
          text: parseErrorMessage(error, "Failed to save draft"),
          type: "error",
        });
      }
      throw error;
    }
  };

  const runSnoozeAlert = async (payload: {
    durationHours: number;
    reason?: string;
  }) => {
    if (!selectedItem || selectedItem.kind !== "alert") return;
    setWorkspaceMessage(null);
    try {
      await snoozeAlert.mutateAsync({
        alertRefId: selectedItem.ref_id,
        durationHours: payload.durationHours,
        reason: payload.reason,
        snoozedBy: profile?.userId ?? undefined,
      });
      setWorkspaceMessage({
        text: `Alert snoozed for ${payload.durationHours}h.`,
        type: "success",
      });
    } catch (error) {
      setWorkspaceMessage({
        text: parseErrorMessage(error, "Failed to snooze alert"),
        type: "error",
      });
    }
  };

  useDashboardShortcuts({
    enabled: dashboardEnabled,
    onOpenShortcutHelp: () => setShortcutHelpOpen(true),
    onOpenCommandPalette: () => setCommandPaletteOpen(true),
    onFocusQueueSearch: focusQueueSearchInput,
    onFocusWorkspacePanel: focusWorkspacePanel,
    onToggleInsights: () => setInsightsOpen((current) => !current),
    onFocusAssign: focusWorkspaceAssignee,
    onEscalate: () => clickWorkspaceAction("escalate"),
    onActionNext: clickActionNext,
  });

  const commandPaletteActions = useMemo<DashboardCommandAction[]>(
    () => [
      {
        id: "focus-queue-search",
        label: "Focus queue search",
        shortcut: "g q",
        group: "Navigation",
        onSelect: focusQueueSearchInput,
      },
      {
        id: "focus-workspace",
        label: "Focus workspace panel",
        shortcut: "g d",
        group: "Navigation",
        onSelect: focusWorkspacePanel,
      },
      {
        id: "toggle-insights",
        label: insightsOpen ? "Hide insights rail" : "Show insights rail",
        shortcut: "i",
        group: "Layout",
        onSelect: () => setInsightsOpen((current) => !current),
      },
      {
        id: "focus-assignee",
        label: "Focus assignee field",
        shortcut: "a",
        group: "Actions",
        onSelect: focusWorkspaceAssignee,
      },
      {
        id: "escalate",
        label: "Run escalate action",
        shortcut: "e",
        group: "Actions",
        onSelect: () => clickWorkspaceAction("escalate"),
      },
      {
        id: "action-next",
        label: "Run first available + Next action",
        shortcut: "n",
        group: "Actions",
        onSelect: clickActionNext,
      },
      {
        id: "open-shortcuts-help",
        label: "Open keyboard shortcuts",
        shortcut: "?",
        group: "Help",
        onSelect: () => setShortcutHelpOpen(true),
      },
    ],
    [insightsOpen],
  );

  if (!hasToken) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <Card className="max-w-md border-border shadow-sm">
          <CardContent className="py-8 text-center space-y-3">
            <div className="mx-auto h-12 w-12 rounded-full bg-red-50 text-red-600 flex items-center justify-center">
              <AlertTriangle className="h-6 w-6" />
            </div>
            <h2 className="text-xl font-semibold text-foreground">
              Session Required
            </h2>
            <p className="text-sm text-muted-foreground">
              Sign in to access the AMLCO command center.
            </p>
            <Link href="/">
              <Button>Sign In</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!DASHBOARD_V3_ENABLED) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <Card className="max-w-xl border-border shadow-sm">
          <div className="flex flex-col space-y-1.5 p-6">
            <h3 className="font-semibold leading-none tracking-tight text-foreground">
              AMLCO Command Center V3 Disabled
            </h3>
          </div>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Enable `NEXT_PUBLIC_DASHBOARD_AMLCO_V3` to activate the
              triage-first AMLCO experience.
            </p>
            <Link href="/dashboard?view=operations&range=7d">
              <Button variant="outline">Open Existing Dashboard</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div
      data-testid="dashboard-hub-root"
      className="flex h-[calc(100vh-3.5rem)] flex-col gap-3"
    >
      <section className="sticky top-0 z-20 rounded-2xl border border-border bg-white p-3 shadow-sm">
        <div className="grid grid-cols-1 gap-2 lg:grid-cols-[1fr_auto_auto] lg:items-center">
          <div>
            <h1 className="text-lg font-semibold text-foreground">
              AMLCO Command Center
            </h1>
            <p className="text-xs text-muted-foreground">
              Triage, investigate, and execute controlled actions.
            </p>
          </div>

          <div
            className="inline-flex rounded-xl border border-border bg-slate-50 p-1"
            role="tablist"
            aria-label="Dashboard view selector"
          >
            {VIEW_OPTIONS.map((option) => (
              <button
                key={option.key}
                type="button"
                role="tab"
                id={`dashboard-view-tab-${dashboardTabsId}-${option.key}`}
                aria-selected={option.key === view}
                aria-controls={`dashboard-view-panel-${dashboardTabsId}-${option.key}`}
                tabIndex={option.key === view ? 0 : -1}
                onClick={() => updateViewRange(option.key, range)}
                className={
                  option.key === view
                    ? "rounded-lg bg-white px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-primary shadow-sm ring-1 ring-border/50"
                    : "rounded-lg px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground hover:bg-slate-100 hover:text-foreground"
                }
              >
                {option.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <select
              value={range}
              onChange={(event) =>
                updateViewRange(view, event.target.value as DashboardTimeRange)
              }
              aria-label="Time range"
              className="h-10 rounded-xl border border-border bg-white px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
              {RANGE_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {formatRangeLabel(option)}
                </option>
              ))}
            </select>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                overviewQuery.refetch();
                queueQuery.refetch();
                detailQuery.refetch();
              }}
            >
              <RefreshCw className="h-3.5 w-3.5 mr-1" />
              Refresh
            </Button>
            <Button
              className="hidden lg:inline-flex"
              variant="outline"
              size="sm"
              onClick={() => setInsightsOpen((current) => !current)}
              aria-expanded={insightsOpen}
              aria-controls="dashboard-insights-panel"
            >
              <PanelRight className="h-3.5 w-3.5" />
              {insightsOpen ? "Hide Insights" : "Insights"}
            </Button>
            <div className="hidden xl:block">
              <DataFreshnessBadge
                freshness={overviewFreshness}
                label="Overview"
                compact
              />
            </div>
            <StatusIndicator status="live" label="AI Active" size="sm" />
          </div>
        </div>
        {overviewIsStale ? (
          <div className="mt-2 rounded-lg border border-orange-200 bg-orange-50 px-2 py-1 text-[11px] text-orange-900">
            Overview metrics may be stale. Queue and detail panels may have newer data.
          </div>
        ) : null}
      </section>

      <CriticalDecisionBar
        data={overviewQuery.data?.critical_bar}
        loading={overviewQuery.isLoading}
        onSelectFilter={applyCriticalFilter}
      />

      <section
        id={activeViewPanelId}
        role="tabpanel"
        aria-labelledby={`dashboard-view-tab-${dashboardTabsId}-${view}`}
        className="min-h-0 flex-1 overflow-hidden"
      >
        <div
          className={cn(
            "hidden h-full gap-3 lg:grid",
            insightsOpen
              ? "lg:grid-cols-[420px_minmax(0,1fr)_320px]"
              : "lg:grid-cols-[420px_minmax(0,1fr)_52px]",
          )}
        >
          <UnifiedWorkQueue
            data={queueQuery.data ?? null}
            filters={filters}
            loading={queueQuery.isLoading}
            error={
              queueQuery.isError
                ? parseErrorMessage(
                    queueQuery.error,
                    "Failed to load work queue",
                  )
                : null
            }
            selectedItemId={selectedItem?.item_id ?? null}
            onSelectItem={(item) => {
              trackDashboardEvent("dashboard_row_select", {
                source: "desktop_queue",
                kind: item.kind,
                severity: item.severity,
                review_required: item.review_requirement?.required ?? false,
              });
              setSelectedItemId(item.item_id);
            }}
            onFiltersChange={(patch) =>
              applyQueueFilterPatch(
                patch,
                isPaginationOnlyPatch(patch) ? "pagination" : "queue_controls",
              )
            }
            onRefresh={() => {
              queueQuery.refetch();
              overviewQuery.refetch();
            }}
            onBulkAction={runBulkAction}
          />

          <InvestigationWorkspace
            key={`workspace-${selectedItem?.item_id ?? "none"}`}
            selectedItem={selectedItem}
            detail={detailQuery.data ?? null}
            loading={detailQuery.isLoading}
            error={
              detailQuery.isError
                ? parseErrorMessage(
                    detailQuery.error,
                    "Failed to load work item detail",
                  )
                : null
            }
            message={workspaceMessage}
            actionPending={performAction.isPending}
            reviewPending={reviewAction.isPending}
            draftPending={saveDraft.isPending}
            currentUserId={profile?.userId}
            onAction={runAction}
            onActionAndNext={runActionAndNext}
            onReview={runReview}
            onReviewAndNext={runReviewAndNext}
            onSaveDraft={runSaveDraft}
            onSnoozeAlert={runSnoozeAlert}
          />

          <InsightsPanel
            open={insightsOpen}
            onToggle={() => setInsightsOpen((current) => !current)}
            governance={overviewQuery.data?.governance}
            queueSummary={overviewQuery.data?.queue_summary}
            health={overviewQuery.data?.system_health}
            throughput={overviewQuery.data?.throughput}
            criticalBar={overviewQuery.data?.critical_bar}
            timeRange={range}
            freshness={overviewFreshness}
            loading={overviewQuery.isLoading}
          />
        </div>

        <div className="flex h-full flex-col gap-3 lg:hidden">
          <div className="min-h-0 flex-1">
            {mobilePanel === "queue" ? (
              <UnifiedWorkQueue
                data={queueQuery.data ?? null}
                filters={filters}
                loading={queueQuery.isLoading}
                error={
                  queueQuery.isError
                    ? parseErrorMessage(
                        queueQuery.error,
                        "Failed to load work queue",
                      )
                    : null
                }
                selectedItemId={selectedItem?.item_id ?? null}
                onSelectItem={(item) => {
                  trackDashboardEvent("dashboard_row_select", {
                    source: "mobile_queue",
                    kind: item.kind,
                    severity: item.severity,
                    review_required: item.review_requirement?.required ?? false,
                  });
                  setSelectedItemId(item.item_id);
                  setMobileWorkspaceOpen(true);
                }}
                onFiltersChange={(patch) =>
                  applyQueueFilterPatch(
                    patch,
                    isPaginationOnlyPatch(patch) ? "pagination" : "queue_controls",
                  )
                }
                onRefresh={() => {
                  queueQuery.refetch();
                  overviewQuery.refetch();
                }}
                onBulkAction={runBulkAction}
              />
            ) : (
              <div className="h-full overflow-auto space-y-3">
                <GovernancePanel
                  governance={overviewQuery.data?.governance}
                  queueSummary={overviewQuery.data?.queue_summary}
                  health={overviewQuery.data?.system_health}
                  freshness={overviewFreshness}
                  loading={overviewQuery.isLoading}
                />
                <TrendStrip
                  queueSummary={overviewQuery.data?.queue_summary}
                  throughput={overviewQuery.data?.throughput}
                  criticalBar={overviewQuery.data?.critical_bar}
                  timeRange={range}
                  freshness={overviewFreshness}
                  loading={overviewQuery.isLoading}
                />
              </div>
            )}
          </div>

          <div className="grid grid-cols-3 gap-2 rounded-xl border border-border bg-slate-50 p-2 shadow-sm">
            <Button
              variant={mobilePanel === "queue" ? "primary" : "outline"}
              size="sm"
              onClick={() => setMobilePanel("queue")}
            >
              Queue
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!selectedItem}
              onClick={() => setMobileWorkspaceOpen(true)}
            >
              Detail
            </Button>
            <Button
              variant={mobilePanel === "governance" ? "primary" : "outline"}
              size="sm"
              onClick={() => setMobilePanel("governance")}
            >
              Governance
            </Button>
          </div>
        </div>
      </section>

      {mobileWorkspaceOpen ? (
        <InvestigationWorkspace
          key={`workspace-mobile-${selectedItem?.item_id ?? "none"}`}
          selectedItem={selectedItem}
          detail={detailQuery.data ?? null}
          loading={detailQuery.isLoading}
          error={
            detailQuery.isError
              ? parseErrorMessage(
                  detailQuery.error,
                  "Failed to load work item detail",
                )
              : null
          }
          message={workspaceMessage}
          actionPending={performAction.isPending}
          reviewPending={reviewAction.isPending}
          draftPending={saveDraft.isPending}
          currentUserId={profile?.userId}
          mobileOpen
          onCloseMobile={() => setMobileWorkspaceOpen(false)}
          onAction={runAction}
          onActionAndNext={runActionAndNext}
          onReview={runReview}
          onReviewAndNext={runReviewAndNext}
          onSaveDraft={runSaveDraft}
          onSnoozeAlert={runSnoozeAlert}
        />
      ) : null}

      <ShortcutHelpDialog
        open={shortcutHelpOpen}
        onOpenChange={setShortcutHelpOpen}
      />
      <CommandPalette
        open={commandPaletteOpen}
        onOpenChange={setCommandPaletteOpen}
        actions={commandPaletteActions}
      />
    </div>
  );
}

export default DashboardHub;
