"use client";

import {
  AlertTriangle,
  CheckCircle2,
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
  if (value >= redThreshold) return "critical" as const;
  if (value >= amberThreshold) return "warning" as const;
  return "ok" as const;
}

function lagTone(minutes: number) {
  if (minutes >= 30) return "critical" as const;
  if (minutes >= 10) return "warning" as const;
  return "ok" as const;
}

function toneClass(tone: "critical" | "warning" | "ok") {
  if (tone === "critical") {
    return "border-risk-critical/50 bg-risk-critical-soft text-risk-critical";
  }
  if (tone === "warning") {
    return "border-risk-high/50 bg-risk-high-soft text-risk-high";
  }
  return "border-risk-clear/50 bg-risk-clear-soft text-risk-clear";
}

function ToneIcon({ tone }: { tone: "critical" | "warning" | "ok" }) {
  if (tone === "critical")
    return <AlertTriangle className="h-4 w-4" aria-hidden="true" />;
  if (tone === "warning")
    return <Clock3 className="h-4 w-4" aria-hidden="true" />;
  return <CheckCircle2 className="h-4 w-4" aria-hidden="true" />;
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
    icon: typeof AlertTriangle;
    tone: "critical" | "warning" | "ok";
    filter: CriticalTileFilter;
    description: string;
  }> = [
    {
      id: "p1",
      label: "P1 SLA Breached",
      value: safe.p1_sla_breaches,
      icon: AlertTriangle,
      tone: tileTone(safe.p1_sla_breaches, 1, 1),
      filter: { queue: "all", sla: "breached", severity: "critical" },
      description: "P1 alerts that exceeded SLA response window.",
    },
    {
      id: "p2",
      label: "P2 SLA Breached",
      value: safe.p2_sla_breaches,
      icon: Clock3,
      tone: tileTone(safe.p2_sla_breaches, 1, 3),
      filter: { queue: "all", sla: "breached", severity: "high" },
      description: "P2 alerts that exceeded SLA response window.",
    },
    {
      id: "sanctions",
      label: "Unreviewed Sanctions/PEP",
      value: safe.sanctions_hits_unreviewed,
      icon: ShieldAlert,
      tone: tileTone(safe.sanctions_hits_unreviewed, 1, 5),
      filter: { queue: "alerts", search: "sanctions" },
      description: "Sanctions/PEP hits pending analyst review.",
    },
    {
      id: "sar",
      label: "SAR Due <24h",
      value: safe.sar_due_24h,
      icon: Flag,
      tone: tileTone(safe.sar_due_24h, 1, 2),
      filter: { queue: "reg_tasks", savedView: "escalations" },
      description: "Regulatory filing items due in the next 24 hours.",
    },
    {
      id: "unassigned",
      label: "High-Risk Unassigned",
      value: safe.high_risk_cases_unassigned,
      icon: UserX,
      tone: tileTone(safe.high_risk_cases_unassigned, 1, 2),
      filter: { queue: "cases", savedView: "escalations" },
      description: "High-risk cases currently unassigned.",
    },
    {
      id: "lag",
      label: "Ingestion Lag (min)",
      value: safe.ingestion_lag_minutes,
      icon: DatabaseZap,
      tone: lagTone(safe.ingestion_lag_minutes),
      filter: { queue: "all", sla: "warning" },
      description: "Data ingestion processing lag in minutes.",
    },
  ];

  return (
    <section
      className="rounded-2xl border border-border bg-white p-3 shadow-sm"
      aria-live="polite"
    >
      <div className="grid grid-cols-3 gap-2 xl:grid-cols-6">
        {(loading
          ? Array.from({ length: 6 }).map((_, i) => ({ id: `skeleton-${i}` }))
          : tiles
        ).map((tile, index) => {
          if (loading) {
            return (
              <div
                key={tile.id}
                className="rounded-xl border border-border bg-slate-50 p-3"
              >
                <div className="mb-2 h-3 w-16 animate-pulse rounded bg-slate-200" />
                <div className="h-6 w-12 animate-pulse rounded bg-slate-200" />
              </div>
            );
          }

          const realTile = tiles[index];
          const isCriticalPulse =
            realTile.tone === "critical" && realTile.value > 0;

          return (
            <button
              key={realTile.id}
              type="button"
              title={realTile.description}
              onClick={() => onSelectFilter?.(realTile.filter)}
              className={cn(
                "rounded-xl border p-3 text-left transition",
                "hover:border-white/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0052FF]/70",
                toneClass(realTile.tone),
                isCriticalPulse && "animate-pulse-soft",
              )}
              aria-label={`Filter queue by ${realTile.label}`}
            >
              <div className="mb-1 flex items-center justify-between">
                <realTile.icon className="h-4 w-4" aria-hidden="true" />
                <ToneIcon tone={realTile.tone} />
              </div>
              <p className="text-[10px] uppercase tracking-wide opacity-85">
                {realTile.label}
              </p>
              <p className="mt-1 text-lg font-semibold leading-none">
                {realTile.value}
              </p>
            </button>
          );
        })}
      </div>
    </section>
  );
}

export default CriticalDecisionBar;
