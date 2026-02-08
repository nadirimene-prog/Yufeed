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
// Note: amlOfficerApi is available for real API calls
// import amlOfficerApi from "@/lib/aml-officer-api";

/**
 * DEMO DATA - Replace with actual API calls in production
 * These mock investigations demonstrate the UI capabilities
 */
const MOCK_INVESTIGATIONS = [
  {
    id: "INV-2024-001",
    alert_id: 1234,
    status: "completed",
    created_at: "2024-01-15T10:30:00Z",
    completed_at: "2024-01-15T10:31:23Z",
    recommendation: "escalate",
    confidence: 0.87,
    risk_score: 78,
    summary:
      "Multiple high-value wire transfers to high-risk jurisdictions detected. Pattern consistent with layering activity.",
    red_flags: ["Rapid fund movement", "High-risk countries", "Round amounts"],
  },
  {
    id: "INV-2024-002",
    alert_id: 1235,
    status: "completed",
    created_at: "2024-01-15T11:00:00Z",
    completed_at: "2024-01-15T11:00:45Z",
    recommendation: "dismiss",
    confidence: 0.92,
    risk_score: 15,
    summary:
      "Transaction pattern consistent with normal business operations. Customer has established history with similar patterns.",
    red_flags: [],
  },
  {
    id: "INV-2024-003",
    alert_id: 1236,
    status: "in_progress",
    created_at: "2024-01-15T11:30:00Z",
    recommendation: null,
    confidence: 0,
    risk_score: null,
    summary: "Investigation in progress...",
    red_flags: [],
  },
];

interface Investigation {
  id: string;
  alert_id: number;
  status: string;
  created_at: string;
  completed_at?: string;
  recommendation: string | null;
  confidence: number;
  risk_score: number | null;
  summary: string;
  red_flags: string[];
}

export default function InvestigationsPage() {
  const [investigations] = useState<Investigation[]>(MOCK_INVESTIGATIONS);
  const [selectedInvestigation, setSelectedInvestigation] =
    useState<Investigation | null>(null);
  const [filter, setFilter] = useState<"all" | "completed" | "in_progress">(
    "all",
  );

  const filteredInvestigations = investigations.filter((inv) => {
    if (filter === "all") return true;
    if (filter === "completed") return inv.status === "completed";
    if (filter === "in_progress") return inv.status === "in_progress";
    return true;
  });

  const getRecommendationStyle = (recommendation: string | null) => {
    switch (recommendation) {
      case "escalate":
        return { bg: "bg-red-100", text: "text-red-700", icon: AlertTriangle };
      case "dismiss":
        return {
          bg: "bg-green-100",
          text: "text-green-700",
          icon: CheckCircle,
        };
      case "review":
        return { bg: "bg-yellow-100", text: "text-yellow-700", icon: Eye };
      default:
        return { bg: "bg-gray-100", text: "text-gray-700", icon: Clock };
    }
  };

  const getRiskScoreColor = (score: number | null) => {
    if (score === null) return "text-gray-400";
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

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Link
              href="/aml-officer"
              className="p-2 hover:bg-gray-100 rounded-lg transition"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </Link>
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-purple-100 rounded-lg">
                <Search className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-gray-900">
                  AI Investigations
                </h1>
                <p className="text-sm text-gray-500">
                  AI-powered alert investigations and analysis
                </p>
              </div>
            </div>
          </div>

          {/* Filter Tabs */}
          <div className="flex items-center space-x-2">
            {[
              { value: "all", label: "All" },
              { value: "completed", label: "Completed" },
              { value: "in_progress", label: "In Progress" },
            ].map((tab) => (
              <button
                key={tab.value}
                onClick={() => setFilter(tab.value as typeof filter)}
                className={`px-4 py-2 text-sm rounded-lg transition ${
                  filter === tab.value
                    ? "bg-indigo-100 text-indigo-700 font-medium"
                    : "text-gray-600 hover:bg-gray-100"
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
          {/* Investigations List */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="p-4 border-b border-gray-100">
                <h2 className="font-medium text-gray-900">
                  Investigations ({filteredInvestigations.length})
                </h2>
              </div>
              <div className="divide-y divide-gray-100 max-h-[600px] overflow-y-auto">
                {filteredInvestigations.map((inv) => {
                  const recStyle = getRecommendationStyle(inv.recommendation);
                  const RecIcon = recStyle.icon;

                  return (
                    <button
                      key={inv.id}
                      onClick={() => setSelectedInvestigation(inv)}
                      className={`w-full p-4 text-left hover:bg-gray-50 transition ${
                        selectedInvestigation?.id === inv.id
                          ? "bg-indigo-50 border-l-4 border-indigo-500"
                          : ""
                      }`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <p className="font-medium text-gray-900">{inv.id}</p>
                          <p className="text-sm text-gray-500">
                            Alert #{inv.alert_id}
                          </p>
                        </div>
                        {inv.status === "completed" ? (
                          <span
                            className={`flex items-center space-x-1 text-xs px-2 py-1 rounded-full ${recStyle.bg} ${recStyle.text}`}
                          >
                            <RecIcon className="w-3 h-3" />
                            <span className="capitalize">
                              {inv.recommendation}
                            </span>
                          </span>
                        ) : (
                          <span className="flex items-center space-x-1 text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-700">
                            <Loader2 className="w-3 h-3 animate-spin" />
                            <span>Processing</span>
                          </span>
                        )}
                      </div>

                      <p className="text-sm text-gray-600 line-clamp-2 mb-2">
                        {inv.summary}
                      </p>

                      <div className="flex items-center justify-between text-xs text-gray-500">
                        <span>
                          {new Date(inv.created_at).toLocaleDateString()}
                        </span>
                        {inv.risk_score !== null && (
                          <span className={getRiskScoreColor(inv.risk_score)}>
                            Risk: {inv.risk_score}%
                          </span>
                        )}
                      </div>
                    </button>
                  );
                })}

                {filteredInvestigations.length === 0 && (
                  <div className="p-8 text-center text-gray-500">
                    <Search className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                    <p>No investigations found</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Investigation Detail */}
          <div className="lg:col-span-2">
            {selectedInvestigation ? (
              <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                {/* Detail Header */}
                <div className="p-6 border-b border-gray-100">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h2 className="text-xl font-semibold text-gray-900">
                        {selectedInvestigation.id}
                      </h2>
                      <p className="text-gray-500">
                        Alert #{selectedInvestigation.alert_id} •{" "}
                        {new Date(
                          selectedInvestigation.created_at,
                        ).toLocaleString()}
                      </p>
                    </div>
                    {selectedInvestigation.status === "completed" && (
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
                  {selectedInvestigation.status === "completed" && (
                    <div className="grid grid-cols-3 gap-4">
                      <div className="bg-gray-50 rounded-lg p-4">
                        <div className="flex items-center space-x-2 mb-1">
                          <Scale className="w-4 h-4 text-gray-500" />
                          <span className="text-sm text-gray-500">
                            Confidence
                          </span>
                        </div>
                        <div className="flex items-baseline space-x-2">
                          <span className="text-2xl font-bold text-gray-900">
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

                      <div className="bg-gray-50 rounded-lg p-4">
                        <div className="flex items-center space-x-2 mb-1">
                          <AlertTriangle className="w-4 h-4 text-gray-500" />
                          <span className="text-sm text-gray-500">
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
                          <span className="text-sm text-gray-500">/ 100</span>
                        </div>
                      </div>

                      <div className="bg-gray-50 rounded-lg p-4">
                        <div className="flex items-center space-x-2 mb-1">
                          <Clock className="w-4 h-4 text-gray-500" />
                          <span className="text-sm text-gray-500">
                            Processing Time
                          </span>
                        </div>
                        <div className="flex items-baseline space-x-2">
                          <span className="text-2xl font-bold text-gray-900">
                            {selectedInvestigation.completed_at
                              ? (
                                  (new Date(
                                    selectedInvestigation.completed_at,
                                  ).getTime() -
                                    new Date(
                                      selectedInvestigation.created_at,
                                    ).getTime()) /
                                  1000
                                ).toFixed(1)
                              : "—"}
                          </span>
                          <span className="text-sm text-gray-500">seconds</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Detail Content */}
                <div className="p-6 space-y-6">
                  {/* Summary */}
                  <div>
                    <h3 className="text-sm font-medium text-gray-700 mb-2 flex items-center space-x-2">
                      <Brain className="w-4 h-4" />
                      <span>AI Analysis Summary</span>
                    </h3>
                    <p className="text-gray-600 bg-gray-50 rounded-lg p-4">
                      {selectedInvestigation.summary}
                    </p>
                  </div>

                  {/* Red Flags */}
                  {selectedInvestigation.red_flags.length > 0 && (
                    <div>
                      <h3 className="text-sm font-medium text-gray-700 mb-2 flex items-center space-x-2">
                        <Flag className="w-4 h-4 text-red-500" />
                        <span>Red Flags Identified</span>
                      </h3>
                      <div className="flex flex-wrap gap-2">
                        {selectedInvestigation.red_flags.map((flag, index) => (
                          <span
                            key={index}
                            className="px-3 py-1.5 bg-red-50 text-red-700 rounded-lg text-sm"
                          >
                            {flag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Actions */}
                  {selectedInvestigation.status === "completed" && (
                    <div className="flex items-center space-x-3 pt-4 border-t border-gray-100">
                      <Link
                        href={`/alerts/${selectedInvestigation.alert_id}`}
                        className="flex items-center space-x-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition"
                      >
                        <Eye className="w-4 h-4" />
                        <span>View Alert</span>
                      </Link>

                      {selectedInvestigation.recommendation === "escalate" && (
                        <Link
                          href={`/cases/new?alert=${selectedInvestigation.alert_id}`}
                          className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition"
                        >
                          <FileText className="w-4 h-4" />
                          <span>Create Case</span>
                        </Link>
                      )}

                      <button className="flex items-center space-x-2 px-4 py-2 border border-gray-200 text-gray-600 rounded-lg hover:bg-gray-50 transition ml-auto">
                        <Shield className="w-4 h-4" />
                        <span>Run Sanctions Check</span>
                      </button>
                    </div>
                  )}

                  {selectedInvestigation.status === "in_progress" && (
                    <div className="flex items-center justify-center py-8">
                      <div className="text-center">
                        <Loader2 className="w-8 h-8 text-indigo-600 animate-spin mx-auto mb-3" />
                        <p className="text-gray-600">
                          AI is analyzing the alert...
                        </p>
                        <p className="text-sm text-gray-500">
                          This usually takes 30-60 seconds
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
                <Brain className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Select an Investigation
                </h3>
                <p className="text-gray-500 mb-6">
                  Choose an investigation from the list to view details
                </p>
                <Link
                  href="/alerts"
                  className="inline-flex items-center space-x-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition"
                >
                  <Play className="w-4 h-4" />
                  <span>Start New Investigation</span>
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
