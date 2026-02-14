"use client";

/**
 * SAR (Suspicious Activity Report) Management Page
 *
 * View cases eligible for SAR filing and manage SAR workflow.
 */

import { useState } from "react";
import Link from "next/link";
import {
  FileText,
  ArrowLeft,
  Brain,
  AlertTriangle,
  CheckCircle,
  Send,
  Eye,
  Download,
  Plus,
  User,
  DollarSign,
  Flag,
  Loader2,
} from "lucide-react";
import { useMonitoringCases } from "@/hooks/queries/useMonitoringData";
import type { MonitoringCase } from "@/types/monitoring";

type CaseStatus =
  | "open"
  | "under_investigation"
  | "escalated"
  | "sar_filed"
  | "closed";

export default function SARManagementPage() {
  const [filter, setFilter] = useState<"all" | "ready" | "filed">("all");

  const casesQuery = useMonitoringCases({ limit: 100 });
  const cases = casesQuery.data ?? [];

  // Filter cases based on SAR relevance
  const sarRelevantCases = cases.filter((c: MonitoringCase) => {
    // Include escalated cases (ready for SAR) and cases with SAR filed
    return c.status === "escalated" || c.outcome === "sar_filed";
  });

  const filteredCases = sarRelevantCases.filter((c: MonitoringCase) => {
    if (filter === "all") return true;
    if (filter === "ready") return c.status === "escalated";
    if (filter === "filed") return c.outcome === "sar_filed";
    return true;
  });

  const getStatusStyle = (caseItem: MonitoringCase) => {
    if (caseItem.outcome === "sar_filed") {
      return { bg: "bg-green-100", text: "text-green-700", label: "SAR Filed" };
    }
    if (caseItem.status === "escalated") {
      return {
        bg: "bg-yellow-100",
        text: "text-yellow-700",
        label: "Ready for SAR",
      };
    }
    return { bg: "bg-gray-100", text: "text-gray-700", label: caseItem.status };
  };

  const stats = {
    total: sarRelevantCases.length,
    ready: sarRelevantCases.filter((c) => c.status === "escalated").length,
    filed: sarRelevantCases.filter((c) => c.outcome === "sar_filed").length,
  };

  if (casesQuery.isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3 text-indigo-600" />
          <p className="text-gray-600">Loading cases...</p>
        </div>
      </div>
    );
  }

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
              <div className="p-2 bg-red-100 rounded-lg">
                <FileText className="w-6 h-6 text-red-600" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-gray-900">
                  SAR Management
                </h1>
                <p className="text-sm text-gray-500">
                  Suspicious Activity Report workflow
                </p>
              </div>
            </div>
          </div>

          <Link
            href="/cases"
            className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition"
          >
            <Plus className="w-4 h-4" />
            <span>View All Cases</span>
          </Link>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          {[
            {
              label: "SAR-Related Cases",
              value: stats.total,
              color: "text-gray-900",
            },
            {
              label: "Ready for Filing",
              value: stats.ready,
              color: "text-yellow-600",
            },
            { label: "Filed", value: stats.filed, color: "text-green-600" },
          ].map((stat) => (
            <div
              key={stat.label}
              className="bg-white rounded-xl border border-gray-200 p-4"
            >
              <p className="text-sm text-gray-500 mb-1">{stat.label}</p>
              <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
            </div>
          ))}
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center space-x-2 mb-6">
          {[
            { value: "all", label: "All Cases" },
            { value: "ready", label: "Ready for SAR" },
            { value: "filed", label: "SAR Filed" },
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

        {/* Cases Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredCases.map((caseItem: MonitoringCase) => {
            const statusStyle = getStatusStyle(caseItem);

            return (
              <div
                key={caseItem.case_id}
                className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition"
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <p className="font-medium text-gray-900">
                      {caseItem.case_id}
                    </p>
                    <p className="text-sm text-gray-500">
                      {caseItem.case_type || "Investigation"}
                    </p>
                  </div>
                  <span
                    className={`text-xs px-2 py-1 rounded-full ${statusStyle.bg} ${statusStyle.text}`}
                  >
                    {statusStyle.label}
                  </span>
                </div>

                <div className="space-y-2 mb-4">
                  <div className="flex items-center space-x-2 text-sm text-gray-600">
                    <User className="w-4 h-4" />
                    <span>{caseItem.subject_id || "Unknown subject"}</span>
                  </div>
                  {caseItem.severity && (
                    <div className="flex items-center space-x-2 text-sm">
                      <AlertTriangle
                        className={`w-4 h-4 ${
                          caseItem.severity === "critical"
                            ? "text-red-500"
                            : caseItem.severity === "high"
                              ? "text-orange-500"
                              : "text-yellow-500"
                        }`}
                      />
                      <span className="capitalize text-gray-600">
                        {caseItem.severity} severity
                      </span>
                    </div>
                  )}
                </div>

                {caseItem.description && (
                  <p className="text-sm text-gray-600 line-clamp-2 mb-4">
                    {caseItem.description}
                  </p>
                )}

                <div className="flex items-center gap-2">
                  <Link
                    href={`/cases/${caseItem.case_id}`}
                    className="flex-1 flex items-center justify-center space-x-1 px-3 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition text-sm"
                  >
                    <Eye className="w-4 h-4" />
                    <span>View Case</span>
                  </Link>

                  {caseItem.status === "escalated" && (
                    <Link
                      href={`/sar/prepare?case_id=${caseItem.case_id}`}
                      className="flex-1 flex items-center justify-center space-x-1 px-3 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition text-sm"
                    >
                      <Send className="w-4 h-4" />
                      <span>Prepare SAR</span>
                    </Link>
                  )}

                  {caseItem.outcome === "sar_filed" && (
                    <button className="flex-1 flex items-center justify-center space-x-1 px-3 py-2 border border-gray-200 text-gray-600 rounded-lg hover:bg-gray-50 transition text-sm">
                      <Download className="w-4 h-4" />
                      <span>Export</span>
                    </button>
                  )}
                </div>
              </div>
            );
          })}

          {filteredCases.length === 0 && (
            <div className="col-span-full bg-white rounded-xl border border-gray-200 p-12 text-center">
              <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No Cases Found
              </h3>
              <p className="text-gray-500 mb-6">
                {filter === "ready"
                  ? "No cases are currently ready for SAR filing."
                  : filter === "filed"
                    ? "No SARs have been filed yet."
                    : "No SAR-related cases found. Escalate cases to prepare SARs."}
              </p>
              <Link
                href="/cases"
                className="inline-flex items-center space-x-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition"
              >
                <Plus className="w-4 h-4" />
                <span>View All Cases</span>
              </Link>
            </div>
          )}
        </div>

        {/* Info Panel */}
        <div className="mt-8 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-xl p-6 border border-blue-200 dark:border-blue-800">
          <div className="flex items-start space-x-4">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Brain className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">
                AI-Powered SAR Generation
              </h3>
              <p className="text-sm text-gray-600 mb-3">
                When you prepare a SAR, our AI generates a comprehensive
                narrative based on case evidence, transaction patterns, and
                regulatory requirements. The generated SAR includes:
              </p>
              <ul className="text-sm text-gray-600 space-y-1">
                <li className="flex items-center space-x-2">
                  <CheckCircle className="w-4 h-4 text-green-500" />
                  <span>Auto-generated suspicious activity narrative</span>
                </li>
                <li className="flex items-center space-x-2">
                  <CheckCircle className="w-4 h-4 text-green-500" />
                  <span>Regulatory citations and compliance mapping</span>
                </li>
                <li className="flex items-center space-x-2">
                  <CheckCircle className="w-4 h-4 text-green-500" />
                  <span>Transaction summaries and red flag analysis</span>
                </li>
                <li className="flex items-center space-x-2">
                  <CheckCircle className="w-4 h-4 text-green-500" />
                  <span>goAML and FIU-compatible export formats</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
