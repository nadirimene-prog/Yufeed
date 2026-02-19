"use client";

import { useId, useMemo, useState } from "react";
import axios from "axios";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StatusIndicator } from "@/components/ui/status-indicator";
import {
  GlassCard,
  GlassCardContent,
  GlassCardHeader,
  GlassCardTitle,
} from "@/components/ui/glass-card";
import apiClient from "@/lib/http";
import { getAuthToken, getAuthUserProfile } from "@/lib/auth";
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
import TrendStrip from "@/features/dashboard/components/TrendStrip";

const VIEW_OPTIONS: Array<{ key: DashboardView; label: string }> = [
  { key: "operations", label: "Operations" },
  { key: "compliance", label: "Compliance" },
  { key: "monitoring", label: "Monitoring" },
];

const RANGE_OPTIONS: DashboardTimeRange[] = ["24h", "7d", "30d"];
const DASHBOARD_V3_ENABLED =
  process.env.NEXT_PUBLIC_DASHBOARD_AMLCO_V3 !== "false";

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
  const dashboardTabsId = useId();

  const view = resolveDashboardView(searchParams.get("view"));
  const range = resolveDashboardTimeRange(searchParams.get("range"));
  const filters = useMemo(
    () => parseFilters(new URLSearchParams(searchParams.toString())),
    [searchParams],
  );

  const hasToken = Boolean(getAuthToken());
  const dashboardEnabled = hasToken && DASHBOARD_V3_ENABLED;

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

  const { performAction, reviewAction, bulkAction, saveDraft } =
    useWorkItemActions(
      selectedItem?.kind ?? null,
      selectedItem?.record_id ?? null,
    );

  const activeViewPanelId = `dashboard-view-panel-${dashboardTabsId}-${view}`;

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

    router.replace(`${pathname}?${params.toString()}`);
  };

  const updateViewRange = (
    nextView: DashboardView = view,
    nextRange: DashboardTimeRange = range,
  ) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("view", nextView);
    params.set("range", nextRange);
    router.replace(`${pathname}?${params.toString()}`);
  };

  const applyQueueFilterPatch = (patch: Partial<DashboardWorkQueueParams>) => {
    updateSearch(patch);
  };

  const applyCriticalFilter = (patch: CriticalTileFilter) => {
    applyQueueFilterPatch({
      page: 1,
      queue: (patch.queue ?? filters.queue) as DashboardQueueFilter,
      severity: (patch.severity ?? filters.severity) as DashboardSeverityFilter,
      sla: (patch.sla ?? filters.sla) as DashboardSlaFilter,
      savedView: (patch.savedView ?? filters.savedView) as DashboardSavedView,
      search: patch.search ?? filters.search,
    });
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
    setWorkspaceMessage(null);
    try {
      const result = await performAction.mutateAsync(payload);
      if (result.created_case_id) {
        setWorkspaceMessage({
          text: `Case created: ${result.created_case_id}`,
          type: "success",
        });
      } else {
        setWorkspaceMessage({ text: result.message, type: "success" });
      }
    } catch (error) {
      setWorkspaceMessage({
        text: parseErrorMessage(error, "Failed to execute action"),
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
    setWorkspaceMessage(null);
    try {
      const result = await reviewAction.mutateAsync(payload);
      setWorkspaceMessage({ text: result.message, type: "success" });
    } catch (error) {
      setWorkspaceMessage({
        text: parseErrorMessage(error, "Failed to submit review action"),
        type: "error",
      });
    }
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
      setWorkspaceMessage({
        text: `${items.length} item(s) updated.`,
        type: "success",
      });
    } catch (error) {
      setWorkspaceMessage({
        text: parseErrorMessage(error, "Bulk action failed"),
        type: "error",
      });
    }
  };

  const runSaveDraft = async (payload: {
    narrative: string;
    notes: string;
  }) => {
    if (!selectedItem) return;
    try {
      await saveDraft.mutateAsync(payload);
      setWorkspaceMessage({ text: "Draft saved.", type: "success" });
    } catch (error) {
      setWorkspaceMessage({
        text: parseErrorMessage(error, "Failed to save draft"),
        type: "error",
      });
    }
  };

  const runSnoozeAlert = async (payload: {
    durationHours: number;
    reason?: string;
  }) => {
    if (!selectedItem || selectedItem.kind !== "alert") return;
    setWorkspaceMessage(null);
    try {
      await apiClient.post(
        `/api/alerts/${encodeURIComponent(selectedItem.ref_id)}/snooze`,
        {
          duration_hours: payload.durationHours,
          reason: payload.reason,
          snoozed_by: profile?.userId ?? undefined,
        },
      );
      setWorkspaceMessage({
        text: `Alert snoozed for ${payload.durationHours}h.`,
        type: "success",
      });
      queueQuery.refetch();
      detailQuery.refetch();
    } catch (error) {
      setWorkspaceMessage({
        text: parseErrorMessage(error, "Failed to snooze alert"),
        type: "error",
      });
    }
  };

  if (!hasToken) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <GlassCard className="max-w-md">
          <GlassCardContent className="py-8 text-center space-y-3">
            <div className="mx-auto h-12 w-12 rounded-full bg-risk-critical-soft text-risk-critical flex items-center justify-center">
              <AlertTriangle className="h-6 w-6" />
            </div>
            <h2 className="text-xl font-semibold text-white">
              Session Required
            </h2>
            <p className="text-sm text-white/60">
              Sign in to access the AMLCO command center.
            </p>
            <Link href="/">
              <Button variant="gradient">Sign In</Button>
            </Link>
          </GlassCardContent>
        </GlassCard>
      </div>
    );
  }

  if (!DASHBOARD_V3_ENABLED) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <GlassCard className="max-w-xl">
          <GlassCardHeader>
            <GlassCardTitle className="text-white">
              AMLCO Command Center V3 Disabled
            </GlassCardTitle>
          </GlassCardHeader>
          <GlassCardContent className="space-y-3">
            <p className="text-sm text-white/70">
              Enable `NEXT_PUBLIC_DASHBOARD_AMLCO_V3` to activate the
              triage-first AMLCO experience.
            </p>
            <Link href="/dashboard?view=operations&range=7d">
              <Button variant="glass">Open Existing Dashboard</Button>
            </Link>
          </GlassCardContent>
        </GlassCard>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col gap-3">
      <section className="sticky top-0 z-20 rounded-2xl border border-white/10 bg-white/[0.03] p-3 backdrop-blur-sm">
        <div className="grid grid-cols-1 gap-2 lg:grid-cols-[1fr_auto_auto] lg:items-center">
          <div>
            <h1 className="text-lg font-semibold text-white">
              AMLCO Command Center
            </h1>
            <p className="text-xs text-white/60">
              Triage, investigate, and execute controlled actions.
            </p>
          </div>

          <div
            className="inline-flex rounded-xl border border-white/10 bg-white/5 p-1"
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
                    ? "rounded-lg bg-aurora-500/20 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-aurora-300"
                    : "rounded-lg px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-white/60 hover:bg-white/5 hover:text-white"
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
              className="h-10 rounded-xl border border-white/10 bg-white/5 px-3 text-sm text-white"
            >
              {RANGE_OPTIONS.map((option) => (
                <option key={option} value={option} className="bg-[#0b1020]">
                  {formatRangeLabel(option)}
                </option>
              ))}
            </select>
            <Button
              variant="glass"
              size="sm"
              onClick={() => {
                overviewQuery.refetch();
                queueQuery.refetch();
                detailQuery.refetch();
              }}
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Refresh
            </Button>
            <StatusIndicator status="live" label="AI Active" size="sm" />
          </div>
        </div>
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
        <div className="hidden h-full gap-3 lg:grid lg:grid-cols-[420px_minmax(0,1fr)_280px]">
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
              setSelectedItemId(item.item_id);
            }}
            onFiltersChange={applyQueueFilterPatch}
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
            onReview={runReview}
            onSaveDraft={runSaveDraft}
            onSnoozeAlert={runSnoozeAlert}
          />

          <div className="min-h-0 space-y-3 overflow-auto">
            <GovernancePanel
              governance={overviewQuery.data?.governance}
              queueSummary={overviewQuery.data?.queue_summary}
              health={overviewQuery.data?.system_health}
              loading={overviewQuery.isLoading}
            />

            <TrendStrip
              queueSummary={overviewQuery.data?.queue_summary}
              throughput={overviewQuery.data?.throughput}
              criticalBar={overviewQuery.data?.critical_bar}
              timeRange={range}
              loading={overviewQuery.isLoading}
            />
          </div>
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
                  setSelectedItemId(item.item_id);
                  setMobileWorkspaceOpen(true);
                }}
                onFiltersChange={applyQueueFilterPatch}
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
                  loading={overviewQuery.isLoading}
                />
                <TrendStrip
                  queueSummary={overviewQuery.data?.queue_summary}
                  throughput={overviewQuery.data?.throughput}
                  criticalBar={overviewQuery.data?.critical_bar}
                  timeRange={range}
                  loading={overviewQuery.isLoading}
                />
              </div>
            )}
          </div>

          <div className="grid grid-cols-3 gap-2 rounded-xl border border-white/10 bg-white/[0.03] p-2">
            <Button
              variant={mobilePanel === "queue" ? "primary" : "glass"}
              size="sm"
              onClick={() => setMobilePanel("queue")}
            >
              Queue
            </Button>
            <Button
              variant="glass"
              size="sm"
              disabled={!selectedItem}
              onClick={() => setMobileWorkspaceOpen(true)}
            >
              Detail
            </Button>
            <Button
              variant={mobilePanel === "governance" ? "primary" : "glass"}
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
          onReview={runReview}
          onSaveDraft={runSaveDraft}
          onSnoozeAlert={runSnoozeAlert}
        />
      ) : null}
    </div>
  );
}

export default DashboardHub;
