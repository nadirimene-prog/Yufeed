"use client";

import { useEffect, useMemo } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  Clock3,
  FolderOpen,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import { useCopilot } from "@/components/aml-officer/copilot-context";
import { LoadingBoundary } from "@/components/shared/LoadingBoundary";
import {
  GlassCard,
  GlassCardContent,
  GlassCardHeader,
  GlassCardTitle,
} from "@/components/ui/glass-card";
import { MetricCard } from "@/components/ui/metric-card";
import DataTable, { type Column } from "@/components/ui/data-table-horizon";
import { Sparkline } from "@/components/ui/sparkline";
import { StatusBadge } from "@/components/ui/badge-horizon";
import { useWorkQueue } from "@/features/dashboard/useWorkQueue";
import { useDashboardOverview } from "@/features/dashboard/useDashboardOverview";
import { useWorkspaceUsers } from "@/hooks/queries/useSpecializedData";
import type { DashboardWorkQueueItem } from "@/features/dashboard/types";

interface AnalystRow {
  analyst: string;
  caseload: number;
  highRisk: number;
  slaBreaches: number;
  sarRequired: number;
  avgRisk: number;
  medianAgeMinutes: number;
  trend: { value: number }[];
}

function percentile(values: number[], p: number) {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.floor((sorted.length - 1) * p);
  return sorted[index] ?? 0;
}

function toTrend(values: number[]) {
  if (values.length === 0) {
    return [{ value: 0 }];
  }

  const bucketSize = Math.max(1, Math.floor(values.length / 7));
  const points: { value: number }[] = [];
  for (let i = 0; i < values.length; i += bucketSize) {
    const slice = values.slice(i, i + bucketSize);
    const avg =
      slice.length === 0
        ? 0
        : slice.reduce((sum, value) => sum + value, 0) / slice.length;
    points.push({ value: Math.round(avg) });
  }

  while (points.length < 7) {
    points.push(points[points.length - 1] ?? { value: 0 });
  }

  return points.slice(0, 7);
}

function aggregateAnalystRows(
  items: DashboardWorkQueueItem[],
  knownAnalysts: string[],
): AnalystRow[] {
  const rows = new Map<
    string,
    {
      ages: number[];
      risks: number[];
      all: DashboardWorkQueueItem[];
    }
  >();

  const analysts = new Set(
    knownAnalysts.map((value) => value.trim()).filter(Boolean),
  );

  for (const item of items) {
    const analyst = (item.owner || "unassigned").trim() || "unassigned";
    analysts.add(analyst);

    if (!rows.has(analyst)) {
      rows.set(analyst, { ages: [], risks: [], all: [] });
    }

    const row = rows.get(analyst);
    if (!row) continue;

    row.ages.push(item.age_minutes);
    row.risks.push(item.risk_score ?? 0);
    row.all.push(item);
  }

  for (const analyst of analysts) {
    if (!rows.has(analyst)) {
      rows.set(analyst, { ages: [], risks: [], all: [] });
    }
  }

  return Array.from(rows.entries())
    .map(([analyst, data]) => {
      const highRisk = data.all.filter((item) => item.risk_score >= 70).length;
      const slaBreaches = data.all.filter(
        (item) => item.sla_status === "breached",
      ).length;
      const sarRequired = data.all.filter((item) => item.sar_required).length;
      const avgRisk =
        data.risks.length === 0
          ? 0
          : data.risks.reduce((sum, value) => sum + value, 0) /
            data.risks.length;

      return {
        analyst,
        caseload: data.all.length,
        highRisk,
        slaBreaches,
        sarRequired,
        avgRisk,
        medianAgeMinutes: percentile(data.ages, 0.5),
        trend: toTrend(data.risks),
      } satisfies AnalystRow;
    })
    .sort((a, b) => {
      if (b.caseload !== a.caseload) return b.caseload - a.caseload;
      return a.analyst.localeCompare(b.analyst);
    });
}

export default function AnalystPerformanceDashboardPage() {
  const { setPageContext } = useCopilot();

  useEffect(() => {
    setPageContext("Operations Dashboard: Analyst performance and throughput");
  }, [setPageContext]);

  const workQueueQuery = useWorkQueue(
    {
      page: 1,
      pageSize: 250,
      queue: "all",
      severity: "all",
      jurisdiction: "",
      sla: "all",
      search: "",
      savedView: "all",
    },
    { enabled: true },
  );
  const overviewQuery = useDashboardOverview("operations", "7d", {
    enabled: true,
  });
  const usersQuery = useWorkspaceUsers();

  const items = useMemo(
    () => workQueueQuery.data?.items ?? [],
    [workQueueQuery.data?.items],
  );

  const analystRows = useMemo(() => {
    const users = (usersQuery.data ?? []).map((user) => user.user_id);
    return aggregateAnalystRows(items, users);
  }, [items, usersQuery.data]);

  const activeAnalysts = analystRows.filter(
    (row) => row.analyst !== "unassigned" && row.caseload > 0,
  ).length;
  const totalCaseload = analystRows.reduce((sum, row) => sum + row.caseload, 0);
  const averageCaseload = activeAnalysts
    ? Math.round(totalCaseload / activeAnalysts)
    : 0;
  const slaBreaches = items.filter(
    (item) => item.sla_status === "breached",
  ).length;
  const slaEligible = items.filter((item) => item.sla_status !== "none").length;
  const slaCompliance = slaEligible
    ? Math.max(0, ((slaEligible - slaBreaches) / slaEligible) * 100)
    : 100;
  const medianResolutionHours =
    overviewQuery.data?.throughput?.median_case_resolution_hours ?? 0;

  const columns = useMemo<Column<AnalystRow>[]>(
    () => [
      {
        key: "analyst",
        header: "Analyst",
        accessor: (row) => (
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-foreground">
              {row.analyst}
            </p>
            <p className="text-xs text-foreground-secondary">Caseload owner</p>
          </div>
        ),
      },
      {
        key: "caseload",
        header: "Caseload",
        sortable: true,
        accessor: (row) => (
          <span className="font-mono text-sm">{row.caseload}</span>
        ),
      },
      {
        key: "highRisk",
        header: "High Risk",
        sortable: true,
        accessor: (row) => (
          <StatusBadge status={row.highRisk > 0 ? "critical" : "approved"}>
            {row.highRisk}
          </StatusBadge>
        ),
      },
      {
        key: "sla",
        header: "SLA Breaches",
        sortable: true,
        accessor: (row) => (
          <StatusBadge status={row.slaBreaches > 0 ? "warning" : "approved"}>
            {row.slaBreaches}
          </StatusBadge>
        ),
      },
      {
        key: "risk",
        header: "Avg Risk",
        sortable: true,
        accessor: (row) => (
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm">{Math.round(row.avgRisk)}</span>
            <Sparkline
              data={row.trend}
              width={60}
              height={20}
              color={
                row.avgRisk >= 70
                  ? "red"
                  : row.avgRisk >= 40
                    ? "orange"
                    : "green"
              }
              ariaLabel={`${row.analyst} risk trend`}
            />
          </div>
        ),
      },
      {
        key: "age",
        header: "Median Age",
        sortable: true,
        accessor: (row) => (
          <span className="text-sm text-foreground-secondary">
            {Math.round(row.medianAgeMinutes)}m
          </span>
        ),
      },
      {
        key: "action",
        header: "Action",
        align: "right",
        accessor: (row) => (
          <Link
            href={`/dashboard?view=operations&search=${encodeURIComponent(row.analyst)}`}
            className="text-sm text-primary hover:underline"
          >
            Open Queue
          </Link>
        ),
      },
    ],
    [],
  );

  return (
    <div className="space-y-6 bg-bg-base text-foreground">
      <header className="space-y-1">
        <h1 className="text-3xl font-display font-semibold">
          Analyst Performance
        </h1>
        <p className="text-foreground-secondary">
          Caseload, throughput, and SLA performance per analyst.
        </p>
      </header>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <MetricCard
          title="Active Analysts"
          value={activeAnalysts}
          color="cyan"
          icon={<UserRound className="h-5 w-5" />}
        />
        <MetricCard
          title="Avg Caseload"
          value={averageCaseload}
          color="aurora"
          icon={<FolderOpen className="h-5 w-5" />}
        />
        <MetricCard
          title="SLA Compliance"
          value={`${slaCompliance.toFixed(1)}%`}
          color={slaCompliance < 85 ? "orange" : "green"}
          icon={<ShieldCheck className="h-5 w-5" />}
          progress={slaCompliance}
        />
        <MetricCard
          title="Median Resolution"
          value={`${Math.round(medianResolutionHours)}h`}
          color={medianResolutionHours > 48 ? "red" : "yellow"}
          icon={<Clock3 className="h-5 w-5" />}
          glow={medianResolutionHours > 72}
        />
      </section>

      <GlassCard>
        <GlassCardHeader className="flex flex-row items-center justify-between gap-2">
          <GlassCardTitle className="text-base">
            Analyst Queue Table
          </GlassCardTitle>
          <StatusBadge
            status={slaBreaches > 0 ? "warning" : "approved"}
            className="capitalize"
          >
            {slaBreaches > 0
              ? `${slaBreaches} SLA breaches in queue`
              : "No SLA breaches"}
          </StatusBadge>
        </GlassCardHeader>
        <GlassCardContent>
          <LoadingBoundary
            loading={
              workQueueQuery.isLoading ||
              overviewQuery.isLoading ||
              usersQuery.isLoading
            }
            error={
              (workQueueQuery.error as Error | undefined) ??
              (overviewQuery.error as Error | undefined) ??
              (usersQuery.error as Error | undefined)
            }
            isEmpty={analystRows.length === 0}
            emptyMessage="No analyst metrics yet"
            emptyDescription="Queue data will appear once work items are created."
            minHeight="260px"
          >
            <DataTable
              data={analystRows}
              columns={columns}
              keyExtractor={(row) => row.analyst}
              pagination
              pageSize={10}
              striped
              bordered
              captionText="Analyst performance metrics table"
              emptyTitle="No analysts found"
              emptyDescription="No active analyst metrics are available for the selected window."
            />
          </LoadingBoundary>
        </GlassCardContent>
      </GlassCard>

      <GlassCard>
        <GlassCardContent className="flex items-start gap-3 text-sm text-foreground-secondary">
          <AlertTriangle
            className="mt-0.5 h-4 w-4 text-risk-high"
            aria-hidden="true"
          />
          <p>
            Throughput metrics are derived from current queue and dashboard
            snapshots. Historical trend contracts can be expanded without
            breaking this page.
          </p>
        </GlassCardContent>
      </GlassCard>
    </div>
  );
}
