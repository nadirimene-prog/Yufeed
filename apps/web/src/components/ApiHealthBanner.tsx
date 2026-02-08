"use client";

import { useApiHealth } from "@/hooks/useApiHealth";
import { cn } from "@/lib/utils";

export default function ApiHealthBanner() {
  const { status, lastError } = useApiHealth();

  if (status === "ok") return null;

  return (
    <div
      className={cn(
        "mb-4 rounded-md border px-3 py-2 text-sm",
        status === "checking"
          ? "border-amber-200 bg-amber-50 text-amber-900"
          : "border-red-200 bg-red-50 text-red-900",
      )}
      role="status"
      aria-live="polite"
    >
      {status === "checking"
        ? "Checking API connection…"
        : `API unreachable${lastError ? `: ${lastError}` : ""}.`}
    </div>
  );
}
