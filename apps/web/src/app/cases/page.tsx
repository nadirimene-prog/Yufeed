'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Folder, Search, Clock, CheckCircle, AlertTriangle, FileText, TrendingUp } from 'lucide-react';
import { fetchWithAuth } from '@/lib/auth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
}

export default function CasesPage() {
  const router = useRouter();
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    status: 'all',
    severity: 'all',
    search: ''
  });

  useEffect(() => {
    fetchCases();
  }, [filters]);

  const fetchCases = async () => {
    try {
      let url = `${API_URL}/api/cases/?limit=50`;

      if (filters.status !== 'all') {
        url += `&status=${filters.status}`;
      }
      if (filters.severity !== 'all') {
        url += `&severity=${filters.severity}`;
      }

      const res = await fetchWithAuth(url);
      const data = await res.json();
      setCases(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching cases:', error);
      setLoading(false);
    }
  };

  const filteredCases = cases.filter(caseItem => {
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      return (
        caseItem.case_id.toLowerCase().includes(searchLower) ||
        (caseItem.subject_id && caseItem.subject_id.toLowerCase().includes(searchLower)) ||
        (caseItem.description && caseItem.description.toLowerCase().includes(searchLower))
      );
    }
    return true;
  });

  const statusColors = {
    open: 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400',
    under_investigation: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400',
    escalated: 'bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-400',
    closed: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
    sar_filed: 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400',
  };

  const severityColors = {
    critical: 'border-red-500',
    high: 'border-orange-500',
    medium: 'border-yellow-500',
    low: 'border-blue-500',
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Folder className="h-12 w-12 animate-spin mx-auto mb-4 text-blue-600" />
          <p className="text-lg text-gray-700 dark:text-gray-300">Loading cases...</p>
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
            Case Management
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Manage AML/CFT investigation cases
          </p>
        </div>

        {/* Filters */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 mb-6">
          <div className="flex flex-col lg:flex-row gap-4">
            {/* Search */}
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search cases, subjects, or descriptions..."
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
              <option value="open">Open</option>
              <option value="under_investigation">Under Investigation</option>
              <option value="escalated">Escalated</option>
              <option value="closed">Closed</option>
              <option value="sar_filed">SAR Filed</option>
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
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <StatCard
            title="Total Cases"
            value={cases.length}
            icon={<Folder className="h-5 w-5" />}
            color="blue"
          />
          <StatCard
            title="Open"
            value={cases.filter(c => c.status === 'open' || c.status === 'under_investigation').length}
            icon={<Clock className="h-5 w-5" />}
            color="yellow"
          />
          <StatCard
            title="Escalated"
            value={cases.filter(c => c.status === 'escalated').length}
            icon={<AlertTriangle className="h-5 w-5" />}
            color="orange"
          />
          <StatCard
            title="SAR Filed"
            value={cases.filter(c => c.status === 'sar_filed').length}
            icon={<FileText className="h-5 w-5" />}
            color="red"
          />
        </div>

        {/* Cases List */}
        <div className="space-y-3">
          {filteredCases.length === 0 ? (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-12 text-center">
              <CheckCircle className="h-16 w-16 mx-auto mb-4 text-green-500" />
              <p className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                No cases found
              </p>
              <p className="text-gray-600 dark:text-gray-400">
                Try adjusting your filters or search criteria
              </p>
            </div>
          ) : (
            filteredCases.map((caseItem) => (
              <CaseCard
                key={caseItem.id}
                caseItem={caseItem}
                onClick={() => router.push(`/cases/${caseItem.case_id}`)}
                statusColors={statusColors}
                severityColors={severityColors}
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
  color: 'blue' | 'yellow' | 'orange' | 'red';
}) {
  const colorClasses = {
    blue: 'text-blue-600 bg-blue-50 dark:bg-blue-900/20',
    yellow: 'text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20',
    orange: 'text-orange-600 bg-orange-50 dark:bg-orange-900/20',
    red: 'text-red-600 bg-red-50 dark:bg-red-900/20',
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">{title}</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          {icon}
        </div>
      </div>
    </div>
  );
}

function CaseCard({ caseItem, onClick, statusColors, severityColors }: {
  caseItem: Case;
  onClick: () => void;
  statusColors: any;
  severityColors: any;
}) {
  const daysSinceOpened = Math.floor(
    (new Date().getTime() - new Date(caseItem.opened_at).getTime()) / (1000 * 60 * 60 * 24)
  );

  return (
    <div
      onClick={onClick}
      className={`bg-white dark:bg-gray-800 rounded-lg shadow p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition cursor-pointer border-l-4 ${severityColors[caseItem.severity as keyof typeof severityColors]}`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-base font-mono font-semibold text-gray-900 dark:text-white">
              {caseItem.case_id}
            </span>
            <span className={`text-xs px-2 py-1 rounded-full ${statusColors[caseItem.status as keyof typeof statusColors]}`}>
              {caseItem.status.replace(/_/g, ' ')}
            </span>
            {caseItem.outcome && (
              <span className="text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300">
                {caseItem.outcome}
              </span>
            )}
          </div>

          <p className="text-base font-medium text-gray-900 dark:text-white mb-1">
            {caseItem.case_type.replace(/_/g, ' ').toUpperCase()}
          </p>

          {caseItem.subject_id && (
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Subject: {caseItem.subject_type} - {caseItem.subject_id}
            </p>
          )}

          {(caseItem.description || caseItem.summary) && (
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-2 line-clamp-2">
              {caseItem.summary || caseItem.description}
            </p>
          )}
        </div>

        <div className="text-right ml-4">
          <div className="text-sm font-semibold text-gray-900 dark:text-white mb-1">
            {caseItem.severity.toUpperCase()}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {daysSinceOpened}d open
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between pt-3 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
          <span>Opened: {new Date(caseItem.opened_at).toLocaleDateString()}</span>
          {caseItem.closed_at && (
            <span>Closed: {new Date(caseItem.closed_at).toLocaleDateString()}</span>
          )}
        </div>

        <div className="flex items-center gap-4 text-xs text-gray-600 dark:text-gray-400">
          {caseItem.related_alert_ids && (
            <span>{caseItem.related_alert_ids.length} alerts</span>
          )}
          {caseItem.related_transaction_ids && (
            <span>{caseItem.related_transaction_ids.length} txs</span>
          )}
          {caseItem.assigned_to && (
            <span>Assigned: {caseItem.assigned_to}</span>
          )}
        </div>
      </div>
    </div>
  );
}
