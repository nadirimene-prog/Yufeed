"use client";

import { memo, useState } from "react";
import { BarChart3, ChevronLeft, PanelRight, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import TrendStrip from "@/features/dashboard/components/TrendStrip";
import GovernancePanel from "@/features/dashboard/components/GovernancePanel";
import {
  CriticalDecisionBar,
  DashboardFreshnessMeta,
  DashboardGovernanceSnapshot,
  DashboardQueueSummary,
  DashboardThroughputSnapshot,
  DashboardTimeRange,
  SystemHealthSnapshot,
} from "@/features/dashboard/types";

type InsightsTab = "governance" | "throughput";

interface InsightsPanelProps {
  open: boolean;
  onToggle: () => void;
  governance: DashboardGovernanceSnapshot | undefined;
  queueSummary: DashboardQueueSummary | undefined;
  queueSummaryPrevious?: DashboardQueueSummary | null;
  health: SystemHealthSnapshot | undefined;
  throughput: DashboardThroughputSnapshot | undefined;
  criticalBar: CriticalDecisionBar | undefined;
  criticalBarPrevious?: CriticalDecisionBar | null;
  timeRange: DashboardTimeRange;
  freshness?: DashboardFreshnessMeta | null;
  nowMs?: number | null;
  loading?: boolean;
  warning?: string | null;
  onRetryWarning?: (() => void) | null;
}

export function InsightsPanel({
  open,
  onToggle,
  governance,
  queueSummary,
  queueSummaryPrevious = null,
  health,
  throughput,
  criticalBar,
  criticalBarPrevious = null,
  timeRange,
  freshness = null,
  nowMs = null,
  loading = false,
  warning = null,
  onRetryWarning = null,
}: InsightsPanelProps) {
  const [activeTab, setActiveTab] = useState<InsightsTab>("governance");

  if (!open) {
    return (
      <aside className="hidden h-full min-h-0 lg:flex">
        <div className="flex h-full w-full items-center justify-center rounded-2xl border border-border bg-white p-2 shadow-sm">
          <button
            type="button"
            onClick={onToggle}
            className="inline-flex h-full w-full flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border bg-slate-50 text-muted-foreground transition hover:bg-slate-100 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
            aria-label="Open insights panel"
            aria-expanded={false}
            aria-controls="dashboard-insights-panel"
          >
            <PanelRight className="h-4 w-4" />
            <span className="-rotate-90 whitespace-nowrap text-[11px] font-semibold uppercase tracking-wide">
              Insights
            </span>
          </button>
        </div>
      </aside>
    );
  }

  return (
    <aside
      id="dashboard-insights-panel"
      className="hidden h-full min-h-0 lg:flex lg:flex-col"
      aria-label="Insights panel"
    >
      <div className="mb-2 rounded-2xl border border-border bg-white p-3 shadow-sm">
        <div className="mb-3 flex items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-semibold text-foreground">Insights</h2>
            <p className="text-xs text-muted-foreground">
              Governance and throughput context
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={onToggle}
            aria-label="Collapse insights panel"
            aria-expanded={true}
            aria-controls="dashboard-insights-panel"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
        </div>

        <div
          className="inline-flex w-full rounded-xl border border-border bg-slate-50 p-1"
          role="tablist"
          aria-label="Insights section selector"
        >
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "governance"}
            aria-controls="insights-panel-governance"
            id="insights-tab-governance"
            tabIndex={activeTab === "governance" ? 0 : -1}
            onClick={() => setActiveTab("governance")}
            className={cn(
              "inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold uppercase tracking-wide transition",
              activeTab === "governance"
                ? "bg-white text-primary shadow-sm ring-1 ring-border/50"
                : "text-muted-foreground hover:bg-slate-100 hover:text-foreground",
            )}
          >
            <Shield className="h-3.5 w-3.5" />
            Governance
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "throughput"}
            aria-controls="insights-panel-throughput"
            id="insights-tab-throughput"
            tabIndex={activeTab === "throughput" ? 0 : -1}
            onClick={() => setActiveTab("throughput")}
            className={cn(
              "inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold uppercase tracking-wide transition",
              activeTab === "throughput"
                ? "bg-white text-primary shadow-sm ring-1 ring-border/50"
                : "text-muted-foreground hover:bg-slate-100 hover:text-foreground",
            )}
          >
            <BarChart3 className="h-3.5 w-3.5" />
            Throughput
          </button>
        </div>
      </div>

      {warning ? (
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          <span>{warning}</span>
          {onRetryWarning ? (
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-7 border-amber-300 bg-white px-2 text-xs text-amber-900 hover:bg-amber-100 hover:text-amber-950"
              onClick={onRetryWarning}
            >
              Retry overview
            </Button>
          ) : null}
        </div>
      ) : null}

      <div className="min-h-0 flex-1 overflow-auto">
        {activeTab === "governance" ? (
          <div
            id="insights-panel-governance"
            role="tabpanel"
            aria-labelledby="insights-tab-governance"
            className="h-full"
          >
            <GovernancePanel
              governance={governance}
              queueSummary={queueSummary}
              health={health}
              freshness={freshness}
              nowMs={nowMs}
              loading={loading}
            />
          </div>
        ) : (
          <div
            id="insights-panel-throughput"
            role="tabpanel"
            aria-labelledby="insights-tab-throughput"
            className="h-full"
          >
            <TrendStrip
              queueSummary={queueSummary}
              queueSummaryPrevious={queueSummaryPrevious}
              throughput={throughput}
              criticalBar={criticalBar}
              criticalBarPrevious={criticalBarPrevious}
              timeRange={timeRange}
              freshness={freshness}
              nowMs={nowMs}
              loading={loading}
            />
          </div>
        )}
      </div>
    </aside>
  );
}

export default memo(InsightsPanel);
