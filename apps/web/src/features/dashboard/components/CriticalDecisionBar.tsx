"use client";

import {
  AlertOctagon,
  Clock3,
  DatabaseZap,
  Flag,
  ShieldAlert,
  UserX,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { CriticalDecisionBar as CriticalDecisionBarData } from "@/features/dashboard/types";

export interface CriticalTileFilter {
  queue?: "all" | "alerts" | "cases" | "approvals" | "reg_tasks";
  severity?: "all" | "low" | "medium" | "high" | "critical";
  sla?: "all" | "breached" | "warning" | "ok" | "none";
  search?: string;
  savedView?: "all" | "my_queue" | "team_queue" | "escalations";
}

interface CriticalDecisionBarProps {
  data: CriticalDecisionBarData | undefined;
  loading?: boolean;
  onSelectFilter?: (filter: CriticalTileFilter) => void;
}

function tileTone(value: number, amberThreshold: number, redThreshold: number) {
  if (value >= redThreshold) return "critical";
  if (value >= amberThreshold) return "warning";
  return "ok";
}

function lagTone(minutes: number) {
  if (minutes >= 30) return "critical";
  if (minutes >= 10) return "warning";
  return "ok";
}

function toneClass(tone: "critical" | "warning" | "ok") {
  if (tone === "critical") {
    return "border-risk-critical/40 bg-risk-critical-soft text-risk-critical";
  }
  if (tone === "warning") {
    return "border-risk-high/40 bg-risk-high-soft text-risk-high";
  }
  return "border-risk-clear/40 bg-risk-clear-soft text-risk-clear";
}

export function CriticalDecisionBar({
  data,
  loading = false,
  onSelectFilter,
}: CriticalDecisionBarProps) {
  const safe =
    data ??
    ({
      p1_sla_breaches: 0,
      p2_sla_breaches: 0,
      sanctions_hits_unreviewed: 0,
      sar_due_24h: 0,
      high_risk_cases_unassigned: 0,
      ingestion_lag_minutes: 0,
    } satisfies CriticalDecisionBarData);

  const tiles: Array<{
    id: string;
    label: string;
    value: number;
    icon: typeof AlertOctagon;
    tone: "critical" | "warning" | "ok";
    filter: CriticalTileFilter;
  }> = [
    {
      id: "p1",
      label: "P1 SLA Breached",
      value: safe.p1_sla_breaches,
      icon: AlertOctagon,
      tone: tileTone(safe.p1_sla_breaches, 1, 1),
      filter: {
        queue: "all",
        sla: "breached",
        severity: "critical",
      } as CriticalTileFilter,
    },
    {
      id: "p2",
      label: "P2 SLA Breached",
      value: safe.p2_sla_breaches,
      icon: Clock3,
      tone: tileTone(safe.p2_sla_breaches, 1, 3),
      filter: {
        queue: "all",
        sla: "breached",
        severity: "high",
      } as CriticalTileFilter,
    },
    {
      id: "sanctions",
      label: "Unreviewed Sanctions/PEP",
      value: safe.sanctions_hits_unreviewed,
      icon: ShieldAlert,
      tone: tileTone(safe.sanctions_hits_unreviewed, 1, 5),
      filter: { queue: "alerts", search: "sanctions" } as CriticalTileFilter,
    },
    {
      id: "sar",
      label: "SAR Due <24h",
      value: safe.sar_due_24h,
      icon: Flag,
      tone: tileTone(safe.sar_due_24h, 1, 2),
      filter: {
        queue: "reg_tasks",
        savedView: "escalations",
      } as CriticalTileFilter,
    },
    {
      id: "unassigned",
      label: "High-Risk Unassigned",
      value: safe.high_risk_cases_unassigned,
      icon: UserX,
      tone: tileTone(safe.high_risk_cases_unassigned, 1, 2),
      filter: {
        queue: "cases",
        savedView: "escalations",
      } as CriticalTileFilter,
    },
    {
      id: "lag",
      label: "Ingestion Lag (min)",
      value: safe.ingestion_lag_minutes,
      icon: DatabaseZap,
      tone: lagTone(safe.ingestion_lag_minutes),
      filter: { queue: "all", sla: "warning" } as CriticalTileFilter,
    },
  ];

  return (
    <section className="sticky top-16 z-20 rounded-2xl border border-white/10 bg-[#0b1020]/95 p-3 backdrop-blur-md">
      <div className="grid grid-cols-2 gap-2 lg:grid-cols-3 xl:grid-cols-6">
        {tiles.map((tile) => (
          <button
            key={tile.id}
            type="button"
            onClick={() => onSelectFilter?.(tile.filter)}
            className={cn(
              "rounded-xl border p-3 text-left transition-colors",
              "hover:border-white/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-aurora-500/70",
              toneClass(tile.tone),
            )}
            disabled={loading}
            aria-label={`Filter queue by ${tile.label}`}
          >
            <div className="mb-1 flex items-center justify-between">
              <tile.icon className="h-4 w-4" />
              <span className="text-[10px] uppercase tracking-wide opacity-80">
                {loading ? "..." : tile.value}
              </span>
            </div>
            <p className="text-[11px] font-semibold leading-tight">
              {tile.label}
            </p>
          </button>
        ))}
      </div>
    </section>
  );
}

export default CriticalDecisionBar;
