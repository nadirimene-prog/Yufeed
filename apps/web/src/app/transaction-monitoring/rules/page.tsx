"use client";

import { useEffect, useMemo, useState } from "react";
import {
    Plus,
    Search,
    Settings2,
    Play,
    Pause,
    Trash2,
    ChevronRight,
    Activity,
    ShieldAlert,
    CheckCircle2,
    TrendingUp
} from "lucide-react";
import { cn } from "@/lib/utils";
import { fetchWithAuth } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/apiBaseUrl";
import { useRules } from "@/hooks/queries/useRulesData";
import { LoadingBoundary } from "@/components/shared/LoadingBoundary";

const API_URL = getApiBaseUrl();

type Rule = {
    id: number;
    rule_id: string;
    name: string;
    description?: string | null;
    category?: string | null;
    severity: string;
    enabled: boolean;
    conditions: Record<string, unknown>;
    thresholds?: Record<string, unknown> | null;
    alert_count: number;
    true_positive_rate?: number | null;
};

type RuleVersion = {
    id: number;
    rule_id: number;
    version_number: number;
    status: string;
    name: string;
    category?: string | null;
    severity: string;
    enabled: boolean;
    created_at: string;
    notes?: string | null;
    conditions?: Record<string, unknown>;
    thresholds?: Record<string, unknown> | null;
};

export default function RuleManagementPage() {
    const { data: rules = [], isLoading, error: queryError } = useRules({ limit: 200 });
    const [saving, setSaving] = useState(false);
    const [editingRule, setEditingRule] = useState<Rule | null>(null);
    const [searchTerm, setSearchTerm] = useState("");
    const [severityFilter, setSeverityFilter] = useState("all");
    const [enabledFilter, setEnabledFilter] = useState("all");
    const [categoryFilter, setCategoryFilter] = useState("all");
    type RulesOverview = {
        total_rules?: number;
        enabled_rules?: number;
        rules_with_regulatory_linkage?: number;
        total_alerts_generated?: number;
    };
    const [overview, setOverview] = useState<RulesOverview | null>(null);
    type TopRule = {
        rule_id: string;
        name: string;
        alert_count: number;
    };
    const [topRules, setTopRules] = useState<TopRule[]>([]);
    const [pendingVersions, setPendingVersions] = useState<RuleVersion[]>([]);
    const [activeVersion, setActiveVersion] = useState<RuleVersion | null>(null);

    const [editName, setEditName] = useState("");
    const [editDescription, setEditDescription] = useState("");
    const [editSeverity, setEditSeverity] = useState("medium");
    const [editEnabled, setEditEnabled] = useState(true);
    const [editConditions, setEditConditions] = useState("{}");
    const [editThresholds, setEditThresholds] = useState("{}");
    const [editNotes, setEditNotes] = useState("");


    const fetchOverview = async () => {
        try {
            const res = await fetchWithAuth(`${API_URL}/api/monitoring-rules/statistics/overview`);
            if (!res.ok) throw new Error(await res.text());
            setOverview(await res.json());
        } catch {
            setOverview(null);
        }
    };

    const fetchTopRules = async () => {
        try {
            const res = await fetchWithAuth(
                `${API_URL}/api/monitoring-rules/performance/top-performers?limit=5&metric=alert_count`
            );
            if (!res.ok) throw new Error(await res.text());
            setTopRules(await res.json());
        } catch {
            setTopRules([]);
        }
    };

    const fetchPendingVersions = async () => {
        try {
            const res = await fetchWithAuth(`${API_URL}/api/monitoring-rules/versions?status=pending`);
            if (!res.ok) throw new Error(await res.text());
            setPendingVersions(await res.json());
        } catch {
            setPendingVersions([]);
        }
    };

    useEffect(() => {
        fetchOverview();
        fetchTopRules();
        fetchPendingVersions();
    }, []);

    const handleToggle = async (rule: Rule) => {
        setError(null);
        try {
            const endpoint = rule.enabled ? "disable" : "enable";
            const res = await fetchWithAuth(`${API_URL}/api/monitoring-rules/${rule.rule_id}/${endpoint}`, {
                method: "POST",
            });
            if (!res.ok) throw new Error(await res.text());
            setRules((prev) =>
                prev.map((item) =>
                    item.rule_id === rule.rule_id ? { ...item, enabled: !rule.enabled } : item
                )
            );
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to update rule");
        }
    };

    const handleDelete = async (rule: Rule) => {
        if (!confirm(`Delete ${rule.name}? This cannot be undone.`)) return;
        setError(null);
        try {
            const res = await fetchWithAuth(`${API_URL}/api/monitoring-rules/${rule.rule_id}`, {
                method: "DELETE",
            });
            if (!res.ok) throw new Error(await res.text());
            setRules((prev) => prev.filter((item) => item.rule_id !== rule.rule_id));
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to delete rule");
        }
    };

    const openEdit = (rule: Rule) => {
        setEditingRule(rule);
        setEditName(rule.name);
        setEditDescription(rule.description || "");
        setEditSeverity(rule.severity || "medium");
        setEditEnabled(rule.enabled);
        setEditConditions(JSON.stringify(rule.conditions || {}, null, 2));
        setEditThresholds(JSON.stringify(rule.thresholds || {}, null, 2));
        setEditNotes("");
        setError(null);
    };

    const handleSubmitForApproval = async () => {
        if (!editingRule) return;
        setSaving(true);
        setError(null);
        try {
            const conditions = editConditions.trim() ? JSON.parse(editConditions) : undefined;
            const thresholds = editThresholds.trim() ? JSON.parse(editThresholds) : undefined;
            const payload: Record<string, unknown> = {
                name: editName,
                description: editDescription || undefined,
                severity: editSeverity,
                enabled: editEnabled,
                notes: editNotes || undefined,
            };
            if (conditions !== undefined) payload.conditions = conditions;
            if (thresholds !== undefined) payload.thresholds = thresholds;

            const res = await fetchWithAuth(`${API_URL}/api/monitoring-rules/${editingRule.rule_id}/versions`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            if (!res.ok) throw new Error(await res.text());
            await fetchPendingVersions();
            setEditingRule(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to submit for approval");
        } finally {
            setSaving(false);
        }
    };

    const handleApproveVersion = async (versionId: number) => {
        setError(null);
        try {
            const res = await fetchWithAuth(`${API_URL}/api/monitoring-rules/versions/${versionId}/approve`, {
                method: "POST",
            });
            if (!res.ok) throw new Error(await res.text());
            await fetchPendingVersions();
            await fetchRules();
            await fetchOverview();
            await fetchTopRules();
            setActiveVersion(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to approve version");
        }
    };

    const handleRejectVersion = async (versionId: number) => {
        setError(null);
        try {
            const res = await fetchWithAuth(`${API_URL}/api/monitoring-rules/versions/${versionId}/reject`, {
                method: "POST",
            });
            if (!res.ok) throw new Error(await res.text());
            await fetchPendingVersions();
            setActiveVersion(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to reject version");
        }
    };

    const sortedRules = [...rules].sort((a, b) => (b.alert_count || 0) - (a.alert_count || 0));
    const categories = useMemo(() => {
        const values = new Set<string>();
        rules.forEach((rule) => {
            if (rule.category) values.add(rule.category);
        });
        return Array.from(values);
    }, [rules]);

    const filteredRules = useMemo(() => {
        const term = searchTerm.trim().toLowerCase();
        return sortedRules.filter((rule) => {
            const matchesSearch =
                !term ||
                rule.name.toLowerCase().includes(term) ||
                rule.rule_id.toLowerCase().includes(term) ||
                (rule.category || "").toLowerCase().includes(term);
            const matchesSeverity = severityFilter === "all" || rule.severity === severityFilter;
            const matchesEnabled =
                enabledFilter === "all" ||
                (enabledFilter === "enabled" ? rule.enabled : !rule.enabled);
            const matchesCategory =
                categoryFilter === "all" || (rule.category || "uncategorized") === categoryFilter;
            return matchesSearch && matchesSeverity && matchesEnabled && matchesCategory;
        });
    }, [sortedRules, searchTerm, severityFilter, enabledFilter, categoryFilter]);

    return (
        <LoadingBoundary
            loading={isLoading}
            error={queryError}
            isEmpty={!rules || rules.length === 0}
            emptyMessage="No monitoring rules configured"
            emptyDescription="Create your first rule to start monitoring transactions"
        >
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
                <div className="flex items-center gap-3">
                    <a
                        href="/transaction-monitoring/rules/lab"
                        className="flex items-center rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors shadow-sm dark:border-gray-800 dark:bg-gray-950 dark:text-gray-200 dark:hover:bg-gray-900"
                    >
                        Rule Lab
                    </a>
                    <a
                        href="/transaction-monitoring/rules/new"
                        className="flex items-center rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 transition-colors shadow-sm"
                    >
                        <Plus className="mr-2 h-4 w-4" />
                        Create Rule
                    </a>
                </div>
            </div>

            <div className="flex flex-col gap-4 sm:flex-row sm:items-center justify-between bg-white dark:bg-gray-950 p-4 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm">
                <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Search rules..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full rounded-lg border border-gray-200 bg-gray-50/50 py-2 pl-10 pr-4 text-sm focus:border-blue-500 focus:outline-none dark:border-gray-800 dark:bg-gray-900/50"
                    />
                </div>
                <div className="flex flex-wrap gap-2">
                    <select
                        value={severityFilter}
                        onChange={(e) => setSeverityFilter(e.target.value)}
                        className="px-3 py-1.5 text-sm font-medium text-gray-600 border border-gray-200 rounded-lg bg-white dark:border-gray-800 dark:bg-gray-950 dark:text-gray-300"
                    >
                        <option value="all">All severities</option>
                        <option value="low">low</option>
                        <option value="medium">medium</option>
                        <option value="high">high</option>
                        <option value="critical">critical</option>
                    </select>
                    <select
                        value={enabledFilter}
                        onChange={(e) => setEnabledFilter(e.target.value)}
                        className="px-3 py-1.5 text-sm font-medium text-gray-600 border border-gray-200 rounded-lg bg-white dark:border-gray-800 dark:bg-gray-950 dark:text-gray-300"
                    >
                        <option value="all">All statuses</option>
                        <option value="enabled">Enabled</option>
                        <option value="disabled">Disabled</option>
                    </select>
                    <select
                        value={categoryFilter}
                        onChange={(e) => setCategoryFilter(e.target.value)}
                        className="px-3 py-1.5 text-sm font-medium text-gray-600 border border-gray-200 rounded-lg bg-white dark:border-gray-800 dark:bg-gray-950 dark:text-gray-300"
                    >
                        <option value="all">All categories</option>
                        {categories.map((category) => (
                            <option key={category} value={category}>
                                {category}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-950">
                    <div className="flex items-center justify-between text-sm text-gray-500">
                        <span>Total Rules</span>
                        <Activity className="h-4 w-4 text-blue-600" />
                    </div>
                    <div className="mt-2 text-2xl font-semibold text-gray-900 dark:text-white">
                        {overview?.total_rules ?? rules.length}
                    </div>
                </div>
                <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-950">
                    <div className="flex items-center justify-between text-sm text-gray-500">
                        <span>Enabled Rules</span>
                        <CheckCircle2 className="h-4 w-4 text-green-600" />
                    </div>
                    <div className="mt-2 text-2xl font-semibold text-gray-900 dark:text-white">
                        {overview?.enabled_rules ?? rules.filter((rule) => rule.enabled).length}
                    </div>
                </div>
                <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-950">
                    <div className="flex items-center justify-between text-sm text-gray-500">
                        <span>Rules w/ Regs</span>
                        <ShieldAlert className="h-4 w-4 text-orange-600" />
                    </div>
                    <div className="mt-2 text-2xl font-semibold text-gray-900 dark:text-white">
                        {overview?.rules_with_regulatory_linkage ?? "—"}
                    </div>
                </div>
                <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-950">
                    <div className="flex items-center justify-between text-sm text-gray-500">
                        <span>Total Alerts</span>
                        <TrendingUp className="h-4 w-4 text-purple-600" />
                    </div>
                    <div className="mt-2 text-2xl font-semibold text-gray-900 dark:text-white">
                        {overview?.total_alerts_generated ?? "—"}
                    </div>
                </div>
            </div>

            <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-950">
                <div className="flex items-center justify-between">
                    <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Top Performing Rules</h2>
                    <span className="text-xs text-gray-500">by alert volume</span>
                </div>
                <div className="mt-4 space-y-2 text-sm">
                    {topRules.length ? (
                        topRules.map((rule) => (
                            <div key={rule.rule_id} className="flex items-center justify-between rounded-lg border border-gray-100 px-3 py-2 dark:border-gray-800">
                                <div>
                                    <div className="font-medium text-gray-900 dark:text-white">{rule.name}</div>
                                    <div className="text-xs text-gray-500">{rule.rule_id}</div>
                                </div>
                                <div className="text-xs text-gray-500">
                                    {rule.alert_count} alerts
                                </div>
                            </div>
                        ))
                    ) : (
                        <div className="text-xs text-gray-500">No rule stats yet.</div>
                    )}
                </div>
            </div>

            <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-950">
                <div className="flex items-center justify-between">
                    <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Pending Approvals</h2>
                    <span className="text-xs text-gray-500">{pendingVersions.length} pending</span>
                </div>
                <div className="mt-4 space-y-3 text-sm">
                    {pendingVersions.length ? (
                        pendingVersions.map((version) => (
                            <div
                                key={version.id}
                                className="flex flex-col gap-3 rounded-lg border border-gray-100 px-4 py-3 dark:border-gray-800"
                            >
                                <div className="flex items-center justify-between">
                                    <div>
                                        <div className="font-medium text-gray-900 dark:text-white">{version.name}</div>
                                        <div className="text-xs text-gray-500">
                                            Version {version.version_number} • {version.severity} • {version.category || "uncategorized"}
                                        </div>
                                    </div>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => setActiveVersion(version)}
                                            className="rounded-lg border border-gray-200 px-3 py-1 text-xs font-semibold text-gray-600 hover:bg-gray-50 dark:border-gray-800 dark:text-gray-300 dark:hover:bg-gray-900"
                                        >
                                            Review
                                        </button>
                                        <button
                                            onClick={() => handleApproveVersion(version.id)}
                                            className="rounded-lg bg-green-600 px-3 py-1 text-xs font-semibold text-white hover:bg-green-700"
                                        >
                                            Approve
                                        </button>
                                        <button
                                            onClick={() => handleRejectVersion(version.id)}
                                            className="rounded-lg border border-gray-200 px-3 py-1 text-xs font-semibold text-gray-600 hover:bg-gray-50 dark:border-gray-800 dark:text-gray-300 dark:hover:bg-gray-900"
                                        >
                                            Reject
                                        </button>
                                    </div>
                                </div>
                                {version.notes ? (
                                    <div className="text-xs text-gray-500">Note: {version.notes}</div>
                                ) : null}
                                <a
                                    href={`/audit?entity_type=rule_version&entity_id=${version.id}`}
                                    className="text-xs text-blue-600 hover:text-blue-700"
                                >
                                    View audit trail
                                </a>
                            </div>
                        ))
                    ) : (
                        <div className="text-xs text-gray-500">No pending approvals.</div>
                    )}
                </div>
            </div>

            {error && (
                <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/20 dark:text-red-300">
                    {error}
                </div>
            )}

            <div className="grid gap-4">
                {loading ? (
                    <div className="rounded-2xl border border-gray-200 bg-white p-6 text-sm text-gray-500 dark:border-gray-800 dark:bg-gray-950">
                        Loading rules...
                    </div>
                ) : filteredRules.length === 0 ? (
                    <div className="rounded-2xl border border-gray-200 bg-white p-6 text-sm text-gray-500 dark:border-gray-800 dark:bg-gray-950">
                        No monitoring rules found yet.
                    </div>
                ) : (
                    filteredRules.map((rule) => (
                        <div key={rule.rule_id} className="group flex items-center justify-between p-6 rounded-2xl border border-gray-200 bg-white hover:border-blue-200 hover:shadow-md transition-all dark:border-gray-800 dark:bg-gray-950 dark:hover:border-blue-900/50">
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
                                    <span className="capitalize">{rule.category || "uncategorized"}</span>
                                    <span className="h-1 w-1 rounded-full bg-gray-300" />
                                    <span>ID: {rule.rule_id}</span>
                                </div>
                            </div>
                        </div>

                        <div className="flex items-center gap-12">
                            <div className="hidden md:flex flex-col items-end">
                                <span className="text-xs text-gray-400 font-medium uppercase tracking-tight">Hits (24h)</span>
                                <span className="text-lg font-bold text-gray-900 dark:text-white">{rule.alert_count ?? 0}</span>
                            </div>
                            <div className="hidden lg:flex flex-col items-end">
                                <span className="text-xs text-gray-400 font-medium uppercase tracking-tight">TPR</span>
                                <span className="text-lg font-bold text-green-600">
                                    {rule.true_positive_rate ? `${rule.true_positive_rate}%` : "—"}
                                </span>
                            </div>
                            <div className="flex items-center gap-2">
                                <button className={cn(
                                    "p-2 rounded-lg transition-colors border",
                                    rule.enabled
                                        ? "text-orange-600 border-orange-100 bg-orange-50 hover:bg-orange-100 dark:bg-orange-950/20 dark:border-orange-900/50"
                                        : "text-green-600 border-green-100 bg-green-50 hover:bg-green-100 dark:bg-green-950/20 dark:border-green-900/50"
                                )} onClick={() => handleToggle(rule)}>
                                    {rule.enabled ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                                </button>
                                <button
                                    onClick={() => handleDelete(rule)}
                                    className="p-2 rounded-lg border border-gray-100 text-gray-400 hover:text-red-600 hover:bg-red-50 transition-all dark:border-gray-800 dark:hover:bg-red-950/20"
                                >
                                    <Trash2 className="h-4 w-4" />
                                </button>
                                <button
                                    onClick={() => openEdit(rule)}
                                    className="flex items-center gap-2 p-2 px-4 rounded-lg bg-gray-50 text-gray-900 font-medium hover:bg-gray-100 transition-colors dark:bg-gray-900 dark:text-white"
                                >
                                    <span>Edit</span>
                                    <ChevronRight className="h-4 w-4" />
                                </button>
                            </div>
                        </div>
                    </div>
                    ))
                )}
            </div>

            {editingRule && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
                    <div className="w-full max-w-2xl rounded-2xl bg-white p-6 shadow-xl dark:bg-gray-950">
                        <div className="flex items-center justify-between">
                            <div>
                                <h3 className="text-xl font-semibold text-gray-900 dark:text-white">Edit Rule</h3>
                                <p className="text-sm text-gray-500">{editingRule.rule_id}</p>
                            </div>
                            <button
                                onClick={() => setEditingRule(null)}
                                className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400"
                            >
                                Close
                            </button>
                        </div>

                        <div className="mt-4 grid gap-4 md:grid-cols-2">
                            <div>
                                <label className="text-xs font-semibold uppercase text-gray-500">Name</label>
                                <input
                                    value={editName}
                                    onChange={(e) => setEditName(e.target.value)}
                                    className="mt-1 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900"
                                />
                            </div>
                            <div>
                                <label className="text-xs font-semibold uppercase text-gray-500">Severity</label>
                                <select
                                    value={editSeverity}
                                    onChange={(e) => setEditSeverity(e.target.value)}
                                    className="mt-1 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900"
                                >
                                    <option value="low">low</option>
                                    <option value="medium">medium</option>
                                    <option value="high">high</option>
                                    <option value="critical">critical</option>
                                </select>
                            </div>
                            <div className="md:col-span-2">
                                <label className="text-xs font-semibold uppercase text-gray-500">Description</label>
                                <input
                                    value={editDescription}
                                    onChange={(e) => setEditDescription(e.target.value)}
                                    className="mt-1 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900"
                                />
                            </div>
                            <div className="md:col-span-2">
                                <label className="text-xs font-semibold uppercase text-gray-500">Approval Note</label>
                                <input
                                    value={editNotes}
                                    onChange={(e) => setEditNotes(e.target.value)}
                                    className="mt-1 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900"
                                    placeholder="Why this change?"
                                />
                            </div>
                        </div>

                        <div className="mt-4 grid gap-4 md:grid-cols-2">
                            <div>
                                <label className="text-xs font-semibold uppercase text-gray-500">Conditions (JSON)</label>
                                <textarea
                                    value={editConditions}
                                    onChange={(e) => setEditConditions(e.target.value)}
                                    rows={8}
                                    className="mt-1 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-xs font-mono dark:border-gray-800 dark:bg-gray-900"
                                />
                            </div>
                            <div>
                                <label className="text-xs font-semibold uppercase text-gray-500">Thresholds (JSON)</label>
                                <textarea
                                    value={editThresholds}
                                    onChange={(e) => setEditThresholds(e.target.value)}
                                    rows={8}
                                    className="mt-1 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-xs font-mono dark:border-gray-800 dark:bg-gray-900"
                                />
                            </div>
                        </div>

                        <div className="mt-4 flex items-center justify-between">
                            <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
                                <input
                                    type="checkbox"
                                    checked={editEnabled}
                                    onChange={(e) => setEditEnabled(e.target.checked)}
                                />
                                Enabled
                            </label>
                            <div className="flex gap-3">
                                <button
                                    onClick={() => setEditingRule(null)}
                                    className="rounded-lg border border-gray-200 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-800 dark:text-gray-300 dark:hover:bg-gray-900"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleSubmitForApproval}
                                    disabled={saving}
                                    className="rounded-lg border border-blue-200 px-4 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50 disabled:opacity-50 dark:border-blue-900/50 dark:text-blue-200 dark:hover:bg-blue-900/20"
                                >
                                    {saving ? "Submitting..." : "Submit for Approval"}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {activeVersion && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
                    <div className="w-full max-w-3xl rounded-2xl bg-white p-6 shadow-xl dark:bg-gray-950">
                        <div className="flex items-center justify-between">
                            <div>
                                <h3 className="text-xl font-semibold text-gray-900 dark:text-white">Review Version</h3>
                                <p className="text-sm text-gray-500">Version {activeVersion.version_number}</p>
                            </div>
                            <button
                                onClick={() => setActiveVersion(null)}
                                className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400"
                            >
                                Close
                            </button>
                        </div>

                        <div className="mt-4 grid gap-4 md:grid-cols-2 text-sm">
                            <div>
                                <div className="text-xs uppercase text-gray-500">Name</div>
                                <div className="text-gray-900 dark:text-white">{activeVersion.name}</div>
                            </div>
                            <div>
                                <div className="text-xs uppercase text-gray-500">Severity</div>
                                <div className="text-gray-900 dark:text-white">{activeVersion.severity}</div>
                            </div>
                            <div>
                                <div className="text-xs uppercase text-gray-500">Category</div>
                                <div className="text-gray-900 dark:text-white">{activeVersion.category || "uncategorized"}</div>
                            </div>
                            <div>
                                <div className="text-xs uppercase text-gray-500">Enabled</div>
                                <div className="text-gray-900 dark:text-white">{activeVersion.enabled ? "Yes" : "No"}</div>
                            </div>
                        </div>

                        <div className="mt-4 grid gap-4 md:grid-cols-2">
                            <div>
                                <div className="text-xs uppercase text-gray-500 mb-2">Conditions</div>
                                <pre className="rounded-lg bg-gray-950 text-gray-100 text-xs p-3 max-h-64 overflow-auto">
                                    {JSON.stringify(activeVersion.conditions || {}, null, 2)}
                                </pre>
                            </div>
                            <div>
                                <div className="text-xs uppercase text-gray-500 mb-2">Thresholds</div>
                                <pre className="rounded-lg bg-gray-950 text-gray-100 text-xs p-3 max-h-64 overflow-auto">
                                    {JSON.stringify(activeVersion.thresholds || {}, null, 2)}
                                </pre>
                            </div>
                        </div>

                        {activeVersion.notes ? (
                            <div className="mt-4 text-xs text-gray-500">Note: {activeVersion.notes}</div>
                        ) : null}

                        <div className="mt-6 flex items-center justify-between">
                            <a
                                href={`/audit?entity_type=rule_version&entity_id=${activeVersion.id}`}
                                className="text-xs text-blue-600 hover:text-blue-700"
                            >
                                View audit trail
                            </a>
                            <div className="flex gap-2">
                                <button
                                    onClick={() => handleRejectVersion(activeVersion.id)}
                                    className="rounded-lg border border-gray-200 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 dark:border-gray-800 dark:text-gray-300 dark:hover:bg-gray-900"
                                >
                                    Reject
                                </button>
                                <button
                                    onClick={() => handleApproveVersion(activeVersion.id)}
                                    className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
                                >
                                    Approve
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
        </LoadingBoundary>
    );
}
