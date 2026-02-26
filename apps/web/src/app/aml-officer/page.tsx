"use client";

/**
 * AI AML Officer Dashboard
 *
 * The main dashboard for the AI AML Officer system.
 * RESKINNED: Using Horizon Design System
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Brain,
  AlertTriangle,
  FileSearch,
  MessageSquare,
  Shield,
  Clock,
  CheckCircle,
  Sparkles,
  Calendar,
  Zap,
} from "lucide-react";

import toast from "react-hot-toast";
import amlOfficerApi, { type ProactiveAlert } from "@/lib/aml-officer-api";
import { useAMLOfficerBriefing } from "@/hooks/queries/useAMLOfficerData";
import { LoadingBoundary } from "@/components/shared/LoadingBoundary";
import { MetricCard } from "@/components/ui/metric-card";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { BentoGrid } from "@/components/ui/bento-grid";
import { Button } from "@/components/ui/button";
import { RiskBadge } from "@/components/ui/badge-horizon";
import { StatusIndicator } from "@/components/ui/status-indicator";
import { staggerContainer, staggerItem } from "@/lib/motion";
import { RecentAlertsTable } from "./recent-alerts-table";
import { useCopilot } from "@/components/aml-officer/copilot-context";
import { logger } from "@/lib/logger";

export default function AMLOfficerDashboard() {
  const { data: briefing, isLoading, error, refetch } = useAMLOfficerBriefing();
  const [proactiveAlerts, setProactiveAlerts] = useState<ProactiveAlert[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const fetchProactiveAlerts = async () => {
    try {
      const alertsData = await amlOfficerApi.getProactiveAlerts();
      setProactiveAlerts(alertsData.alerts || []);
    } catch (err) {
      logger.error("Failed to fetch proactive alerts:", err);
      setProactiveAlerts([]);
    } finally {
      setRefreshing(false);
    }
  };

  const { setPageContext } = useCopilot();

  useEffect(() => {
    setPageContext(
      "Daily Briefing Dashboard: Review critical alerts and priority actions.",
    );
    fetchProactiveAlerts();
    return () => setPageContext(""); // Cleanup
  }, [setPageContext]);

  const handleRefresh = () => {
    setRefreshing(true);
    refetch();
    fetchProactiveAlerts();
  };

  const criticalAlerts = briefing?.alerts.critical ?? 0;
  const pendingAlerts = briefing?.alerts.pending ?? 0;
  const openCases = briefing?.cases.open ?? 0;
  const sarPending = briefing?.cases.sar_pending ?? 0;

  const toRiskLevel = (
    severity: string,
  ): "critical" | "high" | "medium" | "low" | "info" => {
    const normalized = severity.toLowerCase();
    if (normalized === "critical") return "critical";
    if (normalized === "high") return "high";
    if (normalized === "medium") return "medium";
    if (normalized === "low") return "low";
    return "info";
  };

  return (
    <LoadingBoundary
      loading={isLoading}
      error={error}
      isEmpty={!briefing}
      loadingMessage="Loading AI AML Officer..."
    >
      <motion.div
        variants={staggerContainer}
        initial="initial"
        animate="animate"
        className="space-y-8"
      >
        {/* ════════════════════════════════════════════════════════════════
          HEADER
          ════════════════════════════════════════════════════════════════ */}
        <motion.header
          variants={staggerItem}
          className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between"
        >
          <div>
            <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-primary">
              <Sparkles className="h-3.5 w-3.5" />
              AI Yufeed
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-foreground font-display">
              AML Officer Cockpit
            </h1>
            <p className="text-muted-foreground mt-2 max-w-2xl">
              Your intelligent compliance partner for daily operations and
              decisioning.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <StatusIndicator status="live" label="AI Active" />
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={refreshing}
            >
              {refreshing ? "Refreshing..." : "Refresh Data"}
            </Button>
          </div>
        </motion.header>

        {/* ════════════════════════════════════════════════════════════════
          METRICS GRID
          ════════════════════════════════════════════════════════════════ */}
        <motion.div variants={staggerItem}>
          <BentoGrid columns={4} gap="md">
            <MetricCard
              title="Critical Alerts"
              value={criticalAlerts}
              icon={<AlertTriangle className="h-5 w-5" />}
              color="red"
              glow={criticalAlerts > 0}
              status={criticalAlerts > 0 ? "error" : "live"}
              trend={{
                direction: criticalAlerts > 0 ? "up" : "neutral",
                value: "Immediate Attention",
              }}
            />
            <MetricCard
              title="Pending Alerts"
              value={pendingAlerts}
              icon={<Clock className="h-5 w-5" />}
              color="yellow"
              trend={{
                direction: "neutral",
                value: "In Queue",
              }}
            />
            <MetricCard
              title="Open Cases"
              value={openCases}
              icon={<FileSearch className="h-5 w-5" />}
              color="blue"
            />
            <MetricCard
              title="SAR Pending"
              value={sarPending}
              icon={<FileSearch className="h-5 w-5" />}
              color="purple"
            />
          </BentoGrid>
        </motion.div>

        {/* ════════════════════════════════════════════════════════════════
          MAIN CONTENT AREA
          ════════════════════════════════════════════════════════════════ */}
        <motion.div
          variants={staggerItem}
          className="grid gap-6 lg:grid-cols-3"
        >
          {/* LEFT COLUMN: Daily Briefing & Actions */}
          <div className="lg:col-span-2 space-y-6">
            {/* Daily Briefing */}
            {briefing && (
              <Card className="relative overflow-hidden border-border shadow-sm bg-white">
                <div className="absolute top-0 right-0 p-4 opacity-5">
                  <Brain className="w-32 h-32 text-primary" />
                </div>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base font-semibold text-foreground">
                    <Sparkles className="w-5 h-5 text-primary" />
                    Daily Briefing
                  </CardTitle>
                  <p className="text-sm text-muted-foreground mt-1">
                    Generated at{" "}
                    {new Date(briefing.generated_at).toLocaleTimeString()}
                  </p>
                </CardHeader>
                <CardContent>
                  <p className="text-foreground text-lg leading-relaxed mb-6">
                    {briefing.narrative.executive_summary}
                  </p>

                  {/* Risk Trend Pill */}
                  <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-50 border border-border">
                    <span className="text-xs uppercase tracking-wider text-muted-foreground">
                      Risk Trend
                    </span>
                    <span className="w-px h-3 bg-border" />
                    <span className="text-sm font-medium capitalize text-foreground">
                      {briefing.risk.trend}
                    </span>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Active Work Queue (RecentAlertsTable) */}
            <div className="h-[400px]">
              <RecentAlertsTable
                data={proactiveAlerts}
                onAction={(alertItem, action) => {
                  // TODO: Implement actual API call to update alert status
                  if (action === "approve") {
                    toast.success("Alert dismissed");
                  } else {
                    toast("Alert escalated", { icon: "⚠️" });
                  }
                }}
              />
            </div>

            {/* Application Quick Links (Compact Row) */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <Link href="/transaction-alerts" className="block group">
                <Card className="h-full border-border shadow-sm bg-white hover:border-primary/50 transition-colors">
                  <CardContent className="p-4 flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-red-50 text-red-600">
                      <AlertTriangle className="w-4 h-4" />
                    </div>
                    <span className="text-sm font-medium text-foreground group-hover:text-red-600 transition-colors">
                      All Alerts
                    </span>
                  </CardContent>
                </Card>
              </Link>

              <Link href="/cases" className="block group">
                <Card className="h-full border-border shadow-sm bg-white hover:border-primary/50 transition-colors">
                  <CardContent className="p-4 flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-blue-50 text-blue-600">
                      <FileSearch className="w-4 h-4" />
                    </div>
                    <span className="text-sm font-medium text-foreground group-hover:text-blue-600 transition-colors">
                      Cases
                    </span>
                  </CardContent>
                </Card>
              </Link>

              <Link href="/aml-officer/ask" className="block group">
                <Card className="h-full border-border shadow-sm bg-white hover:border-primary/50 transition-colors">
                  <CardContent className="p-4 flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-green-50 text-green-600">
                      <MessageSquare className="w-4 h-4" />
                    </div>
                    <span className="text-sm font-medium text-foreground group-hover:text-green-600 transition-colors">
                      Copilot
                    </span>
                  </CardContent>
                </Card>
              </Link>

              <Link href="/aml-officer/sanctions" className="block group">
                <Card className="h-full border-border shadow-sm bg-white hover:border-primary/50 transition-colors">
                  <CardContent className="p-4 flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-red-50 text-red-600">
                      <Shield className="w-4 h-4" />
                    </div>
                    <span className="text-sm font-medium text-foreground group-hover:text-red-600 transition-colors">
                      Sanctions
                    </span>
                  </CardContent>
                </Card>
              </Link>
            </div>
          </div>

          {/* RIGHT COLUMN: AI Capabilities & Context */}
          <div className="space-y-6">
            {/* Priority Actions */}
            {briefing &&
              briefing.recommendations.priority_actions.length > 0 && (
                <Card className="border-border shadow-sm bg-white">
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2 font-semibold text-foreground">
                      <CheckCircle className="w-4 h-4 text-green-500" />
                      Priority Actions
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3 pt-0">
                    {briefing.recommendations.priority_actions.map(
                      (action, index) => (
                        <div
                          key={index}
                          className="flex gap-3 text-sm p-2 rounded-lg hover:bg-slate-50 transition-colors"
                        >
                          <span className="flex-shrink-0 w-5 h-5 bg-primary text-white rounded-full flex items-center justify-center text-[10px] font-bold">
                            {index + 1}
                          </span>
                          <span className="text-foreground">{action}</span>
                        </div>
                      ),
                    )}
                  </CardContent>
                </Card>
              )}

            {/* AI Detected Risks */}
            <Card className="h-fit border-border shadow-sm bg-white">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2 font-semibold text-foreground">
                  <Zap className="w-4 h-4 text-primary" />
                  AI Detected Risks
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 pt-0">
                {proactiveAlerts.length === 0 ? (
                  <div className="text-center py-6 text-muted-foreground text-sm">
                    No proactive alerts detected.
                  </div>
                ) : (
                  proactiveAlerts.map((alert, index) => (
                    <div
                      key={index}
                      className={`p-3 rounded-lg border border-border bg-slate-50`}
                    >
                      <div className="flex justify-between items-start mb-1">
                        <RiskBadge
                          level={toRiskLevel(alert.severity)}
                          className="text-[10px] font-bold uppercase"
                        >
                          {alert.severity}
                        </RiskBadge>
                      </div>
                      <p className="text-sm font-medium text-foreground mb-1">
                        {alert.message}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {alert.recommendation}
                      </p>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>

            {/* Regulations */}
            {briefing && briefing.regulatory.upcoming_deadlines.length > 0 && (
              <Card className="border-border shadow-sm bg-white">
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2 font-semibold text-foreground">
                    <Calendar className="w-4 h-4 text-primary" />
                    Up Next
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  {briefing.regulatory.upcoming_deadlines.map(
                    (deadline, index) => (
                      <div
                        key={index}
                        className="py-2 border-b border-border last:border-0"
                      >
                        <p className="text-sm text-foreground">
                          {deadline.title}
                        </p>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {deadline.days_remaining} days remaining
                        </p>
                      </div>
                    ),
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </motion.div>
      </motion.div>
    </LoadingBoundary>
  );
}
