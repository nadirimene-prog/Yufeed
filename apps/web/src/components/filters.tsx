"use client";

import { cn } from "@/lib/utils";
import type { SearchFilters } from "@/lib/types";

interface FiltersProps {
  filters: SearchFilters;
  onChange: (filters: SearchFilters) => void;
  className?: string;
}

export default function Filters({
  filters,
  onChange,
  className,
}: FiltersProps) {
  const documentTypes = ["Directive", "Regulation", "Decision"];
  const statuses = ["In Force", "No Longer in Force", "Proposal"];

  const toggleFilter = (key: keyof SearchFilters, value: string) => {
    if (filters[key] === value) {
      const newFilters = { ...filters };
      delete newFilters[key];
      onChange(newFilters);
    } else {
      onChange({ ...filters, [key]: value });
    }
  };

  return (
    <div className={cn("space-y-6", className)}>
      <div>
        <h3 className="mb-3 text-sm font-semibold text-slate-900 ">
          Document Type
        </h3>
        <div className="space-y-2">
          {documentTypes.map((type) => (
            <label key={type} className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={filters.type === type}
                onChange={() => toggleFilter("type", type)}
                className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500   "
              />
              <span className="text-sm text-slate-700 ">{type}</span>
            </label>
          ))}
        </div>
      </div>

      <hr className="border-slate-200 " />

      <div>
        <h3 className="mb-3 text-sm font-semibold text-slate-900 ">Status</h3>
        <div className="space-y-2">
          {statuses.map((status) => (
            <label key={status} className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={filters.status === status}
                onChange={() => toggleFilter("status", status)}
                className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500   "
              />
              <span className="text-sm text-slate-700 ">{status}</span>
            </label>
          ))}
        </div>
      </div>

      <hr className="border-slate-200 " />

      {/* Date Range Placeholder - Keeping it simple for MVP */}
      <div>
        <h3 className="mb-3 text-sm font-semibold text-slate-900 ">
          Date Range
        </h3>
        <div className="grid grid-cols-1 gap-2">
          <input
            type="date"
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm bg-white   "
            placeholder="From"
            value={filters.dateFrom || ""}
            onChange={(e) => onChange({ ...filters, dateFrom: e.target.value })}
          />
          <input
            type="date"
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm bg-white   "
            placeholder="To"
            value={filters.dateTo || ""}
            onChange={(e) => onChange({ ...filters, dateTo: e.target.value })}
          />
        </div>
      </div>
    </div>
  );
}
