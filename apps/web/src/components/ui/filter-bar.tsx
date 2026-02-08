"use client";

import * as React from "react";
import {
  Search,
  X,
  SlidersHorizontal,
  ChevronDown,
  Calendar,
} from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * ===================================================================
 * FILTER BAR - Sentinel Design System
 * Reusable filter bar with glass/dark theme for list pages
 * ===================================================================
 */

/**
 * Definition for a single filter field rendered in the bar.
 */
export interface FilterDefinition {
  /** Unique key matching the URL filter key */
  key: string;
  /** Display label for the filter */
  label: string;
  /** The type of filter input to render */
  type: "select" | "search" | "date-range";
  /** Options for select-type filters */
  options?: { value: string; label: string }[];
  /** Placeholder text */
  placeholder?: string;
}

/**
 * Props for the FilterBar component.
 */
export interface FilterBarProps {
  /** Filter definitions describing which controls to render */
  filters: FilterDefinition[];
  /** Current filter values keyed by filter key */
  values: Record<string, unknown>;
  /** Callback when a filter value changes */
  onChange: (key: string, value: unknown) => void;
  /** Callback to reset all filters */
  onReset: () => void;
  /** Number of currently active (non-default) filters */
  activeCount: number;
  /** Additional className for the container */
  className?: string;
}

/**
 * A reusable filter bar component that renders filter controls based on
 * FilterDefinition configurations. Styled with the Sentinel glass/dark theme.
 *
 * @example
 * ```tsx
 * <FilterBar
 *   filters={[
 *     {
 *       key: 'status',
 *       label: 'Status',
 *       type: 'select',
 *       options: [
 *         { value: 'all', label: 'All Statuses' },
 *         { value: 'pending', label: 'Pending' },
 *       ],
 *     },
 *     { key: 'search', label: 'Search', type: 'search', placeholder: 'Search...' },
 *   ]}
 *   values={filters}
 *   onChange={setFilter}
 *   onReset={resetFilters}
 *   activeCount={activeFilterCount}
 * />
 * ```
 */
export function FilterBar({
  filters,
  values,
  onChange,
  onReset,
  activeCount,
  className,
}: FilterBarProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-xl",
        "border border-white/[0.08] bg-white/[0.03] backdrop-blur-sm",
        "p-4",
        className,
      )}
    >
      <div className="flex flex-col gap-3">
        {/* Top row: filter icon + label + active count badge + reset button */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="h-4 w-4 text-white/40" />
            <span className="text-sm font-medium text-white/70">Filters</span>
            {activeCount > 0 && (
              <span
                className={cn(
                  "inline-flex items-center justify-center",
                  "h-5 min-w-[20px] rounded-full px-1.5",
                  "bg-[#6d5acd] text-[10px] font-semibold text-white",
                  "shadow-[0_0_8px_rgba(109,90,205,0.4)]",
                )}
              >
                {activeCount}
              </span>
            )}
          </div>
          {activeCount > 0 && (
            <button
              type="button"
              onClick={onReset}
              className={cn(
                "flex items-center gap-1.5 rounded-lg px-2.5 py-1",
                "text-xs font-medium text-white/50",
                "transition-all duration-200",
                "hover:bg-white/[0.06] hover:text-white/80",
                "active:scale-[0.97]",
              )}
            >
              <X className="h-3 w-3" />
              Reset all
            </button>
          )}
        </div>

        {/* Filter controls grid */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {filters.map((filter) => (
            <FilterControl
              key={filter.key}
              definition={filter}
              value={values[filter.key]}
              onChange={(value) => onChange(filter.key, value)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * Internal component that renders the appropriate input control
 * based on the filter definition type.
 */
function FilterControl({
  definition,
  value,
  onChange,
}: {
  definition: FilterDefinition;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  switch (definition.type) {
    case "search":
      return (
        <SearchFilter
          definition={definition}
          value={(value as string) ?? ""}
          onChange={onChange}
        />
      );
    case "select":
      return (
        <SelectFilter
          definition={definition}
          value={(value as string) ?? ""}
          onChange={onChange}
        />
      );
    case "date-range":
      return (
        <DateRangeFilter
          definition={definition}
          value={value as { start?: string; end?: string } | undefined}
          onChange={onChange}
        />
      );
    default:
      return null;
  }
}

/**
 * Search input filter with glass styling and animated icon.
 */
function SearchFilter({
  definition,
  value,
  onChange,
}: {
  definition: FilterDefinition;
  value: string;
  onChange: (value: unknown) => void;
}) {
  const [isFocused, setIsFocused] = React.useState(false);

  return (
    <div className="relative">
      <label className="sr-only">{definition.label}</label>
      <div className="relative">
        <Search
          className={cn(
            "absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 transition-colors duration-200",
            isFocused ? "text-[#6d5acd]" : "text-white/30",
          )}
        />
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder={definition.placeholder ?? `Search...`}
          className={cn(
            "h-9 w-full rounded-lg border pl-9 pr-8 text-sm",
            "text-white placeholder:text-white/25",
            "transition-all duration-200 ease-out",
            "focus:outline-none focus:ring-2 focus:ring-offset-0",
            "border-white/[0.08] bg-white/[0.03] backdrop-blur-sm",
            "focus:border-[#6d5acd]/40 focus:bg-white/[0.05]",
            "focus:ring-[#6d5acd]/20",
            "focus:shadow-[0_0_20px_rgba(109,90,205,0.15)]",
          )}
        />
        {value && (
          <button
            type="button"
            onClick={() => onChange("")}
            className={cn(
              "absolute right-2 top-1/2 -translate-y-1/2",
              "rounded p-0.5 text-white/30",
              "transition-colors duration-150",
              "hover:bg-white/[0.08] hover:text-white/60",
            )}
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
    </div>
  );
}

/**
 * Select dropdown filter with glass styling and custom chevron.
 */
function SelectFilter({
  definition,
  value,
  onChange,
}: {
  definition: FilterDefinition;
  value: string;
  onChange: (value: unknown) => void;
}) {
  const options = definition.options ?? [];
  const hasNonDefaultValue = value && value !== options[0]?.value;

  return (
    <div className="relative">
      <label className="sr-only">{definition.label}</label>
      <div className="relative">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={cn(
            "h-9 w-full appearance-none rounded-lg border pl-3 pr-8 text-sm",
            "text-white",
            "transition-all duration-200 ease-out",
            "focus:outline-none focus:ring-2 focus:ring-offset-0",
            "border-white/[0.08] bg-white/[0.03] backdrop-blur-sm",
            "focus:border-[#6d5acd]/40 focus:bg-white/[0.05]",
            "focus:ring-[#6d5acd]/20",
            "focus:shadow-[0_0_20px_rgba(109,90,205,0.15)]",
            "cursor-pointer",
            // Style options for the dropdown overlay (dark background)
            "[&>option]:bg-[#1a1a2e] [&>option]:text-white",
          )}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <div className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 flex items-center gap-1">
          {hasNonDefaultValue && (
            <span className="h-1.5 w-1.5 rounded-full bg-[#6d5acd]" />
          )}
          <ChevronDown className="h-3.5 w-3.5 text-white/30" />
        </div>
      </div>
    </div>
  );
}

/**
 * Date range filter with start and end date inputs.
 */
function DateRangeFilter({
  definition,
  value,
  onChange,
}: {
  definition: FilterDefinition;
  value: { start?: string; end?: string } | undefined;
  onChange: (value: unknown) => void;
}) {
  const start = value?.start ?? "";
  const end = value?.end ?? "";

  const handleStartChange = (newStart: string) => {
    onChange({ start: newStart || undefined, end: end || undefined });
  };

  const handleEndChange = (newEnd: string) => {
    onChange({ start: start || undefined, end: newEnd || undefined });
  };

  return (
    <div className="col-span-1 sm:col-span-2">
      <label className="sr-only">{definition.label}</label>
      <div className="flex items-center gap-2">
        <Calendar className="h-4 w-4 shrink-0 text-white/30" />
        <div className="flex flex-1 items-center gap-2">
          <input
            type="date"
            value={start}
            onChange={(e) => handleStartChange(e.target.value)}
            placeholder="Start date"
            className={cn(
              "h-9 flex-1 rounded-lg border px-3 text-sm",
              "text-white",
              "transition-all duration-200 ease-out",
              "focus:outline-none focus:ring-2 focus:ring-offset-0",
              "border-white/[0.08] bg-white/[0.03] backdrop-blur-sm",
              "focus:border-[#6d5acd]/40 focus:bg-white/[0.05]",
              "focus:ring-[#6d5acd]/20",
              "[color-scheme:dark]",
            )}
          />
          <span className="text-xs text-white/30">to</span>
          <input
            type="date"
            value={end}
            onChange={(e) => handleEndChange(e.target.value)}
            placeholder="End date"
            className={cn(
              "h-9 flex-1 rounded-lg border px-3 text-sm",
              "text-white",
              "transition-all duration-200 ease-out",
              "focus:outline-none focus:ring-2 focus:ring-offset-0",
              "border-white/[0.08] bg-white/[0.03] backdrop-blur-sm",
              "focus:border-[#6d5acd]/40 focus:bg-white/[0.05]",
              "focus:ring-[#6d5acd]/20",
              "[color-scheme:dark]",
            )}
          />
        </div>
        {(start || end) && (
          <button
            type="button"
            onClick={() => onChange({ start: undefined, end: undefined })}
            className={cn(
              "rounded p-1 text-white/30",
              "transition-colors duration-150",
              "hover:bg-white/[0.08] hover:text-white/60",
            )}
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
    </div>
  );
}

export default FilterBar;
