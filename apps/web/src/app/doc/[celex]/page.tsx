"use client";

import { use, useEffect, useState } from "react";
import DocTabs from "@/components/doc-tabs";
import { TimelineView } from "@/components/doc/timeline-view";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { getDocument } from "@/lib/api";

interface LegalDocument {
  celex: string;
  eli?: string;
  cellar_id?: string;
  title: string;
  type?: string;
  publication_date?: string;
  entry_into_force_date?: string;
  status: string;
  last_modified?: string;
  compliance_domain?: string;
  risk_level?: string;
  implementation_deadline?: string;
  jurisdictional_scope?: string;
  obligations_json?: Record<string, string | number | boolean>;
  ai_summary?: string;
  analyzed_at?: string;
}

export default function DocPage({
  params,
}: {
  params: Promise<{ celex: string }>;
}) {
  const { celex } = use(params);
  const [document, setDocument] = useState<LegalDocument | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDocument();
  }, [celex]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadDocument = async () => {
    try {
      const data = await getDocument(celex);
      setDocument(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load document");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Loading document...</div>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <div className="text-lg text-red-600">
          {error || "Document not found"}
        </div>
        <Link href="/search" className="text-blue-600 hover:underline">
          Back to Search
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex items-center gap-4">
        <Link
          href="/search"
          className="rounded-full p-2 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        >
          <ArrowLeft className="h-6 w-6 text-gray-600 dark:text-gray-400" />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            {document.type && (
              <span className="rounded bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                {document.type}
              </span>
            )}
            <span className="rounded bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-800 dark:bg-green-900 dark:text-green-200">
              {document.status || "Active"}
            </span>
            {document.compliance_domain && (
              <span className="rounded bg-purple-100 px-2 py-0.5 text-xs font-semibold text-purple-800 dark:bg-purple-900 dark:text-purple-200 uppercase">
                {document.compliance_domain}
              </span>
            )}
            {document.risk_level && (
              <span
                className={`rounded px-2 py-0.5 text-xs font-semibold uppercase ${
                  document.risk_level === "high"
                    ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
                    : document.risk_level === "medium"
                      ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"
                      : "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200"
                }`}
              >
                {document.risk_level} Risk
              </span>
            )}
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 sm:text-3xl">
            {document.title}
          </h1>
          <p className="text-sm text-gray-500 mt-1">CELEX: {document.celex}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <DocTabs document={document} celex={celex} />
        </div>
        <div className="lg:col-span-1 space-y-6">
          <TimelineView celex={celex} />
        </div>
      </div>
    </div>
  );
}
