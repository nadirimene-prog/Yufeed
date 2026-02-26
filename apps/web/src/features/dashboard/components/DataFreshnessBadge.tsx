"use client";

import { Clock3, Database } from "lucide-react";
import { DashboardFreshnessMeta } from "@/features/dashboard/types";
import { cn } from "@/lib/utils";

interface DataFreshnessBadgeProps {
  freshness?: DashboardFreshnessMeta | null;
  label?: string;
  className?: string;
  compact?: boolean;
}

function parseDate(value?: string | null) {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.valueOf())) return null;
  return parsed;
}

function formatRelativeShort(value: Date) {
  const diffSeconds = Math.max(0, Math.round((Date.now() - value.getTime()) / 1000));
  if (diffSeconds < 60) return `${diffSeconds}s ago`;
  const minutes = Math.floor(diffSeconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function DataFreshnessBadge({
  freshness = null,
  label = "Updated",
  className,
  compact = false,
}: DataFreshnessBadgeProps) {
  if (!freshness) {
    return (
      <div
        className={cn(
          "inline-flex items-center gap-1 rounded-lg border border-border bg-slate-50 px-2 py-1 text-[11px] text-muted-foreground",
          className,
        )}
      >
        <Clock3 className="h-3.5 w-3.5" />
        <span>No freshness data</span>
      </div>
    );
  }

  const generatedAt = parseDate(freshness.generated_at);
  const sourceWatermark = parseDate(freshness.source_watermark_at ?? null);
  const staleAfter = Math.max(1, freshness.stale_after_seconds ?? 60);
  const isStale = generatedAt
    ? Date.now() - generatedAt.getTime() > staleAfter * 1000
    : false;
  const sourceLag = typeof freshness.source_lag_seconds === "number" ? freshness.source_lag_seconds : null;

  return (
    <div
      className={cn(
        "inline-flex items-center gap-1 rounded-lg border px-2 py-1 text-[11px]",
        isStale
          ? "border-orange-200 bg-orange-50 text-orange-800"
          : "border-border bg-slate-50 text-muted-foreground",
        className,
      )}
      title={
        generatedAt
          ? `${label}: ${generatedAt.toLocaleString()}`
          : `${label}: unavailable`
      }
      aria-label={
        generatedAt
          ? `${label} ${formatRelativeShort(generatedAt)}${isStale ? ", stale" : ""}`
          : `${label} unavailable`
      }
    >
      <Clock3 className="h-3.5 w-3.5" />
      <span className={cn("font-medium", isStale && "text-orange-900")}>
        {isStale ? "Stale" : label}
      </span>
      {generatedAt ? (
        <span className={cn(compact && "hidden sm:inline")}>
          {formatRelativeShort(generatedAt)}
        </span>
      ) : (
        <span className={cn(compact && "hidden sm:inline")}>unknown</span>
      )}
      {sourceLag !== null ? (
        <span className={cn("inline-flex items-center gap-1", compact && "hidden lg:inline-flex")}>
          <Database className="h-3 w-3" />
          lag {Math.round(sourceLag / 60)}m
        </span>
      ) : null}
      {sourceWatermark ? (
        <span className={cn("text-foreground/60", compact && "hidden xl:inline")}>
          src {formatRelativeShort(sourceWatermark)}
        </span>
      ) : null}
    </div>
  );
}

export default DataFreshnessBadge;
