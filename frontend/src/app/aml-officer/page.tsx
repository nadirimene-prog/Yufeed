"use client";

/**
 * AI AML Officer Dashboard
 *
 * The main dashboard for the AI AML Officer system.
 * Provides:
 * - Daily briefing overview
 * - Quick actions panel
 * - Pending investigations queue
 * - Proactive alerts feed
 * - Compliance Q&A access
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Brain,
  AlertTriangle,
  FileSearch,
  MessageSquare,
  Shield,
  TrendingUp,
  TrendingDown,
  Minus,
  Clock,
  CheckCircle,
  XCircle,
  ArrowRight,
  RefreshCw,
  Sparkles,
  FileText,
  Calendar,
} from "lucide-react";
import amlOfficerApi, {
  DailyBriefing,
  ProactiveAlert,
  AMLOfficerCapabilities,
} from "@/lib/aml-officer-api";

export default function AMLOfficerDashboard() {
  const [briefing, setBriefing] = useState<DailyBriefing | null>(null);
  const [proactiveAlerts, setProactiveAlerts] = useState<ProactiveAlert[]>([]);
  const [capabilities, setCapabilities] =
    useState<AMLOfficerCapabilities | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = async () => {
    try {
      setError(null);
      const [briefingData, alertsData, capabilitiesData] = await Promise.all([
        amlOfficerApi.getDailyBriefing().catch(() => null),
        amlOfficerApi.getProactiveAlerts().catch(() => ({ alerts: [] })),
        amlOfficerApi.getCapabilities().catch(() => null),
      ]);

      if (briefingData) setBriefing(briefingData);
      setProactiveAlerts(alertsData.alerts || []);
      if (capabilitiesData) setCapabilities(capabilitiesData);
    } catch (err) {
      setError("Failed to load dashboard data");
      console.error(err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case "increasing":
        return <TrendingUp className="w-4 h-4 text-red-500" />;
      case "decreasing":
        return <TrendingDown className="w-4 h-4 text-green-500" />;
      default:
        return <Minus className="w-4 h-4 text-gray-500" />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "critical":
        return "bg-red-100 text-red-800 border-red-200";
      case "high":
        return "bg-orange-100 text-orange-800 border-orange-200";
      case "medium":
        return "bg-yellow-100 text-yellow-800 border-yellow-200";
      default:
        return "bg-blue-100 text-blue-800 border-blue-200";
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Brain className="w-16 h-16 text-indigo-600 mx-auto animate-pulse" />
          <p className="mt-4 text-gray-600">Loading AI AML Officer...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white">
        <div className="max-w-7xl mx-auto px-4 py-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="p-3 bg-white/10 rounded-lg">
                <Brain className="w-8 h-8" />
              </div>
              <div>
                <h1 className="text-2xl font-bold">AI AML Officer</h1>
                <p className="text-indigo-200">
                  Your intelligent compliance partner
                </p>
              </div>
            </div>
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="flex items-center space-x-2 px-4 py-2 bg-white/10 rounded-lg hover:bg-white/20 transition"
            >
              <RefreshCw
                className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`}
              />
              <span>Refresh</span>
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {/* Daily Briefing Card */}
        {briefing && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-8">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-3">
                <Sparkles className="w-6 h-6 text-indigo-600" />
                <h2 className="text-xl font-semibold text-gray-900">
                  Daily Briefing
                </h2>
              </div>
              <span className="text-sm text-gray-500">
                Generated{" "}
                {new Date(briefing.generated_at).toLocaleTimeString()}
              </span>
            </div>

            <p className="text-gray-700 mb-6">
              {briefing.narrative.executive_summary}
            </p>

            {/* Metrics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-red-50 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <span className="text-red-600 text-sm font-medium">
                    Critical Alerts
                  </span>
                  <AlertTriangle className="w-5 h-5 text-red-500" />
                </div>
                <p className="text-2xl font-bold text-red-700 mt-2">
                  {briefing.alerts.critical}
                </p>
              </div>

              <div className="bg-yellow-50 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <span className="text-yellow-600 text-sm font-medium">
                    Pending Alerts
                  </span>
                  <Clock className="w-5 h-5 text-yellow-500" />
                </div>
                <p className="text-2xl font-bold text-yellow-700 mt-2">
                  {briefing.alerts.pending}
                </p>
              </div>

              <div className="bg-blue-50 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <span className="text-blue-600 text-sm font-medium">
                    Open Cases
                  </span>
                  <FileSearch className="w-5 h-5 text-blue-500" />
                </div>
                <p className="text-2xl font-bold text-blue-700 mt-2">
                  {briefing.cases.open}
                </p>
              </div>

              <div className="bg-purple-50 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <span className="text-purple-600 text-sm font-medium">
                    SAR Pending
                  </span>
                  <FileText className="w-5 h-5 text-purple-500" />
                </div>
                <p className="text-2xl font-bold text-purple-700 mt-2">
                  {briefing.cases.sar_pending}
                </p>
              </div>
            </div>

            {/* Risk Trend */}
            <div className="flex items-center space-x-4 p-4 bg-gray-50 rounded-lg">
              <span className="text-gray-600">Risk Trend:</span>
              <div className="flex items-center space-x-2">
                {getTrendIcon(briefing.risk.trend)}
                <span className="font-medium capitalize">
                  {briefing.risk.trend}
                </span>
              </div>
              {briefing.risk.emerging_patterns.length > 0 && (
                <span className="text-sm text-gray-500">
                  | {briefing.risk.emerging_patterns.length} emerging patterns
                  detected
                </span>
              )}
            </div>
          </div>
        )}

        {/* Quick Actions */}
        <div className="grid md:grid-cols-4 gap-4 mb-8">
          <Link
            href="/transaction-alerts"
            className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:border-indigo-300 hover:shadow-md transition group"
          >
            <AlertTriangle className="w-8 h-8 text-orange-500 mb-3" />
            <h3 className="font-semibold text-gray-900 mb-1">Review Alerts</h3>
            <p className="text-sm text-gray-500">
              Triage pending transaction alerts
            </p>
            <div className="mt-4 flex items-center text-indigo-600 text-sm font-medium group-hover:translate-x-1 transition-transform">
              Open <ArrowRight className="w-4 h-4 ml-1" />
            </div>
          </Link>

          <Link
            href="/cases"
            className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:border-indigo-300 hover:shadow-md transition group"
          >
            <FileSearch className="w-8 h-8 text-blue-500 mb-3" />
            <h3 className="font-semibold text-gray-900 mb-1">
              Case Management
            </h3>
            <p className="text-sm text-gray-500">
              Manage investigation cases
            </p>
            <div className="mt-4 flex items-center text-indigo-600 text-sm font-medium group-hover:translate-x-1 transition-transform">
              Open <ArrowRight className="w-4 h-4 ml-1" />
            </div>
          </Link>

          <Link
            href="/aml-officer/ask"
            className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:border-indigo-300 hover:shadow-md transition group"
          >
            <MessageSquare className="w-8 h-8 text-green-500 mb-3" />
            <h3 className="font-semibold text-gray-900 mb-1">Ask AI</h3>
            <p className="text-sm text-gray-500">
              Get compliance guidance
            </p>
            <div className="mt-4 flex items-center text-indigo-600 text-sm font-medium group-hover:translate-x-1 transition-transform">
              Open <ArrowRight className="w-4 h-4 ml-1" />
            </div>
          </Link>

          <Link
            href="/aml-officer/sanctions"
            className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:border-indigo-300 hover:shadow-md transition group"
          >
            <Shield className="w-8 h-8 text-red-500 mb-3" />
            <h3 className="font-semibold text-gray-900 mb-1">
              Sanctions Check
            </h3>
            <p className="text-sm text-gray-500">
              Screen names against lists
            </p>
            <div className="mt-4 flex items-center text-indigo-600 text-sm font-medium group-hover:translate-x-1 transition-transform">
              Open <ArrowRight className="w-4 h-4 ml-1" />
            </div>
          </Link>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {/* Priority Actions */}
          {briefing && briefing.recommendations.priority_actions.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <CheckCircle className="w-5 h-5 text-green-500 mr-2" />
                Priority Actions
              </h3>
              <ul className="space-y-3">
                {briefing.recommendations.priority_actions.map(
                  (action, index) => (
                    <li
                      key={index}
                      className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg"
                    >
                      <span className="flex-shrink-0 w-6 h-6 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center text-sm font-medium">
                        {index + 1}
                      </span>
                      <span className="text-gray-700">{action}</span>
                    </li>
                  )
                )}
              </ul>
            </div>
          )}

          {/* Proactive Alerts */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <Brain className="w-5 h-5 text-indigo-500 mr-2" />
              AI-Detected Risks
            </h3>
            {proactiveAlerts.length === 0 ? (
              <p className="text-gray-500 text-center py-8">
                No proactive alerts at this time
              </p>
            ) : (
              <ul className="space-y-3">
                {proactiveAlerts.map((alert, index) => (
                  <li
                    key={index}
                    className={`p-4 rounded-lg border ${getSeverityColor(
                      alert.severity
                    )}`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-medium">{alert.message}</p>
                        <p className="text-sm mt-1 opacity-75">
                          {alert.recommendation}
                        </p>
                      </div>
                      <span className="text-xs font-medium uppercase">
                        {alert.severity}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* Regulatory Calendar */}
        {briefing && briefing.regulatory.upcoming_deadlines.length > 0 && (
          <div className="mt-8 bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <Calendar className="w-5 h-5 text-purple-500 mr-2" />
              Upcoming Regulatory Deadlines
            </h3>
            <div className="grid md:grid-cols-3 gap-4">
              {briefing.regulatory.upcoming_deadlines.map((deadline, index) => (
                <div
                  key={index}
                  className="p-4 bg-purple-50 rounded-lg border border-purple-100"
                >
                  <p className="font-medium text-purple-900">{deadline.title}</p>
                  <p className="text-sm text-purple-600 mt-1">
                    {deadline.days_remaining} days remaining
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Agent Status */}
        {capabilities && (
          <div className="mt-8 bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              AI Agent Status
            </h3>
            <div className="grid md:grid-cols-3 gap-4">
              {capabilities.agents.map((agent, index) => (
                <div
                  key={index}
                  className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg"
                >
                  {agent.status === "active" ? (
                    <CheckCircle className="w-5 h-5 text-green-500" />
                  ) : agent.status === "coming_soon" ? (
                    <Clock className="w-5 h-5 text-yellow-500" />
                  ) : (
                    <XCircle className="w-5 h-5 text-gray-400" />
                  )}
                  <div>
                    <p className="font-medium text-gray-900 capitalize">
                      {agent.type.replace("_", " ")}
                    </p>
                    <p className="text-xs text-gray-500">{agent.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
