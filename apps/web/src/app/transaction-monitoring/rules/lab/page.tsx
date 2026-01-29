"use client";

import { useState } from "react";
import { FlaskConical, PlayCircle, LineChart, CheckCircle2, XCircle } from "lucide-react";
import { fetchWithAuth } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/apiBaseUrl";

const API_URL = getApiBaseUrl();

const SAMPLE_PAYLOAD = JSON.stringify(
    {
        amount: 12500,
        currency: "EUR",
        transaction_type: "transfer",
        country_code: "FR",
    },
    null,
    2
);

type SimulationResult = {
    rule_id: string;
    transaction_id?: string | null;
    would_trigger: boolean;
    logic: string;
    condition_results: { condition: Record<string, any>; passed: boolean }[];
    evaluated_at: string;
};

type BacktestResult = {
    rule_id: string;
    total_transactions: number;
    matches: number;
    match_rate: number;
    evaluated_at: string;
    window: { start_date?: string | null; end_date?: string | null };
    samples: {
        transaction_id: string;
        amount: number;
        currency: string;
        transaction_type?: string | null;
        country_code?: string | null;
        timestamp: string;
        would_trigger: boolean;
    }[];
};

export default function RuleLabPage() {
    const [ruleId, setRuleId] = useState("RULE-001");
    const [transactionId, setTransactionId] = useState("");
    const [payload, setPayload] = useState(SAMPLE_PAYLOAD);
    const [simulationResult, setSimulationResult] = useState<SimulationResult | null>(null);
    const [backtestResult, setBacktestResult] = useState<BacktestResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [backtestLoading, setBacktestLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [startDate, setStartDate] = useState("");
    const [endDate, setEndDate] = useState("");
    const [limit, setLimit] = useState(500);
    const [sampleSize, setSampleSize] = useState(5);

    const parsePayload = () => {
        if (!payload.trim()) return {};
        return JSON.parse(payload);
    };

    const runSimulation = async () => {
        setLoading(true);
        setError(null);
        setSimulationResult(null);
        try {
            const body: Record<string, any> = {};
            if (transactionId.trim()) {
                body.transaction_id = Number(transactionId);
            } else {
                body.payload = parsePayload();
            }
            const res = await fetchWithAuth(`${API_URL}/api/monitoring-rules/${ruleId}/simulate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
            if (!res.ok) throw new Error(await res.text());
            setSimulationResult(await res.json());
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to simulate rule");
        } finally {
            setLoading(false);
        }
    };

    const runBacktest = async () => {
        setBacktestLoading(true);
        setError(null);
        setBacktestResult(null);
        try {
            const body: Record<string, any> = {
                limit,
                sample_size: sampleSize,
            };
            if (startDate) body.start_date = startDate;
            if (endDate) body.end_date = endDate;
            const res = await fetchWithAuth(`${API_URL}/api/monitoring-rules/${ruleId}/backtest`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
            if (!res.ok) throw new Error(await res.text());
            setBacktestResult(await res.json());
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to backtest rule");
        } finally {
            setBacktestLoading(false);
        }
    };

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            <div className="flex flex-col gap-3">
                <div className="inline-flex items-center gap-3 text-gray-900 dark:text-gray-100">
                    <FlaskConical className="h-7 w-7 text-blue-600" />
                    <h1 className="text-3xl font-bold tracking-tight">Rule Lab</h1>
                </div>
                <p className="text-gray-600 dark:text-gray-400 max-w-2xl">
                    Simulate and backtest monitoring rules against payloads or historical transactions without creating alerts.
                </p>
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
                <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-950">
                    <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">Rule Simulation</h2>
                    <div className="space-y-4">
                        <div className="grid gap-3 md:grid-cols-2">
                            <div>
                                <label className="text-xs font-semibold uppercase text-gray-500">Rule ID</label>
                                <input
                                    value={ruleId}
                                    onChange={(e) => setRuleId(e.target.value)}
                                    className="mt-1 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900"
                                />
                            </div>
                            <div>
                                <label className="text-xs font-semibold uppercase text-gray-500">Transaction ID (optional)</label>
                                <input
                                    value={transactionId}
                                    onChange={(e) => setTransactionId(e.target.value)}
                                    className="mt-1 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900"
                                    placeholder="Use payload if empty"
                                />
                            </div>
                        </div>
                        <div>
                            <label className="text-xs font-semibold uppercase text-gray-500">Payload JSON</label>
                            <textarea
                                value={payload}
                                onChange={(e) => setPayload(e.target.value)}
                                rows={8}
                                className="mt-1 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-xs font-mono dark:border-gray-800 dark:bg-gray-900"
                            />
                        </div>
                        <button
                            onClick={runSimulation}
                            disabled={loading}
                            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                        >
                            <PlayCircle className="h-4 w-4" />
                            {loading ? "Simulating..." : "Run Simulation"}
                        </button>
                    </div>
                </div>

                <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-950">
                    <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">Rule Backtest</h2>
                    <div className="space-y-4">
                        <div className="grid gap-3 md:grid-cols-2">
                            <div>
                                <label className="text-xs font-semibold uppercase text-gray-500">Start Date</label>
                                <input
                                    type="date"
                                    value={startDate}
                                    onChange={(e) => setStartDate(e.target.value)}
                                    className="mt-1 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900"
                                />
                            </div>
                            <div>
                                <label className="text-xs font-semibold uppercase text-gray-500">End Date</label>
                                <input
                                    type="date"
                                    value={endDate}
                                    onChange={(e) => setEndDate(e.target.value)}
                                    className="mt-1 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900"
                                />
                            </div>
                        </div>
                        <div className="grid gap-3 md:grid-cols-2">
                            <div>
                                <label className="text-xs font-semibold uppercase text-gray-500">Limit</label>
                                <input
                                    type="number"
                                    value={limit}
                                    onChange={(e) => setLimit(Number(e.target.value))}
                                    className="mt-1 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900"
                                />
                            </div>
                            <div>
                                <label className="text-xs font-semibold uppercase text-gray-500">Sample Size</label>
                                <input
                                    type="number"
                                    value={sampleSize}
                                    onChange={(e) => setSampleSize(Number(e.target.value))}
                                    className="mt-1 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900"
                                />
                            </div>
                        </div>
                        <button
                            onClick={runBacktest}
                            disabled={backtestLoading}
                            className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50 dark:bg-white dark:text-gray-900 dark:hover:bg-gray-100"
                        >
                            <LineChart className="h-4 w-4" />
                            {backtestLoading ? "Backtesting..." : "Run Backtest"}
                        </button>
                    </div>
                </div>
            </div>

            {error && (
                <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/20 dark:text-red-300">
                    {error}
                </div>
            )}

            <div className="grid gap-6 lg:grid-cols-2">
                <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-950">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Simulation Results</h3>
                    {simulationResult ? (
                        <div className="space-y-4">
                            <div className="flex items-center gap-2 text-sm">
                                {simulationResult.would_trigger ? (
                                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                                ) : (
                                    <XCircle className="h-4 w-4 text-gray-400" />
                                )}
                                <span className="text-gray-700 dark:text-gray-300">
                                    {simulationResult.would_trigger ? "Rule would trigger" : "Rule would not trigger"}
                                </span>
                            </div>
                            <div className="text-xs text-gray-500">
                                Logic: {simulationResult.logic} • Evaluated {new Date(simulationResult.evaluated_at).toLocaleString()}
                            </div>
                            <div className="space-y-2">
                                {simulationResult.condition_results.map((result, index) => (
                                    <div key={index} className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-xs dark:border-gray-800 dark:bg-gray-900">
                                        <div className="flex items-center justify-between">
                                            <span className="text-gray-600 dark:text-gray-300">
                                                {result.condition.field} {result.condition.operator} {JSON.stringify(result.condition.value)}
                                            </span>
                                            <span className={result.passed ? "text-green-600" : "text-gray-400"}>
                                                {result.passed ? "pass" : "fail"}
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <p className="text-sm text-gray-500">Run a simulation to see condition-level outcomes.</p>
                    )}
                </div>

                <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-950">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Backtest Summary</h3>
                    {backtestResult ? (
                        <div className="space-y-4">
                            <div className="grid gap-3 md:grid-cols-3">
                                <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 dark:border-gray-800 dark:bg-gray-900">
                                    <div className="text-xs uppercase text-gray-500">Transactions</div>
                                    <div className="text-lg font-semibold text-gray-900 dark:text-white">{backtestResult.total_transactions}</div>
                                </div>
                                <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 dark:border-gray-800 dark:bg-gray-900">
                                    <div className="text-xs uppercase text-gray-500">Matches</div>
                                    <div className="text-lg font-semibold text-gray-900 dark:text-white">{backtestResult.matches}</div>
                                </div>
                                <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 dark:border-gray-800 dark:bg-gray-900">
                                    <div className="text-xs uppercase text-gray-500">Match Rate</div>
                                    <div className="text-lg font-semibold text-gray-900 dark:text-white">{backtestResult.match_rate}%</div>
                                </div>
                            </div>
                            <div className="space-y-2">
                                {backtestResult.samples.length === 0 ? (
                                    <p className="text-sm text-gray-500">No matches found in the sampled range.</p>
                                ) : (
                                    backtestResult.samples.map((sample) => (
                                        <div key={sample.transaction_id} className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-xs dark:border-gray-800 dark:bg-gray-900">
                                            <div className="flex items-center justify-between">
                                                <span className="text-gray-700 dark:text-gray-300">
                                                    {sample.transaction_id} • {sample.amount} {sample.currency}
                                                </span>
                                                <span className="text-gray-500">{sample.country_code || "N/A"}</span>
                                            </div>
                                            <div className="text-gray-400">{new Date(sample.timestamp).toLocaleString()}</div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    ) : (
                        <p className="text-sm text-gray-500">Run a backtest to get rule coverage stats.</p>
                    )}
                </div>
            </div>
        </div>
    );
}
