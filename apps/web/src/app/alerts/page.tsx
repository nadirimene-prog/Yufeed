"use client";

import { useEffect, useState } from "react";
import { Bell, AlertTriangle, FileText, ExternalLink, Filter, Check, Clock, Search, CheckSquare, Square, X, Archive } from "lucide-react";
import Link from "next/link";
import { format } from "date-fns";
import { getAlerts } from "@/lib/api";
import { StatusIndicator } from "@/components/ui/status-indicator";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface Alert {
    id: number;
    doc_id: number;
    watchlist_id?: number;
    event_type: string;
    detected_at: string;
    document?: {
        celex: string;
        title: string;
    };
}

type AlertFilter = 'all' | 'new_doc' | 'updated_doc' | 'new_version';

export default function AlertsPage() {
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<AlertFilter>('all');
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedAlerts, setSelectedAlerts] = useState<Set<number>>(new Set());
    const [processingBulk, setProcessingBulk] = useState(false);

    useEffect(() => {
        loadAlerts();
    }, []);

    const loadAlerts = async () => {
        try {
            const data = await getAlerts();
            setAlerts(data);
        } catch (error) {
            console.error("Failed to load alerts:", error);
        } finally {
            setLoading(false);
        }
    };

    const getAlertConfig = (eventType: string) => {
        const configs = {
            'new_doc': {
                title: 'New Document',
                color: 'text-green-600 dark:text-green-400',
                bgColor: 'bg-green-100 dark:bg-green-900/20',
                borderColor: 'border-green-200 dark:border-green-800',
                status: 'success' as const,
                icon: FileText,
            },
            'updated_doc': {
                title: 'Document Updated',
                color: 'text-blue-600 dark:text-blue-400',
                bgColor: 'bg-blue-100 dark:bg-blue-900/20',
                borderColor: 'border-blue-200 dark:border-blue-800',
                status: 'active' as const,
                icon: Bell,
            },
            'new_version': {
                title: 'New Version',
                color: 'text-yellow-600 dark:text-yellow-400',
                bgColor: 'bg-yellow-100 dark:bg-yellow-900/20',
                borderColor: 'border-yellow-200 dark:border-yellow-800',
                status: 'warning' as const,
                icon: AlertTriangle,
            },
        };
        return configs[eventType as keyof typeof configs] || configs.updated_doc;
    };

    const filteredAlerts = alerts.filter(alert => {
        const matchesFilter = filter === 'all' || alert.event_type === filter;
        const matchesSearch = !searchQuery ||
            alert.document?.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
            alert.document?.celex.toLowerCase().includes(searchQuery.toLowerCase());
        return matchesFilter && matchesSearch;
    });

    const alertStats = {
        total: alerts.length,
        new_doc: alerts.filter(a => a.event_type === 'new_doc').length,
        updated_doc: alerts.filter(a => a.event_type === 'updated_doc').length,
        new_version: alerts.filter(a => a.event_type === 'new_version').length,
    };

    const toggleSelectAll = () => {
        if (selectedAlerts.size === filteredAlerts.length) {
            setSelectedAlerts(new Set());
        } else {
            setSelectedAlerts(new Set(filteredAlerts.map(a => a.id)));
        }
    };

    const toggleSelectAlert = (id: number) => {
        const newSelected = new Set(selectedAlerts);
        if (newSelected.has(id)) {
            newSelected.delete(id);
        } else {
            newSelected.add(id);
        }
        setSelectedAlerts(newSelected);
    };

    const handleBulkAcknowledge = async () => {
        setProcessingBulk(true);
        try {
            // Simulate API call
            await new Promise(resolve => setTimeout(resolve, 1000));
            // console.log('Acknowledged alerts:', Array.from(selectedAlerts));
            setSelectedAlerts(new Set());
        } finally {
            setProcessingBulk(false);
        }
    };

    const handleBulkArchive = async () => {
        setProcessingBulk(true);
        try {
            // Simulate API call
            await new Promise(resolve => setTimeout(resolve, 1000));
            // console.log('Archived alerts:', Array.from(selectedAlerts));
            setSelectedAlerts(new Set());
        } finally {
            setProcessingBulk(false);
        }
    };

    if (loading) {
        return (
            <div className="space-y-8 animate-fade-in">
                <div>
                    <div className="h-10 w-48 bg-gray-200 dark:bg-slate-700 rounded animate-pulse mb-2" />
                    <div className="h-6 w-96 bg-gray-100 dark:bg-slate-800 rounded animate-pulse" />
                </div>
                <TableSkeleton rows={5} />
            </div>
        );
    }

    return (
        <div className="space-y-8 animate-slide-up">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">
                        Alerts
                    </h1>
                    <p className="mt-2 text-gray-600 dark:text-gray-400">
                        Recent updates from your watchlists
                    </p>
                </div>
                <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                    <Clock className="h-4 w-4" />
                    <span>{alerts.length} total alerts</span>
                </div>
            </div>

            {/* Filter Tabs */}
            <div className="bg-white dark:bg-slate-900 rounded-lg border border-gray-200 dark:border-slate-800 p-1 inline-flex gap-1">
                <button
                    onClick={() => setFilter('all')}
                    className={cn(
                        'px-4 py-2 text-sm font-medium rounded-md transition-colors',
                        filter === 'all'
                            ? 'bg-gray-100 dark:bg-slate-800 text-gray-900 dark:text-white'
                            : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                    )}
                >
                    All ({alertStats.total})
                </button>
                <button
                    onClick={() => setFilter('new_doc')}
                    className={cn(
                        'px-4 py-2 text-sm font-medium rounded-md transition-colors',
                        filter === 'new_doc'
                            ? 'bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400'
                            : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                    )}
                >
                    New Documents ({alertStats.new_doc})
                </button>
                <button
                    onClick={() => setFilter('updated_doc')}
                    className={cn(
                        'px-4 py-2 text-sm font-medium rounded-md transition-colors',
                        filter === 'updated_doc'
                            ? 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400'
                            : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                    )}
                >
                    Updated ({alertStats.updated_doc})
                </button>
                <button
                    onClick={() => setFilter('new_version')}
                    className={cn(
                        'px-4 py-2 text-sm font-medium rounded-md transition-colors',
                        filter === 'new_version'
                            ? 'bg-yellow-100 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-400'
                            : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                    )}
                >
                    New Versions ({alertStats.new_version})
                </button>
            </div>

            {/* Bulk Actions Bar */}
            {selectedAlerts.size > 0 && (
                <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <CheckSquare className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                        <span className="font-medium text-blue-900 dark:text-blue-100">
                            {selectedAlerts.size} alert{selectedAlerts.size === 1 ? '' : 's'} selected
                        </span>
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={handleBulkAcknowledge}
                            disabled={processingBulk}
                            className="px-4 py-2 text-sm font-medium text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/40 rounded-md transition-colors disabled:opacity-50 flex items-center gap-2"
                        >
                            <Check className="h-4 w-4" />
                            Acknowledge All
                        </button>
                        <button
                            onClick={handleBulkArchive}
                            disabled={processingBulk}
                            className="px-4 py-2 text-sm font-medium text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/40 rounded-md transition-colors disabled:opacity-50 flex items-center gap-2"
                        >
                            <Archive className="h-4 w-4" />
                            Archive
                        </button>
                        <button
                            onClick={() => setSelectedAlerts(new Set())}
                            className="px-3 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-800 rounded-md transition-colors"
                        >
                            <X className="h-4 w-4" />
                        </button>
                    </div>
                </div>
            )}

            {/* Search Bar */}
            <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                    type="text"
                    placeholder="Search alerts by document title or CELEX..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-3 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-lg text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
                />
            </div>

            {/* Alerts List */}
            <div className="space-y-3">
                {filteredAlerts.length > 0 && (
                    <div className="flex items-center gap-3 px-2 py-2">
                        <button
                            onClick={toggleSelectAll}
                            className="p-1 hover:bg-gray-100 dark:hover:bg-slate-800 rounded transition-colors"
                        >
                            {selectedAlerts.size === filteredAlerts.length ? (
                                <CheckSquare className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                            ) : (
                                <Square className="h-5 w-5 text-gray-400" />
                            )}
                        </button>
                        <span className="text-sm text-gray-600 dark:text-gray-400">
                            {selectedAlerts.size > 0 ? `${selectedAlerts.size} selected` : 'Select all'}
                        </span>
                    </div>
                )}

                {filteredAlerts.length === 0 ? (
                    <EmptyState
                        variant={searchQuery ? "no-results" : "no-data"}
                        title={searchQuery ? "No matching alerts" : "No alerts yet"}
                        description={searchQuery ? "Try adjusting your search criteria" : "New alerts will appear here when documents are updated"}
                    />
                ) : (
                    filteredAlerts.map((alert) => {
                        const config = getAlertConfig(alert.event_type);
                        const Icon = config.icon;

                        const isSelected = selectedAlerts.has(alert.id);

                        return (
                            <div
                                key={alert.id}
                                className={cn(
                                    'group bg-white dark:bg-slate-900 rounded-lg border shadow-sm hover:shadow-md transition-all',
                                    isSelected
                                        ? 'border-blue-500 dark:border-blue-400 bg-blue-50/50 dark:bg-blue-900/10'
                                        : 'border-gray-200 dark:border-slate-800 hover:border-gray-300 dark:hover:border-slate-700'
                                )}
                            >
                                <div className="p-6">
                                    <div className="flex gap-4">
                                        {/* Checkbox */}
                                        <div className="flex-shrink-0 pt-1">
                                            <button
                                                onClick={() => toggleSelectAlert(alert.id)}
                                                className="p-1 hover:bg-gray-100 dark:hover:bg-slate-800 rounded transition-colors"
                                            >
                                                {isSelected ? (
                                                    <CheckSquare className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                                                ) : (
                                                    <Square className="h-5 w-5 text-gray-400" />
                                                )}
                                            </button>
                                        </div>

                                        {/* Icon */}
                                        <div className="flex-shrink-0">
                                            <div className={cn('rounded-lg p-3', config.bgColor, config.borderColor, 'border')}>
                                                <Icon className={cn('h-6 w-6', config.color)} />
                                            </div>
                                        </div>

                                        {/* Content */}
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-start justify-between gap-4 mb-2">
                                                <div className="flex items-center gap-3">
                                                    <h3 className="font-semibold text-gray-900 dark:text-white">
                                                        {config.title}
                                                    </h3>
                                                    <StatusIndicator status={config.status} size="sm" />
                                                </div>
                                                <time className="text-sm text-gray-500 dark:text-gray-400 whitespace-nowrap">
                                                    {format(new Date(alert.detected_at), 'MMM d, h:mm a')}
                                                </time>
                                            </div>

                                            {alert.document && (
                                                <>
                                                    <p className="text-gray-900 dark:text-white mb-2 line-clamp-2">
                                                        {alert.document.title}
                                                    </p>
                                                    <div className="flex items-center justify-between">
                                                        <p className="text-xs text-gray-500 dark:text-gray-400 font-mono">
                                                            {alert.document.celex}
                                                        </p>
                                                        <Link
                                                            href={`/doc/${alert.document.celex}`}
                                                            className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 transition-colors"
                                                        >
                                                            View Document
                                                            <ExternalLink className="h-3 w-3" />
                                                        </Link>
                                                    </div>
                                                </>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
}
