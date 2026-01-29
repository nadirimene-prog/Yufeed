"use client";

import { useEffect, useState } from "react";
import {
    ShieldAlert,
    Activity,
    CheckCircle2,
    Clock,
    ArrowUpRight,
    Filter,
    Search,
    MoreHorizontal
} from "lucide-react";
import { cn } from "@/lib/utils";

// Mock data for initial layout testing
const MOCK_STATS = [
    { label: "Total Alerts (24h)", value: "1,284", change: "+12.5%", color: "blue", icon: Activity },
    { label: "Pending Review", value: "42", change: "-5", color: "orange", icon: Clock },
    { label: "True Positive Rate", value: "68%", change: "+2.1%", color: "green", icon: CheckCircle2 },
    { label: "Critical Alerts", value: "12", change: "+3", color: "red", icon: ShieldAlert },
];

const MOCK_ALERTS = [
    { id: "AL-8291", user: "John Doe", type: "Velocity", amount: "$5,200", status: "pending", time: "2m ago", severity: "high" },
    { id: "AL-8290", user: "Alice Smith", type: "Sanctions", amount: "$120", status: "in_review", time: "15m ago", severity: "critical" },
    { id: "AL-8289", user: "Bob Builder", type: "Structuring", amount: "$9,800", status: "resolved", time: "1h ago", severity: "medium" },
    { id: "AL-8288", user: "Charlie Root", type: "High Risk Country", amount: "$15,000", status: "pending", time: "2h ago", severity: "high" },
];

export default function TransactionMonitoringDashboard() {
    return (
        <div className="space-y-8 animate-in fade-in duration-500 pb-12">
            {/* Header */}
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-gray-100 sm:text-4xl">
                        Transaction Monitoring
                    </h1>
                    <p className="text-lg text-gray-500 dark:text-gray-400">
                        Real-time fraud and compliance oversight.
                    </p>
                </div>
                <div className="flex gap-3">
                    <button className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-gray-800 dark:bg-gray-950 dark:text-gray-300 dark:hover:bg-gray-900 transition-all">
                        <Filter className="h-4 w-4" />
                        <span>Filters</span>
                    </button>
                    <a
                        href="/transaction-monitoring/rules/lab"
                        className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-gray-800 dark:bg-gray-950 dark:text-gray-300 dark:hover:bg-gray-900 transition-all"
                    >
                        <span>Rule Lab</span>
                        <ArrowUpRight className="h-4 w-4" />
                    </a>
                    <a href="/transaction-monitoring/rules" className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-950 transition-all">
                        <span>Manage Rules</span>
                        <ArrowUpRight className="h-4 w-4" />
                    </a>
                </div>
            </div>

            {/* Stats Grid */}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {MOCK_STATS.map((stat) => (
                    <div key={stat.label} className="group relative overflow-hidden rounded-2xl border border-gray-200 bg-white p-6 shadow-sm transition-all hover:shadow-md dark:border-gray-800 dark:bg-gray-950">
                        <div className="flex items-center justify-between">
                            <div className={cn(
                                "rounded-xl p-2.5 transition-colors",
                                stat.color === 'blue' && "bg-blue-50 text-blue-600 dark:bg-blue-500/10",
                                stat.color === 'orange' && "bg-orange-50 text-orange-600 dark:bg-orange-500/10",
                                stat.color === 'green' && "bg-green-50 text-green-600 dark:bg-green-500/10",
                                stat.color === 'red' && "bg-red-50 text-red-600 dark:bg-red-500/10",
                            )}>
                                <stat.icon className="h-6 w-6" />
                            </div>
                            <span className={cn(
                                "text-xs font-semibold px-2 py-1 rounded-full",
                                stat.change.startsWith('+') ? "text-green-600 bg-green-50 dark:bg-green-500/10" : "text-red-600 bg-red-50 dark:bg-red-500/10"
                            )}>
                                {stat.change}
                            </span>
                        </div>
                        <div className="mt-4">
                            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">{stat.label}</h3>
                            <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{stat.value}</p>
                        </div>
                        <div className="absolute -bottom-1 -right-1 opacity-5 group-hover:opacity-10 transition-opacity">
                            <stat.icon className="h-16 w-16" />
                        </div>
                    </div>
                ))}
            </div>

            {/* Alerts Table */}
            <div className="rounded-2xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-950 overflow-hidden">
                <div className="border-b border-gray-100 p-6 dark:border-gray-800">
                    <div className="flex items-center justify-between">
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Recent Alerts</h2>
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                            <input
                                type="text"
                                placeholder="Search alerts..."
                                className="rounded-lg border border-gray-200 bg-gray-50/50 py-2 pl-10 pr-4 text-sm focus:border-blue-500 focus:outline-none dark:border-gray-800 dark:bg-gray-900/50"
                            />
                        </div>
                    </div>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead>
                            <tr className="bg-gray-50/50 border-b border-gray-100 text-xs font-semibold uppercase tracking-wider text-gray-500 dark:bg-gray-900/50 dark:border-gray-800">
                                <th className="px-6 py-4">Alert ID</th>
                                <th className="px-6 py-4">User</th>
                                <th className="px-6 py-4">Type</th>
                                <th className="px-6 py-4">Amount</th>
                                <th className="px-6 py-4">Severity</th>
                                <th className="px-6 py-4">Status</th>
                                <th className="px-6 py-4 text-right">Time</th>
                                <th className="px-6 py-4"></th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                            {MOCK_ALERTS.map((alert) => (
                                <tr key={alert.id} className="group hover:bg-gray-50/50 dark:hover:bg-gray-900/30 transition-colors cursor-pointer">
                                    <td className="px-6 py-4 text-sm font-medium text-blue-600 dark:text-blue-400">
                                        <a href={`/transaction-monitoring/alerts/${alert.id}`}>{alert.id}</a>
                                    </td>
                                    <td className="px-6 py-4 text-sm text-gray-900 dark:text-white font-medium">{alert.user}</td>
                                    <td className="px-6 py-4">
                                        <span className="rounded-md bg-gray-100 px-2 py-1 text-xs font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-400">
                                            {alert.type}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-sm font-mono text-gray-900 dark:text-white">{alert.amount}</td>
                                    <td className="px-6 py-4">
                                        <span className={cn(
                                            "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold",
                                            alert.severity === 'critical' ? 'bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-400' :
                                                alert.severity === 'high' ? 'bg-orange-50 text-orange-700 dark:bg-orange-500/10 dark:text-orange-400' :
                                                    'bg-yellow-50 text-yellow-700 dark:bg-yellow-500/10 dark:text-yellow-400'
                                        )}>
                                            <div className={cn(
                                                "h-1.5 w-1.5 rounded-full",
                                                alert.severity === 'critical' ? 'bg-red-600' :
                                                    alert.severity === 'high' ? 'bg-orange-600' : 'bg-yellow-600'
                                            )} />
                                            {alert.severity}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className={cn(
                                            "rounded-full px-2 py-0.5 text-xs font-medium",
                                            alert.status === 'pending' ? 'bg-blue-50 text-blue-700 dark:bg-blue-500/10' :
                                                alert.status === 'in_review' ? 'bg-purple-50 text-purple-700 dark:bg-purple-500/10' :
                                                    'bg-green-50 text-green-700 dark:bg-green-500/10'
                                        )}>
                                            {alert.status.replace('_', ' ')}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-right text-sm text-gray-500 dark:text-gray-400">{alert.time}</td>
                                    <td className="px-6 py-4 text-right">
                                        <button className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
                                            <MoreHorizontal className="h-5 w-5" />
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
