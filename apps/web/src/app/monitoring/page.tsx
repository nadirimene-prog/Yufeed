'use client';

import { useEffect, useState } from 'react';
import { AlertCircle, Clock, AlertTriangle, TrendingUp, Activity, Shield, CheckCircle, XCircle } from 'lucide-react';
import { fetchWithAuth } from '@/lib/auth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface RealtimeMetrics {
  timestamp: string;
  transactions_last_hour: number;
  alerts_last_hour: number;
  critical_alerts_pending: number;
  high_risk_transactions_last_hour: number;
  average_processing_time_ms: number;
  system_status: string;
}

interface Alert {
  id: number;
  alert_id: string;
  alert_type: string;
  severity: string;
  user_id: string;
  status: string;
  priority: number;
  description: string;
  risk_score: number;
  created_at: string;
}

interface Transaction {
  id: number;
  transaction_id: string;
  user_id: string;
  amount: number;
  currency: string;
  transaction_type: string;
  timestamp: string;
  risk_level: string;
  status: string;
  country_code: string;
}

export default function MonitoringDashboard() {
  const [metrics, setMetrics] = useState<RealtimeMetrics | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [recentTransactions, setRecentTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      // Fetch realtime metrics
      const metricsRes = await fetchWithAuth(`${API_URL}/api/monitoring/metrics/realtime`);
      const metricsData = await metricsRes.json();
      setMetrics(metricsData);

      // Fetch pending alerts
      const alertsRes = await fetchWithAuth(`${API_URL}/api/alerts/pending?limit=10`);
      const alertsData = await alertsRes.json();
      setAlerts(alertsData);

      // Fetch recent transactions
      const txRes = await fetchWithAuth(`${API_URL}/api/transactions/?limit=10`);
      const txData = await txRes.json();
      setRecentTransactions(txData);

      setLoading(false);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Activity className="h-12 w-12 animate-spin mx-auto mb-4 text-blue-600" />
          <p className="text-lg text-gray-700 dark:text-gray-300">Loading monitoring dashboard...</p>
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
            Transaction Monitoring
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Real-time AML/CFT compliance monitoring dashboard
          </p>
        </div>

        {/* Real-time Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <MetricCard
            title="Active Alerts"
            value={metrics?.alerts_last_hour || 0}
            icon={<AlertCircle className="h-6 w-6" />}
            iconColor="text-orange-600"
            bgColor="bg-orange-50 dark:bg-orange-900/20"
          />
          <MetricCard
            title="Critical Pending"
            value={metrics?.critical_alerts_pending || 0}
            icon={<AlertTriangle className="h-6 w-6" />}
            iconColor="text-red-600"
            bgColor="bg-red-50 dark:bg-red-900/20"
          />
          <MetricCard
            title="High Risk (1h)"
            value={metrics?.high_risk_transactions_last_hour || 0}
            icon={<Shield className="h-6 w-6" />}
            iconColor="text-purple-600"
            bgColor="bg-purple-50 dark:bg-purple-900/20"
          />
          <MetricCard
            title="Transactions (1h)"
            value={metrics?.transactions_last_hour || 0}
            icon={<TrendingUp className="h-6 w-6" />}
            iconColor="text-green-600"
            bgColor="bg-green-50 dark:bg-green-900/20"
          />
        </div>

        {/* System Status */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 mb-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Activity className={`h-5 w-5 ${metrics?.system_status === 'operational' ? 'text-green-600' : 'text-red-600'}`} />
              <span className="text-sm font-medium text-gray-900 dark:text-white">
                System Status: <span className="text-green-600">{metrics?.system_status || 'Unknown'}</span>
              </span>
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Avg Processing: {metrics?.average_processing_time_ms}ms
            </div>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Pending Alerts Queue */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Pending Alerts Queue
              </h2>
            </div>
            <div className="p-6">
              {alerts.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <CheckCircle className="h-12 w-12 mx-auto mb-2 text-green-500" />
                  <p>No pending alerts</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {alerts.map((alert) => (
                    <AlertCard key={alert.id} alert={alert} />
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Recent Transactions */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Recent Transactions
              </h2>
            </div>
            <div className="p-6">
              {recentTransactions.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <Activity className="h-12 w-12 mx-auto mb-2" />
                  <p>No recent transactions</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {recentTransactions.map((tx) => (
                    <TransactionCard key={tx.id} transaction={tx} />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ title, value, icon, iconColor, bgColor }: {
  title: string;
  value: number;
  icon: React.ReactNode;
  iconColor: string;
  bgColor: string;
}) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">{title}</p>
          <p className="text-3xl font-bold text-gray-900 dark:text-white">{value}</p>
        </div>
        <div className={`p-3 rounded-lg ${bgColor}`}>
          <div className={iconColor}>{icon}</div>
        </div>
      </div>
    </div>
  );
}

function AlertCard({ alert }: { alert: Alert }) {
  const severityColors = {
    critical: 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400',
    high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-400',
    medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400',
    low: 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400',
  };

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition cursor-pointer">
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-1">
            <span className="text-sm font-mono text-gray-600 dark:text-gray-400">
              {alert.alert_id}
            </span>
            <span className={`text-xs px-2 py-1 rounded-full ${severityColors[alert.severity as keyof typeof severityColors]}`}>
              {alert.severity}
            </span>
          </div>
          <p className="text-sm font-medium text-gray-900 dark:text-white">
            {alert.alert_type.replace(/_/g, ' ').toUpperCase()}
          </p>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            User: {alert.user_id}
          </p>
        </div>
        <div className="text-right">
          <div className="text-xs text-gray-500 dark:text-gray-400">
            Priority {alert.priority}
          </div>
          {alert.risk_score && (
            <div className="text-sm font-semibold text-red-600 mt-1">
              Risk: {alert.risk_score.toFixed(0)}
            </div>
          )}
        </div>
      </div>
      <p className="text-xs text-gray-600 dark:text-gray-400 mt-2">
        {new Date(alert.created_at).toLocaleString()}
      </p>
    </div>
  );
}

function TransactionCard({ transaction }: { transaction: Transaction }) {
  const riskColors = {
    critical: 'text-red-600',
    high: 'text-orange-600',
    medium: 'text-yellow-600',
    low: 'text-green-600',
  };

  const statusIcons = {
    completed: <CheckCircle className="h-4 w-4 text-green-600" />,
    flagged: <AlertTriangle className="h-4 w-4 text-red-600" />,
    blocked: <XCircle className="h-4 w-4 text-red-600" />,
    pending: <Clock className="h-4 w-4 text-gray-600" />,
  };

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-1">
            <span className="text-sm font-mono text-gray-600 dark:text-gray-400">
              {transaction.transaction_id}
            </span>
            {statusIcons[transaction.status as keyof typeof statusIcons]}
          </div>
          <p className="text-lg font-semibold text-gray-900 dark:text-white">
            {transaction.amount.toLocaleString()} {transaction.currency}
          </p>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {transaction.transaction_type.replace(/_/g, ' ')} • {transaction.country_code}
          </p>
        </div>
        <div className="text-right">
          {transaction.risk_level && (
            <span className={`text-sm font-semibold ${riskColors[transaction.risk_level as keyof typeof riskColors]}`}>
              {transaction.risk_level.toUpperCase()}
            </span>
          )}
        </div>
      </div>
      <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
        {new Date(transaction.timestamp).toLocaleString()}
      </p>
    </div>
  );
}
