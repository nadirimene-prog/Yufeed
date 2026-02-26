"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Folder,
  Clock,
  TrendingUp,
  ExternalLink,
  CheckCircle,
  Gavel,
  Archive,
} from "lucide-react";
import { fetchWithAuth } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/apiBaseUrl";
import { logger } from "@/lib/logger";
import { useWorkspaceUsers } from "@/hooks/queries/useSpecializedData";
import CaseComments from "@/components/workbench/CaseComments";

const API_URL = getApiBaseUrl();

interface Case {
  id: number;
  case_id: string;
  case_type: string;
  status: string;
  severity: string;
  subject_type?: string;
  subject_id?: string;
  description?: string;
  summary?: string;
  opened_at: string;
  closed_at?: string;
  assigned_to?: string;
  escalated_to?: string;
  outcome?: string;
  related_alert_ids?: number[];
  related_transaction_ids?: number[];
  applicable_regulation_ids?: number[];
  evidence?: Record<string, unknown>;
  regulatory_violations?: Record<string, unknown>;
}

interface Alert {
  id: number;
  alert_id: string;
  alert_type: string;
  severity: string;
  status: string;
  created_at: string;
}

interface Transaction {
  id: number;
  transaction_id: string;
  amount: number;
  currency: string;
  transaction_type: string;
  timestamp: string;
  risk_level?: string;
}

export default function CaseDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const caseId = typeof params.id === "string" ? params.id : params.id?.[0];
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const workspaceUsersQuery = useWorkspaceUsers();

  const fetchCaseDetails = useCallback(async () => {
    if (!caseId) return;
    try {
      // Fetch case
      const caseRes = await fetchWithAuth(`${API_URL}/api/cases/${caseId}`);
      const caseDataRes = await caseRes.json();
      setCaseData(caseDataRes);

      // Fetch related alerts
      const alertsRes = await fetchWithAuth(
        `${API_URL}/api/cases/${caseId}/alerts`,
      );
      const alertsData = await alertsRes.json();
      setAlerts(alertsData);

      // Fetch related transactions
      const txRes = await fetchWithAuth(
        `${API_URL}/api/cases/${caseId}/transactions`,
      );
      const txData = await txRes.json();
      setTransactions(txData);

      setLoading(false);
    } catch (error) {
      logger.error("Error fetching case details:", error);
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    const frameId = requestAnimationFrame(() => {
      fetchCaseDetails();
    });
    return () => cancelAnimationFrame(frameId);
  }, [fetchCaseDetails]);

  const handleAssign = async (analyst: string) => {
    if (!caseData) return;

    try {
      await fetchWithAuth(`${API_URL}/api/cases/${caseData.id}/assign`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ assigned_to: analyst }),
      });
      fetchCaseDetails();
    } catch (error) {
      logger.error("Error assigning case:", error);
    }
  };

  const handleEscalate = async () => {
    if (!caseData) return;

    const escalatedTo = prompt("Escalate to:");
    if (!escalatedTo) return;

    try {
      await fetchWithAuth(`${API_URL}/api/cases/${caseData.id}/escalate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ escalated_to: escalatedTo }),
      });
      fetchCaseDetails();
    } catch (error) {
      logger.error("Error escalating case:", error);
    }
  };

  const handleClose = async (outcome: string) => {
    if (!caseData) return;

    const summary = prompt("Case summary:");
    if (!summary) return;

    try {
      await fetchWithAuth(`${API_URL}/api/cases/${caseData.id}/close`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ outcome, summary }),
      });
      router.push("/cases");
    } catch (error) {
      logger.error("Error closing case:", error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Folder className="h-12 w-12 animate-spin mx-auto mb-4 text-blue-600" />
          <p className="text-lg text-slate-700 ">Loading case details...</p>
        </div>
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Folder className="h-12 w-12 mx-auto mb-4 text-red-600" />
          <p className="text-lg text-slate-700 ">Case not found</p>
        </div>
      </div>
    );
  }

  const statusColors = {
    open: "bg-blue-100 text-blue-800  ",
    under_investigation: "bg-yellow-100 text-yellow-800  ",
    escalated: "bg-orange-100 text-orange-800  ",
    closed: "bg-slate-100 text-slate-800  ",
    sar_filed: "bg-red-100 text-red-800  ",
  };

  const severityColors = {
    critical: "bg-red-100 text-red-800   border-red-200",
    high: "bg-orange-100 text-orange-800   border-orange-200",
    medium: "bg-yellow-100 text-yellow-800   border-yellow-200",
    low: "bg-blue-100 text-blue-800   border-blue-200",
  };
  const evidenceEntries = caseData.evidence
    ? Object.keys(caseData.evidence)
    : [];

  return (
    <div className="min-h-screen bg-slate-50  p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => router.back()}
            className="flex items-center gap-2 text-slate-600  hover:text-slate-900  mb-4"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Cases
          </button>

          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-3xl font-bold text-slate-900 ">
                  {caseData.case_id}
                </h1>
                <span
                  className={`text-xs px-3 py-1 rounded-full border ${severityColors[caseData.severity as keyof typeof severityColors]}`}
                >
                  {caseData.severity.toUpperCase()}
                </span>
                <span
                  className={`text-sm px-3 py-1 rounded-full ${statusColors[caseData.status as keyof typeof statusColors]}`}
                >
                  {caseData.status.replace(/_/g, " ")}
                </span>
              </div>
              <p className="text-lg text-slate-600 ">
                {caseData.case_type.replace(/_/g, " ").toUpperCase()}
              </p>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2">
              {caseData.status !== "closed" &&
                caseData.status !== "sar_filed" && (
                  <>
                    <button
                      onClick={handleEscalate}
                      className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition"
                    >
                      Escalate
                    </button>
                    <button
                      onClick={() =>
                        router.push(`/sar/prepare?case_id=${caseData.case_id}`)
                      }
                      className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
                    >
                      Prepare SAR
                    </button>
                  </>
                )}
            </div>
          </div>
        </div>

        {/* Tab navigation */}
        <div className="flex gap-1 p-1 rounded-xl bg-slate-100  w-fit mb-6">
          <div className="px-4 py-2 rounded-lg bg-white  text-sm font-medium text-slate-900  shadow-sm">
            Overview
          </div>
          <button
            onClick={() => router.push(`/cases/${caseData.case_id}/decisions`)}
            className="px-4 py-2 rounded-lg text-sm font-medium text-slate-500  hover:text-slate-900  hover:bg-white/50  transition flex items-center gap-1.5"
          >
            <Gavel className="h-3.5 w-3.5" />
            Decisions
          </button>
          <button
            onClick={() => router.push(`/cases/${caseData.case_id}/evidence`)}
            className="px-4 py-2 rounded-lg text-sm font-medium text-slate-500  hover:text-slate-900  hover:bg-white/50  transition flex items-center gap-1.5"
          >
            <Archive className="h-3.5 w-3.5" />
            Evidence Packs
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Case Details */}
            <div className="bg-white  rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold text-slate-900  mb-4">
                Case Details
              </h2>

              <div className="space-y-4">
                {(caseData.description || caseData.summary) && (
                  <div>
                    <p className="text-sm text-slate-600  mb-1">Description</p>
                    <p className="text-slate-900 ">
                      {caseData.summary ?? caseData.description}
                    </p>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4">
                  {caseData.subject_id && (
                    <>
                      <div>
                        <p className="text-sm text-slate-600  mb-1">
                          Subject Type
                        </p>
                        <p className="text-slate-900 ">
                          {caseData.subject_type}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-slate-600  mb-1">
                          Subject ID
                        </p>
                        <Link
                          href={`/entities/user/${caseData.subject_id}`}
                          className="text-slate-900  font-mono hover:text-blue-500 hover:underline"
                        >
                          {caseData.subject_id}
                        </Link>
                      </div>
                    </>
                  )}
                  <div>
                    <p className="text-sm text-slate-600  mb-1">Opened</p>
                    <p className="text-slate-900 ">
                      {new Date(caseData.opened_at).toLocaleString()}
                    </p>
                  </div>
                  {caseData.closed_at && (
                    <div>
                      <p className="text-sm text-slate-600  mb-1">Closed</p>
                      <p className="text-slate-900 ">
                        {new Date(caseData.closed_at).toLocaleString()}
                      </p>
                    </div>
                  )}
                  {caseData.assigned_to && (
                    <div>
                      <p className="text-sm text-slate-600  mb-1">
                        Assigned To
                      </p>
                      <p className="text-slate-900 ">{caseData.assigned_to}</p>
                    </div>
                  )}
                  {caseData.escalated_to && (
                    <div>
                      <p className="text-sm text-slate-600  mb-1">
                        Escalated To
                      </p>
                      <p className="text-slate-900 ">{caseData.escalated_to}</p>
                    </div>
                  )}
                  {caseData.outcome && (
                    <div>
                      <p className="text-sm text-slate-600  mb-1">Outcome</p>
                      <p className="text-slate-900  font-semibold">
                        {caseData.outcome}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Related Alerts */}
            <div className="bg-white  rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold text-slate-900  mb-4">
                Comments
              </h2>
              <CaseComments caseId={caseData.case_id} />
            </div>

            {/* Related Alerts */}
            <div className="bg-white  rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold text-slate-900  mb-4">
                Related Alerts ({alerts.length})
              </h2>

              {alerts.length === 0 ? (
                <p className="text-slate-500  text-center py-8">
                  No related alerts
                </p>
              ) : (
                <div className="space-y-3">
                  {alerts.map((alert) => (
                    <div
                      key={alert.id}
                      onClick={() =>
                        router.push(`/transaction-alerts/${alert.alert_id}`)
                      }
                      className="p-4 border border-slate-200  rounded-lg hover:bg-slate-50  cursor-pointer transition"
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-sm font-mono text-slate-600 ">
                              {alert.alert_id}
                            </span>
                            <span
                              className={`text-xs px-2 py-1 rounded-full border ${severityColors[alert.severity as keyof typeof severityColors]}`}
                            >
                              {alert.severity}
                            </span>
                          </div>
                          <p className="text-sm font-medium text-slate-900 ">
                            {alert.alert_type.replace(/_/g, " ").toUpperCase()}
                          </p>
                        </div>
                        <ExternalLink className="h-4 w-4 text-slate-400" />
                      </div>
                      <p className="text-xs text-slate-500  mt-2">
                        {new Date(alert.created_at).toLocaleString()}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Related Transactions */}
            <div className="bg-white  rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold text-slate-900  mb-4">
                Related Transactions ({transactions.length})
              </h2>

              {transactions.length === 0 ? (
                <p className="text-slate-500  text-center py-8">
                  No related transactions
                </p>
              ) : (
                <div className="space-y-3">
                  {transactions.map((tx) => (
                    <div
                      key={tx.id}
                      className="p-4 border border-slate-200  rounded-lg"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <span className="text-sm font-mono text-slate-600 ">
                            {tx.transaction_id}
                          </span>
                        </div>
                        <div className="text-right">
                          <p className="text-lg font-bold text-slate-900 ">
                            {tx.amount.toLocaleString()} {tx.currency}
                          </p>
                          {tx.risk_level && (
                            <span
                              className={`text-xs font-semibold ${
                                tx.risk_level === "critical"
                                  ? "text-red-600"
                                  : tx.risk_level === "high"
                                    ? "text-orange-600"
                                    : tx.risk_level === "medium"
                                      ? "text-yellow-600"
                                      : "text-green-600"
                              }`}
                            >
                              {tx.risk_level.toUpperCase()}
                            </span>
                          )}
                        </div>
                      </div>
                      <p className="text-sm text-slate-600 ">
                        {tx.transaction_type.replace(/_/g, " ")}
                      </p>
                      <p className="text-xs text-slate-500  mt-2">
                        {new Date(tx.timestamp).toLocaleString()}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Evidence */}
            {evidenceEntries.length > 0 && (
              <div className="bg-white  rounded-lg shadow p-6">
                <h2 className="text-xl font-semibold text-slate-900  mb-4">
                  Evidence
                </h2>
                <pre className="text-sm text-slate-900  bg-slate-50  p-4 rounded overflow-x-auto">
                  {JSON.stringify(caseData.evidence ?? {}, null, 2)}
                </pre>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Actions */}
            {caseData.status !== "closed" &&
              caseData.status !== "sar_filed" && (
                <div className="bg-white  rounded-lg shadow p-6">
                  <h3 className="text-lg font-semibold text-slate-900  mb-4">
                    Actions
                  </h3>

                  <div className="space-y-2">
                    <select
                      onChange={(e) => handleAssign(e.target.value)}
                      defaultValue={caseData.assigned_to || ""}
                      className="w-full px-3 py-2 border border-slate-300  rounded-lg bg-white  text-slate-900 "
                    >
                      <option value="" disabled>
                        Assign to...
                      </option>
                      {(workspaceUsersQuery.data ?? []).map((user) => (
                        <option key={user.user_id} value={user.user_id}>
                          {user.user_id}
                        </option>
                      ))}
                    </select>

                    <button
                      onClick={() => handleClose("resolved")}
                      className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
                    >
                      Close - Resolved
                    </button>

                    <button
                      onClick={() => handleClose("false_positive")}
                      className="w-full px-4 py-2 bg-slate-600 text-white rounded-lg hover:bg-slate-700 transition"
                    >
                      Close - False Positive
                    </button>

                    <button
                      onClick={() => handleClose("sar_filed")}
                      className="w-full px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
                    >
                      Close - SAR Filed
                    </button>
                  </div>
                </div>
              )}

            {/* Investigation Timeline */}
            <div className="bg-white  rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-slate-900  mb-4">
                Timeline
              </h3>

              <div className="space-y-4">
                <div className="flex gap-3">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100  flex items-center justify-center">
                    <Clock className="h-4 w-4 text-blue-600" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-slate-900 ">
                      Case Opened
                    </p>
                    <p className="text-xs text-slate-500 ">
                      {new Date(caseData.opened_at).toLocaleString()}
                    </p>
                  </div>
                </div>

                {caseData.escalated_to && (
                  <div className="flex gap-3">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-orange-100  flex items-center justify-center">
                      <TrendingUp className="h-4 w-4 text-orange-600" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-slate-900 ">
                        Escalated
                      </p>
                      <p className="text-xs text-slate-500 ">
                        To: {caseData.escalated_to}
                      </p>
                    </div>
                  </div>
                )}

                {caseData.closed_at && (
                  <div className="flex gap-3">
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-green-100  flex items-center justify-center">
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-slate-900 ">
                        Case Closed
                      </p>
                      <p className="text-xs text-slate-500 ">
                        {new Date(caseData.closed_at).toLocaleString()}
                      </p>
                      {caseData.outcome && (
                        <p className="text-xs text-slate-500  mt-1">
                          Outcome: {caseData.outcome}
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
