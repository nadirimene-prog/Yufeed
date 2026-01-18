"use client";

import { useEffect, useState } from "react";
import { getComplianceMetrics, getHighRiskDocuments, getUpcomingDeadlines, type ComplianceMetrics } from "@/lib/compliance-api";
import { RiskBadge, ComplianceDomainBadge } from "@/components/compliance-badges";
import { MetricCard } from "@/components/ui/metric-card";
import { EmptyStateInline } from "@/components/ui/empty-state";
import { CardSkeleton } from "@/components/ui/skeleton";
import { RiskTrendChart } from "@/components/dashboard/risk-trend-chart";
import { AlertCircle, Calendar, TrendingUp, FileText, Clock, ArrowUpRight, BarChart3 } from "lucide-react";
import Link from "next/link";
import { DataTable } from "@/components/ui/data-table";
import { ColumnDef } from "@tanstack/react-table";
import { Button } from "@/components/ui/button";

// Define columns for High Risk Docs
const highRiskColumns: ColumnDef<any>[] = [
    {
        accessorKey: "title",
        header: "Document Title",
        cell: ({ row }) => (
            <div className="max-w-[300px] truncate font-medium text-foreground">
                <Link href={`/doc/${row.original.celex}`} className="hover:underline">
                    {row.original.title}
                </Link>
            </div>
        ),
    },
    {
        accessorKey: "celex",
        header: "CELEX",
        cell: ({ row }) => <span className="font-mono text-xs text-muted-foreground">{row.getValue("celex")}</span>,
    },
    {
        accessorKey: "risk_level",
        header: "Risk Level",
        cell: ({ row }) => <RiskBadge level={row.getValue("risk_level")} />,
    },
    {
        accessorKey: "compliance_domain",
        header: "Domain",
        cell: ({ row }) => (
            row.original.compliance_domain ? <ComplianceDomainBadge domain={row.original.compliance_domain} /> : null
        ),
    },
    {
        id: "actions",
        cell: ({ row }) => (
            <Link href={`/doc/${row.original.celex}`}>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                    <ArrowUpRight className="h-4 w-4" />
                </Button>
            </Link>
        ),
    },
];

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

                // Mock data for demonstration if API returns empty
                const mockHighRiskDocs = [
                    { celex: "32015L0849", title: "Directive (EU) 2015/849 on the prevention of the use of the financial system for the purposes of money laundering or terrorist financing", risk_level: "critical", compliance_domain: "AML/CFT" },
                    { celex: "32018L0843", title: "Directive (EU) 2018/843 amending Directive (EU) 2015/849", risk_level: "high", compliance_domain: "AML/CFT" },
                    { celex: "32023R1113", title: "Regulation (EU) 2023/1113 on information accompanying transfers of funds and certain crypto-assets", risk_level: "high", compliance_domain: "Crypto-assets" },
                    { celex: "32024R1624", title: "Regulation (EU) 2024/1624 on the prevention of the use of the financial system for the purposes of money laundering or terrorist financing", risk_level: "critical", compliance_domain: "AML/CFT" },
                    { celex: "32019L1153", title: "Directive (EU) 2019/1153 laying down rules facilitating the use of financial and other information for the prevention, detection, investigation or prosecution of certain criminal offences", risk_level: "medium", compliance_domain: "Financial Intelligence" },
                ];

                setMetrics(metricsData);
                setHighRiskDocs(highRisk && highRisk.length > 0 ? highRisk : mockHighRiskDocs);
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
            <div className="space-y-8 animate-fade-in">
                <div>
                    <div className="h-10 w-64 bg-gray-200 dark:bg-slate-700 rounded animate-pulse mb-2" />
                    <div className="h-6 w-96 bg-gray-100 dark:bg-slate-800 rounded animate-pulse" />
                </div>

                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                    {[1, 2, 3, 4].map((i) => (
                        <MetricCard key={i} title="" value={0} loading />
                    ))}
                </div>

                <div className="grid gap-6 lg:grid-cols-2">
                    <CardSkeleton />
                    <CardSkeleton />
                </div>
            </div>
        );
    }

    // Calculate trends (mock data for now - could be enhanced with historical data)
    const highRiskTrend = { direction: 'down' as const, value: '12%', label: 'vs last week' };
    const mediumRiskTrend = { direction: 'up' as const, value: '5%', label: 'vs last week' };
    const deadlinesTrend = { direction: 'neutral' as const, value: '0%', label: 'vs last month' };

    return (
        <div className="space-y-8 animate-slide-up">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">
                        Compliance Dashboard
                    </h1>
                    <p className="text-gray-600 dark:text-gray-400 mt-2">
                        AML/CFT Regulatory Monitoring Overview
                    </p>
                </div>
                <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                    <Clock className="h-4 w-4" />
                    <span>Updated just now</span>
                </div>
            </div>

            {/* Metrics Overview */}
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                <MetricCard
                    title="High Risk Documents"
                    value={metrics?.high_risk_count || 0}
                    icon={<AlertCircle className="h-5 w-5" />}
                    color="red"
                    trend={highRiskTrend}
                    sparklineData={[
                        { value: 10 }, { value: 12 }, { value: 15 }, { value: 13 }, { value: 18 }, { value: 20 }, { value: 15 }
                    ]}
                />
                <MetricCard
                    title="Medium Risk Documents"
                    value={metrics?.medium_risk_count || 0}
                    icon={<TrendingUp className="h-5 w-5" />}
                    color="yellow"
                    trend={mediumRiskTrend}
                    sparklineData={[
                        { value: 50 }, { value: 45 }, { value: 48 }, { value: 52 }, { value: 55 }, { value: 53 }, { value: 58 }
                    ]}
                />
                <MetricCard
                    title="Deadlines (30 days)"
                    value={metrics?.upcoming_deadlines_30d || 0}
                    icon={<Calendar className="h-5 w-5" />}
                    color="blue"
                    trend={deadlinesTrend}
                    sparklineData={[
                        { value: 5 }, { value: 8 }, { value: 6 }, { value: 9 }, { value: 12 }, { value: 8 }, { value: 10 }
                    ]}
                />
                <MetricCard
                    title="Total Documents"
                    value={metrics?.total_documents || 0}
                    icon={<FileText className="h-5 w-5" />}
                    color="gray"
                    sparklineData={[
                        { value: 100 }, { value: 102 }, { value: 105 }, { value: 110 }, { value: 108 }, { value: 112 }, { value: 115 }
                    ]}
                />
            </div>

            {/* Risk Trend Chart */}
            <RiskTrendChartSection />

            {/* Main Content Grid */}
            <div className="grid gap-6 lg:grid-cols-2">
                {/* High Risk Documents */}
                <div className="bg-white dark:bg-slate-900 rounded-lg border border-gray-200 dark:border-slate-800 shadow-sm overflow-hidden flex flex-col">
                    <div className="p-6 border-b border-gray-200 dark:border-slate-800 flex items-center justify-between shrink-0">
                        <div>
                            <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                                <AlertCircle className="h-5 w-5 text-red-600" />
                                High-Risk Documents
                            </h2>
                            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                                Documents requiring immediate attention
                            </p>
                        </div>
                        <Link
                            href="/search?risk=high"
                            className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 flex items-center gap-1"
                        >
                            View all
                            <ArrowUpRight className="h-3 w-3" />
                        </Link>
                    </div>
                    {/* Use DataTable here */}
                    <div className="p-0 flex-1 overflow-hidden">
                        {highRiskDocs.length === 0 ? (
                            <div className="p-6"><EmptyStateInline message="No high-risk documents found" /></div>
                        ) : (
                            <DataTable columns={highRiskColumns} data={highRiskDocs} />
                        )}
                    </div>
                </div>

                {/* Upcoming Deadlines */}
                <div className="bg-white dark:bg-slate-900 rounded-lg border border-gray-200 dark:border-slate-800 shadow-sm">
                    <div className="p-6 border-b border-gray-200 dark:border-slate-800">
                        <div className="flex items-center justify-between">
                            <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                                <Calendar className="h-5 w-5 text-blue-600" />
                                Upcoming Deadlines
                            </h2>
                            <Link
                                href="/search?has_deadline=true"
                                className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 flex items-center gap-1"
                            >
                                View all
                                <ArrowUpRight className="h-3 w-3" />
                            </Link>
                        </div>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                            Implementation deadlines in next 90 days
                        </p>
                    </div>
                    <div className="p-6">
                        {upcomingDeadlines.length === 0 ? (
                            <EmptyStateInline message="No upcoming deadlines in the next 90 days" />
                        ) : (
                            <div className="space-y-3">
                                {upcomingDeadlines.map((doc) => (
                                    <Link
                                        key={doc.celex}
                                        href={`/doc/${doc.celex}`}
                                        className="block p-4 rounded-lg border border-gray-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors group"
                                    >
                                        <div className="flex items-start justify-between gap-4">
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 mb-2">
                                                    {doc.implementation_deadline && (
                                                        <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 border border-blue-200 dark:border-blue-800">
                                                            <Calendar className="h-3 w-3" />
                                                            {new Date(doc.implementation_deadline).toLocaleDateString()}
                                                        </span>
                                                    )}
                                                    {doc.compliance_domain && (
                                                        <ComplianceDomainBadge domain={doc.compliance_domain} />
                                                    )}
                                                </div>
                                                <h3 className="font-medium text-sm text-gray-900 dark:text-white line-clamp-2 group-hover:text-blue-600 dark:group-hover:text-blue-400">
                                                    {doc.title}
                                                </h3>
                                                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 font-mono">
                                                    {doc.celex}
                                                </p>
                                            </div>
                                        </div>
                                    </Link>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* Documents by Domain */}
                {metrics && metrics.by_domain && Object.keys(metrics.by_domain).length > 0 && (
                    <div className="bg-white dark:bg-slate-900 rounded-lg border border-gray-200 dark:border-slate-800 shadow-sm">
                        <div className="p-6 border-b border-gray-200 dark:border-slate-800">
                            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                                Documents by Compliance Domain
                            </h2>
                            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                                Distribution across regulatory areas
                            </p>
                        </div>
                        <div className="p-6">
                            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                                {Object.entries(metrics.by_domain).map(([domain, count]) => (
                                    <div key={domain} className="p-4 rounded-lg border border-gray-200 dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors">
                                        <ComplianceDomainBadge domain={domain} />
                                        <p className="text-2xl font-bold text-gray-900 dark:text-white mt-2">
                                            {count}
                                        </p>
                                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                            documents
                                        </p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

// Risk Trend Chart Section Component
function RiskTrendChartSection() {
    const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d');

    const timeRanges = [
        { value: '7d' as const, label: '7 Days' },
        { value: '30d' as const, label: '30 Days' },
        { value: '90d' as const, label: '90 Days' },
    ];

    return (
        <div className="bg-white dark:bg-slate-900 rounded-lg border border-gray-200 dark:border-slate-800 shadow-sm">
            <div className="p-6 border-b border-gray-200 dark:border-slate-800">
                <div className="flex items-center justify-between">
                    <div>
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                            <BarChart3 className="h-5 w-5 text-blue-600" />
                            Risk Trend Analysis
                        </h2>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                            Document risk distribution over time
                        </p>
                    </div>

                    {/* Time Range Selector */}
                    <div className="flex items-center gap-2 bg-gray-100 dark:bg-slate-800 rounded-lg p-1">
                        {timeRanges.map((range) => (
                            <button
                                key={range.value}
                                onClick={() => setTimeRange(range.value)}
                                className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${timeRange === range.value
                                    ? 'bg-white dark:bg-slate-700 text-gray-900 dark:text-white shadow-sm'
                                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                                    }`}
                            >
                                {range.label}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            <div className="p-6">
                <div className="h-80">
                    <RiskTrendChart timeRange={timeRange} />
                </div>
            </div>
        </div>
    );
}
