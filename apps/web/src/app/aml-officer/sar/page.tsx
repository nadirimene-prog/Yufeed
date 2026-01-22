"use client";

/**
 * SAR (Suspicious Activity Report) Management Page
 *
 * AI-powered SAR narrative generation and filing workflow.
 */

import { useState } from "react";
import Link from "next/link";
import {
  FileText,
  ArrowLeft,
  Brain,
  AlertTriangle,
  CheckCircle,
  Clock,
  Send,
  Edit,
  Eye,
  Download,
  Plus,
  Loader2,
  Building,
  User,
  Calendar,
  DollarSign,
  Flag,
  BookOpen,
  ChevronRight,
  XCircle,
} from "lucide-react";
// Note: amlOfficerApi is available for real API calls
// import amlOfficerApi from "@/lib/aml-officer-api";

type SARStatus = "draft" | "pending_review" | "approved" | "filed";

interface SAR {
  id: string;
  case_id: string;
  status: SARStatus;
  created_at: string;
  subject_name: string;
  activity_type: string;
  total_amount: number;
  currency: string;
  narrative_preview: string;
  red_flags: string[];
  confidence: number;
}

/**
 * DEMO DATA - Replace with actual API calls in production
 * These mock SARs demonstrate the UI capabilities
 */
const MOCK_SARS: SAR[] = [
  {
    id: "SAR-2024-001",
    case_id: "CASE-2024-001",
    status: "draft",
    created_at: "2024-01-15T10:30:00Z",
    subject_name: "John Smith",
    activity_type: "money_laundering",
    total_amount: 250000,
    currency: "EUR",
    narrative_preview: "The subject conducted multiple high-value wire transfers to jurisdictions with weak AML controls...",
    red_flags: ["Structuring", "High-risk jurisdictions", "Rapid movement"],
    confidence: 0.85,
  },
  {
    id: "SAR-2024-002",
    case_id: "CASE-2024-002",
    status: "pending_review",
    created_at: "2024-01-14T15:00:00Z",
    subject_name: "Global Trading Ltd",
    activity_type: "fraud",
    total_amount: 180000,
    currency: "EUR",
    narrative_preview: "Analysis reveals a pattern of invoice manipulation and fictitious trading activity...",
    red_flags: ["Invoice discrepancies", "Shell companies", "No economic purpose"],
    confidence: 0.78,
  },
  {
    id: "SAR-2024-003",
    case_id: "CASE-2024-003",
    status: "approved",
    created_at: "2024-01-13T09:00:00Z",
    subject_name: "Maria Rodriguez",
    activity_type: "terrorist_financing",
    total_amount: 45000,
    currency: "EUR",
    narrative_preview: "Transactions show a pattern consistent with potential terrorist financing indicators...",
    red_flags: ["Conflict zone transfers", "NGO misuse", "Smurfing"],
    confidence: 0.92,
  },
  {
    id: "SAR-2024-004",
    case_id: "CASE-2024-004",
    status: "filed",
    created_at: "2024-01-10T11:00:00Z",
    subject_name: "Tech Innovations Inc",
    activity_type: "tax_evasion",
    total_amount: 520000,
    currency: "EUR",
    narrative_preview: "Corporate structure utilized for apparent tax evasion through transfer pricing manipulation...",
    red_flags: ["Complex structures", "Tax haven jurisdictions", "Round-tripping"],
    confidence: 0.88,
  },
];

export default function SARManagementPage() {
  const [sars] = useState<SAR[]>(MOCK_SARS);
  const [selectedSAR, setSelectedSAR] = useState<SAR | null>(null);
  const [filter, setFilter] = useState<"all" | SARStatus>("all");

  const filteredSARs = sars.filter((sar) => {
    if (filter === "all") return true;
    return sar.status === filter;
  });

  const getStatusStyle = (status: SARStatus) => {
    switch (status) {
      case "draft":
        return { bg: "bg-gray-100", text: "text-gray-700", label: "Draft" };
      case "pending_review":
        return { bg: "bg-yellow-100", text: "text-yellow-700", label: "Pending Review" };
      case "approved":
        return { bg: "bg-blue-100", text: "text-blue-700", label: "Approved" };
      case "filed":
        return { bg: "bg-green-100", text: "text-green-700", label: "Filed" };
    }
  };

  const getActivityTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      money_laundering: "Money Laundering",
      terrorist_financing: "Terrorist Financing",
      fraud: "Fraud",
      tax_evasion: "Tax Evasion",
      sanctions_violation: "Sanctions Violation",
      corruption: "Corruption",
      other: "Other",
    };
    return labels[type] || type;
  };

  // TODO: Implement SAR generation with real API
  // const handleGenerateSAR = async () => {
  //   const result = await amlOfficerApi.prepareSAR(caseId, caseData);
  //   // Handle result
  // };

  const stats = {
    total: sars.length,
    draft: sars.filter((s) => s.status === "draft").length,
    pending: sars.filter((s) => s.status === "pending_review").length,
    approved: sars.filter((s) => s.status === "approved").length,
    filed: sars.filter((s) => s.status === "filed").length,
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
              <div className="p-2 bg-red-100 rounded-lg">
                <FileText className="w-6 h-6 text-red-600" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-gray-900">
                  SAR Management
                </h1>
                <p className="text-sm text-gray-500">
                  AI-generated Suspicious Activity Reports
                </p>
              </div>
            </div>
          </div>

          <Link
            href="/cases"
            className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition"
          >
            <Plus className="w-4 h-4" />
            <span>New SAR from Case</span>
          </Link>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Stats */}
        <div className="grid grid-cols-5 gap-4 mb-8">
          {[
            { label: "Total SARs", value: stats.total, color: "text-gray-900" },
            { label: "Drafts", value: stats.draft, color: "text-gray-600" },
            { label: "Pending Review", value: stats.pending, color: "text-yellow-600" },
            { label: "Approved", value: stats.approved, color: "text-blue-600" },
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
            { value: "all", label: "All SARs" },
            { value: "draft", label: "Drafts" },
            { value: "pending_review", label: "Pending Review" },
            { value: "approved", label: "Approved" },
            { value: "filed", label: "Filed" },
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

        <div className="grid lg:grid-cols-3 gap-6">
          {/* SAR List */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="divide-y divide-gray-100 max-h-[600px] overflow-y-auto">
                {filteredSARs.map((sar) => {
                  const statusStyle = getStatusStyle(sar.status);

                  return (
                    <button
                      key={sar.id}
                      onClick={() => setSelectedSAR(sar)}
                      className={`w-full p-4 text-left hover:bg-gray-50 transition ${
                        selectedSAR?.id === sar.id
                          ? "bg-indigo-50 border-l-4 border-indigo-500"
                          : ""
                      }`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <p className="font-medium text-gray-900">{sar.id}</p>
                          <p className="text-sm text-gray-500">
                            {sar.subject_name}
                          </p>
                        </div>
                        <span
                          className={`text-xs px-2 py-1 rounded-full ${statusStyle.bg} ${statusStyle.text}`}
                        >
                          {statusStyle.label}
                        </span>
                      </div>

                      <div className="flex items-center space-x-3 text-sm text-gray-500 mb-2">
                        <span className="flex items-center space-x-1">
                          <DollarSign className="w-3.5 h-3.5" />
                          <span>
                            {sar.total_amount.toLocaleString()} {sar.currency}
                          </span>
                        </span>
                        <span className="flex items-center space-x-1">
                          <AlertTriangle className="w-3.5 h-3.5" />
                          <span>{getActivityTypeLabel(sar.activity_type)}</span>
                        </span>
                      </div>

                      <p className="text-sm text-gray-600 line-clamp-2">
                        {sar.narrative_preview}
                      </p>
                    </button>
                  );
                })}

                {filteredSARs.length === 0 && (
                  <div className="p-8 text-center text-gray-500">
                    <FileText className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                    <p>No SARs found</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* SAR Detail */}
          <div className="lg:col-span-2">
            {selectedSAR ? (
              <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                {/* Detail Header */}
                <div className="p-6 border-b border-gray-100">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h2 className="text-xl font-semibold text-gray-900">
                        {selectedSAR.id}
                      </h2>
                      <p className="text-gray-500">
                        Case: {selectedSAR.case_id} •{" "}
                        {new Date(selectedSAR.created_at).toLocaleString()}
                      </p>
                    </div>
                    {(() => {
                      const statusStyle = getStatusStyle(selectedSAR.status);
                      return (
                        <span
                          className={`px-4 py-2 rounded-lg ${statusStyle.bg} ${statusStyle.text} font-medium`}
                        >
                          {statusStyle.label}
                        </span>
                      );
                    })()}
                  </div>

                  {/* Quick Info */}
                  <div className="grid grid-cols-4 gap-4">
                    <div className="bg-gray-50 rounded-lg p-3">
                      <div className="flex items-center space-x-2 text-gray-500 mb-1">
                        <User className="w-4 h-4" />
                        <span className="text-xs">Subject</span>
                      </div>
                      <p className="font-medium text-gray-900 truncate">
                        {selectedSAR.subject_name}
                      </p>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-3">
                      <div className="flex items-center space-x-2 text-gray-500 mb-1">
                        <AlertTriangle className="w-4 h-4" />
                        <span className="text-xs">Activity Type</span>
                      </div>
                      <p className="font-medium text-gray-900">
                        {getActivityTypeLabel(selectedSAR.activity_type)}
                      </p>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-3">
                      <div className="flex items-center space-x-2 text-gray-500 mb-1">
                        <DollarSign className="w-4 h-4" />
                        <span className="text-xs">Total Amount</span>
                      </div>
                      <p className="font-medium text-gray-900">
                        {selectedSAR.total_amount.toLocaleString()}{" "}
                        {selectedSAR.currency}
                      </p>
                    </div>
                    <div className="bg-gray-50 rounded-lg p-3">
                      <div className="flex items-center space-x-2 text-gray-500 mb-1">
                        <Brain className="w-4 h-4" />
                        <span className="text-xs">AI Confidence</span>
                      </div>
                      <p className="font-medium text-gray-900">
                        {(selectedSAR.confidence * 100).toFixed(0)}%
                      </p>
                    </div>
                  </div>
                </div>

                {/* Narrative */}
                <div className="p-6 border-b border-gray-100">
                  <h3 className="text-sm font-medium text-gray-700 mb-3 flex items-center space-x-2">
                    <BookOpen className="w-4 h-4" />
                    <span>AI-Generated Narrative</span>
                  </h3>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-gray-700 whitespace-pre-wrap">
                      {selectedSAR.narrative_preview}
                    </p>
                    <button className="mt-3 text-sm text-indigo-600 hover:text-indigo-700 flex items-center space-x-1">
                      <span>View full narrative</span>
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Red Flags */}
                <div className="p-6 border-b border-gray-100">
                  <h3 className="text-sm font-medium text-gray-700 mb-3 flex items-center space-x-2">
                    <Flag className="w-4 h-4 text-red-500" />
                    <span>Red Flags Identified</span>
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedSAR.red_flags.map((flag, index) => (
                      <span
                        key={index}
                        className="px-3 py-1.5 bg-red-50 text-red-700 rounded-lg text-sm"
                      >
                        {flag}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Actions */}
                <div className="p-6">
                  <div className="flex items-center space-x-3">
                    {selectedSAR.status === "draft" && (
                      <>
                        <button className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition">
                          <Edit className="w-4 h-4" />
                          <span>Edit Narrative</span>
                        </button>
                        <button className="flex items-center space-x-2 px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition">
                          <Send className="w-4 h-4" />
                          <span>Submit for Review</span>
                        </button>
                      </>
                    )}

                    {selectedSAR.status === "pending_review" && (
                      <>
                        <button className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition">
                          <CheckCircle className="w-4 h-4" />
                          <span>Approve</span>
                        </button>
                        <button className="flex items-center space-x-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition">
                          <XCircle className="w-4 h-4" />
                          <span>Request Changes</span>
                        </button>
                      </>
                    )}

                    {selectedSAR.status === "approved" && (
                      <button className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition">
                        <Send className="w-4 h-4" />
                        <span>File with FIU</span>
                      </button>
                    )}

                    {selectedSAR.status === "filed" && (
                      <div className="flex items-center space-x-2 text-green-600">
                        <CheckCircle className="w-5 h-5" />
                        <span className="font-medium">
                          Filed successfully
                        </span>
                      </div>
                    )}

                    <button className="flex items-center space-x-2 px-4 py-2 border border-gray-200 text-gray-600 rounded-lg hover:bg-gray-50 transition ml-auto">
                      <Download className="w-4 h-4" />
                      <span>Export PDF</span>
                    </button>

                    <button className="flex items-center space-x-2 px-4 py-2 border border-gray-200 text-gray-600 rounded-lg hover:bg-gray-50 transition">
                      <Eye className="w-4 h-4" />
                      <span>Preview goAML</span>
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
                <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Select a SAR
                </h3>
                <p className="text-gray-500 mb-6">
                  Choose a SAR from the list to view details and take action
                </p>
                <Link
                  href="/cases"
                  className="inline-flex items-center space-x-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition"
                >
                  <Plus className="w-4 h-4" />
                  <span>Create SAR from Case</span>
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
