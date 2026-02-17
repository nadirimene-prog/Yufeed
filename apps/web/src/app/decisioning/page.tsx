"use client";

import { useEffect, useState } from "react";
import { fetchWithAuth } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/apiBaseUrl";
import DecisionLog from "@/app/decisioning/components/DecisionLog";
import DecisionSimulator from "@/app/decisioning/components/DecisionSimulator";
import type {
  DecisionEvidenceBundle,
  DecisionListItem,
  DecisionListResponse,
  DecisionResponse,
  EventResponse,
  FeatureSetResponse,
  TransactionResponse,
} from "@/app/decisioning/components/types";

const API_URL = getApiBaseUrl();

const SAMPLE_PAYLOAD = JSON.stringify(
  {
    transaction_id: "TXN-0001",
    user_id: "user-123",
    amount: 12500,
    currency: "EUR",
    transaction_type: "transfer",
  },
  null,
  2,
);

const SAMPLE_CONTEXT = JSON.stringify(
  {
    channel: "console",
    requested_by: "analyst",
    note: "Decisioning UI smoke test",
  },
  null,
  2,
);

const SAMPLE_FEATURES = JSON.stringify(
  {
    avg_tx_amount_30d: { value: 532.7, feature_type: "numeric" },
    high_risk_country_count: { value: 2, feature_type: "numeric" },
  },
  null,
  2,
);

const decisionBadgeStyles: Record<string, string> = {
  allow:
    "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
  "step-up":
    "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  step_up:
    "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  alert:
    "bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300",
  block: "bg-rose-50 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300",
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
  const [featureResponse, setFeatureResponse] =
    useState<FeatureSetResponse | null>(null);

  const [loading, setLoading] = useState(false);
  const [featureLoading, setFeatureLoading] = useState(false);
  const [auditLoading, setAuditLoading] = useState(false);
  const [transactionLoading, setTransactionLoading] = useState(false);

  const [eventResult, setEventResult] = useState<EventResponse | null>(null);
  const [decisionResult, setDecisionResult] = useState<DecisionResponse | null>(
    null,
  );
  const [transactionResult, setTransactionResult] =
    useState<TransactionResponse | null>(null);
  const [auditLogs, setAuditLogs] = useState<Record<string, unknown>[]>([]);
  const [eventRecord, setEventRecord] = useState<Record<
    string,
    unknown
  > | null>(null);
  const [decisionRecord, setDecisionRecord] = useState<Record<
    string,
    unknown
  > | null>(null);
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
  const [selectedDecision, setSelectedDecision] =
    useState<DecisionListItem | null>(null);
  const [evidenceBundle, setEvidenceBundle] =
    useState<DecisionEvidenceBundle | null>(null);
  const [evidenceLoading, setEvidenceLoading] = useState(false);
  const [replaySourceDecisionId, setReplaySourceDecisionId] = useState<
    string | null
  >(null);
  const [replayResult, setReplayResult] = useState<DecisionResponse | null>(
    null,
  );

  const parseJson = (value: string, label: string) => {
    if (!value.trim()) return {};
    try {
      return JSON.parse(value);
    } catch {
      throw new Error(`${label} must be valid JSON`);
    }
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
      }),
    );

  const handleCreateTransaction = async () => {
    setTransactionLoading(true);
    setError(null);
    setTransactionResult(null);
    try {
      const payloadObj = parseJson(payload, "Payload");
      const txPayload = {
        transaction_id: payloadObj.transaction_id ?? `TXN-${Date.now()}`,
        user_id: payloadObj.user_id ?? "user-123",
        amount: payloadObj.amount ?? 1000,
        currency: payloadObj.currency ?? "EUR",
        transaction_type: payloadObj.transaction_type ?? "transfer",
        country_code: payloadObj.country_code ?? "FR",
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
      setError(
        err instanceof Error ? err.message : "Failed to create transaction",
      );
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
      const payload = normalizeFeaturePayload(
        parseJson(featuresJson, "Features"),
      );
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
        `${API_URL}/api/features/${featureEntityType}/${featureEntityId}`,
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
          `${API_URL}/api/audit/logs?entity_type=decision&entity_id=${decisionId}&limit=20`,
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
  }, [autoRun, autoRunDone]); // eslint-disable-line react-hooks/exhaustive-deps

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
          `${API_URL}/api/audit/decisions?${query}`,
        );
        if (!res.ok) throw new Error(await res.text());
        const data = (await res.json()) as DecisionListResponse;
        setDecisions(data.items);
        setDecisionTotal(data.total ?? 0);
        setSelectedDecision((prev) => {
          if (!data.items.length) return null;
          if (!prev) return data.items[0];
          const exists = data.items.some(
            (item) => item.decision_id === prev.decision_id,
          );
          return exists ? prev : data.items[0];
        });
      } catch (err) {
        setDecisionError(
          err instanceof Error ? err.message : "Failed to load decision log",
        );
        setDecisions([]);
      } finally {
        setDecisionLoading(false);
      }
    };
    if (activeTab === "log") {
      fetchDecisions();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
          `${API_URL}/api/reporting/evidence/decision/${selectedDecision.decision_id}`,
        );
        if (!res.ok) throw new Error(await res.text());
        setEvidenceBundle((await res.json()) as DecisionEvidenceBundle);
      } catch {
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
    const metadataObj: Record<string, unknown> & {
      context?: Record<string, unknown>;
    } = event.metadata ?? {};
    const contextObj = metadataObj.context ?? metadataObj;

    setEventType(String(event.event_type ?? eventType));
    setEntityType(String(event.entity_type ?? ""));
    setEntityId(String(event.entity_id ?? ""));
    setSource(String(event.source ?? "replay"));
    setPayload(JSON.stringify(payloadObj, null, 2));
    setContext(JSON.stringify(contextObj, null, 2));
    setReplaySourceDecisionId(selectedDecision?.decision_id ?? null);
    setActiveTab("console");
    if (autoRunReplay) {
      setTimeout(() => {
        handleDecide();
      }, 0);
    }
  };

  const renderDecisionLog = () => (
    <DecisionLog
      apiUrl={API_URL}
      decisions={decisions}
      decisionTotal={decisionTotal}
      decisionPage={decisionPage}
      setDecisionPage={setDecisionPage}
      decisionPageSize={decisionPageSize}
      setDecisionPageSize={setDecisionPageSize}
      decisionFilter={decisionFilter}
      setDecisionFilter={setDecisionFilter}
      eventTypeFilter={eventTypeFilter}
      setEventTypeFilter={setEventTypeFilter}
      entityTypeFilter={entityTypeFilter}
      setEntityTypeFilter={setEntityTypeFilter}
      entityIdFilter={entityIdFilter}
      setEntityIdFilter={setEntityIdFilter}
      decisionIdFilter={decisionIdFilter}
      setDecisionIdFilter={setDecisionIdFilter}
      eventIdFilter={eventIdFilter}
      setEventIdFilter={setEventIdFilter}
      fromFilter={fromFilter}
      setFromFilter={setFromFilter}
      toFilter={toFilter}
      setToFilter={setToFilter}
      decisionLoading={decisionLoading}
      decisionError={decisionError}
      selectedDecision={selectedDecision}
      onSelectDecision={(item) => setSelectedDecision(item)}
      onRefresh={() => setRefreshTick((tick) => tick + 1)}
      decisionBadgeStyles={decisionBadgeStyles}
      evidenceBundle={evidenceBundle}
      evidenceLoading={evidenceLoading}
      onLoadReplayIntoSimulator={loadReplayIntoSimulator}
      replaySourceDecisionId={replaySourceDecisionId}
      replayResult={replayResult}
    />
  );

  const renderConsole = () => (
    <DecisionSimulator
      apiUrl={API_URL}
      autoRun={autoRun}
      onAutoRunChange={setAutoRun}
      eventType={eventType}
      onEventTypeChange={setEventType}
      transactionId={transactionId}
      onTransactionIdChange={setTransactionId}
      entityType={entityType}
      onEntityTypeChange={setEntityType}
      entityId={entityId}
      onEntityIdChange={setEntityId}
      source={source}
      onSourceChange={setSource}
      payload={payload}
      onPayloadChange={setPayload}
      context={context}
      onContextChange={setContext}
      error={error}
      loading={loading}
      transactionLoading={transactionLoading}
      onIngestEvent={handleIngest}
      onCreateTransaction={handleCreateTransaction}
      onRunDecision={handleDecide}
      featureEntityType={featureEntityType}
      onFeatureEntityTypeChange={setFeatureEntityType}
      featureEntityId={featureEntityId}
      onFeatureEntityIdChange={setFeatureEntityId}
      featuresJson={featuresJson}
      onFeaturesJsonChange={setFeaturesJson}
      featureLoading={featureLoading}
      featureResponse={featureResponse}
      onSetFeatures={handleSetFeatures}
      onLoadFeatures={handleLoadFeatures}
      eventResult={eventResult}
      transactionResult={transactionResult}
      decisionResult={decisionResult}
      auditLoading={auditLoading}
      eventRecord={eventRecord}
      decisionRecord={decisionRecord}
      auditLogs={auditLogs}
    />
  );

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        <div>
          <div className="text-xs uppercase tracking-[0.3em] text-gray-400">
            YuFeed Risk OS
          </div>
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
