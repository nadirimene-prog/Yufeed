'use client';

/**
 * Customer Grouped Alerts
 *
 * Displays alerts grouped by customer with collapsible sections.
 */

import React, { useState } from 'react';
import { ChevronDown, ChevronRight, AlertTriangle, User } from 'lucide-react';
import { Alert, CustomerGroup } from './unified-alert-queue';
import { AlertRow } from './alert-row';

interface CustomerGroupedAlertsProps {
  groups: CustomerGroup[];
  selectedAlerts: Set<string>;
  onAlertSelect: (alertId: string, selected: boolean) => void;
  onAlertClick?: (alert: Alert) => void;
  onAlertAction?: (alertId: string, action: string) => void;
}

const RISK_COLORS: Record<string, string> = {
  critical: 'bg-red-500',
  high: 'bg-orange-500',
  medium: 'bg-yellow-500',
  low: 'bg-green-500',
  unknown: 'bg-slate-500',
};

export function CustomerGroupedAlerts({
  groups,
  selectedAlerts,
  onAlertSelect,
  onAlertClick,
  onAlertAction,
}: CustomerGroupedAlertsProps) {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(
    new Set(groups.slice(0, 3).map((g) => g.customer_id))
  );

  const toggleGroup = (customerId: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(customerId)) {
        next.delete(customerId);
      } else {
        next.add(customerId);
      }
      return next;
    });
  };

  const isGroupSelected = (group: CustomerGroup) => {
    return group.alerts.every((a) => selectedAlerts.has(a.alert_id));
  };

  const handleGroupSelect = (group: CustomerGroup, selected: boolean) => {
    group.alerts.forEach((alert) => {
      onAlertSelect(alert.alert_id, selected);
    });
  };

  return (
    <div className="space-y-3">
      {groups.map((group) => {
        const isExpanded = expandedGroups.has(group.customer_id);
        const riskColor = RISK_COLORS[group.risk_level] || RISK_COLORS.unknown;

        return (
          <div
            key={group.customer_id}
            className="bg-slate-900 rounded-lg overflow-hidden border border-slate-800"
          >
            {/* Group Header */}
            <div
              className="px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-slate-850 transition-colors"
              onClick={() => toggleGroup(group.customer_id)}
            >
              <div className="flex items-center space-x-4">
                {/* Checkbox */}
                <input
                  type="checkbox"
                  checked={isGroupSelected(group)}
                  onChange={(e) => {
                    e.stopPropagation();
                    handleGroupSelect(group, e.target.checked);
                  }}
                  onClick={(e) => e.stopPropagation()}
                  className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-blue-600 focus:ring-blue-500"
                />

                {/* Expand/Collapse Icon */}
                {isExpanded ? (
                  <ChevronDown className="w-5 h-5 text-slate-400" />
                ) : (
                  <ChevronRight className="w-5 h-5 text-slate-400" />
                )}

                {/* Customer Info */}
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center">
                    <User className="w-5 h-5 text-slate-400" />
                  </div>
                  <div>
                    <div className="font-medium text-white">
                      {group.customer_name}
                    </div>
                    <div className="text-sm text-slate-400">
                      {group.customer_id}
                    </div>
                  </div>
                </div>

                {/* Risk Badge */}
                <div className="flex items-center space-x-2">
                  <span
                    className={`px-2 py-1 rounded text-xs font-medium text-white ${riskColor}`}
                  >
                    {group.risk_level.toUpperCase()}
                  </span>
                  <span className="text-sm text-slate-400">
                    Score: {group.risk_score}
                  </span>
                </div>
              </div>

              {/* Alert Counts */}
              <div className="flex items-center space-x-4">
                {group.critical_count > 0 && (
                  <div className="flex items-center space-x-1 text-red-400">
                    <AlertTriangle className="w-4 h-4" />
                    <span className="text-sm font-medium">{group.critical_count}</span>
                  </div>
                )}
                {group.high_count > 0 && (
                  <div className="flex items-center space-x-1 text-orange-400">
                    <AlertTriangle className="w-4 h-4" />
                    <span className="text-sm font-medium">{group.high_count}</span>
                  </div>
                )}
                <span className="text-sm text-slate-400">
                  {group.alert_count} alert{group.alert_count !== 1 ? 's' : ''}
                </span>
              </div>
            </div>

            {/* Expanded Alerts */}
            {isExpanded && (
              <div className="border-t border-slate-800">
                {group.alerts.map((alert) => (
                  <AlertRow
                    key={alert.alert_id}
                    alert={alert}
                    isSelected={selectedAlerts.has(alert.alert_id)}
                    onSelect={(selected) => onAlertSelect(alert.alert_id, selected)}
                    onClick={() => onAlertClick?.(alert)}
                    onAction={(action) => onAlertAction?.(alert.alert_id, action)}
                    compact
                  />
                ))}

                {/* Investigate All Button */}
                <div className="px-4 py-3 bg-slate-850 flex justify-end">
                  <button
                    onClick={() => {
                      // Navigate to customer investigation
                      console.log('Investigate customer:', group.customer_id);
                    }}
                    className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 transition-colors"
                  >
                    Investigate Customer
                  </button>
                </div>
              </div>
            )}
          </div>
        );
      })}

      {groups.length === 0 && (
        <div className="bg-slate-900 rounded-lg px-4 py-12 text-center text-slate-500">
          No customer groups found
        </div>
      )}
    </div>
  );
}

export default CustomerGroupedAlerts;
