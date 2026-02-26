"use client";

import Link from "next/link";
import {
  BarChart3,
  ClipboardCheck,
  FileCheck2,
  FileWarning,
  Shield,
  Users,
} from "lucide-react";
import { Sparkline } from "@/components/ui/sparkline";
import { StatusIndicator } from "@/components/ui/status-indicator";
import {
  DashboardFreshnessMeta,
  DashboardGovernanceSnapshot,
  DashboardQueueSummary,
  SystemHealthSnapshot,
} from "@/features/dashboard/types";
import DataFreshnessBadge from "@/features/dashboard/components/DataFreshnessBadge";

interface GovernancePanelProps {
  governance: DashboardGovernanceSnapshot | undefined;
  queueSummary: DashboardQueueSummary | undefined;
  health: SystemHealthSnapshot | undefined;
  freshness?: DashboardFreshnessMeta | null;
  loading?: boolean;
}

function percent(value: number) {
  return `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`;
}

function riskTone(value: number) {
  if (value >= 0.8) return "critical" as const;
  if (value >= 0.5) return "warning" as const;
  return "ok" as const;
}

function highIsGoodTone(
  value: number,
  warningThreshold: number,
  criticalThreshold: number,
) {
  if (value < criticalThreshold) return "critical" as const;
  if (value < warningThreshold) return "warning" as const;
  return "ok" as const;
}

function lowIsGoodTone(
  value: number,
  warningThreshold: number,
  criticalThreshold: number,
) {
  if (value >= criticalThreshold) return "critical" as const;
  if (value >= warningThreshold) return "warning" as const;
  return "ok" as const;
}

function toneClass(tone: "critical" | "warning" | "ok") {
  if (tone === "critical") return "text-risk-critical";
  if (tone === "warning") return "text-risk-high";
  return "text-risk-clear";
}

function toSparklineData(history?: number[] | null) {
  if (!history || history.length < 2) return null;
  return history.map((value) => ({ value: Math.max(0, value) }));
}

function healthStatusToIndicator(status?: string) {
  const normalized = (status ?? "").toLowerCase();
  if (normalized === "degraded") return "error" as const;
  if (normalized === "warning") return "warning" as const;
  return "success" as const;
}

export function GovernancePanel({
  governance,
  queueSummary,
  health,
  freshness = null,
  loading = false,
}: GovernancePanelProps) {
  const safeGovernance: DashboardGovernanceSnapshot =
    governance ??
    ({
      rule_drift_score: 0,
      alert_to_case_rate: 0,
      fp_proxy_rate: 0,
      audit_completeness_rate: 0,
    } satisfies DashboardGovernanceSnapshot);

  const safeSummary: DashboardQueueSummary =
    queueSummary ??
    ({
      alerts_open: 0,
      cases_open: 0,
      approvals_pending: 0,
      reg_tasks_due: 0,
    } satisfies DashboardQueueSummary);

  const widgets: Array<{
    title: string;
    icon: typeof Shield;
    value: string;
    tone: "critical" | "warning" | "ok";
    href: string;
    history?: { value: number }[] | null;
  }> = [
    {
      title: "Rule Drift",
      icon: Shield,
      value: `${safeGovernance.rule_drift_score.toFixed(1)}%`,
      tone: riskTone(safeGovernance.rule_drift_score / 100),
      href: "/transaction-monitoring/rules",
      history: toSparklineData(safeGovernance.rule_drift_score_history),
    },
    {
      title: "Alert→Case Conversion",
      icon: BarChart3,
      value: percent(safeGovernance.alert_to_case_rate),
      tone: highIsGoodTone(safeGovernance.alert_to_case_rate, 0.2, 0.1),
      href: "/cases",
      history: toSparklineData(safeGovernance.alert_to_case_rate_history),
    },
    {
      title: "False Positive Proxy",
      icon: ClipboardCheck,
      value: percent(safeGovernance.fp_proxy_rate),
      tone: lowIsGoodTone(safeGovernance.fp_proxy_rate, 0.2, 0.35),
      href: "/transaction-alerts",
      history: toSparklineData(safeGovernance.fp_proxy_rate_history),
    },
    {
      title: "Audit Completeness",
      icon: FileCheck2,
      value: percent(safeGovernance.audit_completeness_rate),
      tone: highIsGoodTone(safeGovernance.audit_completeness_rate, 0.9, 0.75),
      href: "/audit",
      history: toSparklineData(safeGovernance.audit_completeness_rate_history),
    },
    {
      title: "Pending Approvals",
      icon: Users,
      value: String(safeSummary.approvals_pending),
      tone: lowIsGoodTone(safeSummary.approvals_pending, 1, 10),
      href: "/cases",
      history: null,
    },
    {
      title: "Reg Tasks Due",
      icon: FileWarning,
      value: String(safeSummary.reg_tasks_due),
      tone: lowIsGoodTone(safeSummary.reg_tasks_due, 1, 5),
      href: "/compliance",
      history: null,
    },
  ];

  return (
    <section
      className="rounded-2xl border border-border bg-white p-3 shadow-sm sm:p-4"
      role="region"
      aria-label="Governance metrics"
    >
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-foreground">
          Governance & Controls
        </h2>
        <DataFreshnessBadge freshness={freshness} label="Updated" compact />
      </div>
      <div className="space-y-2">
        {loading
          ? Array.from({ length: 6 }).map((_, index) => (
              <div
                key={`skeleton-${index}`}
                className="rounded-xl border border-border bg-slate-50 p-2"
              >
                <div className="mb-2 h-3 w-24 animate-pulse rounded bg-slate-200" />
                <div className="h-5 w-16 animate-pulse rounded bg-slate-200" />
              </div>
            ))
          : widgets.map((widget) => (
              <Link
                key={widget.title}
                href={widget.href}
                className="block rounded-xl border border-border bg-slate-50 p-2 transition hover:border-border/60 hover:shadow-[0_2px_8px_-4px_rgba(0,0,0,0.1)]"
                aria-label={`${widget.title} details`}
              >
                <p className="mb-1 flex items-center justify-between text-[10px] uppercase tracking-wide text-muted-foreground">
                  <span className="inline-flex items-center gap-1.5 font-medium">
                    <widget.icon className="h-3.5 w-3.5" aria-hidden="true" />
                    {widget.title}
                  </span>
                  {widget.history ? (
                    <Sparkline
                      data={widget.history}
                      width={56}
                      height={18}
                      color="primary"
                      ariaLabel={`${widget.title} trend`}
                      className="opacity-80"
                    />
                  ) : (
                    <span className="text-[10px] font-medium text-foreground/60">
                      No trend
                    </span>
                  )}
                </p>
                <p
                  className={`text-sm font-semibold ${toneClass(widget.tone)}`}
                >
                  {widget.value}
                </p>
              </Link>
            ))}
      </div>

      <div className="mt-3 rounded-xl border border-border bg-slate-50 p-3 text-xs text-foreground">
        <p className="mb-1 text-[10px] uppercase tracking-wide text-muted-foreground font-medium">
          System health
        </p>
        <StatusIndicator
          status={healthStatusToIndicator(health?.status)}
          label={health?.status ?? "unknown"}
          size="sm"
        />
        <p className="mt-2 text-muted-foreground">
          Stuck alerts: {health?.stuck_alerts ?? 0}
        </p>
        <p className="text-muted-foreground">
          Unprocessed transactions: {health?.unprocessed_transactions ?? 0}
        </p>
      </div>
    </section>
  );
}

export default GovernancePanel;
