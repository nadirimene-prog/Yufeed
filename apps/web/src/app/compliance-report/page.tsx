"use client";

import { useState } from "react";
import {
  BarChart3,
  TrendingUp,
  AlertTriangle,
  FileText,
  Clock,
  CheckCircle,
  Download,
  Calendar,
} from "lucide-react";
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { motion } from "framer-motion";
import toast from "react-hot-toast";
import { useComplianceReport } from "@/hooks/queries/useSpecializedData";
import { LoadingBoundary } from "@/components/shared/LoadingBoundary";
import { logger } from "@/lib/logger";
import { fetchWithAuth } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/apiBaseUrl";

const API_URL = getApiBaseUrl();

interface ComplianceMetrics {
  alert_metrics: {
    total_alerts: number;
    by_severity: Record<string, number>;
    by_status: Record<string, number>;
    resolution_time_avg_hours: number;
    false_positive_rate: number;
  };
  case_metrics: {
    total_cases: number;
    open_cases: number;
    closed_cases: number;
    sar_filed: number;
    sar_rate: number;
    avg_investigation_days: number;
  };
  transaction_metrics: {
    total_transactions: number;
    flagged_transactions: number;
    flag_rate: number;
    high_risk_transactions: number;
    total_volume: Record<string, number>;
  };
  regulatory_coverage: {
    total_rules: number;
    active_rules: number;
    rules_with_regulations: number;
    regulatory_coverage_rate: number;
  };
  ai_metrics?: {
    alerts_triaged: number;
    avg_confidence: number;
    auto_escalated: number;
    auto_resolved: number;
  };
}

export default function ComplianceReportPage() {
  const { data: metrics, isLoading, error } = useComplianceReport();
  const [dateRange, setDateRange] = useState(() => {
    const now = new Date();
    const fromDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    return {
      from: fromDate.toISOString().split("T")[0],
      to: now.toISOString().split("T")[0],
    };
  });

  const handleExport = async () => {
    const toastId = toast.loading("Exporting report...");
    try {
      const params = new URLSearchParams({
        date_from: dateRange.from,
        date_to: dateRange.to,
        format: "json",
      });

      const res = await fetchWithAuth(
        `${API_URL}/api/reporting/export?${params}`,
      );
      const data = await res.json();

      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `compliance-report-${dateRange.from}-${dateRange.to}.json`;
      a.click();
      URL.revokeObjectURL(url);

      toast.success("Report exported successfully!", { id: toastId });
    } catch (error) {
      logger.error("Error exporting report:", error);
      toast.error("Failed to export report", { id: toastId });
    }
  };

  return (
    <LoadingBoundary
      loading={isLoading}
      error={error}
      isEmpty={!metrics}
      loadingMessage="Loading compliance report..."
    >
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                  Compliance Reporting Dashboard
                </h1>
                <p className="text-gray-600 dark:text-gray-400">
                  AML/CFT compliance metrics and analytics
                </p>
              </div>

              <button
                onClick={handleExport}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
              >
                <Download className="h-4 w-4" />
                Export Report
              </button>
            </div>

            {/* Date Range Selector */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <div className="flex items-center gap-4">
                <Calendar className="h-5 w-5 text-gray-400" />
                <div className="flex items-center gap-2">
                  <label className="text-sm text-gray-600 dark:text-gray-400">
                    From:
                  </label>
                  <input
                    type="date"
                    value={dateRange.from}
                    onChange={(e) =>
                      setDateRange((prev) => ({
                        ...prev,
                        from: e.target.value,
                      }))
                    }
                    className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <label className="text-sm text-gray-600 dark:text-gray-400">
                    To:
                  </label>
                  <input
                    type="date"
                    value={dateRange.to}
                    onChange={(e) =>
                      setDateRange((prev) => ({ ...prev, to: e.target.value }))
                    }
                    className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Alert Metrics */}
          <div className="mb-8">
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">
              Alert Metrics
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              <MetricCard
                title="Total Alerts"
                value={metrics.alert_metrics.total_alerts}
                icon={<AlertTriangle className="h-5 w-5" />}
                color="blue"
              />
              <MetricCard
                title="Avg Resolution Time"
                value={`${metrics.alert_metrics.resolution_time_avg_hours.toFixed(1)}h`}
                icon={<Clock className="h-5 w-5" />}
                color="yellow"
              />
              <MetricCard
                title="False Positive Rate"
                value={`${metrics.alert_metrics.false_positive_rate.toFixed(1)}%`}
                icon={<CheckCircle className="h-5 w-5" />}
                color="green"
              />
              <MetricCard
                title="Critical Alerts"
                value={metrics.alert_metrics.by_severity.critical || 0}
                icon={<AlertTriangle className="h-5 w-5" />}
                color="red"
              />
            </div>

            {/* Alert Breakdown */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* By Severity - Pie Chart */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="bg-white dark:bg-gray-800 rounded-lg shadow p-6"
              >
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Alerts by Severity
                </h3>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={Object.entries(
                        metrics.alert_metrics.by_severity,
                      ).map(([name, value]) => ({
                        name: name.charAt(0).toUpperCase() + name.slice(1),
                        value,
                      }))}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) =>
                        `${name} ${((percent || 0) * 100).toFixed(0)}%`
                      }
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {Object.keys(metrics.alert_metrics.by_severity).map(
                        (severity, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={
                              severity === "critical"
                                ? "#dc2626"
                                : severity === "high"
                                  ? "#ea580c"
                                  : severity === "medium"
                                    ? "#ca8a04"
                                    : "#2563eb"
                            }
                          />
                        ),
                      )}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </motion.div>

              {/* By Status - Bar Chart */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.1 }}
                className="bg-white dark:bg-gray-800 rounded-lg shadow p-6"
              >
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Alerts by Status
                </h3>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart
                    data={Object.entries(metrics.alert_metrics.by_status).map(
                      ([name, value]) => ({
                        name: name.replace(/_/g, " "),
                        value,
                      }),
                    )}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis
                      dataKey="name"
                      tick={{ fontSize: 12 }}
                      angle={-15}
                      textAnchor="end"
                      height={70}
                    />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="value" fill="#3b82f6" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </motion.div>
            </div>
          </div>

          {/* Case Metrics */}
          <div className="mb-8">
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">
              Case Metrics
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              <MetricCard
                title="Total Cases"
                value={metrics.case_metrics.total_cases}
                icon={<FileText className="h-5 w-5" />}
                color="blue"
              />
              <MetricCard
                title="Open Cases"
                value={metrics.case_metrics.open_cases}
                icon={<Clock className="h-5 w-5" />}
                color="yellow"
              />
              <MetricCard
                title="SAR Filed"
                value={metrics.case_metrics.sar_filed}
                icon={<FileText className="h-5 w-5" />}
                color="red"
              />
              <MetricCard
                title="SAR Rate"
                value={`${metrics.case_metrics.sar_rate.toFixed(1)}%`}
                icon={<TrendingUp className="h-5 w-5" />}
                color="purple"
              />
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <div className="grid grid-cols-3 gap-6">
                <div className="text-center">
                  <p className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                    {metrics.case_metrics.open_cases}
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Open Cases
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                    {metrics.case_metrics.closed_cases}
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Closed Cases
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                    {metrics.case_metrics.avg_investigation_days.toFixed(1)}d
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Avg Investigation Time
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Transaction Metrics */}
          <div className="mb-8">
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">
              Transaction Metrics
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              <MetricCard
                title="Total Transactions"
                value={metrics.transaction_metrics.total_transactions.toLocaleString()}
                icon={<TrendingUp className="h-5 w-5" />}
                color="blue"
              />
              <MetricCard
                title="Flagged"
                value={metrics.transaction_metrics.flagged_transactions.toLocaleString()}
                icon={<AlertTriangle className="h-5 w-5" />}
                color="orange"
              />
              <MetricCard
                title="Flag Rate"
                value={`${metrics.transaction_metrics.flag_rate.toFixed(2)}%`}
                icon={<BarChart3 className="h-5 w-5" />}
                color="yellow"
              />
              <MetricCard
                title="High Risk"
                value={metrics.transaction_metrics.high_risk_transactions.toLocaleString()}
                icon={<AlertTriangle className="h-5 w-5" />}
                color="red"
              />
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Total Volume by Currency
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Object.entries(metrics.transaction_metrics.total_volume).map(
                  ([currency, amount]) => (
                    <div
                      key={currency}
                      className="text-center p-4 bg-gray-50 dark:bg-gray-900 rounded-lg"
                    >
                      <p className="text-2xl font-bold text-gray-900 dark:text-white mb-1">
                        {(amount as number).toLocaleString()}
                      </p>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        {currency}
                      </p>
                    </div>
                  ),
                )}
              </div>
            </div>
          </div>

          {/* Regulatory Coverage (YUFEED INNOVATION) */}
          <div className="mb-8">
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">
              Regulatory Coverage
              <span className="ml-2 text-sm font-normal text-blue-600 dark:text-blue-400">
                Yufeed Innovation
              </span>
            </h2>

            <div className="bg-gradient-to-br from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-lg shadow p-6 border border-blue-200 dark:border-blue-800">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div className="text-center">
                  <p className="text-3xl font-bold text-blue-600 mb-2">
                    {metrics.regulatory_coverage.total_rules}
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Total Rules
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-3xl font-bold text-green-600 mb-2">
                    {metrics.regulatory_coverage.active_rules}
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Active Rules
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-3xl font-bold text-purple-600 mb-2">
                    {metrics.regulatory_coverage.rules_with_regulations}
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Linked to Regulations
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-3xl font-bold text-blue-600 mb-2">
                    {metrics.regulatory_coverage.regulatory_coverage_rate.toFixed(
                      1,
                    )}
                    %
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Coverage Rate
                  </p>
                </div>
              </div>

              <div className="mt-6 p-4 bg-white dark:bg-gray-800 rounded-lg">
                <p className="text-sm text-gray-700 dark:text-gray-300">
                  Regulatory coverage measures the percentage of monitoring
                  rules that are linked to specific EU regulations. Higher
                  coverage ensures that all alerts include regulatory context
                  and compliance explanations.
                </p>
              </div>
            </div>
          </div>

          {/* AI Metrics */}
          {metrics.ai_metrics && (
            <div>
              <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">
                AI Agent Performance
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricCard
                  title="Alerts Triaged"
                  value={metrics.ai_metrics.alerts_triaged}
                  icon={<BarChart3 className="h-5 w-5" />}
                  color="purple"
                />
                <MetricCard
                  title="Avg Confidence"
                  value={`${(metrics.ai_metrics.avg_confidence * 100).toFixed(1)}%`}
                  icon={<TrendingUp className="h-5 w-5" />}
                  color="blue"
                />
                <MetricCard
                  title="Auto Escalated"
                  value={metrics.ai_metrics.auto_escalated}
                  icon={<AlertTriangle className="h-5 w-5" />}
                  color="orange"
                />
                <MetricCard
                  title="Auto Resolved"
                  value={metrics.ai_metrics.auto_resolved}
                  icon={<CheckCircle className="h-5 w-5" />}
                  color="green"
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </LoadingBoundary>
  );
}

function MetricCard({
  title,
  value,
  icon,
  color,
}: {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  color: "blue" | "yellow" | "orange" | "red" | "green" | "purple";
}) {
  const colorClasses = {
    blue: "text-blue-600 bg-blue-50 dark:bg-blue-900/20",
    yellow: "text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20",
    orange: "text-orange-600 bg-orange-50 dark:bg-orange-900/20",
    red: "text-red-600 bg-red-50 dark:bg-red-900/20",
    green: "text-green-600 bg-green-50 dark:bg-green-900/20",
    purple: "text-purple-600 bg-purple-50 dark:bg-purple-900/20",
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: 1.02 }}
      transition={{ duration: 0.2 }}
      className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 cursor-pointer"
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
            {title}
          </p>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="text-2xl font-bold text-gray-900 dark:text-white"
          >
            {value}
          </motion.p>
        </div>
        <motion.div
          whileHover={{ rotate: 360 }}
          transition={{ duration: 0.5 }}
          className={`p-3 rounded-lg ${colorClasses[color]}`}
        >
          {icon}
        </motion.div>
      </div>
    </motion.div>
  );
}
