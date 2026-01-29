"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
    Scale,
    FileText,
    AlertTriangle,
    Check,
    Clock,
    TrendingUp,
    ArrowRight,
    Activity,
    Shield,
    Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { GlassCard } from "@/components/ui/glass-card";
import { MetricCard } from "@/components/ui/metric-card";
import {
    getObligations,
    getPolicies,
    getRiskMap,
} from "@/lib/compliance-api";
import type { Obligation, Policy, RiskMapSummary } from "@/types/compliance";
import Link from "next/link";

export default function ComplianceDashboardPage() {
    const [loading, setLoading] = useState(true);
    const [obligations, setObligations] = useState<Obligation[]>([]);
    const [policies, setPolicies] = useState<Policy[]>([]);
    const [riskMap, setRiskMap] = useState<RiskMapSummary | null>(null);
    const [obligationCounts, setObligationCounts] = useState({
        draft: 0,
        in_review: 0,
        approved: 0,
        rejected: 0,
        total: 0,
    });

    useEffect(() => {
        const loadData = async () => {
            setLoading(true);
            try {
                const [obligationsRes, policiesRes, riskMapRes] = await Promise.all([
                    getObligations({ limit: 10 }),
                    getPolicies({ limit: 10 }),
                    getRiskMap(),
                ]);

                setObligations(obligationsRes.items);
                setPolicies(policiesRes.items);
                setRiskMap(riskMapRes);

                // Calculate obligation counts by status
                const [draftRes, reviewRes, approvedRes, rejectedRes] = await Promise.all([
                    getObligations({ status: "draft", limit: 1 }),
                    getObligations({ status: "in_review", limit: 1 }),
                    getObligations({ status: "approved", limit: 1 }),
                    getObligations({ status: "rejected", limit: 1 }),
                ]);

                setObligationCounts({
                    draft: draftRes.total,
                    in_review: reviewRes.total,
                    approved: approvedRes.total,
                    rejected: rejectedRes.total,
                    total: draftRes.total + reviewRes.total + approvedRes.total + rejectedRes.total,
                });
            } catch (err) {
                console.error("Failed to load dashboard data:", err);
            } finally {
                setLoading(false);
            }
        };

        loadData();
    }, []);

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <Loader2 className="h-8 w-8 animate-spin text-[#6d5acd]" />
            </div>
        );
    }

    const activePolicies = policies.filter((p) => p.status === "active" || p.status === "approved").length;
    const highRisks = riskMap?.high_priority_risks?.length || 0;

    return (
        <div className="p-6 space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white">Compliance Dashboard</h1>
                    <p className="text-white/60 mt-1">
                        Overview of regulatory obligations, policies, and risk management
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Link
                        href="/compliance/obligations"
                        className="px-4 py-2 text-sm font-medium text-white/70 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
                    >
                        View All Obligations
                    </Link>
                </div>
            </div>

            {/* Metrics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricCard
                    title="Total Obligations"
                    value={obligationCounts.total}
                    icon={<Scale className="h-5 w-5" />}
                    trend={{ value: obligationCounts.approved, label: "approved" }}
                    className="bg-gradient-to-br from-[#6d5acd]/20 to-transparent"
                />
                <MetricCard
                    title="Pending Review"
                    value={obligationCounts.in_review + obligationCounts.draft}
                    icon={<Clock className="h-5 w-5" />}
                    trend={{ value: obligationCounts.in_review, label: "in review" }}
                    className="bg-gradient-to-br from-amber-500/20 to-transparent"
                />
                <MetricCard
                    title="Active Policies"
                    value={activePolicies}
                    icon={<FileText className="h-5 w-5" />}
                    trend={{ value: policies.length, label: "total" }}
                    className="bg-gradient-to-br from-blue-500/20 to-transparent"
                />
                <MetricCard
                    title="High Priority Risks"
                    value={highRisks}
                    icon={<AlertTriangle className="h-5 w-5" />}
                    trend={{ value: riskMap?.total_entries || 0, label: "total risks" }}
                    className="bg-gradient-to-br from-red-500/20 to-transparent"
                />
            </div>

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Obligations by Status */}
                <GlassCard className="lg:col-span-2">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                            <Scale className="h-5 w-5 text-[#6d5acd]" />
                            Obligations by Status
                        </h2>
                        <Link
                            href="/compliance/obligations"
                            className="text-sm text-[#00d4ff] hover:underline flex items-center gap-1"
                        >
                            View all <ArrowRight className="h-4 w-4" />
                        </Link>
                    </div>

                    <div className="grid grid-cols-4 gap-3 mb-6">
                        <StatusCard
                            label="Draft"
                            count={obligationCounts.draft}
                            color="bg-gray-500/20 text-gray-400"
                            icon={<FileText className="h-4 w-4" />}
                        />
                        <StatusCard
                            label="In Review"
                            count={obligationCounts.in_review}
                            color="bg-amber-500/20 text-amber-400"
                            icon={<Clock className="h-4 w-4" />}
                        />
                        <StatusCard
                            label="Approved"
                            count={obligationCounts.approved}
                            color="bg-green-500/20 text-green-400"
                            icon={<Check className="h-4 w-4" />}
                        />
                        <StatusCard
                            label="Rejected"
                            count={obligationCounts.rejected}
                            color="bg-red-500/20 text-red-400"
                            icon={<AlertTriangle className="h-4 w-4" />}
                        />
                    </div>

                    {/* Recent Obligations */}
                    <div className="space-y-2">
                        <h3 className="text-sm font-medium text-white/70 mb-2">Recent Obligations</h3>
                        {obligations.slice(0, 5).map((obl) => (
                            <Link
                                key={obl.id}
                                href={`/compliance/obligations/${obl.id}`}
                                className="flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 transition-colors"
                            >
                                <StatusBadge status={obl.status} />
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm text-white truncate">
                                        {obl.article_ref || obl.obligation_id}
                                    </p>
                                    <p className="text-xs text-white/50 truncate">
                                        {obl.obligation_text.substring(0, 80)}...
                                    </p>
                                </div>
                                <span className="text-xs text-white/40">
                                    {obl.document?.celex}
                                </span>
                            </Link>
                        ))}
                    </div>
                </GlassCard>

                {/* Risk Summary */}
                <GlassCard>
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                            <Shield className="h-5 w-5 text-red-400" />
                            Risk Overview
                        </h2>
                        <Link
                            href="/compliance/risk-map"
                            className="text-sm text-[#00d4ff] hover:underline flex items-center gap-1"
                        >
                            View map <ArrowRight className="h-4 w-4" />
                        </Link>
                    </div>

                    {riskMap && (
                        <>
                            {/* Risk Level Distribution */}
                            <div className="space-y-3 mb-6">
                                <RiskLevelBar
                                    label="Critical"
                                    count={riskMap.by_inherent_level.critical || 0}
                                    total={riskMap.total_entries}
                                    color="bg-red-500"
                                />
                                <RiskLevelBar
                                    label="High"
                                    count={riskMap.by_inherent_level.high || 0}
                                    total={riskMap.total_entries}
                                    color="bg-orange-500"
                                />
                                <RiskLevelBar
                                    label="Medium"
                                    count={riskMap.by_inherent_level.medium || 0}
                                    total={riskMap.total_entries}
                                    color="bg-yellow-500"
                                />
                                <RiskLevelBar
                                    label="Low"
                                    count={riskMap.by_inherent_level.low || 0}
                                    total={riskMap.total_entries}
                                    color="bg-green-500"
                                />
                            </div>

                            {/* High Priority Risks */}
                            {riskMap.high_priority_risks.length > 0 && (
                                <div>
                                    <h3 className="text-sm font-medium text-white/70 mb-2">
                                        High Priority Risks
                                    </h3>
                                    <div className="space-y-2">
                                        {riskMap.high_priority_risks.slice(0, 3).map((risk) => (
                                            <div
                                                key={risk.id}
                                                className="p-2 rounded-lg bg-white/5 border border-white/10"
                                            >
                                                <p className="text-sm text-white truncate">{risk.name}</p>
                                                <div className="flex items-center gap-2 mt-1">
                                                    <span className={cn(
                                                        "text-xs px-1.5 py-0.5 rounded",
                                                        risk.inherent_risk_level === "critical"
                                                            ? "bg-red-500/20 text-red-400"
                                                            : "bg-orange-500/20 text-orange-400"
                                                    )}>
                                                        {risk.inherent_risk_level}
                                                    </span>
                                                    <span className="text-xs text-white/40">
                                                        {risk.category_name}
                                                    </span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </GlassCard>
            </div>

            {/* Policies Section */}
            <GlassCard>
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                        <FileText className="h-5 w-5 text-blue-400" />
                        Recent Policies
                    </h2>
                    <Link
                        href="/compliance/policies"
                        className="text-sm text-[#00d4ff] hover:underline flex items-center gap-1"
                    >
                        View all <ArrowRight className="h-4 w-4" />
                    </Link>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    {policies.slice(0, 4).map((policy) => (
                        <Link
                            key={policy.id}
                            href={`/compliance/policies?id=${policy.id}`}
                            className="p-3 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"
                        >
                            <div className="flex items-center gap-2 mb-2">
                                <FileText className="h-4 w-4 text-[#6d5acd]" />
                                <span className={cn(
                                    "text-xs px-1.5 py-0.5 rounded",
                                    policy.status === "active" && "bg-green-500/20 text-green-400",
                                    policy.status === "approved" && "bg-blue-500/20 text-blue-400",
                                    policy.status === "draft" && "bg-gray-500/20 text-gray-400",
                                    policy.status === "in_review" && "bg-yellow-500/20 text-yellow-400"
                                )}>
                                    {policy.status}
                                </span>
                            </div>
                            <p className="text-sm font-medium text-white truncate">{policy.name}</p>
                            <p className="text-xs text-white/50">{policy.policy_id}</p>
                        </Link>
                    ))}
                </div>
            </GlassCard>

            {/* Quick Actions */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Link
                    href="/compliance/obligations?status=in_review"
                    className="p-4 rounded-xl bg-gradient-to-br from-amber-500/20 to-transparent border border-amber-500/20 hover:border-amber-500/40 transition-colors group"
                >
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-amber-500/20">
                            <Clock className="h-5 w-5 text-amber-400" />
                        </div>
                        <div>
                            <h3 className="font-medium text-white">Review Pending</h3>
                            <p className="text-sm text-white/50">
                                {obligationCounts.in_review} obligations awaiting review
                            </p>
                        </div>
                        <ArrowRight className="h-5 w-5 text-white/30 ml-auto group-hover:text-amber-400 transition-colors" />
                    </div>
                </Link>

                <Link
                    href="/compliance/risk-map"
                    className="p-4 rounded-xl bg-gradient-to-br from-red-500/20 to-transparent border border-red-500/20 hover:border-red-500/40 transition-colors group"
                >
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-red-500/20">
                            <AlertTriangle className="h-5 w-5 text-red-400" />
                        </div>
                        <div>
                            <h3 className="font-medium text-white">Risk Assessment</h3>
                            <p className="text-sm text-white/50">
                                {highRisks} high priority risks identified
                            </p>
                        </div>
                        <ArrowRight className="h-5 w-5 text-white/30 ml-auto group-hover:text-red-400 transition-colors" />
                    </div>
                </Link>

                <Link
                    href="/compliance/policies"
                    className="p-4 rounded-xl bg-gradient-to-br from-[#6d5acd]/20 to-transparent border border-[#6d5acd]/20 hover:border-[#6d5acd]/40 transition-colors group"
                >
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-[#6d5acd]/20">
                            <FileText className="h-5 w-5 text-[#6d5acd]" />
                        </div>
                        <div>
                            <h3 className="font-medium text-white">Manage Policies</h3>
                            <p className="text-sm text-white/50">
                                {policies.length} policies in system
                            </p>
                        </div>
                        <ArrowRight className="h-5 w-5 text-white/30 ml-auto group-hover:text-[#6d5acd] transition-colors" />
                    </div>
                </Link>
            </div>
        </div>
    );
}

function StatusCard({
    label,
    count,
    color,
    icon,
}: {
    label: string;
    count: number;
    color: string;
    icon: React.ReactNode;
}) {
    return (
        <div className={cn("p-3 rounded-lg", color)}>
            <div className="flex items-center gap-2 mb-1">
                {icon}
                <span className="text-xs font-medium">{label}</span>
            </div>
            <p className="text-2xl font-bold">{count}</p>
        </div>
    );
}

function StatusBadge({ status }: { status: string }) {
    const colors: Record<string, string> = {
        draft: "bg-gray-500/20 text-gray-400",
        in_review: "bg-amber-500/20 text-amber-400",
        approved: "bg-green-500/20 text-green-400",
        rejected: "bg-red-500/20 text-red-400",
        deprecated: "bg-gray-500/20 text-gray-400",
    };

    return (
        <span className={cn("text-xs px-2 py-0.5 rounded", colors[status] || colors.draft)}>
            {status.replace("_", " ")}
        </span>
    );
}

function RiskLevelBar({
    label,
    count,
    total,
    color,
}: {
    label: string;
    count: number;
    total: number;
    color: string;
}) {
    const percentage = total > 0 ? (count / total) * 100 : 0;

    return (
        <div>
            <div className="flex items-center justify-between text-xs mb-1">
                <span className="text-white/70">{label}</span>
                <span className="text-white/50">{count}</span>
            </div>
            <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                <motion.div
                    className={cn("h-full rounded-full", color)}
                    initial={{ width: 0 }}
                    animate={{ width: `${percentage}%` }}
                    transition={{ duration: 0.5, delay: 0.2 }}
                />
            </div>
        </div>
    );
}
