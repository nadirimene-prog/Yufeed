"use client";

import { useState } from "react";
import {
    Plus,
    Search,
    Settings2,
    Play,
    Pause,
    Trash2,
    ExternalLink,
    ChevronRight
} from "lucide-react";
import { cn } from "@/lib/utils";

const MOCK_RULES = [
    { id: "RULE-001", name: "High Velocity Deposit", category: "velocity", severity: "high", enabled: true, alertCount: 450, tpr: "85%" },
    { id: "RULE-002", name: "Sanctioned Entity Match", category: "sanctions", severity: "critical", enabled: true, alertCount: 12, tpr: "92%" },
    { id: "RULE-003", name: "Structuring Threshold", category: "behavior", severity: "medium", enabled: false, alertCount: 89, tpr: "45%" },
    { id: "RULE-004", name: "High Risk Geo (RU/IR)", category: "geography", severity: "high", enabled: true, alertCount: 156, tpr: "78%" },
];

export default function RuleManagementPage() {
    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-gray-100 sm:text-4xl">
                        Monitoring Rules
                    </h1>
                    <p className="mt-2 text-lg text-gray-600 dark:text-gray-400">
                        Define and manage your automated compliance logic.
                    </p>
                </div>
                <a
                    href="/transaction-monitoring/rules/new"
                    className="flex items-center rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 transition-colors shadow-sm"
                >
                    <Plus className="mr-2 h-4 w-4" />
                    Create Rule
                </a>
            </div>

            <div className="flex flex-col gap-4 sm:flex-row sm:items-center justify-between bg-white dark:bg-gray-950 p-4 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm">
                <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Search rules..."
                        className="w-full rounded-lg border border-gray-200 bg-gray-50/50 py-2 pl-10 pr-4 text-sm focus:border-blue-500 focus:outline-none dark:border-gray-800 dark:bg-gray-900/50"
                    />
                </div>
                <div className="flex gap-2">
                    <button className="px-3 py-1.5 text-sm font-medium text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white transition-colors">All Rules</button>
                    <button className="px-3 py-1.5 text-sm font-medium text-gray-400 hover:text-gray-900 transition-colors">Templates</button>
                    <button className="px-3 py-1.5 text-sm font-medium text-gray-400 hover:text-gray-900 transition-colors">Archived</button>
                </div>
            </div>

            <div className="grid gap-4">
                {MOCK_RULES.map((rule) => (
                    <div key={rule.id} className="group flex items-center justify-between p-6 rounded-2xl border border-gray-200 bg-white hover:border-blue-200 hover:shadow-md transition-all dark:border-gray-800 dark:bg-gray-950 dark:hover:border-blue-900/50">
                        <div className="flex items-center gap-6">
                            <div className={cn(
                                "flex h-12 w-12 items-center justify-center rounded-xl",
                                rule.enabled ? "bg-blue-50 text-blue-600 dark:bg-blue-500/10" : "bg-gray-50 text-gray-400 dark:bg-gray-900"
                            )}>
                                <Settings2 className="h-6 w-6" />
                            </div>
                            <div>
                                <div className="flex items-center gap-2 mb-1">
                                    <h3 className="font-semibold text-gray-900 dark:text-white">{rule.name}</h3>
                                    <span className={cn(
                                        "text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded",
                                        rule.severity === 'critical' ? 'bg-red-100 text-red-700 dark:bg-red-900/30' :
                                            rule.severity === 'high' ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30' :
                                                'bg-blue-100 text-blue-700 dark:bg-blue-900/30'
                                    )}>
                                        {rule.severity}
                                    </span>
                                </div>
                                <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                                    <span className="capitalize">{rule.category}</span>
                                    <span className="h-1 w-1 rounded-full bg-gray-300" />
                                    <span>ID: {rule.id}</span>
                                </div>
                            </div>
                        </div>

                        <div className="flex items-center gap-12">
                            <div className="hidden md:flex flex-col items-end">
                                <span className="text-xs text-gray-400 font-medium uppercase tracking-tight">Hits (24h)</span>
                                <span className="text-lg font-bold text-gray-900 dark:text-white">{rule.alertCount}</span>
                            </div>
                            <div className="hidden lg:flex flex-col items-end">
                                <span className="text-xs text-gray-400 font-medium uppercase tracking-tight">TPR</span>
                                <span className="text-lg font-bold text-green-600">{rule.tpr}</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <button className={cn(
                                    "p-2 rounded-lg transition-colors border",
                                    rule.enabled
                                        ? "text-orange-600 border-orange-100 bg-orange-50 hover:bg-orange-100 dark:bg-orange-950/20 dark:border-orange-900/50"
                                        : "text-green-600 border-green-100 bg-green-50 hover:bg-green-100 dark:bg-green-950/20 dark:border-green-900/50"
                                )}>
                                    {rule.enabled ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                                </button>
                                <button className="p-2 rounded-lg border border-gray-100 text-gray-400 hover:text-red-600 hover:bg-red-50 transition-all dark:border-gray-800 dark:hover:bg-red-950/20">
                                    <Trash2 className="h-4 w-4" />
                                </button>
                                <button className="flex items-center gap-2 p-2 px-4 rounded-lg bg-gray-50 text-gray-900 font-medium hover:bg-gray-100 transition-colors dark:bg-gray-900 dark:text-white">
                                    <span>Edit</span>
                                    <ChevronRight className="h-4 w-4" />
                                </button>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
