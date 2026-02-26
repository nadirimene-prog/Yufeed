"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  FileText,
  AlertTriangle,
  CheckCircle,
  Download,
  Send,
} from "lucide-react";
import { fetchWithAuth } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/apiBaseUrl";
import { logger } from "@/lib/logger";

const API_URL = getApiBaseUrl();

interface CitedRegulation {
  celex?: string;
  title?: string;
  relevance?: string;
  [key: string]: unknown;
}

interface SupportingAlert {
  alert_id?: string;
  type?: string;
  severity?: string;
  created_at?: string;
  [key: string]: unknown;
}

interface SupportingDocuments {
  alerts: SupportingAlert[];
  investigation_summary?: string;
  [key: string]: unknown;
}

interface SARData {
  sar_id: string;
  filing_date: string;
  case_reference: string;
  filing_institution: {
    name?: string;
    type?: string;
    country?: string;
    contact?: string;
    [key: string]: unknown;
  };
  subject_information: {
    type?: string;
    identifier?: string;
    transaction_count?: number;
    total_amount?: number | string;
    [key: string]: unknown;
  };
  suspicious_activity: {
    narrative: string;
    activity_type: string;
    activity_dates: Record<string, unknown> | string | null;
    total_amount: Record<string, number | string> | number | string | null;
    transaction_count: number;
    alert_count: number;
  };
  regulatory_basis: {
    cited_regulations: CitedRegulation[];
    violations: Record<string, unknown> | string | null;
    regulatory_context: string;
  };
  supporting_documents: SupportingDocuments;
  case_details: Record<string, unknown>;
}

function SARPrepareContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [sarData, setSarData] = useState<SARData | null>(null);
  const [loading, setLoading] = useState(true);
  const [preparing, setPreparing] = useState(false);
  const [jurisdiction, setJurisdiction] = useState("EU");
  // Institution info state is reserved for future use when editing institution details

  const [_institutionInfo] = useState({
    name: "",
    type: "Financial Institution",
    country: "EU",
    contact: "",
  });

  const caseId = searchParams.get("case_id");

  useEffect(() => {
    if (caseId) {
      prepareSAR();
    }
  }, [caseId]); // eslint-disable-line react-hooks/exhaustive-deps

  const prepareSAR = async () => {
    if (!caseId) return;

    setPreparing(true);
    try {
      const res = await fetchWithAuth(
        `${API_URL}/api/reporting/sar/prepare/${caseId}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        },
      );

      if (res.ok) {
        const data = await res.json();
        setSarData(data);
      }
      setLoading(false);
    } catch (error) {
      logger.error("Error preparing SAR:", error);
      setLoading(false);
    } finally {
      setPreparing(false);
    }
  };

  const handleFile = async (dryRun: boolean = true) => {
    if (!sarData) return;

    try {
      const res = await fetchWithAuth(
        `${API_URL}/api/reporting/sar/file/${sarData.case_reference}?jurisdiction=${jurisdiction}&dry_run=${dryRun}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        },
      );

      if (res.ok) {
        const result = await res.json();
        alert(
          `SAR ${dryRun ? "validated" : "filed"} successfully!\n\nReference: ${result.filing_reference ?? result.sar_id}`,
        );

        if (!dryRun) {
          router.push("/cases");
        }
      }
    } catch (error) {
      logger.error("Error filing SAR:", error);
      alert("Error filing SAR. Please try again.");
    }
  };

  const handleDownload = () => {
    if (!sarData) return;

    const blob = new Blob([JSON.stringify(sarData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${sarData.sar_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading || preparing) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <FileText className="h-12 w-12 animate-spin mx-auto mb-4 text-blue-600" />
          <p className="text-lg text-slate-700 ">
            {preparing ? "Preparing SAR..." : "Loading..."}
          </p>
        </div>
      </div>
    );
  }

  if (!sarData) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <AlertTriangle className="h-12 w-12 mx-auto mb-4 text-red-600" />
          <p className="text-lg text-slate-700  mb-4">Unable to prepare SAR</p>
          <button
            onClick={() => router.back()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50  p-6">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-3xl font-bold text-slate-900  mb-2">
                Suspicious Activity Report
              </h1>
              <p className="text-slate-600 ">
                Review and file SAR for case {sarData.case_reference}
              </p>
            </div>

            <div className="flex gap-2">
              <button
                onClick={handleDownload}
                className="flex items-center gap-2 px-4 py-2 bg-slate-600 text-white rounded-lg hover:bg-slate-700 transition"
              >
                <Download className="h-4 w-4" />
                Download
              </button>
              <button
                onClick={() => handleFile(true)}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
              >
                <CheckCircle className="h-4 w-4" />
                Validate
              </button>
              <button
                onClick={() => handleFile(false)}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
              >
                <Send className="h-4 w-4" />
                File SAR
              </button>
            </div>
          </div>

          {/* Jurisdiction Selector */}
          <div className="bg-white  rounded-lg shadow p-4">
            <label className="block text-sm font-medium text-slate-700  mb-2">
              Filing Jurisdiction
            </label>
            <select
              value={jurisdiction}
              onChange={(e) => setJurisdiction(e.target.value)}
              className="w-full px-4 py-2 border border-slate-300  rounded-lg bg-white  text-slate-900 "
            >
              <option value="US">United States (FinCEN)</option>
              <option value="EU">European Union (National FIU)</option>
              <option value="INTL">International (goAML)</option>
            </select>
          </div>
        </div>

        <div className="space-y-6">
          {/* SAR Header */}
          <div className="bg-white  rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-slate-900  mb-4">
              SAR Information
            </h2>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-slate-600  mb-1">SAR ID</p>
                <p className="text-slate-900  font-mono">{sarData.sar_id}</p>
              </div>
              <div>
                <p className="text-sm text-slate-600  mb-1">Filing Date</p>
                <p className="text-slate-900 ">
                  {new Date(sarData.filing_date).toLocaleString()}
                </p>
              </div>
              <div>
                <p className="text-sm text-slate-600  mb-1">Case Reference</p>
                <p className="text-slate-900  font-mono">
                  {sarData.case_reference}
                </p>
              </div>
              <div>
                <p className="text-sm text-slate-600  mb-1">Institution</p>
                <p className="text-slate-900 ">
                  {sarData.filing_institution.name}
                </p>
              </div>
            </div>
          </div>

          {/* Subject Information */}
          <div className="bg-white  rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-slate-900  mb-4">
              Subject Information
            </h2>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-slate-600  mb-1">Type</p>
                <p className="text-slate-900  capitalize">
                  {sarData.subject_information.type}
                </p>
              </div>
              <div>
                <p className="text-sm text-slate-600  mb-1">Identifier</p>
                <p className="text-slate-900  font-mono">
                  {sarData.subject_information.identifier}
                </p>
              </div>
              {sarData.subject_information.transaction_count && (
                <div>
                  <p className="text-sm text-slate-600  mb-1">
                    Transaction Count
                  </p>
                  <p className="text-slate-900 ">
                    {sarData.subject_information.transaction_count}
                  </p>
                </div>
              )}
              {sarData.subject_information.total_amount && (
                <div>
                  <p className="text-sm text-slate-600  mb-1">Total Amount</p>
                  <p className="text-slate-900  font-semibold">
                    {sarData.subject_information.total_amount.toLocaleString()}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Suspicious Activity */}
          <div className="bg-white  rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-slate-900  mb-4">
              Suspicious Activity
            </h2>

            <div className="space-y-4">
              <div>
                <p className="text-sm text-slate-600  mb-1">Activity Type</p>
                <p className="text-slate-900  font-medium">
                  {sarData.suspicious_activity.activity_type}
                </p>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <p className="text-sm text-slate-600  mb-1">
                    Transaction Count
                  </p>
                  <p className="text-2xl font-bold text-slate-900 ">
                    {sarData.suspicious_activity.transaction_count}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-slate-600  mb-1">Alert Count</p>
                  <p className="text-2xl font-bold text-slate-900 ">
                    {sarData.suspicious_activity.alert_count}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-slate-600  mb-1">Total Amount</p>
                  <p className="text-2xl font-bold text-slate-900 ">
                    {typeof sarData.suspicious_activity.total_amount ===
                      "object" &&
                    sarData.suspicious_activity.total_amount !== null
                      ? Object.entries(
                          sarData.suspicious_activity.total_amount,
                        ).map(([currency, amount]) => (
                          <span key={currency}>
                            {Number(amount).toLocaleString()} {currency}
                          </span>
                        ))
                      : (sarData.suspicious_activity.total_amount ?? "-")}
                  </p>
                </div>
              </div>

              <div>
                <p className="text-sm text-slate-600  mb-2">Narrative</p>
                <div className="bg-slate-50  p-4 rounded-lg">
                  <p className="text-slate-900  whitespace-pre-wrap leading-relaxed">
                    {sarData.suspicious_activity.narrative}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Regulatory Basis (YUFEED INNOVATION) */}
          <div className="bg-gradient-to-br from-blue-50 to-purple-50   rounded-lg shadow p-6 border border-blue-200 ">
            <h2 className="text-xl font-semibold text-slate-900  mb-4">
              Regulatory Basis
              <span className="ml-2 text-sm font-normal text-blue-600 ">
                Yufeed Innovation
              </span>
            </h2>

            <div className="space-y-4">
              {sarData.regulatory_basis.cited_regulations.length > 0 && (
                <div>
                  <p className="text-sm text-slate-600  mb-2">
                    Cited Regulations
                  </p>
                  <div className="space-y-2">
                    {sarData.regulatory_basis.cited_regulations.map(
                      (reg, idx: number) => (
                        <div key={idx} className="p-3 bg-white  rounded-lg">
                          <p className="text-xs font-mono text-slate-600  mb-1">
                            {reg.celex}
                          </p>
                          <p className="text-sm text-slate-900 ">{reg.title}</p>
                          <p className="text-xs text-slate-500  mt-1">
                            {reg.relevance}
                          </p>
                        </div>
                      ),
                    )}
                  </div>
                </div>
              )}

              <div>
                <p className="text-sm text-slate-600  mb-2">
                  Regulatory Context
                </p>
                <div className="bg-white  p-4 rounded-lg">
                  <p className="text-sm text-slate-900  whitespace-pre-wrap">
                    {sarData.regulatory_basis.regulatory_context}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Supporting Documents */}
          <div className="bg-white  rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-slate-900  mb-4">
              Supporting Documentation
            </h2>

            <div className="space-y-4">
              <div>
                <p className="text-sm text-slate-600  mb-2">
                  Alerts ({sarData.supporting_documents.alerts.length})
                </p>
                <div className="space-y-2">
                  {sarData.supporting_documents.alerts.map(
                    (alert, idx: number) => (
                      <div
                        key={idx}
                        className="p-3 bg-slate-50  rounded-lg flex items-center justify-between"
                      >
                        <div>
                          <p className="text-sm font-mono text-slate-900 ">
                            {alert.alert_id}
                          </p>
                          <p className="text-xs text-slate-600 ">
                            {alert.type} - {alert.severity}
                          </p>
                        </div>
                        <p className="text-xs text-slate-500 ">
                          {alert.created_at
                            ? new Date(alert.created_at).toLocaleDateString()
                            : "-"}
                        </p>
                      </div>
                    ),
                  )}
                </div>
              </div>

              {sarData.supporting_documents.investigation_summary && (
                <div>
                  <p className="text-sm text-slate-600  mb-2">
                    Investigation Summary
                  </p>
                  <div className="bg-slate-50  p-4 rounded-lg">
                    <p className="text-sm text-slate-900 ">
                      {sarData.supporting_documents.investigation_summary}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function SARPreparePage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-pulse text-muted-foreground">
            Processing context and compiling initial narrative map...
          </div>
        </div>
      }
    >
      <SARPrepareContent />
    </Suspense>
  );
}
