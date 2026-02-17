"use client";

import { useEffect, useState } from "react";
import { Link2, ShieldCheck } from "lucide-react";
import { fetchWithAuth } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/apiBaseUrl";

const API_URL = getApiBaseUrl();

type ScoreResponse = {
  address: string;
  risk_score: number;
  risk_level: string;
  vendor: string;
  signals: Record<string, unknown>;
};

export default function OnchainRiskPage() {
  const [address, setAddress] = useState(
    "0x9fB1b2e8cB8bB0b1111111111111111111111111",
  );
  const [chain, setChain] = useState("eth");
  const [asset, setAsset] = useState("USDC");
  const [plugins, setPlugins] = useState<string[]>([]);
  const [result, setResult] = useState<ScoreResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchPlugins = async () => {
    try {
      const res = await fetchWithAuth(`${API_URL}/api/onchain/plugins`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setPlugins(data.plugins ?? []);
    } catch {
      setPlugins([]);
    }
  };

  useEffect(() => {
    fetchPlugins();
  }, []);

  const handleScore = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetchWithAuth(`${API_URL}/api/onchain/score`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          address,
          chain: chain || undefined,
          asset: asset || undefined,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      setResult(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to score address");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen p-6 bg-gray-50 dark:bg-gray-900">
      <div className="max-w-4xl mx-auto space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            On-chain Risk
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Score wallet addresses with pluggable on-chain risk providers.
          </p>
        </div>

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/20 dark:text-red-300">
            {error}
          </div>
        )}

        <div className="rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-950 space-y-4">
          <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
            <ShieldCheck className="h-4 w-4 text-blue-600" />
            Providers: {plugins.length ? plugins.join(", ") : "mock-onchain"}
          </div>
          <div>
            <label className="text-xs font-semibold uppercase text-gray-500">
              Wallet Address
            </label>
            <input
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              className="mt-1 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900"
            />
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <label className="text-xs font-semibold uppercase text-gray-500">
                Chain
              </label>
              <input
                value={chain}
                onChange={(e) => setChain(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900"
              />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase text-gray-500">
                Asset
              </label>
              <input
                value={asset}
                onChange={(e) => setAsset(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900"
              />
            </div>
          </div>
          <button
            onClick={handleScore}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            <Link2 className="h-4 w-4" />
            {loading ? "Scoring..." : "Score Address"}
          </button>
        </div>

        <div className="rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-950">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
            Score Result
          </h2>
          {result ? (
            <pre className="mt-3 rounded-lg bg-gray-950 p-4 text-xs text-gray-100 overflow-auto">
              {JSON.stringify(result, null, 2)}
            </pre>
          ) : (
            <p className="mt-3 text-xs text-gray-500">No score yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}
