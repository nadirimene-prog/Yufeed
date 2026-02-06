"use client";

import { useState } from "react";
import { Bell, AlertTriangle, FileText, Clock, CheckSquare, Square, Archive } from "lucide-react";
import Link from "next/link";
import { format } from "date-fns";
import { useAlerts, useBulkUpdateAlerts } from "@/hooks/queries/useAlertData";
import { LoadingBoundary } from "@/components/shared";
import { StatusIndicator } from "@/components/ui/status-indicator";
import { EmptyState } from "@/components/ui/empty-state";
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
    const [filter, setFilter] = useState<AlertFilter>('all');
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedAlerts, setSelectedAlerts] = useState<Set<number>>(new Set());

    // React Query hook replaces useState + useEffect + getAlerts
    const { data: alerts = [], isLoading, error } = useAlerts();
    const { mutate: bulkUpdate, isPending: processingBulk } = useBulkUpdateAlerts();

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

    const handleBulkAcknowledge = () => {
        bulkUpdate(
            {
                ids: Array.from(selectedAlerts).map(String),
                data: { status: 'acknowledged' },
            },
            {
                onSuccess: () => setSelectedAlerts(new Set()),
            }
        );
    };

    const handleBulkArchive = () => {
        bulkUpdate(
            {
                ids: Array.from(selectedAlerts).map(String),
                data: { status: 'archived' },
            },
            {
                onSuccess: () => setSelectedAlerts(new Set()),
            }
        );
    };

    return (
        <LoadingBoundary
            loading={isLoading}
            error={error}
            isEmpty={alerts.length === 0}
            emptyMessage="No alerts found"
            emptyDescription="You'll see alerts here when documents in your watchlists are updated"
        >
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
                        Updated Documents ({alertStats.updated_doc})
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

                {/* Bulk Actions */}
                {selectedAlerts.size > 0 && (
                    <div className="flex items-center gap-3 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                        <span className="text-sm font-medium text-blue-900 dark:text-blue-100">
                            {selectedAlerts.size} alert{selectedAlerts.size > 1 ? 's' : ''} selected
                        </span>
                        <button
                            onClick={handleBulkAcknowledge}
                            disabled={processingBulk}
                            className="px-3 py-1.5 text-sm font-medium text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/40 rounded-md transition-colors disabled:opacity-50"
                        >
                            Acknowledge
                        </button>
                        <button
                            onClick={handleBulkArchive}
                            disabled={processingBulk}
                            className="px-3 py-1.5 text-sm font-medium text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/40 rounded-md transition-colors disabled:opacity-50"
                        >
                            <Archive className="h-4 w-4 inline mr-1" />
                            Archive
                        </button>
                    </div>
                )}

                {/* Alerts List */}
                <div className="space-y-3">
                    {filteredAlerts.map((alert) => {
                        const config = getAlertConfig(alert.event_type);
                        const AlertIcon = config.icon;
                        const isSelected = selectedAlerts.has(alert.id);

                        return (
                            <div
                                key={alert.id}
                                className={cn(
                                    'group relative flex items-start gap-4 p-4 bg-white dark:bg-slate-900 border rounded-lg transition-all hover:shadow-md',
                                    config.borderColor,
                                    isSelected && 'ring-2 ring-blue-500 dark:ring-blue-400'
                                )}
                            >
                                {/* Selection Checkbox */}
                                <button
                                    onClick={() => toggleSelectAlert(alert.id)}
                                    className="flex-shrink-0 mt-1"
                                    aria-label={isSelected ? 'Deselect alert' : 'Select alert'}
                                >
                                    {isSelected ? (
                                        <CheckSquare className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                                    ) : (
                                        <Square className="h-5 w-5 text-gray-400 dark:text-gray-600 group-hover:text-gray-600 dark:group-hover:text-gray-400 transition-colors" />
                                    )}
                                </button>

                                {/* Alert Icon */}
                                <div className={cn('flex-shrink-0 p-2 rounded-lg', config.bgColor)}>
                                    <AlertIcon className={cn('h-5 w-5', config.color)} />
                                </div>

                                {/* Alert Content */}
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-start justify-between gap-4">
                                        <div>
                                            <div className="flex items-center gap-2 mb-1">
                                                <span className={cn('text-xs font-semibold uppercase tracking-wide', config.color)}>
                                                    {config.title}
                                                </span>
                                                <StatusIndicator status={config.status} size="sm" />
                                            </div>
                                            <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-1">
                                                {alert.document?.title || 'Untitled Document'}
                                            </h3>
                                            <p className="text-sm text-gray-600 dark:text-gray-400">
                                                CELEX: {alert.document?.celex || 'N/A'}
                                            </p>
                                        </div>
                                        <time className="flex-shrink-0 text-xs text-gray-500 dark:text-gray-400">
                                            {format(new Date(alert.detected_at), 'MMM d, h:mm a')}
                                        </time>
                                    </div>
                                </div>

                                {/* View Document Link */}
                                {alert.doc_id && (
                                    <Link
                                        href={`/documents/${alert.doc_id}`}
                                        className="flex-shrink-0 text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
                                        aria-label="View document"
                                    >
                                        <span className="sr-only">View document</span>
                                        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                        </svg>
                                    </Link>
                                )}
                            </div>
                        );
                    })}
                </div>

                {/* Select All Button */}
                {filteredAlerts.length > 0 && (
                    <button
                        onClick={toggleSelectAll}
                        className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium transition-colors"
                    >
                        {selectedAlerts.size === filteredAlerts.length ? 'Deselect All' : 'Select All'}
                    </button>
                )}
            </div>
        </LoadingBoundary>
    );
}
