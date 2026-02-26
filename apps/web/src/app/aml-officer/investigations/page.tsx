"use client";

/**
 * AI Investigations Page
 *
 * View and manage AI-powered alert investigations.
 * Launch new investigations and review completed ones.
 */

import { useState } from "react";
import Link from "next/link";
import {
  Search,
  ArrowLeft,
  Brain,
  AlertTriangle,
  CheckCircle,
  Clock,
  FileText,
  Loader2,
  Play,
  Eye,
  Flag,
  Scale,
  Shield,
} from "lucide-react";
import { useMonitoringAlerts } from "@/hooks/queries/useMonitoringData";
import { useInvestigateAlert } from "@/hooks/queries/useAMLOfficerData";
import type { InvestigationResult } from "@/lib/aml-officer-api";
import type { MonitoringAlert } from "@/types/monitoring";

interface Investigation {
  id: string;
  alert_id: number;
  status: "pending" | "in_progress" | "completed";
  created_at: string;
  completed_at?: string;
  recommendation: string | null;
  confidence: number;
  risk_score: number | null;
  summary: string;
  red_flags: string[];
}

export default function InvestigationsPage() {
  const [investigations, setInvestigations] = useState<
    Map<number, Investigation>
  >(new Map());
  const [selectedAlertId, setSelectedAlertId] = useState<number | null>(null);
  const [filter, setFilter] = useState<"all" | "pending" | "investigated">(
    "all",
  );

  const alertsQuery = useMonitoringAlerts({ status: "open", limit: 50 });
  const investigateMutation = useInvestigateAlert();

  const alerts: MonitoringAlert[] = alertsQuery.data ?? [];

  const handleInvestigate = async (alertId: number) => {
    const alert = alerts.find((a) => a.id === alertId);
    if (!alert) return;

    // Set as in progress
    setInvestigations((prev) => {
      const updated = new Map(prev);
      updated.set(alertId, {
        id: `INV-${Date.now()}`,
        alert_id: alertId,
        status: "in_progress",
        created_at: new Date().toISOString(),
        recommendation: null,
        confidence: 0,
        risk_score: null,
        summary: "Investigation in progress...",
        red_flags: [],
      });
      return updated;
    });

    try {
      const result: InvestigationResult = await investigateMutation.mutateAsync(
        {
          alertId: alertId,
          alertData: {
            id: alert.id,
            alert_id: alert.alert_id,
            alert_type: alert.alert_type,
            severity: alert.severity,
            user_id: alert.user_id,
            description: alert.description,
            risk_score: alert.risk_score,
          },
        },
      );

      // Update with results
      setInvestigations((prev) => {
        const updated = new Map(prev);
        updated.set(alertId, {
          id: `INV-${Date.now()}`,
          alert_id: alertId,
          status: "completed",
          created_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
          recommendation: result.recommendation || "review",
          confidence: result.confidence,
          risk_score: result.risk_score ?? null,
          summary: result.summary,
          red_flags: result.red_flags,
        });
        return updated;
      });
    } catch {
      // Remove failed investigation
      setInvestigations((prev) => {
        const updated = new Map(prev);
        updated.delete(alertId);
        return updated;
      });
    }
  };

  const filteredAlerts = alerts.filter((alert) => {
    const investigation = investigations.get(alert.id);
    if (filter === "all") return true;
    if (filter === "pending") return !investigation;
    if (filter === "investigated") return !!investigation;
    return true;
  });

  const selectedAlert = alerts.find((a) => a.id === selectedAlertId);
  const selectedInvestigation = selectedAlertId
    ? investigations.get(selectedAlertId)
    : null;

  const getRecommendationStyle = (recommendation: string | null) => {
    switch (recommendation) {
      case "escalate":
        return { bg: "bg-red-100", text: "text-red-700", icon: AlertTriangle };
      case "dismiss":
      case "false_positive":
        return {
          bg: "bg-green-100",
          text: "text-green-700",
          icon: CheckCircle,
        };
      case "review":
      case "investigate":
        return { bg: "bg-yellow-100", text: "text-yellow-700", icon: Eye };
      default:
        return { bg: "bg-slate-100", text: "text-slate-700", icon: Clock };
    }
  };

  const getRiskScoreColor = (score: number | null) => {
    if (score === null) return "text-slate-400";
    if (score >= 70) return "text-red-600";
    if (score >= 40) return "text-yellow-600";
    return "text-green-600";
  };

  const getConfidenceLevel = (confidence: number) => {
    if (confidence >= 0.9)
      return { label: "Very High", color: "text-green-600" };
    if (confidence >= 0.75) return { label: "High", color: "text-blue-600" };
    if (confidence >= 0.5) return { label: "Medium", color: "text-yellow-600" };
    return { label: "Low", color: "text-red-600" };
  };

  if (alertsQuery.isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-50">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3 text-indigo-600" />
          <p className="text-slate-600">Loading alerts...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-4 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Link
              href="/aml-officer"
              className="p-2 hover:bg-slate-100 rounded-lg transition"
            >
              <ArrowLeft className="w-5 h-5 text-slate-600" />
            </Link>
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-purple-100 rounded-lg">
                <Search className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-slate-900">
                  AI Investigations
                </h1>
                <p className="text-sm text-slate-500">
                  AI-powered alert investigations and analysis
                </p>
              </div>
            </div>
          </div>

          {/* Filter Tabs */}
          <div className="flex items-center space-x-2">
            {[
              { value: "all", label: "All Alerts" },
              { value: "pending", label: "Pending Investigation" },
              { value: "investigated", label: "Investigated" },
            ].map((tab) => (
              <button
                key={tab.value}
                onClick={() => setFilter(tab.value as typeof filter)}
                className={`px-4 py-2 text-sm rounded-lg transition ${
                  filter === tab.value
                    ? "bg-indigo-100 text-indigo-700 font-medium"
                    : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Alerts List */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
              <div className="p-4 border-b border-slate-100">
                <h2 className="font-medium text-slate-900">
                  Alerts ({filteredAlerts.length})
                </h2>
              </div>
              <div className="divide-y divide-slate-100 max-h-[600px] overflow-y-auto">
                {filteredAlerts.map((alert) => {
                  const investigation = investigations.get(alert.id);
                  const recStyle = investigation
                    ? getRecommendationStyle(investigation.recommendation)
                    : null;

                  return (
                    <button
                      key={alert.id}
                      onClick={() => setSelectedAlertId(alert.id)}
                      className={`w-full p-4 text-left hover:bg-slate-50 transition ${
                        selectedAlertId === alert.id
                          ? "bg-indigo-50 border-l-4 border-indigo-500"
                          : ""
                      }`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <p className="font-medium text-slate-900">
                            Alert #{alert.id}
                          </p>
                          <p className="text-sm text-slate-500">
                            {alert.alert_type}
                          </p>
                        </div>
                        {investigation?.status === "completed" && recStyle ? (
                          <span
                            className={`flex items-center space-x-1 text-xs px-2 py-1 rounded-full ${recStyle.bg} ${recStyle.text}`}
                          >
                            <recStyle.icon className="w-3 h-3" />
                            <span className="capitalize">
                              {investigation.recommendation}
                            </span>
                          </span>
                        ) : investigation?.status === "in_progress" ? (
                          <span className="flex items-center space-x-1 text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-700">
                            <Loader2 className="w-3 h-3 animate-spin" />
                            <span>Processing</span>
                          </span>
                        ) : (
                          <span className="text-xs px-2 py-1 rounded-full bg-slate-100 text-slate-600">
                            Not investigated
                          </span>
                        )}
                      </div>

                      <p className="text-sm text-slate-600 line-clamp-2 mb-2">
                        {alert.description || "No description available"}
                      </p>

                      <div className="flex items-center justify-between text-xs text-slate-500">
                        <span>
                          {new Date(alert.created_at).toLocaleDateString()}
                        </span>
                        <span
                          className={
                            alert.severity === "critical"
                              ? "text-red-600"
                              : alert.severity === "high"
                                ? "text-orange-600"
                                : "text-slate-600"
                          }
                        >
                          {alert.severity}
                        </span>
                      </div>
                    </button>
                  );
                })}

                {filteredAlerts.length === 0 && (
                  <div className="p-8 text-center text-slate-500">
                    <Search className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                    <p>No alerts found</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Investigation Detail */}
          <div className="lg:col-span-2">
            {selectedAlert ? (
              <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                {/* Detail Header */}
                <div className="p-6 border-b border-slate-100">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h2 className="text-xl font-semibold text-slate-900">
                        Alert #{selectedAlert.id}
                      </h2>
                      <p className="text-slate-500">
                        {selectedAlert.alert_type} •{" "}
                        {new Date(selectedAlert.created_at).toLocaleString()}
                      </p>
                    </div>
                    {selectedInvestigation?.status === "completed" && (
                      <div className="flex items-center space-x-3">
                        {(() => {
                          const recStyle = getRecommendationStyle(
                            selectedInvestigation.recommendation,
                          );
                          const RecIcon = recStyle.icon;
                          return (
                            <span
                              className={`flex items-center space-x-2 px-4 py-2 rounded-lg ${recStyle.bg} ${recStyle.text}`}
                            >
                              <RecIcon className="w-5 h-5" />
                              <span className="font-medium capitalize">
                                {selectedInvestigation.recommendation}
                              </span>
                            </span>
                          );
                        })()}
                      </div>
                    )}
                  </div>

                  {/* Metrics Row */}
                  {selectedInvestigation?.status === "completed" && (
                    <div className="grid grid-cols-3 gap-4">
                      <div className="bg-slate-50 rounded-lg p-4">
                        <div className="flex items-center space-x-2 mb-1">
                          <Scale className="w-4 h-4 text-slate-500" />
                          <span className="text-sm text-slate-500">
                            Confidence
                          </span>
                        </div>
                        <div className="flex items-baseline space-x-2">
                          <span className="text-2xl font-bold text-slate-900">
                            {(selectedInvestigation.confidence * 100).toFixed(
                              0,
                            )}
                            %
                          </span>
                          <span
                            className={`text-sm ${
                              getConfidenceLevel(
                                selectedInvestigation.confidence,
                              ).color
                            }`}
                          >
                            {
                              getConfidenceLevel(
                                selectedInvestigation.confidence,
                              ).label
                            }
                          </span>
                        </div>
                      </div>

                      <div className="bg-slate-50 rounded-lg p-4">
                        <div className="flex items-center space-x-2 mb-1">
                          <AlertTriangle className="w-4 h-4 text-slate-500" />
                          <span className="text-sm text-slate-500">
                            Risk Score
                          </span>
                        </div>
                        <div className="flex items-baseline space-x-2">
                          <span
                            className={`text-2xl font-bold ${getRiskScoreColor(
                              selectedInvestigation.risk_score,
                            )}`}
                          >
                            {selectedInvestigation.risk_score ?? "N/A"}
                          </span>
                          <span className="text-sm text-slate-500">/ 100</span>
                        </div>
                      </div>

                      <div className="bg-slate-50 rounded-lg p-4">
                        <div className="flex items-center space-x-2 mb-1">
                          <Clock className="w-4 h-4 text-slate-500" />
                          <span className="text-sm text-slate-500">Status</span>
                        </div>
                        <div className="flex items-baseline space-x-2">
                          <span className="text-2xl font-bold text-green-600">
                            Complete
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Detail Content */}
                <div className="p-6 space-y-6">
                  {/* Summary */}
                  {selectedInvestigation?.status === "completed" && (
                    <>
                      <div>
                        <h3 className="text-sm font-medium text-slate-700 mb-2 flex items-center space-x-2">
                          <Brain className="w-4 h-4" />
                          <span>AI Analysis Summary</span>
                        </h3>
                        <p className="text-slate-600 bg-slate-50 rounded-lg p-4">
                          {selectedInvestigation.summary}
                        </p>
                      </div>

                      {/* Red Flags */}
                      {selectedInvestigation.red_flags.length > 0 && (
                        <div>
                          <h3 className="text-sm font-medium text-slate-700 mb-2 flex items-center space-x-2">
                            <Flag className="w-4 h-4 text-red-500" />
                            <span>Red Flags Identified</span>
                          </h3>
                          <div className="flex flex-wrap gap-2">
                            {selectedInvestigation.red_flags.map(
                              (flag, index) => (
                                <span
                                  key={index}
                                  className="px-3 py-1.5 bg-red-50 text-red-700 rounded-lg text-sm"
                                >
                                  {flag}
                                </span>
                              ),
                            )}
                          </div>
                        </div>
                      )}
                    </>
                  )}

                  {/* Actions */}
                  <div className="flex items-center space-x-3 pt-4 border-t border-slate-100">
                    {!selectedInvestigation && (
                      <button
                        onClick={() => handleInvestigate(selectedAlert.id)}
                        disabled={investigateMutation.isPending}
                        className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition disabled:opacity-50"
                      >
                        {investigateMutation.isPending ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Play className="w-4 h-4" />
                        )}
                        <span>Run AI Investigation</span>
                      </button>
                    )}

                    {selectedInvestigation?.status === "in_progress" && (
                      <div className="flex items-center space-x-2 text-indigo-600">
                        <Loader2 className="w-5 h-5 animate-spin" />
                        <span className="font-medium">
                          AI is analyzing the alert...
                        </span>
                      </div>
                    )}

                    {selectedInvestigation?.status === "completed" && (
                      <>
                        <Link
                          href={`/transaction-alerts/${selectedAlert.id}`}
                          className="flex items-center space-x-2 px-4 py-2 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 transition"
                        >
                          <Eye className="w-4 h-4" />
                          <span>View Alert</span>
                        </Link>

                        {selectedInvestigation.recommendation ===
                          "escalate" && (
                          <Link
                            href={`/cases/new?alert=${selectedAlert.id}`}
                            className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition"
                          >
                            <FileText className="w-4 h-4" />
                            <span>Create Case</span>
                          </Link>
                        )}

                        <button className="flex items-center space-x-2 px-4 py-2 border border-slate-200 text-slate-600 rounded-lg hover:bg-slate-50 transition ml-auto">
                          <Shield className="w-4 h-4" />
                          <span>Run Sanctions Check</span>
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
                <Brain className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-slate-900 mb-2">
                  Select an Alert to Investigate
                </h3>
                <p className="text-slate-500 mb-6">
                  Choose an alert from the list to run an AI-powered
                  investigation
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
