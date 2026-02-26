"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Folder, AlertTriangle, Loader2, ArrowLeft } from "lucide-react";
import { fetchWithAuth } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/apiBaseUrl";
import { logger } from "@/lib/logger";
import Link from "next/link";

const API_URL = getApiBaseUrl();

function NewCaseContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const alertId = searchParams.get("alert");

  useEffect(() => {
    if (alertId) {
      createCaseFromAlert(alertId);
    }
  }, [alertId]); // eslint-disable-line react-hooks/exhaustive-deps

  const createCaseFromAlert = async (alertId: string) => {
    setLoading(true);
    setError(null);

    try {
      const res = await fetchWithAuth(
        `${API_URL}/api/cases/from-alert/${alertId}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        },
      );

      if (res.ok) {
        const data = await res.json();
        router.push(`/cases/${data.case_id}`);
      } else {
        const errorData = await res.json().catch(() => ({}));
        setError(errorData.detail ?? "Failed to create case from alert");
      }
    } catch (err) {
      logger.error("Error creating case from alert:", err);
      setError("Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (alertId && loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-50 ">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin mx-auto mb-4 text-blue-600" />
          <p className="text-lg text-slate-700 ">
            Creating case from alert #{alertId}...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-50 ">
        <div className="text-center max-w-md">
          <AlertTriangle className="h-12 w-12 mx-auto mb-4 text-red-600" />
          <p className="text-lg text-slate-700  mb-4">{error}</p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={() => router.back()}
              className="px-4 py-2 bg-slate-600 text-white rounded-lg hover:bg-slate-700"
            >
              Go Back
            </button>
            {alertId && (
              <button
                onClick={() => createCaseFromAlert(alertId)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Retry
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  // No alert ID - show manual case creation form
  return (
    <div className="min-h-screen bg-slate-50  p-6">
      <div className="max-w-2xl mx-auto">
        <div className="mb-6">
          <Link
            href="/cases"
            className="inline-flex items-center text-slate-600  hover:text-slate-900 "
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Cases
          </Link>
        </div>

        <div className="bg-white  rounded-lg shadow p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-blue-100  rounded-lg">
              <Folder className="w-6 h-6 text-blue-600 " />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-slate-900 ">
                Create New Case
              </h1>
              <p className="text-sm text-slate-500 ">
                Start a new investigation case
              </p>
            </div>
          </div>

          <p className="text-slate-600  mb-6">
            To create a case, you can either escalate a finding or an alert from
            the respective pages. Cases are automatically created with the
            relevant context and evidence attached.
          </p>

          <div className="flex gap-3">
            <Link
              href="/findings"
              className="flex-1 px-4 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition text-center"
            >
              View Findings
            </Link>
            <Link
              href="/alerts"
              className="flex-1 px-4 py-3 bg-slate-100  text-slate-700  rounded-lg hover:bg-slate-200  transition text-center"
            >
              View Alerts
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function NewCasePage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-pulse text-slate-500">Loading...</div>
        </div>
      }
    >
      <NewCaseContent />
    </Suspense>
  );
}
