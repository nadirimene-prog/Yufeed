"use client";

import { useEffect, useState } from "react";
import { fetchWithAuth } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/apiBaseUrl";
import {
    PlayCircle,
    Database,
    FileJson,
    AlertTriangle,
    Sparkles,
    History,
    List,
    RefreshCw,
    Search,
    Download,
} from "lucide-react";

const API_URL = getApiBaseUrl();

type DecisionResponse = {
    event_id: string;
    decision_id: string;
    decision: string;
    risk_score?: number | null;
    risk_level?: string | null;
    alerts: string[];
    reason_codes: string[];
    evidence: Record<string, unknown>;
};

type DecisionListItem = {
    decision_id: string;
    event_id?: string | null;
    decision: string;
    reason_codes?: string[] | null;
    rule_version?: string | null;
    model_version?: string | null;
    created_at: string;
    event_type?: string | null;
    entity_type?: string | null;
    entity_id?: string | null;
    source?: string | null;
};

type DecisionEvidenceBundle = {
    export_id: string;
    exported_at: string;
    decision: Record<string, unknown> & {
        evidence?: {
            risk_score?: number | string | null;
            risk_level?: string | null;
            alerts?: unknown[] | null;
            onchain?: { risk_level?: string | null } | null;
        };
    };
    event?: {
        event_type?: string | null;
        entity_type?: string | null;
        entity_id?: string | null;
        source?: string | null;
        payload?: Record<string, unknown> | null;
        metadata?: (Record<string, unknown> & { context?: Record<string, unknown> }) | null;
    } | null;
    transaction?: Record<string, unknown> | null;
    alerts: Record<string, unknown>[];
    audit_logs: Record<string, unknown>[];
};

type DecisionListResponse = {
    total: number;
    items: DecisionListItem[];
};

type EventResponse = {
    event_id: string;
    event_type: string;
    entity_type?: string | null;
    entity_id?: string | null;
    metadata: Record<string, unknown>;
};

type FeatureSetResponse = {
    entity_type: string;
    entity_id: string;
    features: Record<string, unknown>;
};

type TransactionResponse = {
    id: number;
    transaction_id: string;
    user_id: string;
    amount: number;
    currency: string;
    transaction_type?: string | null;
};

const SAMPLE_PAYLOAD = JSON.stringify(
    {
        transaction_id: "TXN-0001",
        user_id: "user-123",
        amount: 12500,
        currency: "EUR",
        transaction_type: "transfer",
    },
    null,
    2
);

const SAMPLE_CONTEXT = JSON.stringify(
    {
        channel: "console",
        requested_by: "analyst",
        note: "Decisioning UI smoke test",
    },
    null,
    2
);

const SAMPLE_FEATURES = JSON.stringify(
    {
        avg_tx_amount_30d: { value: 532.7, feature_type: "numeric" },
        high_risk_country_count: { value: 2, feature_type: "numeric" },
    },
    null,
    2
);

const decisionBadgeStyles: Record<string, string> = {
    allow: "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
    "step-up": "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
    step_up: "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
    alert: "bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300",
    block: "bg-rose-50 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300",
};

const downloadFile = (filename: string, content: string, mime: string) => {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
};

const toCsv = (items: DecisionListItem[]) => {
    const headers = [
        "decision_id",
        "event_id",
        "decision",
        "created_at",
        "event_type",
        "entity_type",
        "entity_id",
        "source",
        "reason_codes",
        "rule_version",
        "model_version",
    ];
    const rows = items.map((item) => [
        item.decision_id,
        item.event_id || "",
        item.decision,
        item.created_at,
        item.event_type || "",
        item.entity_type || "",
        item.entity_id || "",
        item.source || "",
        (item.reason_codes || []).join("|"),
        item.rule_version || "",
        item.model_version || "",
    ]);
    return [headers, ...rows]
        .map((row) =>
            row
                .map((value) =>
                    `"${String(value ?? "").replace(/"/g, '""')}"`
                )
                .join(",")
        )
        .join("\n");
};

export default function DecisioningPage() {
    const [eventType, setEventType] = useState("txn_fiat");
    const [transactionId, setTransactionId] = useState<string>("");
    const [entityType, setEntityType] = useState<string>("transaction");
    const [entityId, setEntityId] = useState<string>("");
    const [source, setSource] = useState<string>("ui");
    const [payload, setPayload] = useState<string>(SAMPLE_PAYLOAD);
    const [context, setContext] = useState<string>(SAMPLE_CONTEXT);

    const [featureEntityType, setFeatureEntityType] = useState("user");
    const [featureEntityId, setFeatureEntityId] = useState("user-123");
    const [featuresJson, setFeaturesJson] = useState(SAMPLE_FEATURES);
    const [featureResponse, setFeatureResponse] = useState<FeatureSetResponse | null>(null);

    const [loading, setLoading] = useState(false);
    const [featureLoading, setFeatureLoading] = useState(false);
    const [auditLoading, setAuditLoading] = useState(false);
    const [transactionLoading, setTransactionLoading] = useState(false);

    const [eventResult, setEventResult] = useState<EventResponse | null>(null);
    const [decisionResult, setDecisionResult] = useState<DecisionResponse | null>(null);
    const [transactionResult, setTransactionResult] = useState<TransactionResponse | null>(null);
    const [auditLogs, setAuditLogs] = useState<Record<string, unknown>[]>([]);
    const [eventRecord, setEventRecord] = useState<Record<string, unknown> | null>(null);
    const [decisionRecord, setDecisionRecord] = useState<Record<string, unknown> | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [autoRun, setAutoRun] = useState(true);
    const [autoRunDone, setAutoRunDone] = useState(false);

    const [activeTab, setActiveTab] = useState<"log" | "console">("log");
    const [decisions, setDecisions] = useState<DecisionListItem[]>([]);
    const [decisionLoading, setDecisionLoading] = useState(false);
    const [decisionError, setDecisionError] = useState<string | null>(null);
    const [refreshTick, setRefreshTick] = useState(0);
    const [decisionTotal, setDecisionTotal] = useState(0);
    const [decisionPage, setDecisionPage] = useState(0);
    const [decisionPageSize, setDecisionPageSize] = useState(25);
    const [decisionFilter, setDecisionFilter] = useState<string>("");
    const [eventTypeFilter, setEventTypeFilter] = useState<string>("");
    const [entityTypeFilter, setEntityTypeFilter] = useState<string>("");
    const [entityIdFilter, setEntityIdFilter] = useState<string>("");
    const [decisionIdFilter, setDecisionIdFilter] = useState<string>("");
    const [eventIdFilter, setEventIdFilter] = useState<string>("");
    const [fromFilter, setFromFilter] = useState<string>("");
    const [toFilter, setToFilter] = useState<string>("");
    const [selectedDecision, setSelectedDecision] = useState<DecisionListItem | null>(null);
    const [evidenceBundle, setEvidenceBundle] = useState<DecisionEvidenceBundle | null>(null);
    const [evidenceLoading, setEvidenceLoading] = useState(false);
    const [replaySourceDecisionId, setReplaySourceDecisionId] = useState<string | null>(null);
    const [replayResult, setReplayResult] = useState<DecisionResponse | null>(null);

    const parseJson = (value: string, label: string) => {
        if (!value.trim()) return {};
        try {
            return JSON.parse(value);
        } catch {
            throw new Error(`${label} must be valid JSON`);
        }
    };

    const formatDateTime = (value?: string | null) => {
        if (!value) return "-";
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return value;
        return date.toLocaleString();
    };

    const buildDecisionQuery = () => {
        const params = new URLSearchParams();
        params.set("limit", String(decisionPageSize));
        params.set("skip", String(decisionPage * decisionPageSize));
        if (decisionFilter) params.set("decision", decisionFilter);
        if (eventTypeFilter) params.set("event_type", eventTypeFilter);
        if (entityTypeFilter) params.set("entity_type", entityTypeFilter);
        if (entityIdFilter) params.set("entity_id", entityIdFilter);
        if (decisionIdFilter) params.set("decision_id", decisionIdFilter);
        if (eventIdFilter) params.set("event_id", eventIdFilter);
        if (fromFilter) {
            const fromDate = new Date(fromFilter);
            if (!Number.isNaN(fromDate.getTime())) {
                params.set("created_from", fromDate.toISOString());
            }
        }
        if (toFilter) {
            const toDate = new Date(toFilter);
            if (!Number.isNaN(toDate.getTime())) {
                params.set("created_to", toDate.toISOString());
            }
        }
        return params.toString();
    };

    const buildDecisionBody = () => ({
        event_type: eventType,
        transaction_id: transactionId ? Number(transactionId) : undefined,
        entity_type: entityType || undefined,
        entity_id: entityId || undefined,
        source: source || undefined,
        payload: parseJson(payload, "Payload"),
        context: parseJson(context, "Context"),
    });

    const normalizeFeaturePayload = (raw: Record<string, unknown>) =>
        Object.fromEntries(
            Object.entries(raw).map(([name, value]) => {
                if (value && typeof value === "object" && "value" in value) {
                    return [name, value];
                }
                return [name, { value }];
            })
        );

    const handleCreateTransaction = async () => {
        setTransactionLoading(true);
        setError(null);
        setTransactionResult(null);
        try {
            const payloadObj = parseJson(payload, "Payload");
            const txPayload = {
                transaction_id: payloadObj.transaction_id || `TXN-${Date.now()}`,
                user_id: payloadObj.user_id || "user-123",
                amount: payloadObj.amount || 1000,
                currency: payloadObj.currency || "EUR",
                transaction_type: payloadObj.transaction_type || "transfer",
                country_code: payloadObj.country_code || "FR",
            };
            const res = await fetchWithAuth(`${API_URL}/api/transactions/ingest`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(txPayload),
            });
            if (!res.ok) throw new Error(await res.text());
            const data = (await res.json()) as TransactionResponse;
            setTransactionResult(data);
            setTransactionId(String(data.id));
            setEntityType("transaction");
            setEntityId(data.transaction_id);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to create transaction");
        } finally {
            setTransactionLoading(false);
        }
    };

    const handleIngest = async () => {
        setLoading(true);
        setError(null);
        setEventResult(null);
        try {
            const body = buildDecisionBody();
            const res = await fetchWithAuth(`${API_URL}/api/decisioning/events`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    event_type: body.event_type,
                    payload: body.payload,
                    entity_type: body.entity_type,
                    entity_id: body.entity_id,
                    source: body.source,
                }),
            });
            if (!res.ok) throw new Error(await res.text());
            setEventResult((await res.json()) as EventResponse);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to ingest event");
        } finally {
            setLoading(false);
        }
    };

    const handleDecide = async () => {
        setLoading(true);
        setError(null);
        setDecisionResult(null);
        try {
            const body = buildDecisionBody();
            const res = await fetchWithAuth(`${API_URL}/api/decisioning/decide`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
            if (!res.ok) throw new Error(await res.text());
            setDecisionResult((await res.json()) as DecisionResponse);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to run decision");
        } finally {
            setLoading(false);
        }
    };

    const handleSetFeatures = async () => {
        setFeatureLoading(true);
        setError(null);
        try {
            const payload = normalizeFeaturePayload(parseJson(featuresJson, "Features"));
            const res = await fetchWithAuth(`${API_URL}/api/features/set`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    entity_type: featureEntityType,
                    entity_id: featureEntityId,
                    features: payload,
                }),
            });
            if (!res.ok) throw new Error(await res.text());
            setFeatureResponse((await res.json()) as FeatureSetResponse);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to set features");
        } finally {
            setFeatureLoading(false);
        }
    };

    const handleLoadFeatures = async () => {
        setFeatureLoading(true);
        setError(null);
        try {
            const res = await fetchWithAuth(
                `${API_URL}/api/features/${featureEntityType}/${featureEntityId}`
            );
            if (!res.ok) throw new Error(await res.text());
            setFeatureResponse((await res.json()) as FeatureSetResponse);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load features");
        } finally {
            setFeatureLoading(false);
        }
    };

    const fetchAudit = async (decisionId?: string, eventId?: string) => {
        if (!decisionId || !eventId) return;
        setAuditLoading(true);
        try {
            const [eventRes, decisionRes, logsRes] = await Promise.all([
                fetchWithAuth(`${API_URL}/api/audit/events/${eventId}`),
                fetchWithAuth(`${API_URL}/api/audit/decisions/${decisionId}`),
                fetchWithAuth(
                    `${API_URL}/api/audit/logs?entity_type=decision&entity_id=${decisionId}&limit=20`
                ),
            ]);
            setEventRecord(eventRes.ok ? await eventRes.json() : null);
            setDecisionRecord(decisionRes.ok ? await decisionRes.json() : null);
            setAuditLogs(logsRes.ok ? await logsRes.json() : []);
        } finally {
            setAuditLoading(false);
        }
    };

    useEffect(() => {
        if (autoRun && !autoRunDone) {
            setAutoRunDone(true);
            handleDecide();
        }
    }, [autoRun, autoRunDone]);

    useEffect(() => {
        setDecisionPage(0);
    }, [
        decisionFilter,
        eventTypeFilter,
        entityTypeFilter,
        entityIdFilter,
        decisionIdFilter,
        eventIdFilter,
        fromFilter,
        toFilter,
    ]);

    useEffect(() => {
        setDecisionPage(0);
    }, [decisionPageSize]);

    useEffect(() => {
        const fetchDecisions = async () => {
            setDecisionLoading(true);
            setDecisionError(null);
            try {
                const query = buildDecisionQuery();
                const res = await fetchWithAuth(
                    `${API_URL}/api/audit/decisions?${query}`
                );
                if (!res.ok) throw new Error(await res.text());
                const data = (await res.json()) as DecisionListResponse;
                setDecisions(data.items);
                setDecisionTotal(data.total ?? 0);
                setSelectedDecision((prev) => {
                    if (!data.items.length) return null;
                    if (!prev) return data.items[0];
                    const exists = data.items.some((item) => item.decision_id === prev.decision_id);
                    return exists ? prev : data.items[0];
                });
            } catch (err) {
                setDecisionError(
                    err instanceof Error ? err.message : "Failed to load decision log"
                );
                setDecisions([]);
            } finally {
                setDecisionLoading(false);
            }
        };
        if (activeTab === "log") {
            fetchDecisions();
        }
    }, [
        activeTab,
        decisionFilter,
        eventTypeFilter,
        entityTypeFilter,
        entityIdFilter,
        decisionIdFilter,
        eventIdFilter,
        fromFilter,
        toFilter,
        refreshTick,
        decisionPage,
        decisionPageSize,
    ]);

    useEffect(() => {
        if (decisionResult) {
            fetchAudit(decisionResult.decision_id, decisionResult.event_id);
        }
    }, [decisionResult]);

    useEffect(() => {
        if (decisionResult && replaySourceDecisionId) {
            setReplayResult(decisionResult);
        }
    }, [decisionResult, replaySourceDecisionId]);

    useEffect(() => {
        const fetchEvidence = async () => {
            if (!selectedDecision?.decision_id) return;
            setEvidenceLoading(true);
            try {
                const res = await fetchWithAuth(
                    `${API_URL}/api/reporting/evidence/decision/${selectedDecision.decision_id}`
                );
                if (!res.ok) throw new Error(await res.text());
                setEvidenceBundle((await res.json()) as DecisionEvidenceBundle);
            } catch (err) {
                setEvidenceBundle(null);
            } finally {
                setEvidenceLoading(false);
            }
        };
        if (activeTab === "log" && selectedDecision) {
            fetchEvidence();
        }
    }, [activeTab, selectedDecision]);

    useEffect(() => {
        setReplayResult(null);
        setReplaySourceDecisionId(null);
    }, [selectedDecision?.decision_id]);

    const loadReplayIntoSimulator = (autoRunReplay: boolean) => {
        if (!evidenceBundle?.event) return;
        const event = evidenceBundle.event;
        const payloadObj: Record<string, unknown> = event.payload ?? {};
        const metadataObj: Record<string, unknown> & { context?: Record<string, unknown> } = event.metadata ?? {};
        const contextObj = metadataObj.context ?? metadataObj;

        setEventType(String(event.event_type || eventType));
        setEntityType(String(event.entity_type || ""));
        setEntityId(String(event.entity_id || ""));
        setSource(String(event.source || "replay"));
        setPayload(JSON.stringify(payloadObj, null, 2));
        setContext(JSON.stringify(contextObj, null, 2));
        setReplaySourceDecisionId(selectedDecision?.decision_id || null);
        setActiveTab("console");
        if (autoRunReplay) {
            setTimeout(() => {
                handleDecide();
            }, 0);
        }
    };

    const renderDecisionLog = () => {
        const originalDecision = evidenceBundle?.decision || {};
        const originalEvidenceRaw = originalDecision["evidence"];
        const originalEvidence =
            typeof originalEvidenceRaw === "object" && originalEvidenceRaw !== null
                ? (originalEvidenceRaw as Record<string, unknown>)
                : {};
        const formatValue = (value: unknown) => {
            if (value === null || value === undefined || value === "") return "-";
            return String(value);
        };
        const canCompare =
            replayResult &&
            replaySourceDecisionId &&
            replaySourceDecisionId === selectedDecision?.decision_id;

        const diffRows = [
            {
                label: "Decision",
                original: formatValue(originalDecision?.decision),
                replay: formatValue(replayResult?.decision),
            },
            {
                label: "Risk score",
                original: formatValue(originalEvidence?.risk_score),
                replay: formatValue(replayResult?.risk_score),
            },
            {
                label: "Risk level",
                original: formatValue(originalEvidence?.risk_level),
                replay: formatValue(replayResult?.risk_level),
            },
            {
                label: "Alerts",
                original: formatValue(
                    Array.isArray(originalEvidence["alerts"])
                        ? (originalEvidence["alerts"] as unknown[]).map(String).join(", ")
                        : ""
                ),
                replay: formatValue(
                    Array.isArray(replayResult?.alerts) ? replayResult.alerts.join(", ") : ""
                ),
            },
            {
                label: "Reason codes",
                original: formatValue(
                    Array.isArray(originalDecision["reason_codes"])
                        ? (originalDecision["reason_codes"] as unknown[]).map(String).join(", ")
                        : ""
                ),
                replay: formatValue(
                    Array.isArray(replayResult?.reason_codes) ? replayResult.reason_codes.join(", ") : ""
                ),
            },
        ];

        return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1 space-y-4">
                <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 p-4 space-y-3">
                    <div className="flex items-center justify-between">
                        <div className="text-sm font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
                            <List className="h-4 w-4" />
                            Decision Log
                        </div>
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => {
                                    const payload = JSON.stringify(decisions, null, 2);
                                    downloadFile("decision-log-page.json", payload, "application/json");
                                }}
                                className="inline-flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400"
                                title="Export JSON"
                            >
                                <Download className="h-3.5 w-3.5" />
                                JSON
                            </button>
                            <button
                                onClick={() => {
                                    const payload = toCsv(decisions);
                                    downloadFile("decision-log-page.csv", payload, "text/csv");
                                }}
                                className="inline-flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400"
                                title="Export CSV"
                            >
                                <Download className="h-3.5 w-3.5" />
                                CSV
                            </button>
                            <button
                                onClick={() => setRefreshTick((tick) => tick + 1)}
                                className="inline-flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400"
                                title="Refresh"
                            >
                                <RefreshCw className="h-3.5 w-3.5" />
                                Refresh
                            </button>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs">
                        <select
                            value={decisionFilter}
                            onChange={(e) => setDecisionFilter(e.target.value)}
                            className="rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1"
                        >
                            <option value="">Decision</option>
                            <option value="allow">Allow</option>
                            <option value="step-up">Step-up</option>
                            <option value="step_up">Step up (legacy)</option>
                            <option value="alert">Alert</option>
                            <option value="block">Block</option>
                        </select>
                        <input
                            value={eventTypeFilter}
                            onChange={(e) => setEventTypeFilter(e.target.value)}
                            placeholder="Event type"
                            className="rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1"
                        />
                        <input
                            value={entityTypeFilter}
                            onChange={(e) => setEntityTypeFilter(e.target.value)}
                            placeholder="Entity type"
                            className="rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1"
                        />
                        <input
                            value={entityIdFilter}
                            onChange={(e) => setEntityIdFilter(e.target.value)}
                            placeholder="Entity ID"
                            className="rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1"
                        />
                        <input
                            value={decisionIdFilter}
                            onChange={(e) => setDecisionIdFilter(e.target.value)}
                            placeholder="Decision ID"
                            className="rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1"
                        />
                        <input
                            value={eventIdFilter}
                            onChange={(e) => setEventIdFilter(e.target.value)}
                            placeholder="Event ID"
                            className="rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1"
                        />
                        <input
                            type="datetime-local"
                            value={fromFilter}
                            onChange={(e) => setFromFilter(e.target.value)}
                            className="rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1"
                        />
                        <input
                            type="datetime-local"
                            value={toFilter}
                            onChange={(e) => setToFilter(e.target.value)}
                            className="rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1"
                        />
                    </div>
                </div>

                <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 p-4 space-y-3">
                    {decisionLoading ? (
                        <div className="text-xs text-gray-500">Loading decisions...</div>
                    ) : decisionError ? (
                        <div className="text-xs text-red-600">{decisionError}</div>
                    ) : decisions.length === 0 ? (
                        <div className="text-xs text-gray-500">No decisions found.</div>
                    ) : (
                        <div className="space-y-2 max-h-[520px] overflow-auto pr-2">
                            {decisions.map((item) => (
                                <button
                                    key={item.decision_id}
                                    onClick={() => setSelectedDecision(item)}
                                    className={`w-full text-left rounded-lg border px-3 py-2 text-xs transition ${
                                        selectedDecision?.decision_id === item.decision_id
                                            ? "border-gray-900 dark:border-gray-100 bg-gray-50 dark:bg-gray-900"
                                            : "border-gray-200 dark:border-gray-800 hover:border-gray-400"
                                    }`}
                                >
                                    <div className="flex items-center justify-between gap-2">
                                        <span
                                            className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                                                decisionBadgeStyles[item.decision] || "bg-gray-100 text-gray-700"
                                            }`}
                                        >
                                            {item.decision}
                                        </span>
                                        <span className="text-[10px] text-gray-500">
                                            {formatDateTime(item.created_at)}
                                        </span>
                                    </div>
                                    <div className="mt-2 text-[11px] text-gray-600 dark:text-gray-400">
                                        <div>Event: {item.event_type || "-"}</div>
                                        <div>Entity: {item.entity_id || "-"}</div>
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}
                    <div className="flex items-center justify-between text-[11px] text-gray-500">
                        <div>
                            {decisionTotal > 0
                                ? `Showing ${decisionPage * decisionPageSize + 1}-${
                                      Math.min(
                                          decisionTotal,
                                          (decisionPage + 1) * decisionPageSize
                                      )
                                  } of ${decisionTotal}`
                                : "No results"}
                        </div>
                        <div className="flex items-center gap-2">
                            <select
                                value={decisionPageSize}
                                onChange={(e) => setDecisionPageSize(Number(e.target.value))}
                                className="rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1"
                            >
                                {[10, 25, 50, 100].map((size) => (
                                    <option key={size} value={size}>
                                        {size}/page
                                    </option>
                                ))}
                            </select>
                            <button
                                onClick={() => setDecisionPage((page) => Math.max(0, page - 1))}
                                disabled={decisionPage === 0}
                                className="rounded-md border border-gray-300 dark:border-gray-700 px-2 py-1 disabled:opacity-50"
                            >
                                Prev
                            </button>
                            <button
                                onClick={() =>
                                    setDecisionPage((page) =>
                                        (page + 1) * decisionPageSize >= decisionTotal ? page : page + 1
                                    )
                                }
                                disabled={(decisionPage + 1) * decisionPageSize >= decisionTotal}
                                className="rounded-md border border-gray-300 dark:border-gray-700 px-2 py-1 disabled:opacity-50"
                            >
                                Next
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <div className="lg:col-span-2 space-y-4">
                <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 p-5">
                    <div className="flex items-center justify-between">
                        <div className="text-sm font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
                            <Search className="h-4 w-4" />
                            Decision Detail
                        </div>
                        {selectedDecision ? (
                            <a
                                href={`${API_URL}/api/reporting/evidence/decision/${selectedDecision.decision_id}`}
                                className="inline-flex items-center gap-2 text-xs text-blue-600 hover:text-blue-700"
                            >
                                <Download className="h-3.5 w-3.5" />
                                Evidence bundle
                            </a>
                        ) : null}
                    </div>

                    {selectedDecision ? (
                        <div className="mt-4 space-y-4 text-xs text-gray-600 dark:text-gray-400">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-3">
                                    <div className="text-[10px] uppercase tracking-wider text-gray-400">Decision</div>
                                    <div className="mt-2">
                                        <span
                                            className={`inline-flex rounded-full px-2 py-1 text-[11px] font-semibold ${
                                                decisionBadgeStyles[selectedDecision.decision] ||
                                                "bg-gray-100 text-gray-700"
                                            }`}
                                        >
                                            {selectedDecision.decision}
                                        </span>
                                    </div>
                                </div>
                                <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-3">
                                    <div className="text-[10px] uppercase tracking-wider text-gray-400">Created</div>
                                    <div className="mt-2 font-medium text-gray-900 dark:text-gray-100">
                                        {formatDateTime(selectedDecision.created_at)}
                                    </div>
                                </div>
                                <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-3">
                                    <div className="text-[10px] uppercase tracking-wider text-gray-400">Reason Codes</div>
                                    <div className="mt-2 flex flex-wrap gap-2">
                                        {(selectedDecision.reason_codes || []).length ? (
                                            selectedDecision.reason_codes?.map((code) => (
                                                <span
                                                    key={code}
                                                    className="rounded-full bg-gray-100 px-2 py-1 text-[11px] text-gray-700 dark:bg-gray-800 dark:text-gray-200"
                                                >
                                                    {code}
                                                </span>
                                            ))
                                        ) : (
                                            <span className="text-[11px] text-gray-500">None</span>
                                        )}
                                    </div>
                                </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <div className="text-[10px] uppercase tracking-wider text-gray-400">Decision ID</div>
                                <div className="font-medium text-gray-900 dark:text-gray-100">{selectedDecision.decision_id}</div>
                            </div>
                            <div>
                                <div className="text-[10px] uppercase tracking-wider text-gray-400">Event ID</div>
                                <div className="font-medium text-gray-900 dark:text-gray-100">{selectedDecision.event_id || "-"}</div>
                            </div>
                            <div>
                                <div className="text-[10px] uppercase tracking-wider text-gray-400">Decision</div>
                                <div className="font-medium text-gray-900 dark:text-gray-100">{selectedDecision.decision}</div>
                            </div>
                            <div>
                                <div className="text-[10px] uppercase tracking-wider text-gray-400">Event Type</div>
                                <div className="font-medium text-gray-900 dark:text-gray-100">{selectedDecision.event_type || "-"}</div>
                            </div>
                            <div>
                                <div className="text-[10px] uppercase tracking-wider text-gray-400">Entity</div>
                                <div className="font-medium text-gray-900 dark:text-gray-100">{selectedDecision.entity_id || "-"}</div>
                            </div>
                            <div>
                                <div className="text-[10px] uppercase tracking-wider text-gray-400">Rule Version</div>
                                <div className="font-medium text-gray-900 dark:text-gray-100">{selectedDecision.rule_version || "-"}</div>
                            </div>
                            <div>
                                <div className="text-[10px] uppercase tracking-wider text-gray-400">Model Version</div>
                                <div className="font-medium text-gray-900 dark:text-gray-100">{selectedDecision.model_version || "-"}</div>
                            </div>
                            </div>

                            <div className="flex flex-wrap gap-2">
                                <button
                                    onClick={() => loadReplayIntoSimulator(false)}
                                    disabled={!evidenceBundle?.event}
                                    className="rounded-md border border-gray-300 dark:border-gray-700 px-3 py-2 text-xs disabled:opacity-50"
                                >
                                    Load into simulator
                                </button>
                                <button
                                    onClick={() => loadReplayIntoSimulator(true)}
                                    disabled={!evidenceBundle?.event}
                                    className="rounded-md bg-gray-900 text-white px-3 py-2 text-xs disabled:opacity-50"
                                >
                                    Replay decision
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="mt-4 text-xs text-gray-500">Select a decision to view details.</div>
                    )}
                </div>

                <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 p-5 space-y-4">
                    <div className="flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
                        <History className="h-4 w-4" />
                        Evidence & Audit Trail
                    </div>
                    {evidenceLoading ? (
                        <div className="text-xs text-gray-500">Loading evidence...</div>
                    ) : evidenceBundle ? (
                        <div className="space-y-3 text-xs text-gray-600 dark:text-gray-400">
                            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                                <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-3">
                                    <div className="text-[10px] uppercase text-gray-400">Risk Score</div>
                                    <div className="mt-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
                                        {evidenceBundle.decision?.evidence?.risk_score ?? "-"}
                                    </div>
                                </div>
                                <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-3">
                                    <div className="text-[10px] uppercase text-gray-400">Risk Level</div>
                                    <div className="mt-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
                                        {evidenceBundle.decision?.evidence?.risk_level ?? "-"}
                                    </div>
                                </div>
                                <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-3">
                                    <div className="text-[10px] uppercase text-gray-400">Alerts</div>
                                    <div className="mt-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
                                        {Array.isArray(evidenceBundle.decision?.evidence?.alerts)
                                            ? evidenceBundle.decision?.evidence?.alerts.length
                                            : "-"}
                                    </div>
                                </div>
                                <div className="rounded-lg border border-gray-200 dark:border-gray-800 p-3">
                                    <div className="text-[10px] uppercase text-gray-400">On-chain</div>
                                    <div className="mt-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
                                        {evidenceBundle.decision?.evidence?.onchain?.risk_level ?? "-"}
                                    </div>
                                </div>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                <div className="rounded-md border border-gray-200 dark:border-gray-800 p-3">
                                    <div className="text-[10px] uppercase text-gray-400">Decision</div>
                                    <pre className="mt-2 max-h-40 overflow-auto bg-gray-950 text-gray-100 p-2 rounded">
                                        {JSON.stringify(evidenceBundle.decision, null, 2)}
                                    </pre>
                                </div>
                                <div className="rounded-md border border-gray-200 dark:border-gray-800 p-3">
                                    <div className="text-[10px] uppercase text-gray-400">Event</div>
                                    <pre className="mt-2 max-h-40 overflow-auto bg-gray-950 text-gray-100 p-2 rounded">
                                        {JSON.stringify(evidenceBundle.event ?? {}, null, 2)}
                                    </pre>
                                </div>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                <div className="rounded-md border border-gray-200 dark:border-gray-800 p-3">
                                    <div className="text-[10px] uppercase text-gray-400">Transaction</div>
                                    <pre className="mt-2 max-h-40 overflow-auto bg-gray-950 text-gray-100 p-2 rounded">
                                        {JSON.stringify(evidenceBundle.transaction ?? {}, null, 2)}
                                    </pre>
                                </div>
                                <div className="rounded-md border border-gray-200 dark:border-gray-800 p-3">
                                    <div className="text-[10px] uppercase text-gray-400">Alerts</div>
                                    <pre className="mt-2 max-h-40 overflow-auto bg-gray-950 text-gray-100 p-2 rounded">
                                        {JSON.stringify(evidenceBundle.alerts ?? [], null, 2)}
                                    </pre>
                                </div>
                            </div>
                            <div className="rounded-md border border-gray-200 dark:border-gray-800 p-3">
                                <div className="text-[10px] uppercase text-gray-400">Audit Logs</div>
                                <pre className="mt-2 max-h-56 overflow-auto bg-gray-950 text-gray-100 p-2 rounded">
                                    {JSON.stringify(evidenceBundle.audit_logs ?? [], null, 2)}
                                </pre>
                            </div>
                        </div>
                    ) : (
                        <div className="text-xs text-gray-500">No evidence loaded.</div>
                    )}
                </div>

                <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 p-5 space-y-4">
                    <div className="flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
                        <Sparkles className="h-4 w-4" />
                        Replay Comparison
                    </div>
                    {canCompare ? (
                        <div className="space-y-2 text-xs">
                            {diffRows.map((row) => {
                                const match = String(row.original ?? "") === String(row.replay ?? "");
                                return (
                                    <div
                                        key={row.label}
                                        className={`rounded-md border px-3 py-2 ${
                                            match
                                                ? "border-emerald-200 bg-emerald-50/50 text-emerald-700 dark:border-emerald-900/40 dark:bg-emerald-900/20 dark:text-emerald-200"
                                                : "border-amber-200 bg-amber-50/60 text-amber-700 dark:border-amber-900/40 dark:bg-amber-900/20 dark:text-amber-200"
                                        }`}
                                    >
                                        <div className="text-[10px] uppercase tracking-wider">{row.label}</div>
                                        <div className="mt-1 grid grid-cols-1 md:grid-cols-2 gap-2">
                                            <div>
                                                <div className="text-[10px] text-gray-500">Original</div>
                                                <div className="font-medium">{row.original || "-"}</div>
                                            </div>
                                            <div>
                                                <div className="text-[10px] text-gray-500">Replay</div>
                                                <div className="font-medium">{row.replay || "-"}</div>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    ) : (
                        <div className="text-xs text-gray-500">
                            Replay a decision to compare outcomes.
                        </div>
                    )}
                </div>
            </div>
        </div>
        );
    };

    const renderConsole = () => (
        <div className="space-y-6">
            <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 p-4 flex items-center justify-between">
                <div className="text-sm text-gray-600 dark:text-gray-400 flex items-center gap-2">
                    <Sparkles className="h-4 w-4" />
                    Auto-run sample decision on load
                </div>
                <label className="flex items-center gap-2 text-sm">
                    <input
                        type="checkbox"
                        checked={autoRun}
                        onChange={(e) => setAutoRun(e.target.checked)}
                    />
                    Enable
                </label>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 space-y-6">
                    <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 p-6 shadow-sm space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="text-xs font-medium text-gray-600 dark:text-gray-400">
                                    Event Type
                                </label>
                                <input
                                    value={eventType}
                                    onChange={(event) => setEventType(event.target.value)}
                                    className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm"
                                />
                            </div>
                            <div>
                                <label className="text-xs font-medium text-gray-600 dark:text-gray-400">
                                    Transaction ID (optional)
                                </label>
                                <input
                                    value={transactionId}
                                    onChange={(event) => setTransactionId(event.target.value)}
                                    className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm"
                                    placeholder="Numeric ID"
                                />
                            </div>
                            <div>
                                <label className="text-xs font-medium text-gray-600 dark:text-gray-400">
                                    Entity Type
                                </label>
                                <input
                                    value={entityType}
                                    onChange={(event) => setEntityType(event.target.value)}
                                    className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm"
                                />
                            </div>
                            <div>
                                <label className="text-xs font-medium text-gray-600 dark:text-gray-400">
                                    Entity ID
                                </label>
                                <input
                                    value={entityId}
                                    onChange={(event) => setEntityId(event.target.value)}
                                    className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm"
                                    placeholder="TXN-0001"
                                />
                            </div>
                            <div>
                                <label className="text-xs font-medium text-gray-600 dark:text-gray-400">
                                    Source
                                </label>
                                <input
                                    value={source}
                                    onChange={(event) => setSource(event.target.value)}
                                    className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm"
                                />
                            </div>
                        </div>

                        <div>
                            <label className="text-xs font-medium text-gray-600 dark:text-gray-400">
                                Payload (JSON)
                            </label>
                            <textarea
                                value={payload}
                                onChange={(event) => setPayload(event.target.value)}
                                rows={8}
                                className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-gray-950 text-gray-100 font-mono text-xs p-3"
                            />
                        </div>

                        <div>
                            <label className="text-xs font-medium text-gray-600 dark:text-gray-400">
                                Context (JSON)
                            </label>
                            <textarea
                                value={context}
                                onChange={(event) => setContext(event.target.value)}
                                rows={6}
                                className="mt-1 w-full rounded-md border border-gray-300 dark:border-gray-700 bg-gray-950 text-gray-100 font-mono text-xs p-3"
                            />
                        </div>

                        {error ? (
                            <div className="rounded-md border border-red-200 bg-red-50 text-red-700 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-200 px-3 py-2 text-xs flex items-center gap-2">
                                <AlertTriangle className="h-4 w-4" />
                                {error}
                            </div>
                        ) : null}

                        <div className="flex flex-wrap gap-3">
                            <button
                                onClick={handleIngest}
                                disabled={loading}
                                className="flex items-center gap-2 px-4 py-2 rounded-md bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 text-sm"
                            >
                                <Database className="h-4 w-4" />
                                Ingest Event
                            </button>
                            <button
                                onClick={handleCreateTransaction}
                                disabled={transactionLoading}
                                className="flex items-center gap-2 px-4 py-2 rounded-md bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 text-sm"
                            >
                                <FileJson className="h-4 w-4" />
                                {transactionLoading ? "Creating..." : "Create Transaction"}
                            </button>
                            <button
                                onClick={handleDecide}
                                disabled={loading}
                                className="flex items-center gap-2 px-4 py-2 rounded-md bg-gray-900 text-white text-sm hover:bg-gray-800 disabled:opacity-60"
                            >
                                <PlayCircle className="h-4 w-4" />
                                Run Decision
                            </button>
                        </div>
                    </div>

                    <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 p-6 shadow-sm space-y-4">
                        <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                            Feature Store
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <input
                                value={featureEntityType}
                                onChange={(e) => setFeatureEntityType(e.target.value)}
                                className="rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm"
                                placeholder="entity_type"
                            />
                            <input
                                value={featureEntityId}
                                onChange={(e) => setFeatureEntityId(e.target.value)}
                                className="rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 py-2 text-sm"
                                placeholder="entity_id"
                            />
                        </div>
                        <textarea
                            value={featuresJson}
                            onChange={(e) => setFeaturesJson(e.target.value)}
                            rows={6}
                            className="w-full rounded-md border border-gray-300 dark:border-gray-700 bg-gray-950 text-gray-100 font-mono text-xs p-3"
                        />
                        <div className="flex flex-wrap gap-3">
                            <button
                                onClick={handleSetFeatures}
                                disabled={featureLoading}
                                className="px-4 py-2 rounded-md bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 text-sm"
                            >
                                Set Features
                            </button>
                            <button
                                onClick={handleLoadFeatures}
                                disabled={featureLoading}
                                className="px-4 py-2 rounded-md bg-gray-900 text-white text-sm"
                            >
                                Load Features
                            </button>
                        </div>
                        {featureResponse ? (
                            <pre className="bg-gray-950 text-gray-100 p-3 rounded-md text-xs overflow-auto max-h-64">
                                {JSON.stringify(featureResponse, null, 2)}
                            </pre>
                        ) : null}
                    </div>
                </div>

                <div className="space-y-6">
                    <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 p-6 shadow-sm">
                        <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                            Event Response
                        </h2>
                        <div className="mt-3 text-xs text-gray-600 dark:text-gray-400">
                            {eventResult ? (
                                <pre className="bg-gray-950 text-gray-100 p-3 rounded-md overflow-auto max-h-72">
                                    {JSON.stringify(eventResult, null, 2)}
                                </pre>
                            ) : (
                                "No event ingested yet."
                            )}
                        </div>
                    </div>

                    <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 p-6 shadow-sm">
                        <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                            Transaction
                        </h2>
                        <div className="mt-3 text-xs text-gray-600 dark:text-gray-400">
                            {transactionResult ? (
                                <pre className="bg-gray-950 text-gray-100 p-3 rounded-md overflow-auto max-h-72">
                                    {JSON.stringify(transactionResult, null, 2)}
                                </pre>
                            ) : (
                                "No transaction created yet."
                            )}
                        </div>
                    </div>

                    <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 p-6 shadow-sm">
                        <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                            Decision Result
                        </h2>
                        <div className="mt-3 text-xs text-gray-600 dark:text-gray-400">
                            {decisionResult ? (
                                <div className="space-y-3">
                                    <pre className="bg-gray-950 text-gray-100 p-3 rounded-md overflow-auto max-h-72">
                                        {JSON.stringify(decisionResult, null, 2)}
                                    </pre>
                                    {decisionResult.reason_codes?.length ? (
                                        <div className="rounded-md border border-gray-200 dark:border-gray-800 p-3 text-xs text-gray-600 dark:text-gray-300">
                                            <div className="font-semibold mb-2">Rules Triggered</div>
                                            <div className="flex flex-wrap gap-2">
                                                {decisionResult.reason_codes.map((code) => (
                                                    <a
                                                        key={code}
                                                        href="/transaction-monitoring/rules"
                                                        className="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-700 dark:bg-gray-800 dark:text-gray-200"
                                                    >
                                                        {code}
                                                    </a>
                                                ))}
                                            </div>
                                        </div>
                                    ) : null}
                                    {decisionResult.alerts?.length ? (
                                        <div className="rounded-md border border-gray-200 dark:border-gray-800 p-3 text-xs text-gray-600 dark:text-gray-300">
                                            <div className="font-semibold mb-2">Alerts</div>
                                            <div className="flex flex-wrap gap-2">
                                                {decisionResult.alerts.map((alertId) => (
                                                    <span
                                                        key={alertId}
                                                        className="rounded-full bg-orange-100 px-2 py-1 text-xs text-orange-700 dark:bg-orange-900/30 dark:text-orange-200"
                                                    >
                                                        {alertId}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    ) : null}
                                    <a
                                        href={`${API_URL}/api/reporting/evidence/decision/${decisionResult.decision_id}`}
                                        className="text-xs text-blue-600 hover:text-blue-700"
                                    >
                                        Download decision evidence
                                    </a>
                                </div>
                            ) : (
                                "No decision run yet."
                            )}
                        </div>
                    </div>

                    <div className="rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 p-6 shadow-sm">
                        <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
                            <History className="h-4 w-4" />
                            Decision Timeline
                        </h2>
                        {auditLoading ? (
                            <div className="text-xs text-gray-500 mt-3">Loading...</div>
                        ) : (
                            <div className="mt-3 space-y-3 text-xs text-gray-600 dark:text-gray-400">
                                {eventRecord ? (
                                    <pre className="bg-gray-950 text-gray-100 p-3 rounded-md overflow-auto max-h-40">
                                        {JSON.stringify(eventRecord, null, 2)}
                                    </pre>
                                ) : null}
                                {decisionRecord ? (
                                    <pre className="bg-gray-950 text-gray-100 p-3 rounded-md overflow-auto max-h-40">
                                        {JSON.stringify(decisionRecord, null, 2)}
                                    </pre>
                                ) : null}
                                {auditLogs?.length ? (
                                    <pre className="bg-gray-950 text-gray-100 p-3 rounded-md overflow-auto max-h-40">
                                        {JSON.stringify(auditLogs, null, 2)}
                                    </pre>
                                ) : (
                                    <div>No audit logs yet.</div>
                                )}
                            </div>
                        )}
                    </div>

                    <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-white/60 dark:bg-gray-950/50 p-5 text-xs text-gray-600 dark:text-gray-400">
                        <div className="flex items-center gap-2 text-gray-700 dark:text-gray-200 font-medium mb-2">
                            <FileJson className="h-4 w-4" />
                            Quick tips
                        </div>
                        <ul className="space-y-2">
                            <li>Use transaction_id to attach decisions to stored transactions.</li>
                            <li>Use /api/features to add online features before deciding.</li>
                            <li>Events are immutable and show in the Audit Trail.</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    );

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
            <div className="max-w-6xl mx-auto space-y-6">
                <div>
                    <div className="text-xs uppercase tracking-[0.3em] text-gray-400">YuFeed Risk OS</div>
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                        Decisioning
                    </h1>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                        Monitor decisions, audit trails, and run live simulations.
                    </p>
                </div>

                <div className="inline-flex rounded-full border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 p-1">
                    <button
                        onClick={() => setActiveTab("log")}
                        className={`px-4 py-1.5 text-xs rounded-full ${
                            activeTab === "log"
                                ? "bg-gray-900 text-white"
                                : "text-gray-600 dark:text-gray-400"
                        }`}
                    >
                        Decision Log
                    </button>
                    <button
                        onClick={() => setActiveTab("console")}
                        className={`px-4 py-1.5 text-xs rounded-full ${
                            activeTab === "console"
                                ? "bg-gray-900 text-white"
                                : "text-gray-600 dark:text-gray-400"
                        }`}
                    >
                        Simulator
                    </button>
                </div>

                {activeTab === "log" ? renderDecisionLog() : renderConsole()}
            </div>
        </div>
    );
}
