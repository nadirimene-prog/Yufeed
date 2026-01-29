"use client";

import { Search } from "lucide-react";

export interface AuditFilters {
  search: string;
  action: string;
  entityType: string;
  entityId: string;
  actorId: string;
}

interface AuditFiltersProps {
  filters: AuditFilters;
  onChange: (filters: AuditFilters) => void;
}

export default function AuditFilters({ filters, onChange }: AuditFiltersProps) {
  return (
    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-4">
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <div className="relative lg:col-span-2">
          <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search audit id, actor, entity id, or path..."
            className="w-full pl-9 pr-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-950 text-sm text-gray-900 dark:text-gray-100"
            value={filters.search}
            onChange={(e) => onChange({ ...filters, search: e.target.value })}
          />
        </div>

        <select
          className="px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-950 text-sm text-gray-900 dark:text-gray-100"
          value={filters.action}
          onChange={(e) => onChange({ ...filters, action: e.target.value })}
        >
          <option value="all">All Actions</option>
          <option value="post">POST</option>
          <option value="patch">PATCH</option>
          <option value="put">PUT</option>
          <option value="delete">DELETE</option>
        </select>

        <select
          className="px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-950 text-sm text-gray-900 dark:text-gray-100"
          value={filters.entityType}
          onChange={(e) => onChange({ ...filters, entityType: e.target.value })}
        >
          <option value="all">All Entities</option>
          <option value="alert">Alerts</option>
          <option value="case">Cases</option>
          <option value="transaction">Transactions</option>
          <option value="rule_version">Rule Versions</option>
          <option value="travel_rule_request">Travel Rule Requests</option>
          <option value="monitoring-rules">Monitoring Rules</option>
          <option value="travel-rule">Travel Rule</option>
          <option value="onchain">On-chain</option>
          <option value="audit">Audit</option>
          <option value="reporting">Reporting</option>
        </select>

        <input
          type="text"
          placeholder="Entity ID (optional)"
          className="lg:col-span-1 px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-950 text-sm text-gray-900 dark:text-gray-100"
          value={filters.entityId}
          onChange={(e) => onChange({ ...filters, entityId: e.target.value })}
        />

        <input
          type="text"
          placeholder="Actor ID (optional)"
          className="lg:col-span-1 px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-950 text-sm text-gray-900 dark:text-gray-100"
          value={filters.actorId}
          onChange={(e) => onChange({ ...filters, actorId: e.target.value })}
        />
      </div>
    </div>
  );
}
