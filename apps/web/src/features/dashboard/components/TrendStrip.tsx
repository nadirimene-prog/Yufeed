"use client";

import {
  Activity,
  Clock,
  FileWarning,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
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
}

export function TrendStrip({
  queueSummary,
  throughput,
  criticalBar,
  timeRange,
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

  const cards = [
    {
      id: "backlog",
      label: "Backlog",
      value: q.alerts_open + q.cases_open,
      helper: "alerts + cases",
      icon: Activity,
    },
    {
      id: "sla",
      label: "SLA Breaches",
      value: c.p1_sla_breaches + c.p2_sla_breaches,
      helper: "P1 + P2",
      icon: FileWarning,
    },
    {
      id: "sar",
      label: "SAR Pressure",
      value: q.reg_tasks_due + c.sar_due_24h,
      helper: "due tasks",
      icon: TrendingUp,
    },
    {
      id: "first_action",
      label: "Median First Action",
      value: Math.round(t.median_time_to_first_action_minutes),
      helper: "minutes",
      icon: Clock,
    },
    {
      id: "resolution",
      label: "Median Resolution",
      value: Math.round(t.median_case_resolution_hours),
      helper: "hours",
      icon: TrendingDown,
    },
  ];

  return (
    <section className="glass-surface rounded-2xl border border-white/10 p-3 sm:p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-white">Trend & Throughput</h2>
        <p className="text-xs text-white/60">
          Window: {formatRangeLabel(timeRange)}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-5">
        {cards.map((card) => (
          <div
            key={card.id}
            className="rounded-xl border border-white/10 bg-white/5 p-3"
          >
            <p className="mb-1 flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-white/50">
              <card.icon className="h-3.5 w-3.5" />
              {card.label}
            </p>
            <p className="text-lg font-semibold text-white">{card.value}</p>
            <p className="text-[11px] text-white/60">{card.helper}</p>
            <div className="mt-2 h-1.5 w-full overflow-hidden rounded bg-white/10">
              <div
                className="h-full rounded bg-aurora-400"
                style={{
                  width: `${Math.min(100, Math.max(4, Number(card.value) * 8))}%`,
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export default TrendStrip;
