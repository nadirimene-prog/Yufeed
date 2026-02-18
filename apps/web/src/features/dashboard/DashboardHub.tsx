"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  Activity,
  AlertTriangle,
  Clock,
  FileSearch,
  FolderOpen,
  Gauge,
  Layers3,
  Route,
  ShieldAlert,
} from "lucide-react";
import { MetricCard } from "@/components/ui/metric-card";
import {
  GlassCard,
  GlassCardContent,
  GlassCardHeader,
  GlassCardTitle,
} from "@/components/ui/glass-card";
import WorkbenchLayout from "@/components/workbench/WorkbenchLayout";
import { Button } from "@/components/ui/button";
import { getAuthToken } from "@/lib/auth";
import {
  DashboardOverviewResponse,
  DashboardTimeRange,
  DashboardView,
} from "@/features/dashboard/types";
import { useDashboardOverview } from "@/features/dashboard/useDashboardOverview";
import {
  formatRangeLabel,
  resolveDashboardTimeRange,
  resolveDashboardView,
  severityBadgeClass,
} from "@/features/dashboard/utils";
import { cn } from "@/lib/utils";

const VIEW_OPTIONS: Array<{ key: DashboardView; label: string }> = [
  { key: "operations", label: "Operations" },
  { key: "compliance", label: "Compliance" },
  { key: "monitoring", label: "Monitoring" },
];

const RANGE_OPTIONS: DashboardTimeRange[] = ["24h", "7d", "30d"];
const DASHBOARD_V2_ENABLED = process.env.NEXT_PUBLIC_DASHBOARD_V2 !== "false";

export function DashboardHub() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const view = resolveDashboardView(searchParams.get("view"));
  const range = resolveDashboardTimeRange(searchParams.get("range"));
  const hasToken = Boolean(getAuthToken());

  const { data, isLoading, isError, error } = useDashboardOverview(
    view,
    range,
    {
      enabled: hasToken && DASHBOARD_V2_ENABLED,
    },
  );

  const updateFilters = (
    nextView: DashboardView = view,
    nextRange: DashboardTimeRange = range,
  ) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("view", nextView);
    params.set("range", nextRange);
    router.replace(`${pathname}?${params.toString()}`);
  };

  if (!hasToken) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <GlassCard className="max-w-md">
          <GlassCardContent className="py-8 text-center space-y-3">
            <div className="mx-auto h-12 w-12 rounded-full bg-risk-critical-soft text-risk-critical flex items-center justify-center">
              <ShieldAlert className="h-6 w-6" />
            </div>
            <h2 className="text-xl font-semibold text-white">
              Session Required
            </h2>
            <p className="text-sm text-white/60">
              Sign in to access the dashboard command center.
            </p>
            <Link href="/">
              <Button variant="gradient">Sign In</Button>
            </Link>
          </GlassCardContent>
        </GlassCard>
      </div>
    );
  }

  if (!DASHBOARD_V2_ENABLED) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <GlassCard className="max-w-xl">
          <GlassCardContent className="py-8 space-y-3 text-center">
            <h2 className="text-xl font-semibold text-white">
              Dashboard V2 Disabled
            </h2>
            <p className="text-sm text-white/60">
              `NEXT_PUBLIC_DASHBOARD_V2` is disabled for this environment.
            </p>
            <div className="flex justify-center">
              <Link href="/compliance">
                <Button variant="glass">Open Compliance</Button>
              </Link>
            </div>
          </GlassCardContent>
        </GlassCard>
      </div>
    );
  }

  return (
    <WorkbenchLayout
      title="Unified Dashboard Hub"
      discoveryRail={
        <AlertQueuePanel data={data} loading={isLoading} error={isError} />
      }
      workspace={
        <div className="space-y-6">
          <DashboardToolbar
            view={view}
            range={range}
            onViewChange={(next) => updateFilters(next, range)}
            onRangeChange={(next) => updateFilters(view, next)}
          />

          {isLoading ? (
            <LoadingState />
          ) : isError ? (
            <ErrorState
              message={
                error instanceof Error
                  ? error.message
                  : "Failed to load dashboard"
              }
            />
          ) : (
            <DashboardBody data={data} range={range} />
          )}
        </div>
      }
      intelligencePanel={
        <HealthAndContextPanel data={data} loading={isLoading} range={range} />
      }
    />
  );
}

function DashboardToolbar({
  view,
  range,
  onViewChange,
  onRangeChange,
}: {
  view: DashboardView;
  range: DashboardTimeRange;
  onViewChange: (view: DashboardView) => void;
  onRangeChange: (range: DashboardTimeRange) => void;
}) {
  const quickActions = [
    { href: "/transaction-alerts", label: "Alert Queue", icon: AlertTriangle },
    { href: "/cases", label: "Case Workspace", icon: FileSearch },
    {
      href: "/transaction-monitoring/rules",
      label: "Rule Tuning",
      icon: Route,
    },
  ];

  return (
    <div className="rounded-2xl border border-white/10 bg-void-925/30 backdrop-blur-md p-4">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="space-y-2">
          <h1 className="text-xl font-semibold text-white">Command Center</h1>
          <p className="text-sm text-white/60">
            Role-aware overview with live queues and health context.
          </p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div
            className="inline-flex rounded-xl border border-white/10 bg-white/5 p-1"
            role="tablist"
            aria-label="Dashboard view selector"
          >
            {VIEW_OPTIONS.map((option) => (
              <button
                key={option.key}
                onClick={() => onViewChange(option.key)}
                role="tab"
                aria-selected={option.key === view}
                className={cn(
                  "rounded-lg px-3 py-1.5 text-xs font-semibold uppercase tracking-wide transition-colors",
                  option.key === view
                    ? "bg-aurora-500/20 text-aurora-300"
                    : "text-white/55 hover:text-white hover:bg-white/5",
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
          <select
            value={range}
            onChange={(event) =>
              onRangeChange(event.target.value as DashboardTimeRange)
            }
            aria-label="Dashboard time range"
            className="h-10 rounded-xl border border-white/10 bg-white/5 px-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-aurora-500/40"
          >
            {RANGE_OPTIONS.map((option) => (
              <option key={option} value={option} className="bg-[#0a0a12]">
                {formatRangeLabel(option)}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {quickActions.map((action) => (
          <Link key={action.href} href={action.href}>
            <Button variant="glass" size="sm">
              <action.icon className="h-3.5 w-3.5 mr-1.5" />
              {action.label}
            </Button>
          </Link>
        ))}
      </div>
    </div>
  );
}

function DashboardBody({
  data,
  range,
}: {
  data: DashboardOverviewResponse | undefined;
  range: DashboardTimeRange;
}) {
  if (!data) {
    return <ErrorState message="No dashboard data received." />;
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <MetricCard
          title="Pending Alerts"
          value={data.kpis.pending_alerts}
          icon={<AlertTriangle className="h-5 w-5" />}
          color="red"
          status="live"
        />
        <MetricCard
          title="Critical Alerts"
          value={data.kpis.critical_alerts}
          icon={<ShieldAlert className="h-5 w-5" />}
          color="orange"
          status="live"
        />
        <MetricCard
          title="Open Cases"
          value={data.kpis.open_cases}
          icon={<FolderOpen className="h-5 w-5" />}
          color="aurora"
        />
        <MetricCard
          title={`Transactions (${range})`}
          value={data.kpis.transactions_in_range}
          icon={<Layers3 className="h-5 w-5" />}
          color="cyan"
        />
      </div>

      <GlassCard variant="surface">
        <GlassCardHeader>
          <GlassCardTitle className="text-white">Active Cases</GlassCardTitle>
        </GlassCardHeader>
        <GlassCardContent>
          {data.queues.cases.length === 0 ? (
            <p className="text-sm text-white/60">No active cases.</p>
          ) : (
            <ul className="space-y-2">
              {data.queues.cases.map((caseItem) => (
                <li
                  key={caseItem.id}
                  className="rounded-xl border border-white/10 bg-white/5 p-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1 min-w-0">
                      <p className="text-sm font-semibold text-white truncate">
                        {caseItem.title}
                      </p>
                      <p className="text-xs text-white/60">
                        {caseItem.case_id} • {caseItem.status}
                      </p>
                    </div>
                    <span className="text-xs rounded-full px-2 py-1 bg-aurora-500/10 text-aurora-300 border border-aurora-500/30">
                      {caseItem.priority}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </GlassCardContent>
      </GlassCard>
    </div>
  );
}

function AlertQueuePanel({
  data,
  loading,
  error,
}: {
  data: DashboardOverviewResponse | undefined;
  loading: boolean;
  error: boolean;
}) {
  return (
    <div className="space-y-3">
      <div className="px-2">
        <h3 className="text-[10px] font-bold uppercase tracking-widest text-white/40">
          Prioritized Alerts
        </h3>
      </div>
      {loading ? (
        <LoadingList />
      ) : error ? (
        <p className="px-2 text-xs text-risk-critical">
          Unable to load alerts.
        </p>
      ) : data?.queues.alerts.length ? (
        <ul className="space-y-2 px-2">
          {data.queues.alerts.map((item) => (
            <li
              key={item.id}
              className="rounded-xl border border-white/10 bg-white/5 p-3 space-y-1"
            >
              <div className="flex items-start justify-between gap-3">
                <p className="text-xs font-semibold text-white truncate">
                  {item.alert_type.replaceAll("_", " ")}
                </p>
                <span
                  className={cn(
                    "text-[10px] rounded-full px-2 py-0.5",
                    severityBadgeClass(item.severity),
                  )}
                >
                  {item.severity}
                </span>
              </div>
              <p className="text-[11px] text-white/60 truncate">
                {item.alert_id}
              </p>
              <p className="text-[10px] text-white/45">
                Priority {item.priority} • User {item.user_id}
              </p>
              <Link
                href={`/transaction-alerts/${item.id}`}
                className="inline-flex text-[10px] text-cyan-300 hover:text-cyan-200"
              >
                Open alert details
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <p className="px-2 text-xs text-white/60">No alerts in this range.</p>
      )}
    </div>
  );
}

function HealthAndContextPanel({
  data,
  loading,
  range,
}: {
  data: DashboardOverviewResponse | undefined;
  loading: boolean;
  range: DashboardTimeRange;
}) {
  if (loading) {
    return <LoadingList />;
  }

  return (
    <div className="space-y-4">
      <GlassCard variant="surface">
        <GlassCardHeader>
          <GlassCardTitle className="text-white flex items-center gap-2">
            <Activity className="h-4 w-4 text-cyan-400" />
            System Health
          </GlassCardTitle>
        </GlassCardHeader>
        <GlassCardContent className="space-y-3">
          <div className="rounded-lg border border-white/10 bg-white/5 px-3 py-2">
            <p className="text-xs text-white/55">Status</p>
            <p
              className={cn(
                "text-sm font-semibold",
                data?.system_health.status === "healthy"
                  ? "text-risk-low"
                  : data?.system_health.status === "warning"
                    ? "text-risk-medium"
                    : "text-risk-critical",
              )}
            >
              {data?.system_health.status ?? "unknown"}
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <StatChip
              label="Stuck Alerts"
              value={data?.system_health.stuck_alerts ?? 0}
            />
            <StatChip
              label="Unprocessed Txns"
              value={data?.system_health.unprocessed_transactions ?? 0}
            />
          </div>
        </GlassCardContent>
      </GlassCard>

      <GlassCard variant="surface">
        <GlassCardHeader>
          <GlassCardTitle className="text-white flex items-center gap-2">
            <Gauge className="h-4 w-4 text-aurora-300" />
            Context ({formatRangeLabel(range)})
          </GlassCardTitle>
        </GlassCardHeader>
        <GlassCardContent className="space-y-2">
          <StatChip
            label="Avg Risk Score"
            value={data?.kpis.average_risk_score ?? 0}
          />
          <StatChip
            label="Alerts Pending"
            value={data?.badges.alerts_pending ?? 0}
          />
          <StatChip label="Cases Open" value={data?.badges.cases_open ?? 0} />
        </GlassCardContent>
      </GlassCard>
    </div>
  );
}

function StatChip({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/5 px-3 py-2">
      <p className="text-[11px] text-white/55">{label}</p>
      <p className="text-sm font-semibold text-white">{value}</p>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
      {[1, 2, 3, 4].map((idx) => (
        <div key={idx} className="h-36 rounded-xl bg-white/5 animate-pulse" />
      ))}
    </div>
  );
}

function LoadingList() {
  return (
    <div className="space-y-2 px-2">
      {[1, 2, 3].map((idx) => (
        <div key={idx} className="h-20 rounded-xl bg-white/5 animate-pulse" />
      ))}
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-2xl border border-risk-critical/30 bg-risk-critical-soft p-5 text-risk-critical">
      <div className="flex items-center gap-2">
        <Clock className="h-4 w-4" />
        <span className="text-sm font-semibold">Dashboard Error</span>
      </div>
      <p className="mt-2 text-sm text-white/70">{message}</p>
    </div>
  );
}

export default DashboardHub;
