"use client";

import { useCallback, useMemo } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";

/**
 * Configuration for a single URL filter parameter.
 */
export interface FilterConfig {
  /** The key used in the URL query string */
  key: string;
  /** The data type for parsing/serializing */
  type: "string" | "number" | "boolean" | "array";
  /** Default value when the parameter is absent from the URL */
  defaultValue?: unknown;
}

/**
 * Return type for the useURLFilters hook.
 */
export interface UseURLFiltersReturn<T> {
  /** Current filter values parsed from the URL */
  filters: T;
  /** Set a single filter value (updates the URL) */
  setFilter: (key: keyof T, value: unknown) => void;
  /** Set multiple filter values at once (updates the URL) */
  setFilters: (filters: Partial<T>) => void;
  /** Reset all filters to their default values (clears URL params) */
  resetFilters: () => void;
  /** Number of filters that differ from their default value */
  activeFilterCount: number;
}

/**
 * Parse a raw URL search param string into a typed value
 * based on the filter config type.
 */
function parseParam(raw: string | null, config: FilterConfig): unknown {
  if (raw === null || raw === "") {
    return config.defaultValue ?? getTypeDefault(config.type);
  }

  switch (config.type) {
    case "number": {
      const parsed = Number(raw);
      return Number.isNaN(parsed) ? (config.defaultValue ?? 0) : parsed;
    }
    case "boolean":
      return raw === "true" || raw === "1";
    case "array":
      return raw
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
    case "string":
    default:
      return raw;
  }
}

/**
 * Serialize a typed value back to a URL search param string.
 * Returns null if the value matches the default (meaning we should omit the param).
 */
function serializeParam(value: unknown, config: FilterConfig): string | null {
  const defaultVal = config.defaultValue ?? getTypeDefault(config.type);

  // If value matches default, omit from URL to keep it clean
  if (isDefaultValue(value, defaultVal, config.type)) {
    return null;
  }

  switch (config.type) {
    case "number":
      return String(value);
    case "boolean":
      return value ? "true" : "false";
    case "array": {
      const arr = Array.isArray(value) ? value : [];
      const joined = arr.filter(Boolean).join(",");
      return joined ?? null;
    }
    case "string":
    default:
      return value ? String(value) : null;
  }
}

/**
 * Get the default "zero value" for a type when no explicit default is provided.
 */
function getTypeDefault(type: FilterConfig["type"]): unknown {
  switch (type) {
    case "number":
      return 0;
    case "boolean":
      return false;
    case "array":
      return [];
    case "string":
    default:
      return "";
  }
}

/**
 * Check if a value is equal to the default value for its type.
 */
function isDefaultValue(
  value: unknown,
  defaultVal: unknown,
  type: FilterConfig["type"],
): boolean {
  if (type === "array") {
    const arr = Array.isArray(value) ? value : [];
    const defArr = Array.isArray(defaultVal) ? defaultVal : [];
    if (arr.length !== defArr.length) return false;
    return arr.every((v, i) => v === defArr[i]);
  }
  return value === defaultVal;
}

/**
 * A custom hook that syncs filter state with URL search params.
 *
 * Filters are read from and written to the URL query string,
 * which means they survive page refreshes and are shareable via URL.
 *
 * Uses `router.replace` to avoid polluting browser history with
 * every filter change.
 *
 * @example
 * ```tsx
 * const filterConfig: FilterConfig[] = [
 *   { key: 'status', type: 'string', defaultValue: 'all' },
 *   { key: 'severity', type: 'string', defaultValue: 'all' },
 *   { key: 'search', type: 'string', defaultValue: '' },
 *   { key: 'tags', type: 'array', defaultValue: [] },
 * ];
 *
 * type Filters = {
 *   status: string;
 *   severity: string;
 *   search: string;
 *   tags: string[];
 * };
 *
 * const { filters, setFilter, resetFilters, activeFilterCount } =
 *   useURLFilters<Filters>(filterConfig);
 * ```
 */
export function useURLFilters<T extends Record<string, unknown>>(
  config: FilterConfig[],
): UseURLFiltersReturn<T> {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  // Build a lookup map from key -> config for fast access
  const configMap = useMemo(() => {
    const map = new Map<string, FilterConfig>();
    for (const c of config) {
      map.set(c.key, c);
    }
    return map;
  }, [config]);

  // Parse all current filter values from URL params
  const filters = useMemo(() => {
    const result: Record<string, unknown> = {};
    for (const c of config) {
      const raw = searchParams.get(c.key);
      result[c.key] = parseParam(raw, c);
    }
    return result as T;
  }, [config, searchParams]);

  // Build a new URL string from a params object
  const buildURL = useCallback(
    (params: URLSearchParams): string => {
      const qs = params.toString();
      return qs ? `${pathname}?${qs}` : pathname;
    },
    [pathname],
  );

  // Set a single filter value
  const setFilter = useCallback(
    (key: keyof T, value: unknown) => {
      const params = new URLSearchParams(searchParams.toString());
      const c = configMap.get(key as string);
      if (!c) return;

      const serialized = serializeParam(value, c);
      if (serialized === null) {
        params.delete(c.key);
      } else {
        params.set(c.key, serialized);
      }

      router.replace(buildURL(params), { scroll: false });
    },
    [searchParams, configMap, router, buildURL],
  );

  // Set multiple filter values at once
  const setFilters = useCallback(
    (newFilters: Partial<T>) => {
      const params = new URLSearchParams(searchParams.toString());

      for (const [key, value] of Object.entries(newFilters)) {
        const c = configMap.get(key);
        if (!c) continue;

        const serialized = serializeParam(value, c);
        if (serialized === null) {
          params.delete(c.key);
        } else {
          params.set(c.key, serialized);
        }
      }

      router.replace(buildURL(params), { scroll: false });
    },
    [searchParams, configMap, router, buildURL],
  );

  // Reset all filters (clear all managed params from URL)
  const resetFilters = useCallback(() => {
    const params = new URLSearchParams(searchParams.toString());

    for (const c of config) {
      params.delete(c.key);
    }

    router.replace(buildURL(params), { scroll: false });
  }, [config, searchParams, router, buildURL]);

  // Count how many filters differ from their default value
  const activeFilterCount = useMemo(() => {
    let count = 0;
    for (const c of config) {
      const currentValue = filters[c.key as keyof T];
      const defaultVal = c.defaultValue ?? getTypeDefault(c.type);
      if (!isDefaultValue(currentValue, defaultVal, c.type)) {
        count++;
      }
    }
    return count;
  }, [config, filters]);

  return {
    filters,
    setFilter,
    setFilters,
    resetFilters,
    activeFilterCount,
  };
}

export default useURLFilters;
