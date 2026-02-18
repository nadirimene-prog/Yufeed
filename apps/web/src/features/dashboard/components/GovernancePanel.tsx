"use client";

import { ComponentType } from "react";
import { BarChart3, ClipboardCheck, Shield, Timer, Users } from "lucide-react";
import {
  DashboardGovernanceSnapshot,
  DashboardQueueSummary,
  SystemHealthSnapshot,
} from "@/features/dashboard/types";

interface GovernancePanelProps {
  governance: DashboardGovernanceSnapshot | undefined;
  queueSummary: DashboardQueueSummary | undefined;
  health: SystemHealthSnapshot | undefined;
}

function percent(value: number) {
  return `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`;
}

function riskTone(value: number) {
  if (value >= 0.8) return "text-risk-critical";
  if (value >= 0.5) return "text-risk-high";
  return "text-risk-clear";
}

export function GovernancePanel({
  governance,
  queueSummary,
  health,
}: GovernancePanelProps) {
  const safeGovernance: DashboardGovernanceSnapshot = governance ?? {
    rule_drift_score: 0,
    alert_to_case_rate: 0,
    fp_proxy_rate: 0,
    audit_completeness_rate: 0,
  };

  const safeSummary: DashboardQueueSummary = queueSummary ?? {
    alerts_open: 0,
    cases_open: 0,
    approvals_pending: 0,
    reg_tasks_due: 0,
  };

  return (
    <section className="glass-surface rounded-2xl border border-white/10 p-3 sm:p-4">
      <h2 className="mb-3 text-sm font-semibold text-white">
        Governance & Controls
      </h2>

      <div className="space-y-2">
        <Widget
          title="Rule Drift"
          icon={Shield}
          value={`${safeGovernance.rule_drift_score.toFixed(1)}%`}
          tone={riskTone(safeGovernance.rule_drift_score / 100)}
        />
        <Widget
          title="Alert→Case Conversion"
          icon={BarChart3}
          value={percent(safeGovernance.alert_to_case_rate)}
          tone="text-white"
        />
        <Widget
          title="False Positive Proxy"
          icon={ClipboardCheck}
          value={percent(safeGovernance.fp_proxy_rate)}
          tone={riskTone(safeGovernance.fp_proxy_rate)}
        />
        <Widget
          title="Audit Completeness"
          icon={ClipboardCheck}
          value={percent(safeGovernance.audit_completeness_rate)}
          tone={riskTone(1 - safeGovernance.audit_completeness_rate)}
        />
        <Widget
          title="Pending Approvals"
          icon={Users}
          value={String(safeSummary.approvals_pending)}
          tone={
            safeSummary.approvals_pending > 0
              ? "text-risk-high"
              : "text-risk-clear"
          }
        />
        <Widget
          title="Regulatory Tasks Due"
          icon={Timer}
          value={String(safeSummary.reg_tasks_due)}
          tone={
            safeSummary.reg_tasks_due > 0 ? "text-risk-high" : "text-risk-clear"
          }
        />
      </div>

      <div className="mt-3 rounded-xl border border-white/10 bg-white/5 p-3 text-xs text-white/80">
        <p className="mb-1 text-[10px] uppercase tracking-wide text-white/50">
          System health
        </p>
        <p className="font-medium">{health?.status ?? "unknown"}</p>
        <p className="text-white/60">
          Stuck alerts: {health?.stuck_alerts ?? 0}
        </p>
        <p className="text-white/60">
          Unprocessed transactions: {health?.unprocessed_transactions ?? 0}
        </p>
      </div>
    </section>
  );
}

function Widget({
  title,
  icon: Icon,
  value,
  tone,
}: {
  title: string;
  icon: ComponentType<{ className?: string }>;
  value: string;
  tone: string;
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-2">
      <p className="mb-1 flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-white/50">
        <Icon className="h-3.5 w-3.5" />
        {title}
      </p>
      <p className={`text-sm font-semibold ${tone}`}>{value}</p>
    </div>
  );
}

export default GovernancePanel;
