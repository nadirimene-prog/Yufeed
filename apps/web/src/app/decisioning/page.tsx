"use client";

import { useEffect, useMemo, useState } from "react";
import { fetchWithAuth } from "@/lib/auth";
import { PlayCircle, Database, FileJson, AlertTriangle, Sparkles, History } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
    features: Record<string, any>;
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
    const [auditLogs, setAuditLogs] = useState<any[]>([]);
    const [eventRecord, setEventRecord] = useState<any | null>(null);
    const [decisionRecord, setDecisionRecord] = useState<any | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [autoRun, setAutoRun] = useState(true);
    const [autoRunDone, setAutoRunDone] = useState(false);

    const parseJson = (value: string, label: string) => {
        if (!value.trim()) return {};
        try {
            return JSON.parse(value);
        } catch {
            throw new Error(`${label} must be valid JSON`);
        }
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

    const normalizeFeaturePayload = (raw: Record<string, any>) =>
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
        if (decisionResult) {
            fetchAudit(decisionResult.decision_id, decisionResult.event_id);
        }
    }, [decisionResult]);

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
            <div className="max-w-6xl mx-auto space-y-6">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                        Decisioning Console
                    </h1>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                        Normalize events, run real-time decisions, and inspect evidence.
                    </p>
                </div>

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
        </div>
    );
}
