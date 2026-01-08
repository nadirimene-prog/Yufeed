"use client";

import { useEffect, useState } from "react";
import { getComplianceMetrics, getHighRiskDocuments, getUpcomingDeadlines, type ComplianceMetrics } from "@/lib/compliance-api";
import { RiskBadge, ComplianceDomainBadge } from "@/components/compliance-badges";
import { AlertCircle, Calendar, TrendingUp } from "lucide-react";
import Link from "next/link";

export default function DashboardPage() {
    const [metrics, setMetrics] = useState<ComplianceMetrics | null>(null);
    const [highRiskDocs, setHighRiskDocs] = useState<any[]>([]);
    const [upcomingDeadlines, setUpcomingDeadlines] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [metricsData, highRisk, deadlines] = await Promise.all([
                    getComplianceMetrics(),
                    getHighRiskDocuments(5),
                    getUpcomingDeadlines(90)
                ]);

                setMetrics(metricsData);
                setHighRiskDocs(highRisk);
                setUpcomingDeadlines(deadlines);
            } catch (error) {
                console.error("Failed to load dashboard data:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="text-lg">Loading compliance dashboard...</div>
            </div>
        );
    }

    return (
        <div className="space-y-8">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Compliance Dashboard</h1>
                <p className="text-gray-600 dark:text-gray-400 mt-2">
                    AML/CFT Regulatory Monitoring Overview
                </p>
            </div>

            {/* Metrics Overview */}
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                <MetricCard
                    title="High Risk"
                    value={metrics?.high_risk_count || 0}
                    icon={<AlertCircle className="h-5 w-5 text-red-600" />}
                    color="red"
                />
                <MetricCard
                    title="Medium Risk"
                    value={metrics?.medium_risk_count || 0}
                    icon={<TrendingUp className="h-5 w-5 text-yellow-600" />}
                    color="yellow"
                />
                <MetricCard
                    title="Deadlines (30d)"
                    value={metrics?.upcoming_deadlines_30d || 0}
                    icon={<Calendar className="h-5 w-5 text-blue-600" />}
                    color="blue"
                />
                <MetricCard
                    title="Total Documents"
                    value={metrics?.total_documents || 0}
                    icon={<TrendingUp className="h-5 w-5 text-gray-600" />}
                    color="gray"
                />
            </div>

            {/* High Risk Documents */}
            <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
                <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                    <AlertCircle className="h-5 w-5 text-red-600" />
                    High-Risk Documents Requiring Attention
                </h2>
                <div className="space-y-3">
                    {highRiskDocs.length === 0 ? (
                        <p className="text-gray-500">No high-risk documents found.</p>
                    ) : (
                        highRiskDocs.map((doc) => (
                            <Link
                                key={doc.celex}
                                href={`/doc/${doc.celex}`}
                                className="block p-4 rounded-lg border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                            >
                                <div className="flex items-start justify-between gap-4">
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-2">
                                            <RiskBadge level={doc.risk_level || "unknown"} />
                                            {doc.compliance_domain && (
                                                <ComplianceDomainBadge domain={doc.compliance_domain} />
                                            )}
                                        </div>
                                        <h3 className="font-medium text-sm">{doc.title}</h3>
                                        <p className="text-xs text-gray-500 mt-1">{doc.celex}</p>
                                    </div>
                                </div>
                            </Link>
                        ))
                    )}
                </div>
            </div>

            {/* Upcoming Deadlines */}
            <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
                <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                    <Calendar className="h-5 w-5 text-blue-600" />
                    Upcoming Implementation Deadlines
                </h2>
                <div className="space-y-3">
                    {upcomingDeadlines.length === 0 ? (
                        <p className="text-gray-500">No upcoming deadlines in the next 90 days.</p>
                    ) : (
                        upcomingDeadlines.map((doc) => (
                            <Link
                                key={doc.celex}
                                href={`/doc/${doc.celex}`}
                                className="block p-4 rounded-lg border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                            >
                                <div className="flex items-start justify-between gap-4">
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-2">
                                            {doc.implementation_deadline && (
                                                <span className="text-xs font-medium text-blue-600">
                                                    {new Date(doc.implementation_deadline).toLocaleDateString()}
                                                </span>
                                            )}
                                            {doc.compliance_domain && (
                                                <ComplianceDomainBadge domain={doc.compliance_domain} />
                                            )}
                                        </div>
                                        <h3 className="font-medium text-sm">{doc.title}</h3>
                                        <p className="text-xs text-gray-500 mt-1">{doc.celex}</p>
                                    </div>
                                </div>
                            </Link>
                        ))
                    )}
                </div>
            </div>

            {/* By Domain Chart */}
            {metrics && metrics.by_domain && Object.keys(metrics.by_domain).length > 0 && (
                <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-6">
                    <h2 className="text-xl font-semibold mb-4">Documents by Compliance Domain</h2>
                    <div className="space-y-2">
                        {Object.entries(metrics.by_domain).map(([domain, count]) => (
                            <div key={domain} className="flex items-center justify-between">
                                <ComplianceDomainBadge domain={domain} />
                                <span className="text-sm font-medium">{count}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

function MetricCard({ title, value, icon, color }: { title: string; value: number; icon: React.ReactNode; color: string }) {
    const colors = {
        red: "border-red-200 dark:border-red-800",
        yellow: "border-yellow-200 dark:border-yellow-800",
        blue: "border-blue-200 dark:border-blue-800",
        gray: "border-gray-200 dark:border-gray-800",
    };

    return (
        <div className={`bg-white dark:bg-gray-900 rounded-lg border ${colors[color as keyof typeof colors]} p-6`}>
            <div className="flex items-center justify-between">
                <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">{title}</p>
                    <p className="text-3xl font-bold mt-2">{value}</p>
                </div>
                {icon}
            </div>
        </div>
    );
}
