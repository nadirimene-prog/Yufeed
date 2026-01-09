'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, AlertTriangle, User, DollarSign, MapPin, Clock, Shield, Sparkles, FileText, ChevronRight, ExternalLink } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
  assigned_to?: string;
  resolution_notes?: string;
  transaction_id?: number;
  related_regulations?: number[];
  regulation_context?: string;
  ai_triage?: {
    recommendation: string;
    confidence: number;
    reasoning: string;
    sar_likelihood: number;
    next_steps: string[];
  };
}

interface Transaction {
  id: number;
  transaction_id: string;
  user_id: string;
  amount: number;
  currency: string;
  transaction_type: string;
  timestamp: string;
  country_code?: string;
  ip_address?: string;
  risk_level?: string;
  status: string;
}

interface Regulation {
  id: number;
  celex: string;
  title: string;
  document_type: string;
}

export default function AlertDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [alert, setAlert] = useState<Alert | null>(null);
  const [transaction, setTransaction] = useState<Transaction | null>(null);
  const [regulations, setRegulations] = useState<Regulation[]>([]);
  const [loading, setLoading] = useState(true);
  const [triaging, setTriaging] = useState(false);

  useEffect(() => {
    fetchAlertDetails();
  }, [params.id]);

  const fetchAlertDetails = async () => {
    try {
      // Fetch alert
      const alertRes = await fetch(`${API_URL}/api/alerts/${params.id}`);
      const alertData = await alertRes.json();
      setAlert(alertData);

      // Fetch transaction if available
      if (alertData.transaction_id) {
        const txRes = await fetch(`${API_URL}/api/transactions/${alertData.transaction_id}`);
        const txData = await txRes.json();
        setTransaction(txData);
      }

      // Fetch related regulations
      if (alertData.related_regulations && alertData.related_regulations.length > 0) {
        const regsRes = await fetch(`${API_URL}/api/documents/batch`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ids: alertData.related_regulations })
        });
        const regsData = await regsRes.json();
        setRegulations(regsData);
      }

      setLoading(false);
    } catch (error) {
      console.error('Error fetching alert details:', error);
      setLoading(false);
    }
  };

  const handleTriage = async () => {
    if (!alert) return;
    setTriaging(true);

    try {
      const res = await fetch(`${API_URL}/api/ai/triage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ alert_id: alert.id })
      });

      if (res.ok) {
        fetchAlertDetails();
      }
    } catch (error) {
      console.error('Error triaging alert:', error);
    } finally {
      setTriaging(false);
    }
  };

  const handleAssign = async (analyst: string) => {
    if (!alert) return;

    try {
      await fetch(`${API_URL}/api/alerts/${alert.id}/assign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ assigned_to: analyst })
      });
      fetchAlertDetails();
    } catch (error) {
      console.error('Error assigning alert:', error);
    }
  };

  const handleEscalate = async () => {
    if (!alert) return;

    try {
      await fetch(`${API_URL}/api/alerts/${alert.id}/escalate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ escalated_to: 'senior_analyst' })
      });
      fetchAlertDetails();
    } catch (error) {
      console.error('Error escalating alert:', error);
    }
  };

  const handleResolve = async (outcome: string) => {
    if (!alert) return;

    const notes = prompt('Resolution notes:');
    if (!notes) return;

    try {
      await fetch(`${API_URL}/api/alerts/${alert.id}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ outcome, resolution_notes: notes })
      });
      router.push('/transaction-alerts');
    } catch (error) {
      console.error('Error resolving alert:', error);
    }
  };

  const handleCreateCase = async () => {
    if (!alert) return;

    try {
      const res = await fetch(`${API_URL}/api/cases/from-alert/${alert.alert_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ assigned_to: alert.assigned_to || 'unassigned' })
      });

      if (res.ok) {
        const caseData = await res.json();
        router.push(`/cases/${caseData.case_id}`);
      }
    } catch (error) {
      console.error('Error creating case:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <AlertTriangle className="h-12 w-12 animate-spin mx-auto mb-4 text-blue-600" />
          <p className="text-lg text-gray-700 dark:text-gray-300">Loading alert details...</p>
        </div>
      </div>
    );
  }

  if (!alert) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <AlertTriangle className="h-12 w-12 mx-auto mb-4 text-red-600" />
          <p className="text-lg text-gray-700 dark:text-gray-300">Alert not found</p>
        </div>
      </div>
    );
  }

  const severityColors = {
    critical: 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400 border-red-200',
    high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-400 border-orange-200',
    medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400 border-yellow-200',
    low: 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400 border-blue-200',
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => router.back()}
            className="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white mb-4"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Alerts
          </button>

          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                  {alert.alert_id}
                </h1>
                <span className={`text-xs px-3 py-1 rounded-full border ${severityColors[alert.severity as keyof typeof severityColors]}`}>
                  {alert.severity.toUpperCase()}
                </span>
                <span className="text-sm px-3 py-1 rounded-full bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300">
                  {alert.status.replace(/_/g, ' ')}
                </span>
              </div>
              <p className="text-lg text-gray-600 dark:text-gray-400">
                {alert.alert_type.replace(/_/g, ' ').toUpperCase()}
              </p>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2">
              {!alert.ai_triage && (
                <button
                  onClick={handleTriage}
                  disabled={triaging}
                  className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition disabled:opacity-50"
                >
                  <Sparkles className="h-4 w-4" />
                  {triaging ? 'Triaging...' : 'AI Triage'}
                </button>
              )}
              <button
                onClick={handleCreateCase}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
              >
                Create Case
              </button>
              <button
                onClick={handleEscalate}
                className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition"
              >
                Escalate
              </button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Alert Details */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
                Alert Details
              </h2>

              <div className="space-y-4">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Description</p>
                  <p className="text-gray-900 dark:text-white">{alert.description || 'No description provided'}</p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">User ID</p>
                    <p className="text-gray-900 dark:text-white font-mono">{alert.user_id}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Priority</p>
                    <p className="text-gray-900 dark:text-white">{alert.priority}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Risk Score</p>
                    <p className={`text-2xl font-bold ${
                      alert.risk_score >= 70 ? 'text-red-600' :
                      alert.risk_score >= 40 ? 'text-orange-600' :
                      'text-green-600'
                    }`}>
                      {alert.risk_score.toFixed(0)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Created</p>
                    <p className="text-gray-900 dark:text-white text-sm">
                      {new Date(alert.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>

                {alert.assigned_to && (
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Assigned To</p>
                    <p className="text-gray-900 dark:text-white">{alert.assigned_to}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Transaction Details */}
            {transaction && (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
                  Transaction Details
                </h2>

                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Transaction ID</p>
                      <p className="text-gray-900 dark:text-white font-mono text-sm">
                        {transaction.transaction_id}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Amount</p>
                      <p className="text-2xl font-bold text-gray-900 dark:text-white">
                        {transaction.amount.toLocaleString()} {transaction.currency}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Type</p>
                      <p className="text-gray-900 dark:text-white">
                        {transaction.transaction_type.replace(/_/g, ' ')}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Timestamp</p>
                      <p className="text-gray-900 dark:text-white text-sm">
                        {new Date(transaction.timestamp).toLocaleString()}
                      </p>
                    </div>
                    {transaction.country_code && (
                      <div>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Country</p>
                        <p className="text-gray-900 dark:text-white">{transaction.country_code}</p>
                      </div>
                    )}
                    {transaction.risk_level && (
                      <div>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Risk Level</p>
                        <p className={`font-semibold ${
                          transaction.risk_level === 'critical' ? 'text-red-600' :
                          transaction.risk_level === 'high' ? 'text-orange-600' :
                          transaction.risk_level === 'medium' ? 'text-yellow-600' :
                          'text-green-600'
                        }`}>
                          {transaction.risk_level.toUpperCase()}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* AI Triage Results */}
            {alert.ai_triage && (
              <div className="bg-gradient-to-br from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 rounded-lg shadow p-6 border border-purple-200 dark:border-purple-800">
                <div className="flex items-center gap-2 mb-4">
                  <Sparkles className="h-5 w-5 text-purple-600" />
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                    AI Triage Analysis
                  </h2>
                </div>

                <div className="space-y-4">
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Recommendation</p>
                    <p className="text-lg font-semibold text-gray-900 dark:text-white capitalize">
                      {alert.ai_triage.recommendation}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Confidence</p>
                      <p className="text-2xl font-bold text-purple-600">
                        {(alert.ai_triage.confidence * 100).toFixed(0)}%
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">SAR Likelihood</p>
                      <p className="text-2xl font-bold text-purple-600">
                        {(alert.ai_triage.sar_likelihood * 100).toFixed(0)}%
                      </p>
                    </div>
                  </div>

                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Reasoning</p>
                    <p className="text-gray-900 dark:text-white text-sm leading-relaxed">
                      {alert.ai_triage.reasoning}
                    </p>
                  </div>

                  {alert.ai_triage.next_steps && alert.ai_triage.next_steps.length > 0 && (
                    <div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Recommended Actions</p>
                      <ul className="space-y-2">
                        {alert.ai_triage.next_steps.map((step, idx) => (
                          <li key={idx} className="flex items-start gap-2 text-sm text-gray-900 dark:text-white">
                            <ChevronRight className="h-4 w-4 mt-0.5 text-purple-600 flex-shrink-0" />
                            <span>{step}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Regulatory Context */}
            {alert.regulation_context && (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
                  Regulatory Context
                </h2>
                <div className="prose dark:prose-invert max-w-none">
                  <p className="text-gray-900 dark:text-white text-sm leading-relaxed whitespace-pre-wrap">
                    {alert.regulation_context}
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Actions */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Actions</h3>

              <div className="space-y-2">
                <select
                  onChange={(e) => handleAssign(e.target.value)}
                  defaultValue={alert.assigned_to || ''}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="" disabled>Assign to...</option>
                  <option value="analyst1">Analyst 1</option>
                  <option value="analyst2">Analyst 2</option>
                  <option value="senior_analyst">Senior Analyst</option>
                </select>

                <button
                  onClick={() => handleResolve('resolved')}
                  className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
                >
                  Resolve
                </button>

                <button
                  onClick={() => handleResolve('false_positive')}
                  className="w-full px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition"
                >
                  Mark False Positive
                </button>

                <button
                  onClick={() => router.push(`/sar/draft?alert_id=${alert.id}`)}
                  className="w-full px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
                >
                  Prepare SAR
                </button>
              </div>
            </div>

            {/* Related Regulations */}
            {regulations.length > 0 && (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Related Regulations
                </h3>

                <div className="space-y-3">
                  {regulations.map((reg) => (
                    <a
                      key={reg.id}
                      href={`/doc/${reg.celex}`}
                      target="_blank"
                      className="block p-3 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-mono text-gray-600 dark:text-gray-400 mb-1">
                            {reg.celex}
                          </p>
                          <p className="text-sm text-gray-900 dark:text-white line-clamp-2">
                            {reg.title}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                            {reg.document_type}
                          </p>
                        </div>
                        <ExternalLink className="h-4 w-4 text-gray-400 flex-shrink-0" />
                      </div>
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
