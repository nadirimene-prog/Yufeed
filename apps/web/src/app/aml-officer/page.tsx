"use client";

/**
 * AI AML Officer Dashboard
 *
 * The main dashboard for the AI AML Officer system.
 * RESKINNED: Using Sentinel Design System (Glass/Dark Mode)
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
    XCircle,
    ArrowRight,
    Sparkles,
    Calendar,
    Zap,
} from "lucide-react";

import amlOfficerApi, {
    DailyBriefing,
    ProactiveAlert,
    AMLOfficerCapabilities,
} from "@/lib/aml-officer-api";
import { MetricCard } from "@/components/ui/metric-card";
import { GlassCard, GlassCardHeader, GlassCardTitle, GlassCardContent } from "@/components/ui/glass-card";
import { BentoGrid, BentoItem } from "@/components/ui/bento-grid";
import { Button } from "@/components/ui/button";
import { StatusIndicator } from "@/components/ui/status-indicator";
import { staggerContainer, staggerItem } from "@/lib/motion";
import { RecentAlertsTable } from "./recent-alerts-table";
import { useCopilot } from "@/components/aml-officer/copilot-context";

export default function AMLOfficerDashboard() {
    const [briefing, setBriefing] = useState<DailyBriefing | null>(null);
    const [proactiveAlerts, setProactiveAlerts] = useState<ProactiveAlert[]>([]);
    const [capabilities, setCapabilities] =
        useState<AMLOfficerCapabilities | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [refreshing, setRefreshing] = useState(false);

    const fetchData = async () => {
        try {
            setError(null);
            const [briefingData, alertsData, capabilitiesData] = await Promise.all([
                amlOfficerApi.getDailyBriefing().catch(() => null),
                amlOfficerApi.getProactiveAlerts().catch(() => ({ alerts: [] })),
                amlOfficerApi.getCapabilities().catch(() => null),
            ]);

            if (briefingData) setBriefing(briefingData);
            setProactiveAlerts(alertsData.alerts || []);
            if (capabilitiesData) setCapabilities(capabilitiesData);
        } catch (err) {
            setError("Failed to load dashboard data");
            console.error(err);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    const { setPageContext } = useCopilot();

    useEffect(() => {
        setPageContext("Daily Briefing Dashboard: Review critical alerts and priority actions.");
        fetchData();
        return () => setPageContext(""); // Cleanup
    }, [setPageContext]);

    const handleRefresh = () => {
        setRefreshing(true);
        fetchData();
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center">
                    <Brain className="w-16 h-16 text-[var(--color-aurora-500)] mx-auto animate-pulse" />
                    <p className="mt-4 text-white/50">Loading AI AML Officer...</p>
                </div>
            </div>
        );
    }

    const criticalAlerts = briefing?.alerts.critical ?? 0;
    const pendingAlerts = briefing?.alerts.pending ?? 0;
    const openCases = briefing?.cases.open ?? 0;
    const sarPending = briefing?.cases.sar_pending ?? 0;

    return (
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
                    <div className="flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-[#00d4ff]/70 mb-2">
                        <Sparkles className="h-3.5 w-3.5" />
                        AI Sentinel
                    </div>
                    <h1 className="text-3xl font-bold tracking-tight text-white font-display">
                        Note: Page Reskin In Progress
                    </h1>
                    <h1 className="text-3xl font-bold tracking-tight text-white font-display">
                        AML Officer Cockpit
                    </h1>
                    <p className="text-white/50 mt-2 max-w-2xl">
                        Your intelligent compliance partner for daily operations and decisioning.
                    </p>
                </div>

                <div className="flex items-center gap-3">
                    <StatusIndicator status="live" label="AI Active" />
                    <Button
                        variant="glass"
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
                            value: "Immediate Attention"
                        }}
                    />
                    <MetricCard
                        title="Pending Alerts"
                        value={pendingAlerts}
                        icon={<Clock className="h-5 w-5" />}
                        color="yellow"
                        trend={{
                            direction: "neutral",
                            value: "In Queue"
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
            <motion.div variants={staggerItem} className="grid gap-6 lg:grid-cols-3">

                {/* LEFT COLUMN: Daily Briefing & Actions */}
                <div className="lg:col-span-2 space-y-6">

                    {/* Daily Briefing */}
                    {briefing && (
                        <GlassCard className="relative overflow-hidden">
                            <div className="absolute top-0 right-0 p-4 opacity-10">
                                <Brain className="w-32 h-32 text-[var(--color-aurora-500)]" />
                            </div>
                            <GlassCardHeader>
                                <GlassCardTitle className="flex items-center gap-2">
                                    <Sparkles className="w-5 h-5 text-[var(--color-aurora-500)]" />
                                    Daily Briefing
                                </GlassCardTitle>
                                <p className="text-sm text-white/40 mt-1">
                                    Generated at {new Date(briefing.generated_at).toLocaleTimeString()}
                                </p>
                            </GlassCardHeader>
                            <GlassCardContent>
                                <p className="text-white/80 text-lg leading-relaxed mb-6">
                                    {briefing.narrative.executive_summary}
                                </p>

                                {/* Risk Trend Pill */}
                                <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10">
                                    <span className="text-xs uppercase tracking-wider text-white/50">Risk Trend</span>
                                    <span className="w-px h-3 bg-white/20" />
                                    <span className="text-sm font-medium capitalize text-white">
                                        {briefing.risk.trend}
                                    </span>
                                </div>
                            </GlassCardContent>
                        </GlassCard>
                    )}

                    {/* Active Work Queue (RecentAlertsTable) */}
                    <div className="h-[400px]">
                        <RecentAlertsTable
                            data={proactiveAlerts}
                            onAction={(alert, action) => {
                                console.log(`Action ${action} on alert`, alert);
                                // Future: Implement actual API call here
                                alert(action === "approve" ? "Alert dismissed" : "Alert escalated");
                            }}
                        />
                    </div>

                    {/* Application Quick Links (Compact Row) */}
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                        <Link href="/transaction-alerts" className="block group">
                            <GlassCard variant="interactive" hover className="h-full">
                                <GlassCardContent className="p-4 flex items-center gap-3">
                                    <div className="p-2 rounded-lg bg-[var(--color-risk-high-soft)] text-[var(--color-risk-high)]">
                                        <AlertTriangle className="w-4 h-4" />
                                    </div>
                                    <span className="text-sm font-medium text-white group-hover:text-[var(--color-risk-high)] transition-colors">
                                        All Alerts
                                    </span>
                                </GlassCardContent>
                            </GlassCard>
                        </Link>

                        <Link href="/cases" className="block group">
                            <GlassCard variant="interactive" hover className="h-full">
                                <GlassCardContent className="p-4 flex items-center gap-3">
                                    <div className="p-2 rounded-lg bg-[var(--color-info-soft)] text-[var(--color-info)]">
                                        <FileSearch className="w-4 h-4" />
                                    </div>
                                    <span className="text-sm font-medium text-white group-hover:text-[var(--color-info)] transition-colors">
                                        Cases
                                    </span>
                                </GlassCardContent>
                            </GlassCard>
                        </Link>

                        <Link href="/aml-officer/ask" className="block group">
                            <GlassCard variant="interactive" hover className="h-full">
                                <GlassCardContent className="p-4 flex items-center gap-3">
                                    <div className="p-2 rounded-lg bg-[var(--color-risk-low-soft)] text-[var(--color-risk-low)]">
                                        <MessageSquare className="w-4 h-4" />
                                    </div>
                                    <span className="text-sm font-medium text-white group-hover:text-[var(--color-risk-low)] transition-colors">
                                        Copilot
                                    </span>
                                </GlassCardContent>
                            </GlassCard>
                        </Link>

                        <Link href="/aml-officer/sanctions" className="block group">
                            <GlassCard variant="interactive" hover className="h-full">
                                <GlassCardContent className="p-4 flex items-center gap-3">
                                    <div className="p-2 rounded-lg bg-[var(--color-risk-critical-soft)] text-[var(--color-risk-critical)]">
                                        <Shield className="w-4 h-4" />
                                    </div>
                                    <span className="text-sm font-medium text-white group-hover:text-[var(--color-risk-critical)] transition-colors">
                                        Sanctions
                                    </span>
                                </GlassCardContent>
                            </GlassCard>
                        </Link>
                    </div>
                </div>

                {/* RIGHT COLUMN: AI Capabilities & Context */}
                <div className="space-y-6">

                    {/* Priority Actions */}
                    {briefing && briefing.recommendations.priority_actions.length > 0 && (
                        <GlassCard>
                            <GlassCardHeader>
                                <GlassCardTitle className="text-base flex items-center gap-2">
                                    <CheckCircle className="w-4 h-4 text-[var(--color-risk-low)]" />
                                    Priority Actions
                                </GlassCardTitle>
                            </GlassCardHeader>
                            <GlassCardContent className="space-y-3 pt-0">
                                {briefing.recommendations.priority_actions.map((action, index) => (
                                    <div key={index} className="flex gap-3 text-sm p-2 rounded-lg hover:bg-white/5 transition-colors">
                                        <span className="flex-shrink-0 w-5 h-5 bg-[var(--color-aurora-500)] text-white rounded-full flex items-center justify-center text-[10px] font-bold">
                                            {index + 1}
                                        </span>
                                        <span className="text-white/80">{action}</span>
                                    </div>
                                ))}
                            </GlassCardContent>
                        </GlassCard>
                    )}

                    {/* AI Detected Risks */}
                    <GlassCard className="h-fit">
                        <GlassCardHeader>
                            <GlassCardTitle className="text-base flex items-center gap-2">
                                <Zap className="w-4 h-4 text-[var(--color-aurora-400)]" />
                                AI Detected Risks
                            </GlassCardTitle>
                        </GlassCardHeader>
                        <GlassCardContent className="space-y-3 pt-0">
                            {proactiveAlerts.length === 0 ? (
                                <div className="text-center py-6 text-white/30 text-sm">
                                    No proactive alerts detected.
                                </div>
                            ) : (
                                proactiveAlerts.map((alert, index) => (
                                    <div
                                        key={index}
                                        className={`p-3 rounded-lg border border-white/5 bg-white/[0.02]`}
                                    >
                                        <div className="flex justify-between items-start mb-1">
                                            <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded-full 
                                        ${alert.severity === 'critical' ? 'bg-red-500/20 text-red-500' :
                                                    alert.severity === 'high' ? 'bg-orange-500/20 text-orange-500' :
                                                        'bg-blue-500/20 text-blue-500'}`}>
                                                {alert.severity}
                                            </span>
                                        </div>
                                        <p className="text-sm font-medium text-white mb-1">{alert.message}</p>
                                        <p className="text-xs text-white/50">{alert.recommendation}</p>
                                    </div>
                                ))
                            )}
                        </GlassCardContent>
                    </GlassCard>

                    {/* Regulations */}
                    {briefing && briefing.regulatory.upcoming_deadlines.length > 0 && (
                        <GlassCard>
                            <GlassCardHeader>
                                <GlassCardTitle className="text-base flex items-center gap-2">
                                    <Calendar className="w-4 h-4 text-[var(--color-aurora-300)]" />
                                    Up Next
                                </GlassCardTitle>
                            </GlassCardHeader>
                            <GlassCardContent className="pt-0">
                                {briefing.regulatory.upcoming_deadlines.map((deadline, index) => (
                                    <div key={index} className="py-2 border-b border-white/5 last:border-0">
                                        <p className="text-sm text-white/80">{deadline.title}</p>
                                        <p className="text-xs text-[var(--color-aurora-300)] mt-0.5">
                                            {deadline.days_remaining} days remaining
                                        </p>
                                    </div>
                                ))}
                            </GlassCardContent>
                        </GlassCard>
                    )}

                </div>
            </motion.div>
        </motion.div>
    );
}
