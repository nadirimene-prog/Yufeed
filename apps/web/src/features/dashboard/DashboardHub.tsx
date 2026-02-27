"use client";

import {
  startTransition,
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";
import axios from "axios";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { AlertTriangle, Bookmark, PanelRight, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StatusIndicator } from "@/components/ui/status-indicator";
import { Card, CardContent } from "@/components/ui/card";
import { getAuthToken, getAuthUserProfile } from "@/lib/auth";
import { cn } from "@/lib/utils";
import {
  DashboardQueueFilter,
  DashboardSavedView,
  DashboardSavedViewCreateRequest,
  DashboardSavedViewRecord,
  DashboardSeverityFilter,
  DashboardSlaFilter,
  DashboardTimeRange,
  DashboardView,
  DashboardWorkQueueItem,
  DashboardWorkQueueParams,
  DashboardLayoutPreferences,
  WorkItemActionRequest,
  ReviewActionRequest,
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
import DashboardSavedViewsDialog from "@/features/dashboard/components/DashboardSavedViewsDialog";
import { useDashboardShortcuts } from "@/features/dashboard/hooks/useDashboardShortcuts";
import { useDashboardTelemetryBridge } from "@/features/dashboard/hooks/useDashboardTelemetryBridge";
import {
  useDashboardPreferences,
  useDashboardPreferencesMutation,
  useDashboardSavedViewMutations,
  useDashboardSavedViews,
} from "@/features/dashboard/useDashboardSettings";
import trackDashboardEvent from "@/features/dashboard/telemetry";
import type { WorkspaceTabKey } from "@/features/dashboard/components/InvestigationWorkspace";

const VIEW_OPTIONS: Array<{ key: DashboardView; label: string }> = [
  { key: "operations", label: "Operations" },
  { key: "compliance", label: "Compliance" },
  { key: "monitoring", label: "Monitoring" },
];

const RANGE_OPTIONS: DashboardTimeRange[] = ["24h", "7d", "30d"];
const DASHBOARD_V3_ENABLED =
  process.env.NEXT_PUBLIC_DASHBOARD_AMLCO_V3 !== "false";
const INSIGHTS_PREF_KEY = "dashboard:insights-open";
const DEFAULT_WORKSPACE_TAB_FALLBACK: WorkspaceTabKey = "overview";
const DEFAULT_OVERVIEW_STALE_AFTER_SECONDS = 120;
const QUEUE_EXPORT_ALLOWED_ROLES = new Set([
  "admin",
  "compliance",
  "auditor",
  "manager",
  "qa_audit",
]);

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

function hasExplicitQueueFilterParams(params: URLSearchParams) {
  return [
    "page",
    "pageSize",
    "queue",
    "severity",
    "sla",
    "search",
    "jurisdiction",
    "savedView",
  ].some((key) => params.has(key));
}

function coerceWorkspaceTabKey(
  value: string | null | undefined,
): WorkspaceTabKey {
  if (
    value === "overview" ||
    value === "actions" ||
    value === "timeline" ||
    value === "evidence" ||
    value === "ai" ||
    value === "comments"
  ) {
    return value;
  }
  return DEFAULT_WORKSPACE_TAB_FALLBACK;
}

function getTelemetryNow() {
  if (
    typeof performance !== "undefined" &&
    Number.isFinite(performance.now())
  ) {
    return performance.now();
  }
  return Date.now();
}

function isFreshnessStaleAt(
  freshness:
    | { generated_at?: string | null; stale_after_seconds?: number | null }
    | null
    | undefined,
  fallbackStaleAfterSeconds: number,
  nowMs: number | null,
) {
  if (!freshness?.generated_at) return false;
  const generatedAt = new Date(freshness.generated_at);
  if (Number.isNaN(generatedAt.valueOf())) return false;
  const staleAfter = Math.max(
    1,
    freshness.stale_after_seconds ?? fallbackStaleAfterSeconds,
  );
  const referenceNow = nowMs ?? generatedAt.getTime();
  return referenceNow - generatedAt.getTime() > staleAfter * 1000;
}

function useMediaQuery(query: string) {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    if (
      typeof window === "undefined" ||
      typeof window.matchMedia !== "function"
    ) {
      return;
    }
    const media = window.matchMedia(query);
    const update = () => setMatches(media.matches);
    update();
    if (typeof media.addEventListener === "function") {
      media.addEventListener("change", update);
      return () => media.removeEventListener("change", update);
    }
    media.addListener(update);
    return () => media.removeListener(update);
  }, [query]);

  return matches;
}

function OverviewFreshnessAlert({
  freshness,
  fallbackStaleAfterSeconds,
}: {
  freshness:
    | { generated_at?: string | null; stale_after_seconds?: number | null }
    | null
    | undefined;
  fallbackStaleAfterSeconds: number;
}) {
  const [nowMs, setNowMs] = useState<number | null>(null);

  useEffect(() => {
    const updateNow = () => setNowMs(Date.now());
    updateNow();
    const timer = window.setInterval(updateNow, 30_000);
    return () => window.clearInterval(timer);
  }, []);

  const stale = isFreshnessStaleAt(freshness, fallbackStaleAfterSeconds, nowMs);
  if (!stale) return null;

  return (
    <div className="mt-2 rounded-lg border border-orange-200 bg-orange-50 px-2 py-1 text-[11px] text-orange-900">
      Overview metrics may be stale. Queue and detail panels may have newer
      data.
    </div>
  );
}

interface PendingQueueFilterTelemetry {
  source: "queue_controls" | "critical_tile" | "pagination";
  keys: string[];
  startedAt: number;
}

interface PendingRowSelectTelemetry {
  source: "desktop_queue" | "mobile_queue";
  kind: DashboardWorkQueueItem["kind"];
  severity: DashboardWorkQueueItem["severity"];
  reviewRequired: boolean;
  itemId: string;
  startedAt: number;
}

export function DashboardHub() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const searchParamsString = useMemo(
    () => searchParams.toString(),
    [searchParams],
  );
  const profile = getAuthUserProfile();
  const hadLocalInsightsPrefAtMountRef = useRef(false);
  const isDesktop = useMediaQuery("(min-width: 1024px)");

  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [workspaceMessage, setWorkspaceMessage] =
    useState<WorkspaceMessage | null>(null);
  const [mobileWorkspaceOpen, setMobileWorkspaceOpen] = useState(false);
  const [mobilePanel, setMobilePanel] = useState<"queue" | "governance">(
    "queue",
  );
  const [shortcutHelpOpen, setShortcutHelpOpen] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [savedViewsDialogOpen, setSavedViewsDialogOpen] = useState(false);
  const [activeSavedViewId, setActiveSavedViewId] = useState<string | null>(
    null,
  );
  const [queueDensityPreference, setQueueDensityPreference] = useState<
    "comfortable" | "compact" | null
  >(null);
  const [workspaceDefaultTab, setWorkspaceDefaultTab] =
    useState<WorkspaceTabKey>(DEFAULT_WORKSPACE_TAB_FALLBACK);
  const [insightsOpen, setInsightsOpen] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    const raw = window.localStorage.getItem(INSIGHTS_PREF_KEY);
    return raw === "1";
  });
  const pendingQueueFilterTelemetryRef =
    useRef<PendingQueueFilterTelemetry | null>(null);
  const pendingRowSelectTelemetryRef = useRef<PendingRowSelectTelemetry | null>(
    null,
  );
  const dashboardTabsId = useId();
  const serverDefaultsAppliedRef = useRef(false);
  const serverInsightsHydratedRef = useRef(false);
  const lastLayoutPrefsSyncRef = useRef<string>("");

  useEffect(() => {
    if (typeof window === "undefined") return;
    const raw = window.localStorage.getItem(INSIGHTS_PREF_KEY);
    hadLocalInsightsPrefAtMountRef.current = raw === "1" || raw === "0";
  }, []);

  const view = resolveDashboardView(searchParams.get("view"));
  const range = resolveDashboardTimeRange(searchParams.get("range"));
  const filters = useMemo(
    () => parseFilters(new URLSearchParams(searchParamsString)),
    [searchParamsString],
  );

  const hasToken = Boolean(getAuthToken());
  const dashboardEnabled = hasToken && DASHBOARD_V3_ENABLED;
  const canExportQueue = QUEUE_EXPORT_ALLOWED_ROLES.has(
    (profile?.role ?? "").toLowerCase(),
  );

  useDashboardTelemetryBridge({ enabled: dashboardEnabled });

  const savedViewsQuery = useDashboardSavedViews({ enabled: dashboardEnabled });
  const preferencesQuery = useDashboardPreferences({
    enabled: dashboardEnabled,
  });
  const { createSavedView, updateSavedView, deleteSavedView } =
    useDashboardSavedViewMutations();
  const updatePreferences = useDashboardPreferencesMutation();

  const saveLayoutPreferencesPatch = useCallback(
    (patch: Partial<DashboardLayoutPreferences>) => {
      if (!dashboardEnabled) return;
      const normalizedPatch: DashboardLayoutPreferences = {};
      if (patch.queueDensity !== undefined) {
        normalizedPatch.queueDensity = patch.queueDensity;
      }
      if (patch.insightsOpen !== undefined) {
        normalizedPatch.insightsOpen = patch.insightsOpen;
      }
      if (patch.defaultWorkspaceTab !== undefined) {
        normalizedPatch.defaultWorkspaceTab = patch.defaultWorkspaceTab;
      }
      const signature = JSON.stringify(normalizedPatch);
      if (signature === "{}") return;
      if (lastLayoutPrefsSyncRef.current === signature) return;
      lastLayoutPrefsSyncRef.current = signature;
      updatePreferences.mutate(
        { layout_prefs: normalizedPatch },
        {
          onError: () => {
            if (lastLayoutPrefsSyncRef.current === signature) {
              lastLayoutPrefsSyncRef.current = "";
            }
          },
        },
      );
    },
    [dashboardEnabled, updatePreferences],
  );

  useEffect(() => {
    const layoutPrefs = preferencesQuery.data?.layout_prefs;
    if (!layoutPrefs) return;

    if (
      !serverInsightsHydratedRef.current &&
      !hadLocalInsightsPrefAtMountRef.current &&
      typeof layoutPrefs.insightsOpen === "boolean"
    ) {
      serverInsightsHydratedRef.current = true;
      queueMicrotask(() => {
        setInsightsOpen(layoutPrefs.insightsOpen ?? false);
      });
    }

    if (
      layoutPrefs.queueDensity === "compact" ||
      layoutPrefs.queueDensity === "comfortable"
    ) {
      queueMicrotask(() => {
        setQueueDensityPreference(
          (current) => current ?? layoutPrefs.queueDensity ?? null,
        );
      });
    }

    if (layoutPrefs.defaultWorkspaceTab) {
      queueMicrotask(() => {
        setWorkspaceDefaultTab((current) =>
          current === DEFAULT_WORKSPACE_TAB_FALLBACK
            ? coerceWorkspaceTabKey(layoutPrefs.defaultWorkspaceTab ?? null)
            : current,
        );
      });
    }
  }, [preferencesQuery.data?.layout_prefs]);

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
    return items.find((item) => item.item_id === selectedItemId) ?? null;
  }, [queueQuery.data?.items, selectedItemId]);
  const selectedItemMissingFromQueue = useMemo(() => {
    const items = queueQuery.data?.items ?? [];
    if (!selectedItemId || items.length === 0) return false;
    return !items.some((item) => item.item_id === selectedItemId);
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

  useEffect(() => {
    const pending = pendingQueueFilterTelemetryRef.current;
    if (!pending) return;
    if (queueQuery.isFetching) return;

    pendingQueueFilterTelemetryRef.current = null;
    trackDashboardEvent("dashboard_filter_apply", {
      source: pending.source,
      keys: pending.keys,
      phase: queueQuery.isError ? "queue_load_error" : "queue_loaded",
      success: !queueQuery.isError,
      latency_ms: Math.max(
        0,
        Math.round(getTelemetryNow() - pending.startedAt),
      ),
      page: queueQuery.data?.page ?? null,
      page_size: queueQuery.data?.page_size ?? null,
      total: queueQuery.data?.total ?? null,
      visible_count: queueQuery.data?.items?.length ?? null,
    });
  }, [
    queueQuery.isFetching,
    queueQuery.isError,
    queueQuery.data?.page,
    queueQuery.data?.page_size,
    queueQuery.data?.total,
    queueQuery.data?.items?.length,
  ]);

  useEffect(() => {
    const pending = pendingRowSelectTelemetryRef.current;
    if (!pending) return;
    if (detailQuery.isFetching) return;

    const selectedId = selectedItem?.item_id ?? null;
    if (selectedId !== pending.itemId) return;

    const detailItemId = detailQuery.data?.work_item.item_id ?? null;
    if (detailItemId && detailItemId !== pending.itemId) return;

    pendingRowSelectTelemetryRef.current = null;
    trackDashboardEvent("dashboard_row_select", {
      source: pending.source,
      kind: pending.kind,
      severity: pending.severity,
      review_required: pending.reviewRequired,
      phase: detailQuery.isError ? "detail_load_error" : "detail_loaded",
      success: !detailQuery.isError,
      latency_ms: Math.max(
        0,
        Math.round(getTelemetryNow() - pending.startedAt),
      ),
      detail_has_freshness: Boolean(detailQuery.data?.freshness),
    });
  }, [
    selectedItem?.item_id,
    detailQuery.isFetching,
    detailQuery.isError,
    detailQuery.data?.work_item.item_id,
    detailQuery.data?.freshness,
  ]);

  const activeViewPanelId = `dashboard-view-panel-${dashboardTabsId}-${view}`;
  const overviewFreshness = overviewQuery.data?.freshness ?? null;
  const overviewErrorMessage =
    overviewQuery.isError && !overviewQuery.isLoading
      ? parseErrorMessage(overviewQuery.error, "Failed to refresh overview")
      : null;
  const overviewHasCachedData = Boolean(overviewQuery.data);
  const overviewMetricsDegraded =
    Boolean(overviewErrorMessage) && overviewHasCachedData;
  const overviewDegradedNotice = overviewMetricsDegraded
    ? `Overview refresh failed. Showing last loaded metrics. ${overviewErrorMessage}`
    : null;
  const partialFailureNotices: string[] = [];
  if (overviewQuery.isError && !overviewQuery.isLoading) {
    partialFailureNotices.push(
      "Overview metrics are temporarily unavailable. Queue and workspace panels may still be usable.",
    );
  }
  if (queueQuery.isError && !queueQuery.isLoading) {
    partialFailureNotices.push(
      "Work queue failed to load. Overview metrics and any open workspace context may still be available.",
    );
  }
  if (selectedItem && detailQuery.isError && !detailQuery.isLoading) {
    partialFailureNotices.push(
      "Selected item detail failed to load. Queue triage remains available while detail data recovers.",
    );
  }

  const updateSearch = useCallback(
    (patch: Partial<DashboardWorkQueueParams>) => {
      const defaults = defaultQueueFilters();
      const next = { ...filters, ...patch };
      const params = new URLSearchParams(searchParamsString);

      params.set("view", view);
      params.set("range", range);

      setParam(params, "page", next.page, defaults.page);
      setParam(params, "pageSize", next.pageSize, defaults.pageSize);
      setParam(params, "queue", next.queue, defaults.queue);
      setParam(params, "severity", next.severity, defaults.severity);
      setParam(params, "sla", next.sla, defaults.sla);
      setParam(params, "search", next.search, defaults.search);
      setParam(
        params,
        "jurisdiction",
        next.jurisdiction,
        defaults.jurisdiction,
      );
      setParam(params, "savedView", next.savedView, defaults.savedView);

      startTransition(() => {
        router.replace(`${pathname}?${params.toString()}`);
      });
    },
    [filters, pathname, range, router, searchParamsString, view],
  );

  const updateViewRange = useCallback(
    (nextView: DashboardView = view, nextRange: DashboardTimeRange = range) => {
      const params = new URLSearchParams(searchParamsString);
      params.set("view", nextView);
      params.set("range", nextRange);
      startTransition(() => {
        router.replace(`${pathname}?${params.toString()}`);
      });
    },
    [pathname, range, router, searchParamsString, view],
  );

  const applySavedViewRecord = useCallback(
    (
      record: DashboardSavedViewRecord,
      source: "saved_view" | "server_default" = "saved_view",
    ) => {
      setActiveSavedViewId(record.id);
      if (
        record.layout_prefs?.insightsOpen !== null &&
        record.layout_prefs?.insightsOpen !== undefined
      ) {
        setInsightsOpen(Boolean(record.layout_prefs.insightsOpen));
      }
      if (
        record.layout_prefs?.queueDensity === "compact" ||
        record.layout_prefs?.queueDensity === "comfortable"
      ) {
        setQueueDensityPreference(record.layout_prefs.queueDensity);
      }
      if (record.layout_prefs?.defaultWorkspaceTab) {
        setWorkspaceDefaultTab(
          coerceWorkspaceTabKey(record.layout_prefs.defaultWorkspaceTab),
        );
      }

      pendingQueueFilterTelemetryRef.current = {
        source: "queue_controls",
        keys: Object.keys(record.filters).sort(),
        startedAt: getTelemetryNow(),
      };
      trackDashboardEvent("dashboard_filter_apply", {
        source,
        keys: Object.keys(record.filters).sort(),
        phase: "submitted",
      });
      updateSearch(record.filters);
    },
    [
      setActiveSavedViewId,
      setInsightsOpen,
      setQueueDensityPreference,
      setWorkspaceDefaultTab,
      updateSearch,
    ],
  );

  useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(INSIGHTS_PREF_KEY, insightsOpen ? "1" : "0");
    }
    const prefsReady =
      preferencesQuery.isSuccess ||
      preferencesQuery.isError ||
      preferencesQuery.isFetched;
    if (!dashboardEnabled || !prefsReady) return;
    saveLayoutPreferencesPatch({ insightsOpen });
  }, [
    dashboardEnabled,
    insightsOpen,
    preferencesQuery.isError,
    preferencesQuery.isFetched,
    preferencesQuery.isSuccess,
    saveLayoutPreferencesPatch,
  ]);

  useEffect(() => {
    if (serverDefaultsAppliedRef.current) return;
    if (!dashboardEnabled) return;
    if (!savedViewsQuery.isSuccess) return;
    if (hasExplicitQueueFilterParams(new URLSearchParams(searchParamsString))) {
      serverDefaultsAppliedRef.current = true;
      return;
    }

    const preferredDefaultId =
      preferencesQuery.data?.default_saved_view_id ??
      savedViewsQuery.data?.resolved_default_view_id ??
      null;
    if (!preferredDefaultId) {
      serverDefaultsAppliedRef.current = true;
      return;
    }
    const target = savedViewsQuery.data.items.find(
      (item) => item.id === preferredDefaultId,
    );
    if (!target) {
      serverDefaultsAppliedRef.current = true;
      return;
    }
    serverDefaultsAppliedRef.current = true;
    queueMicrotask(() => {
      applySavedViewRecord(target, "server_default");
    });
  }, [
    dashboardEnabled,
    savedViewsQuery.isSuccess,
    savedViewsQuery.data,
    preferencesQuery.data?.default_saved_view_id,
    searchParamsString,
    applySavedViewRecord,
  ]);

  const applyQueueFilterPatch = useCallback(
    (
      patch: Partial<DashboardWorkQueueParams>,
      source:
        | "queue_controls"
        | "critical_tile"
        | "pagination" = "queue_controls",
    ) => {
      setActiveSavedViewId(null);
      const keys = Object.keys(patch).sort();
      pendingQueueFilterTelemetryRef.current = {
        source,
        keys,
        startedAt: getTelemetryNow(),
      };
      trackDashboardEvent("dashboard_filter_apply", {
        source,
        keys,
        phase: "submitted",
      });
      updateSearch(patch);
    },
    [setActiveSavedViewId, updateSearch],
  );

  const applyCriticalFilter = useCallback(
    (patch: CriticalTileFilter) => {
      applyQueueFilterPatch(
        {
          page: 1,
          queue: (patch.queue ?? filters.queue) as DashboardQueueFilter,
          severity: (patch.severity ??
            filters.severity) as DashboardSeverityFilter,
          sla: (patch.sla ?? filters.sla) as DashboardSlaFilter,
          savedView: (patch.savedView ??
            filters.savedView) as DashboardSavedView,
          search: patch.search ?? filters.search,
        },
        "critical_tile",
      );
    },
    [
      applyQueueFilterPatch,
      filters.queue,
      filters.savedView,
      filters.search,
      filters.severity,
      filters.sla,
    ],
  );

  const openWorkspaceActionsTab = useCallback(() => {
    if (typeof document === "undefined") return;
    const actionTab = Array.from(
      document.querySelectorAll<HTMLElement>("[role='tab']"),
    ).find((node) => node.textContent?.trim() === "Actions");
    actionTab?.click();
  }, []);

  const focusQueueSearchInput = useCallback(() => {
    if (typeof document === "undefined") return;
    const input = document.querySelector<HTMLInputElement>(
      "[data-dashboard-queue-search-input]",
    );
    if (!input) return;
    input.focus();
    input.select();
  }, []);

  const focusWorkspacePanel = useCallback(() => {
    if (typeof document === "undefined") return;
    const panel = document.querySelector<HTMLElement>(
      "[data-dashboard-workspace-panel]",
    );
    panel?.focus();
  }, []);

  const focusWorkspaceAssignee = useCallback(() => {
    openWorkspaceActionsTab();
    window.requestAnimationFrame(() => {
      const input = document.querySelector<HTMLInputElement>(
        "[data-dashboard-assignee-input]",
      );
      input?.focus();
      input?.select();
    });
  }, [openWorkspaceActionsTab]);

  const clickWorkspaceAction = useCallback(
    (action: string) => {
      openWorkspaceActionsTab();
      window.requestAnimationFrame(() => {
        const button = document.querySelector<HTMLButtonElement>(
          `[data-dashboard-action="${action}"]:not([disabled])`,
        );
        button?.click();
      });
    },
    [openWorkspaceActionsTab],
  );

  const retryOverviewPanels = useCallback(() => {
    overviewQuery.refetch();
  }, [overviewQuery]);

  const clickActionNext = useCallback(() => {
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
  }, [openWorkspaceActionsTab]);

  const selectNextQueueItem = useCallback(
    (preferredItemId?: string | null) => {
      const items = queueQuery.data?.items ?? [];
      if (items.length === 0 || !selectedItem) return false;

      if (preferredItemId) {
        const preferred = items.find(
          (item) => item.item_id === preferredItemId,
        );
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
    },
    [queueQuery.data?.items, selectedItem, setSelectedItemId],
  );

  const handleQueueItemSelect = useCallback(
    (
      item: DashboardWorkQueueItem,
      source: "desktop_queue" | "mobile_queue",
    ) => {
      pendingRowSelectTelemetryRef.current = {
        source,
        kind: item.kind,
        severity: item.severity,
        reviewRequired: item.review_requirement?.required ?? false,
        itemId: item.item_id,
        startedAt: getTelemetryNow(),
      };
      trackDashboardEvent("dashboard_row_select", {
        source,
        kind: item.kind,
        severity: item.severity,
        review_required: item.review_requirement?.required ?? false,
        phase: "selected",
      });
      setSelectedItemId(item.item_id);
    },
    [setSelectedItemId],
  );

  const refreshSelectedDetailWithWarning = async (options?: {
    onFailureMessage?: string;
    clearWarningOnSuccess?: boolean;
    telemetryTrigger?:
      | "post_action"
      | "post_review"
      | "snooze"
      | "manual_retry";
  }) => {
    if (!selectedItem) return true;
    const startedAt = getTelemetryNow();
    let failed = false;
    try {
      const result = await detailQuery.refetch();
      failed = Boolean(result?.isError);
    } catch {
      failed = true;
    }
    trackDashboardEvent("dashboard_ui_timing", {
      metric: "detail_refresh_complete",
      trigger: options?.telemetryTrigger ?? "manual_retry",
      success: !failed,
      has_error: failed,
      latency_ms: Math.max(0, Math.round(getTelemetryNow() - startedAt)),
      kind: selectedItem.kind,
    });
    if (failed) {
      if (options?.onFailureMessage) {
        setWorkspaceMessage({
          text: options.onFailureMessage,
          type: "warning",
        });
      }
      return false;
    }
    if (options?.clearWarningOnSuccess) {
      setWorkspaceMessage((current) =>
        current?.type === "warning" ? null : current,
      );
    }
    return true;
  };

  const executeAction = async (
    payload: WorkItemActionRequest,
    options?: { advanceToNext?: boolean },
  ) => {
    setWorkspaceMessage(null);
    const startedAt = getTelemetryNow();
    const actedOnItemId = selectedItem?.item_id ?? null;
    try {
      const result = await performAction.mutateAsync(payload);
      const movedToNext = options?.advanceToNext
        ? selectNextQueueItem(result.next_recommended_item_id)
        : false;
      let successMessage = result.created_case_id
        ? `Case created: ${result.created_case_id}${movedToNext ? " • Opened next item." : ""}`
        : `${result.message}${movedToNext ? " • Opened next item." : ""}`;
      if (!movedToNext && actedOnItemId) {
        const detailRefreshOk = await refreshSelectedDetailWithWarning({
          onFailureMessage: `${successMessage} • Detail panel failed to refresh. Retry detail.`,
          telemetryTrigger: "post_action",
        });
        if (!detailRefreshOk) {
          successMessage = "";
        }
      }
      trackDashboardEvent("dashboard_action_submit", {
        mode: "single",
        kind: selectedItem?.kind ?? null,
        action: payload.action,
        success: true,
        advance_to_next: Boolean(options?.advanceToNext),
        latency_ms: Math.max(0, Math.round(getTelemetryNow() - startedAt)),
      });
      if (options?.advanceToNext) {
        trackDashboardEvent("dashboard_action_next", {
          initiator: "action",
          success: true,
          moved_to_next: movedToNext,
          used_backend_hint: Boolean(result.next_recommended_item_id),
        });
      }
      if (successMessage) {
        setWorkspaceMessage({
          text: successMessage,
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
        latency_ms: Math.max(0, Math.round(getTelemetryNow() - startedAt)),
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

  const runAction = async (payload: WorkItemActionRequest) => {
    await executeAction(payload, { advanceToNext: false });
  };

  const runActionAndNext = async (payload: WorkItemActionRequest) => {
    await executeAction(payload, { advanceToNext: true });
  };

  const executeReview = async (
    payload: ReviewActionRequest,
    options?: { advanceToNext?: boolean },
  ) => {
    setWorkspaceMessage(null);
    const startedAt = getTelemetryNow();
    const reviewedItemId = selectedItem?.item_id ?? null;
    try {
      const result = await reviewAction.mutateAsync(payload);
      const movedToNext = options?.advanceToNext
        ? selectNextQueueItem(result.next_recommended_item_id)
        : false;
      let successMessage = `${result.message}${movedToNext ? " • Opened next item." : ""}`;
      if (!movedToNext && reviewedItemId) {
        const detailRefreshOk = await refreshSelectedDetailWithWarning({
          onFailureMessage: `${successMessage} • Detail panel failed to refresh. Retry detail.`,
          telemetryTrigger: "post_review",
        });
        if (!detailRefreshOk) {
          successMessage = "";
        }
      }
      trackDashboardEvent("dashboard_action_submit", {
        mode: "review",
        kind: selectedItem?.kind ?? null,
        decision: payload.decision,
        proposed_action: payload.proposed_action,
        success: true,
        advance_to_next: Boolean(options?.advanceToNext),
        latency_ms: Math.max(0, Math.round(getTelemetryNow() - startedAt)),
      });
      if (options?.advanceToNext) {
        trackDashboardEvent("dashboard_action_next", {
          initiator: "review",
          success: true,
          moved_to_next: movedToNext,
          used_backend_hint: Boolean(result.next_recommended_item_id),
        });
      }
      if (successMessage) {
        setWorkspaceMessage({
          text: successMessage,
          type: "success",
        });
      }
    } catch (error) {
      trackDashboardEvent("dashboard_action_submit", {
        mode: "review",
        kind: selectedItem?.kind ?? null,
        decision: payload.decision,
        proposed_action: payload.proposed_action,
        success: false,
        advance_to_next: Boolean(options?.advanceToNext),
        latency_ms: Math.max(0, Math.round(getTelemetryNow() - startedAt)),
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

  const runReview = async (payload: ReviewActionRequest) => {
    await executeReview(payload, { advanceToNext: false });
  };

  const runReviewAndNext = async (payload: ReviewActionRequest) => {
    await executeReview(payload, { advanceToNext: true });
  };

  const runBulkAction = async (
    items: DashboardWorkQueueItem[],
    action: "assign" | "escalate" | "mark_in_progress",
    assignee?: string,
  ) => {
    if (items.length === 0) return;
    const startedAt = getTelemetryNow();

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
        latency_ms: Math.max(0, Math.round(getTelemetryNow() - startedAt)),
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
        latency_ms: Math.max(0, Math.round(getTelemetryNow() - startedAt)),
      });
      setWorkspaceMessage({
        text: parseErrorMessage(error, "Bulk action failed"),
        type: "error",
      });
    }
  };

  const runSaveDraft = async (
    payload: {
      narrative: string;
      notes: string;
    },
    options?: { silent?: boolean; source?: "manual" | "autosave" },
  ) => {
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
    const snoozedItemId = selectedItem.item_id;
    try {
      await snoozeAlert.mutateAsync({
        alertRefId: selectedItem.ref_id,
        durationHours: payload.durationHours,
        reason: payload.reason,
        snoozedBy: profile?.userId ?? undefined,
      });
      const successMessage = `Alert snoozed for ${payload.durationHours}h.`;
      if (snoozedItemId) {
        const detailRefreshOk = await refreshSelectedDetailWithWarning({
          onFailureMessage: `${successMessage} • Detail panel failed to refresh. Retry detail.`,
          telemetryTrigger: "snooze",
        });
        if (!detailRefreshOk) return;
      }
      setWorkspaceMessage({
        text: successMessage,
        type: "success",
      });
    } catch (error) {
      setWorkspaceMessage({
        text: parseErrorMessage(error, "Failed to snooze alert"),
        type: "error",
      });
    }
  };

  const retryDetailLoad = async () => {
    await refreshSelectedDetailWithWarning({
      onFailureMessage:
        "Detail panel failed to refresh. Queue triage remains available while detail data recovers.",
      clearWarningOnSuccess: true,
      telemetryTrigger: "manual_retry",
    });
  };

  const handleSetUserDefaultSavedView = useCallback(
    async (viewId: string | null) => {
      await updatePreferences.mutateAsync({
        default_saved_view_id: viewId,
      });
    },
    [updatePreferences],
  );

  const handleCreateSavedView = useCallback(
    async (
      payload: DashboardSavedViewCreateRequest,
      options?: { setAsUserDefault?: boolean },
    ) => {
      const created = await createSavedView.mutateAsync(payload);
      if (options?.setAsUserDefault) {
        await handleSetUserDefaultSavedView(created.id);
      }
      setActiveSavedViewId(created.id);
    },
    [createSavedView, handleSetUserDefaultSavedView, setActiveSavedViewId],
  );

  const handleUpdateSavedView = useCallback(
    async (
      viewId: string,
      payload: Partial<DashboardSavedViewCreateRequest>,
      options?: { setAsUserDefault?: boolean },
    ) => {
      const updated = await updateSavedView.mutateAsync({
        id: viewId,
        patch: payload,
      });
      if (options?.setAsUserDefault) {
        await handleSetUserDefaultSavedView(updated.id);
      } else if (preferencesQuery.data?.default_saved_view_id === updated.id) {
        await handleSetUserDefaultSavedView(null);
      }
      setActiveSavedViewId(updated.id);
    },
    [
      handleSetUserDefaultSavedView,
      preferencesQuery.data?.default_saved_view_id,
      setActiveSavedViewId,
      updateSavedView,
    ],
  );

  const handleDeleteSavedView = useCallback(
    async (viewId: string) => {
      await deleteSavedView.mutateAsync(viewId);
      setActiveSavedViewId((current) => (current === viewId ? null : current));
    },
    [deleteSavedView, setActiveSavedViewId],
  );

  const currentLayoutPrefsForSave: DashboardLayoutPreferences = {
    queueDensity: queueDensityPreference,
    insightsOpen,
    defaultWorkspaceTab: workspaceDefaultTab,
  };
  const handleQueueDensityPreferenceChange = useCallback(
    (value: "comfortable" | "compact") => {
      setQueueDensityPreference(value);
      saveLayoutPreferencesPatch({ queueDensity: value });
    },
    [saveLayoutPreferencesPatch, setQueueDensityPreference],
  );
  const handleWorkspaceTabPreferenceChange = useCallback(
    (tab: WorkspaceTabKey) => {
      setWorkspaceDefaultTab(tab);
      saveLayoutPreferencesPatch({ defaultWorkspaceTab: tab });
    },
    [saveLayoutPreferencesPatch, setWorkspaceDefaultTab],
  );
  const dashboardSavedViews = savedViewsQuery.data?.items ?? [];
  const savedViewsPending =
    savedViewsQuery.isFetching ||
    createSavedView.isPending ||
    updateSavedView.isPending ||
    deleteSavedView.isPending ||
    updatePreferences.isPending;

  const openShortcutHelp = useCallback(() => {
    setShortcutHelpOpen(true);
  }, [setShortcutHelpOpen]);
  const openCommandPalette = useCallback(() => {
    setCommandPaletteOpen(true);
  }, [setCommandPaletteOpen]);
  const toggleInsights = useCallback(() => {
    setInsightsOpen((current) => !current);
  }, [setInsightsOpen]);
  const runEscalateShortcut = useCallback(() => {
    clickWorkspaceAction("escalate");
  }, [clickWorkspaceAction]);
  const openSavedViewsDialog = useCallback(() => {
    setSavedViewsDialogOpen(true);
  }, [setSavedViewsDialogOpen]);

  useDashboardShortcuts({
    enabled: dashboardEnabled,
    onOpenShortcutHelp: openShortcutHelp,
    onOpenCommandPalette: openCommandPalette,
    onFocusQueueSearch: focusQueueSearchInput,
    onFocusWorkspacePanel: focusWorkspacePanel,
    onToggleInsights: toggleInsights,
    onFocusAssign: focusWorkspaceAssignee,
    onEscalate: runEscalateShortcut,
    onActionNext: clickActionNext,
  });

  const commandPaletteActions: DashboardCommandAction[] = useMemo(
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
        onSelect: toggleInsights,
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
        onSelect: runEscalateShortcut,
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
        onSelect: openShortcutHelp,
      },
      {
        id: "open-saved-views",
        label: "Open saved views manager",
        group: "Layout",
        onSelect: openSavedViewsDialog,
      },
    ],
    [
      clickActionNext,
      focusQueueSearchInput,
      focusWorkspaceAssignee,
      focusWorkspacePanel,
      insightsOpen,
      openSavedViewsDialog,
      openShortcutHelp,
      runEscalateShortcut,
      toggleInsights,
    ],
  );

  const handleDesktopQueueSelect = (item: DashboardWorkQueueItem) => {
    handleQueueItemSelect(item, "desktop_queue");
  };

  const handleMobileQueueSelect = (item: DashboardWorkQueueItem) => {
    handleQueueItemSelect(item, "mobile_queue");
    setMobileWorkspaceOpen(true);
  };

  const refreshQueueAndOverview = useCallback(() => {
    queueQuery.refetch();
    overviewQuery.refetch();
  }, [overviewQuery, queueQuery]);

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
              AMLCO dashboard v3 is disabled because
              `NEXT_PUBLIC_DASHBOARD_AMLCO_V3=false`.
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
            <Button variant="outline" size="sm" onClick={openSavedViewsDialog}>
              <Bookmark className="h-3.5 w-3.5 mr-1" />
              Views
            </Button>
            <Button
              className="hidden lg:inline-flex"
              variant="outline"
              size="sm"
              onClick={toggleInsights}
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
        <OverviewFreshnessAlert
          freshness={overviewFreshness}
          fallbackStaleAfterSeconds={DEFAULT_OVERVIEW_STALE_AFTER_SECONDS}
        />
        {partialFailureNotices.length > 0 ? (
          <div
            data-testid="dashboard-partial-outage-banner"
            className="mt-2 rounded-lg border border-red-200 bg-red-50 px-2 py-2 text-[11px] text-red-900"
            role="status"
            aria-live="polite"
          >
            {partialFailureNotices.map((notice, index) => (
              <p key={notice} className={index > 0 ? "mt-1" : undefined}>
                {notice}
              </p>
            ))}
          </div>
        ) : null}
      </section>

      <div className="space-y-2">
        {overviewDegradedNotice ? (
          <div
            data-testid="overview-degraded-inline-banner"
            className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900"
            role="status"
            aria-live="polite"
          >
            <span>{overviewDegradedNotice}</span>
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-7 border-amber-300 bg-white px-2 text-xs text-amber-900 hover:bg-amber-100 hover:text-amber-950"
              onClick={retryOverviewPanels}
            >
              Retry overview
            </Button>
          </div>
        ) : null}
        {selectedItemMissingFromQueue ? (
          <div
            data-testid="dashboard-selection-missing-banner"
            className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900"
            role="status"
            aria-live="polite"
          >
            <span>
              The selected item is no longer in the current queue. Select
              another item or adjust filters.
            </span>
          </div>
        ) : null}

        <CriticalDecisionBar
          data={overviewQuery.data?.critical_bar}
          loading={overviewQuery.isLoading}
          onSelectFilter={applyCriticalFilter}
        />
      </div>

      <section
        id={activeViewPanelId}
        role="tabpanel"
        aria-labelledby={`dashboard-view-tab-${dashboardTabsId}-${view}`}
        className="min-h-0 flex-1 overflow-hidden"
      >
        {isDesktop ? (
          <div
            className={cn(
              "h-full gap-3 lg:grid",
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
              onSelectItem={handleDesktopQueueSelect}
              onFiltersChange={(patch) =>
                applyQueueFilterPatch(
                  patch,
                  isPaginationOnlyPatch(patch)
                    ? "pagination"
                    : "queue_controls",
                )
              }
              onRefresh={refreshQueueAndOverview}
              canExport={canExportQueue}
              serverDensityPreference={queueDensityPreference}
              onDensityPreferenceChange={handleQueueDensityPreferenceChange}
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
              detailRefreshPending={
                detailQuery.isFetching && !detailQuery.isLoading
              }
              defaultTab={workspaceDefaultTab}
              currentUserId={profile?.userId}
              onRetryDetail={retryDetailLoad}
              onWorkspaceTabChange={handleWorkspaceTabPreferenceChange}
              onAction={runAction}
              onActionAndNext={runActionAndNext}
              onReview={runReview}
              onReviewAndNext={runReviewAndNext}
              onSaveDraft={runSaveDraft}
              onSnoozeAlert={runSnoozeAlert}
            />

            <InsightsPanel
              open={insightsOpen}
              onToggle={toggleInsights}
              governance={overviewQuery.data?.governance}
              queueSummary={overviewQuery.data?.queue_summary}
              queueSummaryPrevious={overviewQuery.data?.queue_summary_previous}
              health={overviewQuery.data?.system_health}
              throughput={overviewQuery.data?.throughput}
              criticalBar={overviewQuery.data?.critical_bar}
              criticalBarPrevious={overviewQuery.data?.critical_bar_previous}
              timeRange={range}
              freshness={overviewFreshness}
              loading={overviewQuery.isLoading}
              warning={overviewDegradedNotice}
              onRetryWarning={retryOverviewPanels}
            />
          </div>
        ) : (
          <div className="flex h-full flex-col gap-3">
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
                  onSelectItem={handleMobileQueueSelect}
                  onFiltersChange={(patch) =>
                    applyQueueFilterPatch(
                      patch,
                      isPaginationOnlyPatch(patch)
                        ? "pagination"
                        : "queue_controls",
                    )
                  }
                  onRefresh={refreshQueueAndOverview}
                  canExport={canExportQueue}
                  serverDensityPreference={queueDensityPreference}
                  onDensityPreferenceChange={handleQueueDensityPreferenceChange}
                  onBulkAction={runBulkAction}
                />
              ) : (
                <div className="h-full overflow-auto space-y-3">
                  {overviewDegradedNotice ? (
                    <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                      <span>{overviewDegradedNotice}</span>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        className="h-7 border-amber-300 bg-white px-2 text-xs text-amber-900 hover:bg-amber-100 hover:text-amber-950"
                        onClick={retryOverviewPanels}
                      >
                        Retry overview
                      </Button>
                    </div>
                  ) : null}
                  <GovernancePanel
                    governance={overviewQuery.data?.governance}
                    queueSummary={overviewQuery.data?.queue_summary}
                    health={overviewQuery.data?.system_health}
                    freshness={overviewFreshness}
                    loading={overviewQuery.isLoading}
                  />
                  <TrendStrip
                    queueSummary={overviewQuery.data?.queue_summary}
                    queueSummaryPrevious={
                      overviewQuery.data?.queue_summary_previous
                    }
                    throughput={overviewQuery.data?.throughput}
                    criticalBar={overviewQuery.data?.critical_bar}
                    criticalBarPrevious={
                      overviewQuery.data?.critical_bar_previous
                    }
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
        )}
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
          detailRefreshPending={
            detailQuery.isFetching && !detailQuery.isLoading
          }
          defaultTab={workspaceDefaultTab}
          currentUserId={profile?.userId}
          mobileOpen
          onCloseMobile={() => setMobileWorkspaceOpen(false)}
          onRetryDetail={retryDetailLoad}
          onWorkspaceTabChange={handleWorkspaceTabPreferenceChange}
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
      <DashboardSavedViewsDialog
        open={savedViewsDialogOpen}
        onOpenChange={setSavedViewsDialogOpen}
        views={dashboardSavedViews}
        loading={savedViewsQuery.isLoading}
        currentRole={profile?.role}
        currentFilters={filters}
        currentLayoutPrefs={currentLayoutPrefsForSave}
        activeViewId={activeSavedViewId}
        defaultSavedViewId={
          preferencesQuery.data?.default_saved_view_id ?? null
        }
        onApplyView={(record) => applySavedViewRecord(record, "saved_view")}
        onCreateView={handleCreateSavedView}
        onUpdateView={handleUpdateSavedView}
        onDeleteView={handleDeleteSavedView}
        onSetUserDefaultView={handleSetUserDefaultSavedView}
        pending={savedViewsPending}
      />
    </div>
  );
}

export default DashboardHub;
