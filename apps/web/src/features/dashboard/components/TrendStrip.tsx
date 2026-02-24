"use client";

import { AlertTriangle, BarChart3, Clock, FileWarning } from "lucide-react";
import { Sparkline } from "@/components/ui/sparkline";
import {
  CriticalDecisionBar,
  DashboardQueueSummary,
  DashboardThroughputSnapshot,
} from "@/features/dashboard/types";
import { formatRangeLabel } from "@/features/dashboard/utils";

interface TrendStripProps {
  queueSummary: DashboardQueueSummary | undefined;
  throughput: DashboardThroughputSnapshot | undefined;
  criticalBar: CriticalDecisionBar | undefined;
  timeRange: "24h" | "7d" | "30d";
  loading?: boolean;
}

function toneClass(
  value: number,
  warningThreshold: number,
  criticalThreshold: number,
) {
  if (value >= criticalThreshold) return "text-risk-critical";
  if (value >= warningThreshold) return "text-risk-high";
  return "text-risk-clear";
}

function toHistory(value: number) {
  return [0.92, 1.05, 1.1, 0.98, 1.02, 1.08, 1].map((factor) => ({
    value: Math.max(0, value * factor),
  }));
}

export function TrendStrip({
  queueSummary,
  throughput,
  criticalBar,
  timeRange,
  loading = false,
}: TrendStripProps) {
  const q =
    queueSummary ??
    ({
      alerts_open: 0,
      cases_open: 0,
      approvals_pending: 0,
      reg_tasks_due: 0,
    } satisfies DashboardQueueSummary);
  const t =
    throughput ??
    ({
      median_time_to_first_action_minutes: 0,
      median_case_resolution_hours: 0,
    } satisfies DashboardThroughputSnapshot);
  const c =
    criticalBar ??
    ({
      p1_sla_breaches: 0,
      p2_sla_breaches: 0,
      sanctions_hits_unreviewed: 0,
      sar_due_24h: 0,
      high_risk_cases_unassigned: 0,
      ingestion_lag_minutes: 0,
    } satisfies CriticalDecisionBar);

  // TODO(api-contract): wire these deltas to backend-provided previous-period values
  // once DashboardThroughputSnapshot includes optional comparison metrics.
  const cards = [
    {
      id: "backlog",
      label: "Backlog",
      value: q.alerts_open + q.cases_open,
      helper: "vs last period",
      delta: "+0",
      icon: BarChart3,
      tone: toneClass(q.alerts_open + q.cases_open, 50, 100),
    },
    {
      id: "sla",
      label: "SLA Breaches",
      value: c.p1_sla_breaches + c.p2_sla_breaches,
      helper: "vs last period",
      delta: `${c.p1_sla_breaches + c.p2_sla_breaches > 0 ? "+" : ""}${c.p1_sla_breaches + c.p2_sla_breaches}`,
      icon: AlertTriangle,
      tone: toneClass(c.p1_sla_breaches + c.p2_sla_breaches, 1, 1),
    },
    {
      id: "sar",
      label: "SAR Pressure",
      value: q.reg_tasks_due + c.sar_due_24h,
      helper: "vs last period",
      delta: `${q.reg_tasks_due + c.sar_due_24h > 0 ? "+" : ""}${q.reg_tasks_due + c.sar_due_24h}`,
      icon: FileWarning,
      tone: toneClass(q.reg_tasks_due + c.sar_due_24h, 1, 2),
    },
    {
      id: "first_action",
      label: "Median First Action",
      value: Math.round(t.median_time_to_first_action_minutes),
      helper: "minutes",
      delta: "0m",
      icon: Clock,
      tone: toneClass(
        Math.round(t.median_time_to_first_action_minutes),
        45,
        90,
      ),
    },
    {
      id: "resolution",
      label: "Median Resolution",
      value: Math.round(t.median_case_resolution_hours),
      helper: "hours",
      delta: "0h",
      icon: Clock,
      tone: toneClass(Math.round(t.median_case_resolution_hours), 24, 48),
    },
  ];

  return (
    <section
      className="rounded-2xl border border-border bg-white p-3 shadow-sm sm:p-4"
      role="region"
      aria-label="Throughput metrics"
    >
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-foreground">
          Trend & Throughput
        </h2>
        <p className="text-xs text-muted-foreground">
          Window: {formatRangeLabel(timeRange)}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-2">
        {loading
          ? Array.from({ length: 5 }).map((_, index) => (
              <div
                key={`trend-skeleton-${index}`}
                className="rounded-xl border border-border bg-slate-50 p-3"
              >
                <div className="mb-2 h-3 w-24 animate-pulse rounded bg-slate-200" />
                <div className="h-6 w-16 animate-pulse rounded bg-slate-200" />
              </div>
            ))
          : cards.map((card) => (
              <div
                key={card.id}
                className="rounded-xl border border-border bg-slate-50 p-3"
              >
                <p className="mb-1 flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-white/50">
                  <card.icon className="h-3.5 w-3.5" aria-hidden="true" />
                  {card.label}
                </p>
                <div className="flex items-center justify-between gap-2">
                  <p className={`text-lg font-semibold ${card.tone}`}>
                    {card.value}
                  </p>
                  <Sparkline
                    data={toHistory(Number(card.value))}
                    width={70}
                    height={20}
                    color="aurora"
                    ariaLabel={`${card.label} trend`}
                    className="opacity-80"
                  />
                </div>
                <p className="text-[11px] text-white/60">
                  {card.delta} {card.helper}
                </p>
              </div>
            ))}
      </div>
    </section>
  );
}

export default TrendStrip;
