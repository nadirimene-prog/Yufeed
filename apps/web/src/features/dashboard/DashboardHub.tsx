"use client";

import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { AlertTriangle, Layers3 } from "lucide-react";
import { Button } from "@/components/ui/button";
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

export function DashboardHub() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const profile = getAuthUserProfile();

  const [filters, setFilters] =
    useState<DashboardWorkQueueParams>(defaultQueueFilters);
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [workspaceMessage, setWorkspaceMessage] = useState<string | null>(null);
  const [mobileWorkspaceOpen, setMobileWorkspaceOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  const view = resolveDashboardView(searchParams.get("view"));
  const range = resolveDashboardTimeRange(searchParams.get("range"));
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

  useEffect(() => {
    const media = window.matchMedia("(max-width: 767px)");
    const apply = () => setIsMobile(media.matches);
    apply();
    if (media.addEventListener) {
      media.addEventListener("change", apply);
      return () => media.removeEventListener("change", apply);
    }
    media.addListener(apply);
    return () => media.removeListener(apply);
  }, []);

  const detailQuery = useWorkItemDetail(
    selectedItem?.kind ?? null,
    selectedItem?.record_id ?? null,
    {
      enabled: dashboardEnabled && Boolean(selectedItem),
    },
  );

  const { performAction, reviewAction } = useWorkItemActions(
    selectedItem?.kind ?? null,
    selectedItem?.record_id ?? null,
  );

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
    setFilters((current) => ({
      ...current,
      ...patch,
    }));
  };

  const applyCriticalFilter = (patch: CriticalTileFilter) => {
    setFilters((current) => ({
      ...current,
      page: 1,
      queue: (patch.queue ?? current.queue) as DashboardQueueFilter,
      severity: (patch.severity ?? current.severity) as DashboardSeverityFilter,
      sla: (patch.sla ?? current.sla) as DashboardSlaFilter,
      savedView: (patch.savedView ?? current.savedView) as DashboardSavedView,
      search: patch.search ?? current.search,
    }));
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
      setWorkspaceMessage(result.message);
      await Promise.all([
        queueQuery.refetch(),
        detailQuery.refetch(),
        overviewQuery.refetch(),
      ]);
      if (result.created_case_id) {
        setWorkspaceMessage(`Case created: ${result.created_case_id}`);
      }
    } catch (error) {
      setWorkspaceMessage(parseErrorMessage(error, "Failed to execute action"));
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
      setWorkspaceMessage(result.message);
      await Promise.all([
        queueQuery.refetch(),
        detailQuery.refetch(),
        overviewQuery.refetch(),
      ]);
    } catch (error) {
      setWorkspaceMessage(
        parseErrorMessage(error, "Failed to submit review action"),
      );
    }
  };

  const runBulkAction = async (
    items: DashboardWorkQueueItem[],
    action: "assign" | "escalate" | "mark_in_progress",
  ) => {
    if (items.length === 0) return;

    const fallbackAssignee = profile?.userId ?? selectedItem?.owner ?? "";

    try {
      await Promise.all(
        items.map((item) =>
          apiClient.post(
            `/api/dashboard/work-items/${item.kind}/${item.record_id}/actions`,
            {
              action,
              assignee: action === "assign" ? fallbackAssignee : undefined,
            },
          ),
        ),
      );
      setWorkspaceMessage(`${items.length} item(s) updated.`);
      await Promise.all([queueQuery.refetch(), overviewQuery.refetch()]);
    } catch (error) {
      setWorkspaceMessage(parseErrorMessage(error, "Bulk action failed"));
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
    <div className="space-y-4">
      <section className="rounded-2xl border border-white/10 bg-[#0b1020]/70 p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-xl font-semibold text-white">
              AMLCO Command Center
            </h1>
            <p className="text-sm text-white/60">
              Triage-first control room aligned to maker-checker review and
              defensible investigations.
            </p>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
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
                  aria-selected={option.key === view}
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
          </div>
        </div>

        <div className="mt-3 flex flex-wrap gap-2 text-xs text-white/60">
          <span className="inline-flex items-center gap-1 rounded-lg border border-white/10 bg-white/5 px-2 py-1">
            <Layers3 className="h-3.5 w-3.5" />
            Role view: {view}
          </span>
          <Link
            href="/dashboard?view=operations"
            className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 hover:text-white"
          >
            Operations
          </Link>
          <Link
            href="/dashboard?view=compliance"
            className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 hover:text-white"
          >
            Compliance
          </Link>
          <Link
            href="/dashboard?view=monitoring"
            className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 hover:text-white"
          >
            Monitoring
          </Link>
        </div>
      </section>

      <CriticalDecisionBar
        data={overviewQuery.data?.critical_bar}
        loading={overviewQuery.isLoading}
        onSelectFilter={applyCriticalFilter}
      />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
        <div className="order-1 xl:col-span-5">
          <UnifiedWorkQueue
            key={`${filters.page}-${filters.queue}-${filters.savedView}-${filters.severity}-${filters.sla}-${filters.search}-${filters.jurisdiction}`}
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
              if (isMobile) {
                setMobileWorkspaceOpen(true);
              }
            }}
            onFiltersChange={applyQueueFilterPatch}
            onRefresh={() => {
              queueQuery.refetch();
              overviewQuery.refetch();
            }}
            onBulkAction={runBulkAction}
          />
        </div>

        <div className="order-2 hidden md:block xl:col-span-4">
          <InvestigationWorkspace
            key={`desktop-${selectedItem?.item_id ?? "none"}-${detailQuery.data ? "ready" : "loading"}`}
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
            onAction={runAction}
            onReview={runReview}
          />
        </div>

        <div className="order-3 xl:col-span-3">
          <GovernancePanel
            governance={overviewQuery.data?.governance}
            queueSummary={overviewQuery.data?.queue_summary}
            health={overviewQuery.data?.system_health}
          />
        </div>
      </div>

      <TrendStrip
        queueSummary={overviewQuery.data?.queue_summary}
        throughput={overviewQuery.data?.throughput}
        criticalBar={overviewQuery.data?.critical_bar}
        timeRange={range}
      />

      {isMobile ? (
        <InvestigationWorkspace
          key={`mobile-${selectedItem?.item_id ?? "none"}-${detailQuery.data ? "ready" : "loading"}`}
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
          mobileOpen={mobileWorkspaceOpen}
          onCloseMobile={() => setMobileWorkspaceOpen(false)}
          onAction={runAction}
          onReview={runReview}
        />
      ) : null}
    </div>
  );
}

export default DashboardHub;
