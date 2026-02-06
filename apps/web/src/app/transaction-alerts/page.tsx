'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { AlertCircle, Search, AlertTriangle, CheckCircle, Clock, Shield, Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import { fetchWithAuth } from '@/lib/auth';
import { getApiBaseUrl } from '@/lib/apiBaseUrl';
import { useMonitoringAlerts } from "@/hooks/queries/useMonitoringData";
import type { MonitoringAlert } from "@/types/monitoring";

const API_URL = getApiBaseUrl();

export default function TransactionAlertsPage() {
  const router = useRouter();
  const [selectedAlerts, setSelectedAlerts] = useState<number[]>([]);
  const [filters, setFilters] = useState({
    status: 'all',
    severity: 'all',
    search: ''
  });

  const alertsQuery = useMonitoringAlerts({
    limit: 50,
    ...(filters.status !== "all" ? { status: filters.status } : {}),
    ...(filters.severity !== "all" ? { severity: filters.severity } : {}),
  });

  const alerts = alertsQuery.data ?? [];
  const loading = alertsQuery.isLoading;

  const handleBulkTriage = async () => {
    if (selectedAlerts.length === 0) {
      toast.error('Please select at least one alert');
      return;
    }

    const toastId = toast.loading(`Triaging ${selectedAlerts.length} alerts...`);
    try {
      const res = await fetchWithAuth(`${API_URL}/api/ai/triage/batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ alert_ids: selectedAlerts })
      });

      if (res.ok) {
        await alertsQuery.refetch();
        setSelectedAlerts([]);
        toast.success(`Successfully triaged ${selectedAlerts.length} alerts`, { id: toastId });
      } else {
        toast.error('Failed to triage alerts', { id: toastId });
      }
    } catch (error) {
      console.error('Error triaging alerts:', error);
      toast.error('Failed to triage alerts', { id: toastId });
    }
  };

  const handleBulkAssign = async (analyst: string) => {
    if (selectedAlerts.length === 0) {
      toast.error('Please select at least one alert');
      return;
    }

    const toastId = toast.loading(`Assigning ${selectedAlerts.length} alerts to ${analyst}...`);
    try {
      for (const alertId of selectedAlerts) {
        await fetchWithAuth(`${API_URL}/api/alerts/${alertId}/assign`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ assigned_to: analyst })
      });
      }
      await alertsQuery.refetch();
      setSelectedAlerts([]);
      toast.success(`Assigned ${selectedAlerts.length} alerts to ${analyst}`, { id: toastId });
    } catch (error) {
      console.error('Error assigning alerts:', error);
      toast.error('Failed to assign alerts', { id: toastId });
    }
  };

  const toggleSelectAlert = (id: number) => {
    setSelectedAlerts(prev =>
      prev.includes(id) ? prev.filter(a => a !== id) : [...prev, id]
    );
  };

  const severityColors = {
    critical: 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400 border-red-200',
    high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-400 border-orange-200',
    medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400 border-yellow-200',
    low: 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400 border-blue-200',
  };

  const statusColors = {
    pending: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
    under_review: 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400',
    escalated: 'bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-400',
    resolved: 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400',
    false_positive: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
  };

  const filteredAlerts = alerts.filter(alert => {
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      return (
        alert.alert_id.toLowerCase().includes(searchLower) ||
        alert.user_id.toLowerCase().includes(searchLower) ||
        alert.alert_type.toLowerCase().includes(searchLower)
      );
    }
    return true;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 animate-spin mx-auto mb-4 text-blue-600" />
          <p className="text-lg text-gray-700 dark:text-gray-300">Loading alerts...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Transaction Alert Management
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Review, triage, and manage AML/CFT transaction alerts
          </p>
        </div>

        {/* Filters and Actions */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 mb-6">
          <div className="flex flex-col lg:flex-row gap-4">
            {/* Search */}
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search alerts, users, or IDs..."
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  value={filters.search}
                  onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                />
              </div>
            </div>

            {/* Status Filter */}
            <select
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              value={filters.status}
              onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value }))}
            >
              <option value="all">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="under_review">Under Review</option>
              <option value="escalated">Escalated</option>
              <option value="resolved">Resolved</option>
              <option value="false_positive">False Positive</option>
            </select>

            {/* Severity Filter */}
            <select
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              value={filters.severity}
              onChange={(e) => setFilters(prev => ({ ...prev, severity: e.target.value }))}
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>

          {/* Bulk Actions */}
          {selectedAlerts.length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-4">
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  {selectedAlerts.length} selected
                </span>
                <button
                  onClick={handleBulkTriage}
                  className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition"
                >
                  <Sparkles className="h-4 w-4" />
                  AI Triage
                </button>
                <select
                  className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  onChange={(e) => handleBulkAssign(e.target.value)}
                  defaultValue=""
                >
                  <option value="" disabled>Assign to...</option>
                  <option value="analyst1">Analyst 1</option>
                  <option value="analyst2">Analyst 2</option>
                  <option value="senior_analyst">Senior Analyst</option>
                </select>
              </div>
            </div>
          )}
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <StatCard
            title="Total Alerts"
            value={alerts.length}
            icon={<AlertCircle className="h-5 w-5" />}
            color="blue"
          />
          <StatCard
            title="Pending"
            value={alerts.filter(a => a.status === 'pending').length}
            icon={<Clock className="h-5 w-5" />}
            color="yellow"
          />
          <StatCard
            title="Critical"
            value={alerts.filter(a => a.severity === 'critical').length}
            icon={<AlertTriangle className="h-5 w-5" />}
            color="red"
          />
          <StatCard
            title="High Risk"
            value={alerts.filter(a => a.risk_score > 70).length}
            icon={<Shield className="h-5 w-5" />}
            color="orange"
          />
        </div>

        {/* Alerts List */}
        <div className="space-y-3">
          {filteredAlerts.length === 0 ? (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-12 text-center">
              <CheckCircle className="h-16 w-16 mx-auto mb-4 text-green-500" />
              <p className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                No alerts found
              </p>
              <p className="text-gray-600 dark:text-gray-400">
                Try adjusting your filters or search criteria
              </p>
            </div>
          ) : (
            filteredAlerts.map((alert) => (
              <AlertCard
                key={alert.id}
                alert={alert}
                selected={selectedAlerts.includes(alert.id)}
                onToggleSelect={toggleSelectAlert}
                onClick={() => router.push(`/transaction-alerts/${alert.alert_id}`)}
                severityColors={severityColors}
                statusColors={statusColors}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, icon, color }: {
  title: string;
  value: number;
  icon: React.ReactNode;
  color: 'blue' | 'yellow' | 'red' | 'orange';
}) {
  const colorClasses = {
    blue: 'text-blue-600 bg-blue-50 dark:bg-blue-900/20',
    yellow: 'text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20',
    red: 'text-red-600 bg-red-50 dark:bg-red-900/20',
    orange: 'text-orange-600 bg-orange-50 dark:bg-orange-900/20',
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: 1.05 }}
      transition={{ duration: 0.2 }}
      className="bg-white dark:bg-gray-800 rounded-lg shadow p-4"
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">{title}</p>
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

type AlertCardColors = Record<string, string>;

function AlertCard({ alert, selected, onToggleSelect, onClick, severityColors, statusColors }: {
  alert: MonitoringAlert;
  selected: boolean;
  onToggleSelect: (id: number) => void;
  onClick: () => void;
  severityColors: AlertCardColors;
  statusColors: AlertCardColors;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -100 }}
      whileHover={{ scale: 1.01, boxShadow: "0 10px 25px rgba(0,0,0,0.1)" }}
      transition={{ duration: 0.2 }}
      className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition"
    >
      <div className="flex items-start gap-4">
        {/* Checkbox */}
        <input
          type="checkbox"
          checked={selected}
          onChange={() => onToggleSelect(alert.id)}
          className="mt-1 h-4 w-4 rounded border-gray-300"
          onClick={(e) => e.stopPropagation()}
        />

        {/* Alert Content */}
        <div className="flex-1 cursor-pointer" onClick={onClick}>
          <div className="flex items-start justify-between mb-2">
            <div>
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                <span className="text-sm font-mono text-gray-600 dark:text-gray-400">
                  {alert.alert_id}
                </span>
                <span className={`text-xs px-2 py-1 rounded-full border ${severityColors[alert.severity as keyof typeof severityColors]}`}>
                  {alert.severity.toUpperCase()}
                </span>
                <span className={`text-xs px-2 py-1 rounded-full ${statusColors[alert.status as keyof typeof statusColors]}`}>
                  {alert.status.replace(/_/g, ' ')}
                </span>
                {alert.ai_recommendation && (
                  <span className="flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-400">
                    <Sparkles className="h-3 w-3" />
                    AI: {alert.ai_recommendation}
                  </span>
                )}
              </div>
              <p className="text-base font-medium text-gray-900 dark:text-white">
                {alert.alert_type.replace(/_/g, ' ').toUpperCase()}
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                User: {alert.user_id}
              </p>
              {alert.description && (
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                  {alert.description}
                </p>
              )}
            </div>

            <div className="text-right">
              <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                Priority {alert.priority}
              </div>
              {alert.risk_score && (
                <div className={`text-lg font-bold ${
                  alert.risk_score >= 70 ? 'text-red-600' :
                  alert.risk_score >= 40 ? 'text-orange-600' :
                  'text-green-600'
                }`}>
                  {alert.risk_score.toFixed(0)}
                </div>
              )}
              {alert.ai_confidence && (
                <div className="text-xs text-purple-600 dark:text-purple-400 mt-1">
                  {(alert.ai_confidence * 100).toFixed(0)}% conf
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {new Date(alert.created_at).toLocaleString()}
            </p>
            {alert.assigned_to && (
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Assigned to: {alert.assigned_to}
              </p>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
