"use client";

import { useEffect, useState } from "react";
import { Plus, LineChart, UploadCloud, Rocket } from "lucide-react";
import { fetchWithAuth } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/apiBaseUrl";
import { useModelRegistry } from "@/hooks/queries/useSpecializedData";
import { LoadingBoundary } from "@/components/shared/LoadingBoundary";

const API_URL = getApiBaseUrl();

type Model = {
    id: number;
    model_id: string;
    name: string;
    description?: string | null;
    model_type: string;
    owner?: string | null;
    status: string;
};

type ModelVersion = {
    id: number;
    version: string;
    status: string;
    artifact_uri?: string | null;
    feature_set_hash?: string | null;
    training_window?: string | null;
    metrics?: Record<string, unknown> | null;
};

export default function ModelRegistryPage() {
    const { data: models = [], isLoading, error: queryError, refetch } = useModelRegistry();
    const [selectedModel, setSelectedModel] = useState<Model | null>(null);
    const [versions, setVersions] = useState<ModelVersion[]>([]);
    const [error, setError] = useState<string | null>(null);

    const [modelId, setModelId] = useState("risk-model");
    const [modelName, setModelName] = useState("Risk Scoring Model");
    const [modelType, setModelType] = useState("ml");
    const [modelOwner, setModelOwner] = useState("risk-team");
    const [modelDescription, setModelDescription] = useState("");

    const [versionValue, setVersionValue] = useState("v1");
    const [artifactUri, setArtifactUri] = useState("");
    const [featureHash, setFeatureHash] = useState("");
    const [trainingWindow, setTrainingWindow] = useState("2025-01-01 to 2025-12-31");
    const [metricsJson, setMetricsJson] = useState("{\"auc\":0.82,\"precision\":0.6}");

    const [driftScore, setDriftScore] = useState("0.12");
    const [driftStatus, setDriftStatus] = useState("ok");
    const [driftMetrics, setDriftMetrics] = useState("{\"psi\":0.12}");


    const loadVersions = async (model: Model) => {
        try {
            const res = await fetchWithAuth(`${API_URL}/api/models/${model.model_id}/versions`);
            if (!res.ok) throw new Error(await res.text());
            setVersions(await res.json());
        } catch {
            setVersions([]);
        }
    };

    useEffect(() => {
        if (models.length && !selectedModel) {
            setSelectedModel(models[0]);
        }
    }, [models, selectedModel]);

    useEffect(() => {
        if (selectedModel) {
            loadVersions(selectedModel);
        }
    }, [selectedModel]);

    const handleCreateModel = async () => {
        setError(null);
        try {
            const res = await fetchWithAuth(`${API_URL}/api/models`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    model_id: modelId,
                    name: modelName,
                    description: modelDescription || undefined,
                    model_type: modelType,
                    owner: modelOwner || undefined,
                }),
            });
            if (!res.ok) throw new Error(await res.text());
            await refetch();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to create model");
        }
    };

    const handleCreateVersion = async () => {
        if (!selectedModel) return;
        setError(null);
        try {
            const res = await fetchWithAuth(`${API_URL}/api/models/${selectedModel.model_id}/versions`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    version: versionValue,
                    status: "staging",
                    artifact_uri: artifactUri || undefined,
                    feature_set_hash: featureHash || undefined,
                    training_window: trainingWindow || undefined,
                    metrics: metricsJson ? JSON.parse(metricsJson) : undefined,
                }),
            });
            if (!res.ok) throw new Error(await res.text());
            await loadVersions(selectedModel);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to create version");
        }
    };

    const handlePromote = async (versionId: number) => {
        if (!selectedModel) return;
        setError(null);
        try {
            const res = await fetchWithAuth(
                `${API_URL}/api/models/${selectedModel.model_id}/versions/${versionId}/promote`,
                { method: "POST" }
            );
            if (!res.ok) throw new Error(await res.text());
            await loadVersions(selectedModel);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to promote version");
        }
    };

    const handleRecordDrift = async () => {
        if (!selectedModel || !versions.length) return;
        setError(null);
        try {
            const latest = versions[0];
            const res = await fetchWithAuth(
                `${API_URL}/api/models/${selectedModel.model_id}/versions/${latest.id}/drift`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        drift_score: Number(driftScore),
                        status: driftStatus,
                        metrics: driftMetrics ? JSON.parse(driftMetrics) : undefined,
                    }),
                }
            );
            if (!res.ok) throw new Error(await res.text());
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to record drift");
        }
    };

    return (
        <LoadingBoundary
            loading={isLoading}
            error={queryError || error}
            isEmpty={!models || models.length === 0}
            emptyMessage="No models registered"
            emptyDescription="Register your first model to start tracking versions"
        >
        <div className="min-h-screen p-6 bg-gray-50 dark:bg-gray-900">
            <div className="max-w-6xl mx-auto space-y-6">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Model Registry</h1>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Register models, track versions, and log drift.</p>
                </div>

                {error && (
                    <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/20 dark:text-red-300">
                        {error}
                    </div>
                )}

                <div className="grid gap-6 lg:grid-cols-3">
                    <div className="rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-950 space-y-4">
                        <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Create Model</h2>
                        <input value={modelId} onChange={(e) => setModelId(e.target.value)} className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900" placeholder="model_id" />
                        <input value={modelName} onChange={(e) => setModelName(e.target.value)} className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900" placeholder="Name" />
                        <input value={modelType} onChange={(e) => setModelType(e.target.value)} className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900" placeholder="Type" />
                        <input value={modelOwner} onChange={(e) => setModelOwner(e.target.value)} className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900" placeholder="Owner" />
                        <textarea value={modelDescription} onChange={(e) => setModelDescription(e.target.value)} rows={3} className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900" placeholder="Description" />
                        <button onClick={handleCreateModel} className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700">
                            <Plus className="h-4 w-4" />
                            Create
                        </button>
                    </div>

                    <div className="lg:col-span-2 rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-950 space-y-4">
                        <div className="flex items-center justify-between">
                            <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Models</h2>
                            {loading ? <span className="text-xs text-gray-500">Loading...</span> : null}
                        </div>
                        <div className="grid gap-2">
                            {models.map((model) => (
                                <button
                                    key={model.model_id}
                                    onClick={() => setSelectedModel(model)}
                                    className={`w-full text-left rounded-lg border px-3 py-2 text-sm ${selectedModel?.model_id === model.model_id ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20" : "border-gray-200 dark:border-gray-800"}`}
                                >
                                    <div className="font-medium text-gray-900 dark:text-white">{model.name}</div>
                                    <div className="text-xs text-gray-500">{model.model_id}</div>
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                {selectedModel && (
                    <div className="grid gap-6 lg:grid-cols-2">
                        <div className="rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-950 space-y-4">
                            <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Create Version</h2>
                            <input value={versionValue} onChange={(e) => setVersionValue(e.target.value)} className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900" placeholder="Version" />
                            <input value={artifactUri} onChange={(e) => setArtifactUri(e.target.value)} className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900" placeholder="Artifact URI" />
                            <input value={featureHash} onChange={(e) => setFeatureHash(e.target.value)} className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900" placeholder="Feature set hash" />
                            <input value={trainingWindow} onChange={(e) => setTrainingWindow(e.target.value)} className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900" placeholder="Training window" />
                            <textarea value={metricsJson} onChange={(e) => setMetricsJson(e.target.value)} rows={3} className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-xs font-mono dark:border-gray-800 dark:bg-gray-900" />
                            <button onClick={handleCreateVersion} className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800">
                                <UploadCloud className="h-4 w-4" />
                                Add Version
                            </button>
                        </div>

                        <div className="rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-950 space-y-4">
                            <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Version History</h2>
                            <div className="space-y-2">
                                {versions.length ? versions.map((version) => (
                                    <div key={version.id} className="rounded-lg border border-gray-100 px-3 py-2 dark:border-gray-800">
                                        <div className="flex items-center justify-between">
                                            <div className="font-medium text-gray-900 dark:text-white">{version.version}</div>
                                            <span className="text-xs text-gray-500">{version.status}</span>
                                        </div>
                                        <div className="mt-2 flex items-center gap-2">
                                            <button onClick={() => handlePromote(version.id)} className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-3 py-1 text-xs font-semibold text-white hover:bg-green-700">
                                                <Rocket className="h-3 w-3" />
                                                Promote
                                            </button>
                                        </div>
                                    </div>
                                )) : (
                                    <div className="text-xs text-gray-500">No versions yet.</div>
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {selectedModel && (
                    <div className="rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-950 space-y-4">
                        <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Record Drift</h2>
                        <div className="grid gap-3 md:grid-cols-3">
                            <input value={driftScore} onChange={(e) => setDriftScore(e.target.value)} className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900" placeholder="Drift score" />
                            <input value={driftStatus} onChange={(e) => setDriftStatus(e.target.value)} className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm dark:border-gray-800 dark:bg-gray-900" placeholder="Status" />
                            <textarea value={driftMetrics} onChange={(e) => setDriftMetrics(e.target.value)} rows={2} className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-xs font-mono dark:border-gray-800 dark:bg-gray-900" />
                        </div>
                        <button onClick={handleRecordDrift} className="inline-flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 dark:border-gray-800 dark:text-gray-300 dark:hover:bg-gray-900">
                            <LineChart className="h-4 w-4" />
                            Record Drift
                        </button>
                    </div>
                )}
            </div>
        </div>
        </LoadingBoundary>
    );
}
