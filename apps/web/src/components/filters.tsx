"use client";

import { cn } from "@/lib/utils";
import type { SearchFilters } from "@/lib/types";

interface FiltersProps {
    filters: SearchFilters;
    onChange: (filters: SearchFilters) => void;
    className?: string;
}

export default function Filters({ filters, onChange, className }: FiltersProps) {
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
                <h3 className="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">Document Type</h3>
                <div className="space-y-2">
                    {documentTypes.map((type) => (
                        <label key={type} className="flex items-center space-x-2">
                            <input
                                type="checkbox"
                                checked={filters.type === type}
                                onChange={() => toggleFilter("type", type)}
                                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-900 dark:checked:bg-blue-500"
                            />
                            <span className="text-sm text-gray-700 dark:text-gray-300">{type}</span>
                        </label>
                    ))}
                </div>
            </div>

            <hr className="border-gray-200 dark:border-gray-800" />

            <div>
                <h3 className="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">Status</h3>
                <div className="space-y-2">
                    {statuses.map((status) => (
                        <label key={status} className="flex items-center space-x-2">
                            <input
                                type="checkbox"
                                checked={filters.status === status}
                                onChange={() => toggleFilter("status", status)}
                                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-900 dark:checked:bg-blue-500"
                            />
                            <span className="text-sm text-gray-700 dark:text-gray-300">{status}</span>
                        </label>
                    ))}
                </div>
            </div>

            <hr className="border-gray-200 dark:border-gray-800" />

            {/* Date Range Placeholder - Keeping it simple for MVP */}
            <div>
                <h3 className="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">Date Range</h3>
                <div className="grid grid-cols-1 gap-2">
                    <input
                        type="date"
                        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white dark:bg-gray-950 dark:border-gray-800 dark:text-gray-100"
                        placeholder="From"
                        value={filters.dateFrom || ''}
                        onChange={(e) => onChange({ ...filters, dateFrom: e.target.value })}
                    />
                    <input
                        type="date"
                        className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white dark:bg-gray-950 dark:border-gray-800 dark:text-gray-100"
                        placeholder="To"
                        value={filters.dateTo || ''}
                        onChange={(e) => onChange({ ...filters, dateTo: e.target.value })}
                    />
                </div>
            </div>
        </div>
    );
}
