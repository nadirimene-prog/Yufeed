"use client";

import { useEffect, useState } from "react";
import { TimelineEvent, getDocumentTimeline } from "@/lib/compliance-api";
import { format } from "date-fns";
import { CheckCircle, Circle, ArrowDown, FileText, Scale, History, FileClock } from "lucide-react";
import { cn } from "@/lib/utils";
import Link from "next/link";

interface TimelineViewProps {
    celex: string;
}

export function TimelineView({ celex }: TimelineViewProps) {
    const [events, setEvents] = useState<TimelineEvent[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchTimeline = async () => {
            try {
                const data = await getDocumentTimeline(celex);
                // Sort by date descending (newest first)
                setEvents(data.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()));
            } catch (error) {
                console.error("Failed to load timeline", error);
            } finally {
                setLoading(false);
            }
        };

        fetchTimeline();
    }, [celex]);

    if (loading) {
        return <div className="p-4 text-center text-gray-500 animate-pulse">Loading legislative history...</div>;
    }

    const getIcon = (type: TimelineEvent['type']) => {
        switch (type) {
            case 'ENTRY_INTO_FORCE': return CheckCircle;
            case 'PUBLICATION': return FileText;
            case 'PROPOSAL': return FileClock;
            case 'AMENDMENT': return Scale;
            case 'REPEAL': return History;
            default: return Circle;
        }
    };

    const getColor = (type: TimelineEvent['type']) => {
        switch (type) {
            case 'ENTRY_INTO_FORCE': return 'text-green-600 bg-green-100 dark:bg-green-900/20 dark:text-green-400 border-green-200 dark:border-green-800';
            case 'PUBLICATION': return 'text-blue-600 bg-blue-100 dark:bg-blue-900/20 dark:text-blue-400 border-blue-200 dark:border-blue-800';
            case 'AMENDMENT': return 'text-purple-600 bg-purple-100 dark:bg-purple-900/20 dark:text-purple-400 border-purple-200 dark:border-purple-800';
            case 'REPEAL': return 'text-red-600 bg-red-100 dark:bg-red-900/20 dark:text-red-400 border-red-200 dark:border-red-800';
            default: return 'text-gray-600 bg-gray-100 dark:bg-gray-800 dark:text-gray-400 border-gray-200 dark:border-gray-700';
        }
    };

    return (
        <div className="bg-white dark:bg-slate-900 rounded-lg border border-gray-200 dark:border-slate-800 shadow-sm p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6 flex items-center gap-2">
                <History className="h-5 w-5" />
                Legislative History
            </h3>

            <div className="relative pl-6 border-l-2 border-gray-200 dark:border-slate-800 space-y-8">
                {events.map((event, index) => {
                    const Icon = getIcon(event.type);
                    const colorClass = getColor(event.type);

                    return (
                        <div key={event.id} className="relative group">
                            {/* Dot on timeline */}
                            <div className={cn(
                                "absolute -left-[31px] top-1 h-6 w-6 rounded-full border-2 flex items-center justify-center transition-transform group-hover:scale-110 bg-white dark:bg-slate-900",
                                colorClass
                            )}>
                                <Icon className="h-3 w-3" />
                            </div>

                            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2">
                                <div>
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className={cn(
                                            "text-xs font-bold px-2 py-0.5 rounded uppercase tracking-wider",
                                            colorClass
                                        )}>
                                            {event.type.replace(/_/g, ' ')}
                                        </span>
                                        <span className="text-sm text-gray-500 dark:text-gray-400 font-mono">
                                            {format(new Date(event.date), 'dd MMM yyyy')}
                                        </span>
                                    </div>
                                    <h4 className="font-medium text-gray-900 dark:text-white">
                                        {event.title}
                                    </h4>
                                    {event.description && (
                                        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 max-w-xl">
                                            {event.description}
                                        </p>
                                    )}
                                </div>

                                {event.related_doc_celex && (
                                    <Link
                                        href={`/doc/${event.related_doc_celex}`}
                                        className="shrink-0 text-xs font-medium text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 border border-blue-200 dark:border-slate-700 rounded px-2 py-1 hover:bg-blue-50 dark:hover:bg-blue-900/30 transition-colors"
                                    >
                                        View Doc &rarr;
                                    </Link>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
