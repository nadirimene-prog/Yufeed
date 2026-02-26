"use client";

import { use, useEffect, useState } from "react";
import DocTabs from "@/components/doc-tabs";
import { TimelineView } from "@/components/doc/timeline-view";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { getDocument } from "@/lib/api";
import { analyzeDocument } from "@/lib/compliance-api";
import { getAuthUserProfile } from "@/lib/auth";
import { handleApiError } from "@/lib/api-error-handler";

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
  const [reanalyzing, setReanalyzing] = useState(false);
  const [reanalyzeFeedback, setReanalyzeFeedback] = useState<{
    kind: "success" | "error";
    message: string;
  } | null>(null);
  const currentUser = getAuthUserProfile();
  const isAdminUser = (currentUser?.role ?? "").toLowerCase() === "admin";

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

  const handleReanalyze = async () => {
    if (!document?.celex) return;
    setReanalyzeFeedback(null);
    setReanalyzing(true);
    try {
      const response = await analyzeDocument(document.celex, true);
      await loadDocument();

      const extractedCandidates = Array.isArray(response?.results?.obligations_json)
        ? response.results.obligations_json.length
        : null;
      setReanalyzeFeedback({
        kind: "success",
        message:
          typeof extractedCandidates === "number"
            ? `Re-analysis complete. Extracted ${extractedCandidates} obligation candidates.`
            : "Re-analysis complete.",
      });
    } catch (err) {
      handleApiError(err, { context: `Re-analyze document ${document.celex}` });
      setReanalyzeFeedback({
        kind: "error",
        message:
          "Re-analysis failed. Check permissions (admin only) or review backend logs.",
      });
    } finally {
      setReanalyzing(false);
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
          {error ?? "Document not found"}
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
          className="rounded-full p-2 hover:bg-slate-100  transition-colors"
        >
          <ArrowLeft className="h-6 w-6 text-slate-600 " />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            {document.type && (
              <span className="rounded bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-800  ">
                {document.type}
              </span>
            )}
            <span className="rounded bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-800  ">
              {document.status || "Active"}
            </span>
            {document.compliance_domain && (
              <span className="rounded bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-800   uppercase">
                {document.compliance_domain}
              </span>
            )}
            {document.risk_level && (
              <span
                className={`rounded px-2 py-0.5 text-xs font-semibold uppercase ${
                  document.risk_level === "high"
                    ? "bg-red-100 text-red-800  "
                    : document.risk_level === "medium"
                      ? "bg-yellow-100 text-yellow-800  "
                      : "bg-slate-100 text-slate-800  "
                }`}
              >
                {document.risk_level} Risk
              </span>
            )}
          </div>
          <h1 className="text-2xl font-bold text-slate-900  sm:text-3xl">
            {document.title}
          </h1>
          <p className="text-sm text-slate-500 mt-1">CELEX: {document.celex}</p>
        </div>
        {isAdminUser && (
          <button
            type="button"
            onClick={() => void handleReanalyze()}
            disabled={reanalyzing}
            className="rounded-full border border-blue-200 bg-blue-50 px-4 py-2 text-xs font-semibold text-blue-700 hover:border-blue-300 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {reanalyzing ? "Re-analyzing..." : "Re-analyze AI"}
          </button>
        )}
      </div>

      {reanalyzeFeedback && (
        <div
          className={
            "rounded-lg border px-4 py-3 text-sm " +
            (reanalyzeFeedback.kind === "success"
              ? "border-emerald-200 bg-emerald-50 text-emerald-800"
              : "border-rose-200 bg-rose-50 text-rose-800")
          }
        >
          {reanalyzeFeedback.message}
        </div>
      )}

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
