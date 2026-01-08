"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2, Mail, Clock, ShieldCheck, FileText, Rss } from "lucide-react";
import { cn } from "@/lib/utils";
import { getWatchlists, createWatchlist } from "@/lib/api";

interface Watchlist {
    id: number;
    name: string;
    mode: string;
    rss_url: string | null;
    query_json: any;
    curated_celex_json: any;
    recipients_json: any;
    schedule: string;
}

export default function WatchlistsPage() {
    const [watchlists, setWatchlists] = useState<Watchlist[]>([]);
    const [loading, setLoading] = useState(true);
    const [isCreating, setIsCreating] = useState(false);
    const [newWatchlist, setNewWatchlist] = useState({
        name: "",
        mode: "email",
        rss_url: "",
        query_json: {},
        curated_celex_json: null,
        recipients_json: [""],
        schedule: "daily"
    });

    useEffect(() => {
        loadWatchlists();
    }, []);

    const loadWatchlists = async () => {
        try {
            const data = await getWatchlists();
            setWatchlists(data);
        } catch (error) {
            console.error("Failed to load watchlists:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleCreate = async () => {
        // Validate
        if (!newWatchlist.name) return;

        try {
            await createWatchlist(newWatchlist);
            await loadWatchlists();
            setIsCreating(false);
            setNewWatchlist({
                name: "",
                mode: "email",
                rss_url: "",
                query_json: {},
                curated_celex_json: null,
                recipients_json: [""],
                schedule: "daily"
            });
        } catch (error) {
            console.error("Failed to create watchlist:", error);
            alert("Failed to create watchlist. Please try again.");
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="text-lg">Loading watchlists...</div>
            </div>
        );
    }

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-gray-100 sm:text-4xl">
                        Watchlists
                    </h1>
                    <p className="mt-2 text-lg text-gray-600 dark:text-gray-400">
                        Manage your legal monitoring feeds and alerts.
                    </p>
                </div>
                <button
                    onClick={() => setIsCreating(true)}
                    className="flex items-center rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
                >
                    <Plus className="mr-2 h-4 w-4" />
                    New Watchlist
                </button>
            </div>

            {isCreating && (
                <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-lg dark:border-gray-800 dark:bg-gray-950">
                    <h2 className="text-xl font-semibold mb-6">Create New Watchlist</h2>
                    <div className="grid gap-6">
                        <div className="space-y-2">
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Name</label>
                            <input
                                type="text"
                                value={newWatchlist.name}
                                onChange={(e) => setNewWatchlist({ ...newWatchlist, name: e.target.value })}
                                className="w-full rounded-md border border-gray-300 px-3 py-2 bg-white dark:bg-gray-900 dark:border-gray-700"
                                placeholder="e.g. AML Regulations Tracker"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">RSS URL (Optional)</label>
                            <input
                                type="text"
                                value={newWatchlist.rss_url}
                                onChange={(e) => setNewWatchlist({ ...newWatchlist, rss_url: e.target.value })}
                                className="w-full rounded-md border border-gray-300 px-3 py-2 bg-white dark:bg-gray-900 dark:border-gray-700"
                                placeholder="https://eur-lex.europa.eu/..."
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Recipients (comma separated)</label>
                            <input
                                type="text"
                                value={newWatchlist.recipients_json.join(", ")}
                                onChange={(e) => setNewWatchlist({ ...newWatchlist, recipients_json: e.target.value.split(",").map(s => s.trim()) })}
                                className="w-full rounded-md border border-gray-300 px-3 py-2 bg-white dark:bg-gray-900 dark:border-gray-700"
                                placeholder="user@example.com, team@example.com"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Schedule</label>
                            <select
                                value={newWatchlist.schedule}
                                onChange={(e) => setNewWatchlist({ ...newWatchlist, schedule: e.target.value })}
                                className="w-full rounded-md border border-gray-300 px-3 py-2 bg-white dark:bg-gray-900 dark:border-gray-700"
                            >
                                <option value="daily">Daily</option>
                                <option value="weekly">Weekly</option>
                            </select>
                        </div>
                    </div>
                    <div className="mt-6 flex justify-end gap-3">
                        <button onClick={() => setIsCreating(false)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900">Cancel</button>
                        <button onClick={handleCreate} className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">Create Watchlist</button>
                    </div>
                </div>
            )}

            {watchlists.length === 0 ? (
                <div className="text-center py-12">
                    <p className="text-gray-500">No watchlists yet. Create your first one to get started!</p>
                </div>
            ) : (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                    {watchlists.map((list) => (
                        <div key={list.id} className="group relative rounded-xl border border-gray-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md dark:border-gray-800 dark:bg-gray-950">
                            <div className="flex items-center gap-3 mb-4">
                                <div className="rounded-lg p-2 bg-blue-100 text-blue-600">
                                    {list.rss_url ? <Rss className="h-5 w-5" /> : <FileText className="h-5 w-5" />}
                                </div>
                                <h3 className="font-semibold text-gray-900 dark:text-gray-100">{list.name}</h3>
                            </div>

                            <div className="space-y-3 text-sm text-gray-600 dark:text-gray-400">
                                <div className="flex items-center gap-2">
                                    <Clock className="h-4 w-4" />
                                    <span>Schedule: <span className="font-medium text-gray-900 dark:text-white capitalize">{list.schedule}</span></span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <Mail className="h-4 w-4" />
                                    <span>{list.recipients_json?.length || 0} Recipient(s)</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <ShieldCheck className="h-4 w-4" />
                                    <span>Mode: {list.mode}</span>
                                </div>
                            </div>

                            {list.rss_url && (
                                <div className="mt-5 pt-4 border-t border-gray-100 dark:border-gray-800">
                                    <p className="truncate text-xs text-gray-400 font-mono" title={list.rss_url}>{list.rss_url}</p>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
