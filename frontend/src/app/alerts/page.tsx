"use client";

import { useEffect, useState } from "react";
import { Bell, AlertTriangle, FileText, ExternalLink } from "lucide-react";
import Link from "next/link";
import { format } from "date-fns";
import { getAlerts } from "@/lib/api";

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

export default function AlertsPage() {
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const [loading, setLoading] = useState(true);

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

    const getAlertType = (eventType: string) => {
        if (eventType === 'new_doc') return 'success';
        if (eventType === 'updated_doc') return 'info';
        if (eventType === 'new_version') return 'info';
        return 'info';
    };

    const getAlertTitle = (alert: Alert) => {
        if (alert.event_type === 'new_doc') return 'New Document Published';
        if (alert.event_type === 'updated_doc') return 'Document Updated';
        if (alert.event_type === 'new_version') return 'New Version Available';
        return 'Document Alert';
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="text-lg">Loading alerts...</div>
            </div>
        );
    }

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div>
                <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-gray-100 sm:text-4xl">
                    Alerts
                </h1>
                <p className="mt-2 text-lg text-gray-600 dark:text-gray-400">
                    Recent updates from your watchlists.
                </p>
            </div>

            <div className="space-y-4">
                {alerts.map((alert) => {
                    const alertType = getAlertType(alert.event_type);
                    return (
                        <div key={alert.id} className="flex gap-4 rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-950">
                            <div className="flex-shrink-0">
                                <div className={`rounded-full p-2 ${
                                    alertType === 'success' ? 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400' :
                                    'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400'
                                }`}>
                                    <Bell className="h-6 w-6" />
                                </div>
                            </div>
                            <div className="flex-grow space-y-1">
                                <div className="flex items-center justify-between">
                                    <h3 className="font-semibold text-gray-900 dark:text-gray-100">{getAlertTitle(alert)}</h3>
                                    <span className="text-sm text-gray-500">{format(new Date(alert.detected_at), 'PPP p')}</span>
                                </div>
                                <p className="text-sm text-gray-600 dark:text-gray-400">
                                    Type: <span className="font-medium text-gray-900 dark:text-gray-200 capitalize">{alert.event_type.replace('_', ' ')}</span>
                                </p>
                                {alert.document && (
                                    <>
                                        <p className="text-gray-700 dark:text-gray-300">
                                            {alert.document.title}
                                        </p>
                                        <div className="pt-2">
                                            <Link href={`/doc/${alert.document.celex}`} className="inline-flex items-center text-sm font-medium text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300">
                                                View Document <ExternalLink className="ml-1 h-3 w-3" />
                                            </Link>
                                        </div>
                                    </>
                                )}
                            </div>
                        </div>
                    );
                })}
                {alerts.length === 0 && (
                    <div className="text-center py-12 text-gray-500">
                        No new alerts.
                    </div>
                )}
            </div>
        </div>
    );
}
