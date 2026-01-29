"use client";

import { useEffect, useState } from "react";
import { Send, CheckCircle2 } from "lucide-react";
import { fetchWithAuth } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/apiBaseUrl";

const API_URL = getApiBaseUrl();

type TravelRuleResponse = {
    request_id: string;
    status: string;
    created_at: string;
    payload: any;
};

export default function TravelRulePage() {
    const [transactionId, setTransactionId] = useState("TXN-0001");
    const [amount, setAmount] = useState("1200");
    const [currency, setCurrency] = useState("EUR");
    const [asset, setAsset] = useState("");
    const [message, setMessage] = useState("");

    const [originatorName, setOriginatorName] = useState("Acme Payments");
    const [originatorAccount, setOriginatorAccount] = useState("ACCT-001");
    const [originatorWallet, setOriginatorWallet] = useState("");
    const [originatorCountry, setOriginatorCountry] = useState("FR");

    const [beneficiaryName, setBeneficiaryName] = useState("Beta Exchange");
    const [beneficiaryAccount, setBeneficiaryAccount] = useState("ACCT-993");
    const [beneficiaryWallet, setBeneficiaryWallet] = useState("");
    const [beneficiaryCountry, setBeneficiaryCountry] = useState("DE");

    const [loading, setLoading] = useState(false);
    const [submitLoading, setSubmitLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<TravelRuleResponse | null>(null);
    const [inbox, setInbox] = useState<TravelRuleResponse[]>([]);
    const [inboxLoading, setInboxLoading] = useState(false);

    const fetchInbox = async () => {
        setInboxLoading(true);
        try {
            const res = await fetchWithAuth(`${API_URL}/api/travel-rule/requests`);
            if (!res.ok) throw new Error(await res.text());
            setInbox(await res.json());
        } catch {
            setInbox([]);
        } finally {
            setInboxLoading(false);
        }
    };

    useEffect(() => {
        fetchInbox();
    }, []);

    const handleCreate = async () => {
        setLoading(true);
        setError(null);
        setResult(null);
        try {
            const payload = {
                transaction_id: transactionId,
                amount: Number(amount),
                currency,
                asset: asset || undefined,
                originator: {
                    name: originatorName,
                    account_id: originatorAccount || undefined,
                    wallet_address: originatorWallet || undefined,
                    country: originatorCountry || undefined,
                },
                beneficiary: {
                    name: beneficiaryName,
                    account_id: beneficiaryAccount || undefined,
                    wallet_address: beneficiaryWallet || undefined,
                    country: beneficiaryCountry || undefined,
                },
                message: message || undefined,
            };
            const res = await fetchWithAuth(`${API_URL}/api/travel-rule/requests`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            if (!res.ok) throw new Error(await res.text());
            setResult(await res.json());
            fetchInbox();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to create travel rule request");
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async () => {
        if (!result?.request_id) return;
        setSubmitLoading(true);
        setError(null);
        try {
            const res = await fetchWithAuth(`${API_URL}/api/travel-rule/requests/${result.request_id}/submit`, {
                method: "POST",
            });
            if (!res.ok) throw new Error(await res.text());
            setResult(await res.json());
            fetchInbox();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to submit travel rule request");
        } finally {
            setSubmitLoading(false);
        }
    };

    return (
        <div className="min-h-screen p-6 bg-gray-50 dark:bg-gray-900">
            <div className="max-w-5xl mx-auto space-y-6">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Travel Rule</h1>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                        Compose and submit Travel Rule payloads for VASP transfers.
                    </p>
                </div>

                {error && (
                    <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/20 dark:text-red-300">
                        {error}
                    </div>
                )}

                <div className="grid gap-6 lg:grid-cols-2">
                    <div className="space-y-4 rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-950">
                        <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Transfer Details</h2>
                        <div className="grid gap-3 md:grid-cols-2">
                            <div>
                                <label className="text-xs font-semibold uppercase text-gray-500">Transaction ID</label>
                                <input
                                    value={transactionId}
                                    onChange={(e) => setTransactionId(e.target.value)}
                                    className="mt-1 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900"
                                />
                            </div>
                            <div>
                                <label className="text-xs font-semibold uppercase text-gray-500">Amount</label>
                                <input
                                    value={amount}
                                    onChange={(e) => setAmount(e.target.value)}
                                    className="mt-1 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900"
                                />
                            </div>
                            <div>
                                <label className="text-xs font-semibold uppercase text-gray-500">Currency</label>
                                <input
                                    value={currency}
                                    onChange={(e) => setCurrency(e.target.value)}
                                    className="mt-1 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900"
                                />
                            </div>
                            <div>
                                <label className="text-xs font-semibold uppercase text-gray-500">Asset (optional)</label>
                                <input
                                    value={asset}
                                    onChange={(e) => setAsset(e.target.value)}
                                    className="mt-1 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900"
                                />
                            </div>
                        </div>
                        <div>
                            <label className="text-xs font-semibold uppercase text-gray-500">Message (optional)</label>
                            <textarea
                                value={message}
                                onChange={(e) => setMessage(e.target.value)}
                                rows={3}
                                className="mt-1 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900"
                            />
                        </div>
                    </div>

                    <div className="space-y-4 rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-950">
                        <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Originator</h2>
                        <input
                            value={originatorName}
                            onChange={(e) => setOriginatorName(e.target.value)}
                            placeholder="Name"
                            className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900"
                        />
                        <div className="grid gap-3 md:grid-cols-2">
                            <input
                                value={originatorAccount}
                                onChange={(e) => setOriginatorAccount(e.target.value)}
                                placeholder="Account ID"
                                className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900"
                            />
                            <input
                                value={originatorWallet}
                                onChange={(e) => setOriginatorWallet(e.target.value)}
                                placeholder="Wallet Address"
                                className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900"
                            />
                        </div>
                        <input
                            value={originatorCountry}
                            onChange={(e) => setOriginatorCountry(e.target.value)}
                            placeholder="Country"
                            className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900"
                        />
                    </div>
                </div>

                <div className="grid gap-6 lg:grid-cols-2">
                    <div className="space-y-4 rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-950">
                        <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Beneficiary</h2>
                        <input
                            value={beneficiaryName}
                            onChange={(e) => setBeneficiaryName(e.target.value)}
                            placeholder="Name"
                            className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900"
                        />
                        <div className="grid gap-3 md:grid-cols-2">
                            <input
                                value={beneficiaryAccount}
                                onChange={(e) => setBeneficiaryAccount(e.target.value)}
                                placeholder="Account ID"
                                className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900"
                            />
                            <input
                                value={beneficiaryWallet}
                                onChange={(e) => setBeneficiaryWallet(e.target.value)}
                                placeholder="Wallet Address"
                                className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900"
                            />
                        </div>
                        <input
                            value={beneficiaryCountry}
                            onChange={(e) => setBeneficiaryCountry(e.target.value)}
                            placeholder="Country"
                            className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900"
                        />
                    </div>

                    <div className="space-y-4 rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-950">
                        <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Actions</h2>
                        <button
                            onClick={handleCreate}
                            disabled={loading}
                            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                        >
                            <Send className="h-4 w-4" />
                            {loading ? "Creating..." : "Create Request"}
                        </button>
                        {result ? (
                            <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-xs text-gray-700 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-300">
                                <div className="flex items-center gap-2 font-semibold text-green-600">
                                    <CheckCircle2 className="h-4 w-4" />
                                    {result.request_id} • {result.status}
                                </div>
                                <pre className="mt-3 max-h-64 overflow-auto rounded bg-gray-950 p-3 text-gray-100">
                                    {JSON.stringify(result, null, 2)}
                                </pre>
                                <button
                                    onClick={handleSubmit}
                                    disabled={submitLoading}
                                    className="mt-3 rounded-lg border border-gray-200 px-3 py-2 text-xs font-semibold text-gray-600 hover:bg-white disabled:opacity-50 dark:border-gray-800 dark:text-gray-200 dark:hover:bg-gray-950"
                                >
                                    {submitLoading ? "Submitting..." : "Submit to Network"}
                                </button>
                            </div>
                        ) : (
                            <p className="text-xs text-gray-500">Create a Travel Rule request to see the payload.</p>
                        )}
                    </div>
                </div>

                <div className="rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-950">
                    <div className="flex items-center justify-between">
                        <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Travel Rule Inbox</h2>
                        <button
                            onClick={fetchInbox}
                            className="text-xs text-gray-500 hover:text-gray-700"
                        >
                            Refresh
                        </button>
                    </div>
                    <div className="mt-4 space-y-3 text-sm">
                        {inboxLoading ? (
                            <div className="text-xs text-gray-500">Loading requests...</div>
                        ) : inbox.length ? (
                            inbox.map((item) => (
                                <div key={item.request_id} className="rounded-lg border border-gray-100 px-3 py-2 dark:border-gray-800">
                                    <div className="flex items-center justify-between">
                                        <div className="font-medium text-gray-900 dark:text-white">{item.request_id}</div>
                                        <span className="text-xs text-gray-500">{item.status}</span>
                                    </div>
                                    <div className="text-xs text-gray-500">
                                        {item.payload?.originator?.name} → {item.payload?.beneficiary?.name} • {item.payload?.amount} {item.payload?.currency}
                                    </div>
                                    <div className="mt-2 flex items-center gap-3 text-xs">
                                        <a
                                            href={`/audit?entity_type=travel_rule_request&entity_id=${item.request_id}`}
                                            className="text-blue-600 hover:text-blue-700"
                                        >
                                            View audit
                                        </a>
                                        <a
                                            href={`${API_URL}/api/reporting/evidence/travel-rule/${item.request_id}`}
                                            className="text-gray-500 hover:text-gray-700"
                                        >
                                            Evidence JSON
                                        </a>
                                    </div>
                                </div>
                            ))
                        ) : (
                            <div className="text-xs text-gray-500">No requests yet.</div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
