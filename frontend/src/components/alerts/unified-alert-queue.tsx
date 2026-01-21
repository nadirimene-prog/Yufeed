'use client';

/**
 * Unified Alert Queue
 *
 * Main component for the unified alert queue with:
 * - Customer-grouped and chronological views
 * - Type filter tabs
 * - Bulk actions
 * - Real-time updates
 */

import React, { useState, useCallback } from 'react';
import { AlertTypeTabs } from './alert-type-tabs';
import { CustomerGroupedAlerts } from './customer-grouped-alerts';
import { AlertRow } from './alert-row';
import { BulkActionToolbar } from './bulk-action-toolbar';

// Types
export interface Alert {
  id: number;
  alert_id: string;
  alert_type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  status: string;
  priority: number;
  user_id: string;
  description: string;
  assigned_to?: string;
  created_at: string;
  updated_at?: string;
  transaction_id?: number;
  sar_filed: boolean;
  regulation_context?: string;
  ai_triage_score?: number;
  ai_recommendation?: string;
}

export interface CustomerGroup {
  customer_id: string;
  customer_name: string;
  risk_level: string;
  risk_score: number;
  alert_count: number;
  critical_count: number;
  high_count: number;
  alerts: Alert[];
}

export interface UnifiedAlertQueueProps {
  initialView?: 'customer' | 'chronological';
  customerId?: string;
  onAlertSelect?: (alert: Alert) => void;
  onAlertAction?: (alertId: string, action: string) => void;
}

type ViewMode = 'customer' | 'chronological';

export function UnifiedAlertQueue({
  initialView = 'customer',
  customerId,
  onAlertSelect,
  onAlertAction,
}: UnifiedAlertQueueProps) {
  const [view, setView] = useState<ViewMode>(initialView);
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [selectedAlerts, setSelectedAlerts] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(false);

  // Mock data - replace with actual API call
  const [alerts] = useState<Alert[]>([
    {
      id: 1,
      alert_id: 'ALT-20240115-ABC123',
      alert_type: 'structuring',
      severity: 'critical',
      status: 'pending',
      priority: 1,
      user_id: 'USR-847291',
      description: 'Multiple transactions near €10k threshold detected',
      created_at: new Date().toISOString(),
      sar_filed: false,
      ai_triage_score: 0.92,
      ai_recommendation: 'escalate',
    },
    {
      id: 2,
      alert_id: 'ALT-20240115-DEF456',
      alert_type: 'velocity',
      severity: 'high',
      status: 'pending',
      priority: 2,
      user_id: 'USR-847291',
      description: 'Unusual transaction velocity detected',
      created_at: new Date(Date.now() - 86400000).toISOString(),
      sar_filed: false,
      ai_triage_score: 0.67,
      ai_recommendation: 'investigate',
    },
    {
      id: 3,
      alert_id: 'ALT-20240115-GHI789',
      alert_type: 'sanctions',
      severity: 'critical',
      status: 'escalated',
      priority: 1,
      user_id: 'USR-123456',
      description: 'Potential sanctions list match',
      created_at: new Date(Date.now() - 172800000).toISOString(),
      sar_filed: false,
      ai_triage_score: 0.95,
      ai_recommendation: 'escalate',
    },
  ]);

  const [typeCounts] = useState<Record<string, number>>({
    structuring: 45,
    velocity: 32,
    sanctions: 18,
    kyc: 32,
  });

  // Group alerts by customer
  const customerGroups: CustomerGroup[] = React.useMemo(() => {
    const groups: Record<string, CustomerGroup> = {};

    alerts.forEach((alert) => {
      if (!groups[alert.user_id]) {
        groups[alert.user_id] = {
          customer_id: alert.user_id,
          customer_name: `Customer ${alert.user_id.slice(-6)}`,
          risk_level: 'high',
          risk_score: 78,
          alert_count: 0,
          critical_count: 0,
          high_count: 0,
          alerts: [],
        };
      }
      groups[alert.user_id].alerts.push(alert);
      groups[alert.user_id].alert_count++;
      if (alert.severity === 'critical') groups[alert.user_id].critical_count++;
      if (alert.severity === 'high') groups[alert.user_id].high_count++;
    });

    return Object.values(groups).sort((a, b) => b.risk_score - a.risk_score);
  }, [alerts]);

  // Filter alerts by selected types
  const filteredAlerts = React.useMemo(() => {
    if (selectedTypes.length === 0) return alerts;
    return alerts.filter((a) => selectedTypes.includes(a.alert_type));
  }, [alerts, selectedTypes]);

  // Handle alert selection
  const handleAlertSelect = useCallback((alertId: string, selected: boolean) => {
    setSelectedAlerts((prev) => {
      const next = new Set(prev);
      if (selected) {
        next.add(alertId);
      } else {
        next.delete(alertId);
      }
      return next;
    });
  }, []);

  // Handle select all
  const handleSelectAll = useCallback((selected: boolean) => {
    if (selected) {
      setSelectedAlerts(new Set(filteredAlerts.map((a) => a.alert_id)));
    } else {
      setSelectedAlerts(new Set());
    }
  }, [filteredAlerts]);

  // Handle bulk action
  const handleBulkAction = useCallback(async (action: string, params?: Record<string, any>) => {
    setIsLoading(true);
    try {
      // Call API
      console.log('Bulk action:', action, Array.from(selectedAlerts), params);
      // Clear selection after action
      setSelectedAlerts(new Set());
    } catch (error) {
      console.error('Bulk action failed:', error);
    } finally {
      setIsLoading(false);
    }
  }, [selectedAlerts]);

  return (
    <div className="space-y-4">
      {/* Type Filter Tabs */}
      <AlertTypeTabs
        typeCounts={typeCounts}
        selectedTypes={selectedTypes}
        onTypeChange={setSelectedTypes}
      />

      {/* View Toggle and Bulk Actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setView('customer')}
            className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
              view === 'customer'
                ? 'bg-blue-600 text-white'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
          >
            By Customer
          </button>
          <button
            onClick={() => setView('chronological')}
            className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
              view === 'chronological'
                ? 'bg-blue-600 text-white'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
          >
            Chronological
          </button>
        </div>

        {selectedAlerts.size > 0 && (
          <BulkActionToolbar
            selectedCount={selectedAlerts.size}
            onAction={handleBulkAction}
            isLoading={isLoading}
          />
        )}
      </div>

      {/* Alert List */}
      {view === 'customer' ? (
        <CustomerGroupedAlerts
          groups={customerGroups}
          selectedAlerts={selectedAlerts}
          onAlertSelect={handleAlertSelect}
          onAlertClick={onAlertSelect}
          onAlertAction={onAlertAction}
        />
      ) : (
        <div className="bg-slate-900 rounded-lg overflow-hidden">
          {/* Header */}
          <div className="px-4 py-3 border-b border-slate-800 flex items-center">
            <input
              type="checkbox"
              checked={selectedAlerts.size === filteredAlerts.length && filteredAlerts.length > 0}
              onChange={(e) => handleSelectAll(e.target.checked)}
              className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-blue-600 focus:ring-blue-500"
            />
            <span className="ml-3 text-sm text-slate-400">
              {filteredAlerts.length} alerts
            </span>
          </div>

          {/* Alerts */}
          <div className="divide-y divide-slate-800">
            {filteredAlerts.map((alert) => (
              <AlertRow
                key={alert.alert_id}
                alert={alert}
                isSelected={selectedAlerts.has(alert.alert_id)}
                onSelect={(selected) => handleAlertSelect(alert.alert_id, selected)}
                onClick={() => onAlertSelect?.(alert)}
                onAction={(action) => onAlertAction?.(alert.alert_id, action)}
              />
            ))}
          </div>

          {filteredAlerts.length === 0 && (
            <div className="px-4 py-12 text-center text-slate-500">
              No alerts found
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default UnifiedAlertQueue;
