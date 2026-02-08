"use client";

import type { FeatureSetResponse } from "@/app/decisioning/components/types";

export default function FeatureStorePanel({
  featureEntityType,
  setFeatureEntityType,
  featureEntityId,
  setFeatureEntityId,
  featuresJson,
  setFeaturesJson,
  featureLoading,
  featureResponse,
  onSetFeatures,
  onLoadFeatures,
}: {
  featureEntityType: string;
  setFeatureEntityType: (value: string) => void;
  featureEntityId: string;
  setFeatureEntityId: (value: string) => void;
  featuresJson: string;
  setFeaturesJson: (value: string) => void;
  featureLoading: boolean;
  featureResponse: FeatureSetResponse | null;
  onSetFeatures: () => void;
  onLoadFeatures: () => void;
}) {
  return (
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
          onClick={onSetFeatures}
          disabled={featureLoading}
          className="px-4 py-2 rounded-md bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 text-sm disabled:opacity-60"
        >
          Set Features
        </button>
        <button
          onClick={onLoadFeatures}
          disabled={featureLoading}
          className="px-4 py-2 rounded-md bg-gray-900 text-white text-sm disabled:opacity-60"
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
  );
}
