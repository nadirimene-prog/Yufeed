"use client";

import { CheckCircle2, Clock3, AlertTriangle } from "lucide-react";
import { StatusBadge } from "@/components/ui/badge-horizon";
import { cn } from "@/lib/utils";

export interface SARLifecycleEvent {
  status: string;
  at?: string;
  note?: string;
}

export interface SARLifecycleData {
  sar_id?: string;
  current_status?: string;
  timeline?: SARLifecycleEvent[];
  updated_at?: string;
}

const STEP_ORDER = [
  "draft",
  "submitted",
  "accepted",
  "accepted_with_warnings",
  "requires_resubmission",
] as const;

const STEP_LABEL: Record<(typeof STEP_ORDER)[number], string> = {
  draft: "Draft",
  submitted: "Submitted",
  accepted: "Accepted",
  accepted_with_warnings: "Accepted (Warnings)",
  requires_resubmission: "Resubmission Required",
};

function stepState(step: string, current: string) {
  if (step === current) return "current" as const;

  const stepIndex = STEP_ORDER.indexOf(step as (typeof STEP_ORDER)[number]);
  const currentIndex = STEP_ORDER.indexOf(
    current as (typeof STEP_ORDER)[number],
  );
  if (stepIndex !== -1 && currentIndex !== -1 && stepIndex < currentIndex) {
    return "done" as const;
  }
  return "pending" as const;
}

export function SARLifecycleTracker({
  lifecycle,
}: {
  lifecycle: SARLifecycleData;
}) {
  const current = (lifecycle.current_status ?? "draft").toLowerCase();

  return (
    <section className="rounded-lg border border-border-subtle bg-bg-overlay p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-foreground-tertiary">
          SAR Lifecycle
        </p>
        {lifecycle.sar_id ? (
          <StatusBadge status="in_review">{lifecycle.sar_id}</StatusBadge>
        ) : null}
      </div>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-5">
        {STEP_ORDER.map((step) => {
          const state = stepState(step, current);
          return (
            <div
              key={step}
              className={cn(
                "rounded-md border p-2 text-xs",
                state === "done" &&
                  "border-risk-clear/40 bg-risk-clear-soft text-risk-clear",
                state === "current" &&
                  "border-primary/40 bg-primary/10 text-primary",
                state === "pending" &&
                  "border-border-subtle bg-bg-base text-foreground-secondary",
              )}
            >
              <p className="mb-1 flex items-center gap-1.5 font-medium">
                {state === "done" ? (
                  <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                ) : state === "current" ? (
                  <Clock3 className="h-3.5 w-3.5" aria-hidden="true" />
                ) : (
                  <AlertTriangle
                    className="h-3.5 w-3.5 opacity-60"
                    aria-hidden="true"
                  />
                )}
                {STEP_LABEL[step]}
              </p>
              {lifecycle.timeline?.find((item) => item.status === step)?.at ? (
                <p className="text-[11px] opacity-80">
                  {new Date(
                    lifecycle.timeline.find((item) => item.status === step)
                      ?.at ?? "",
                  ).toLocaleString()}
                </p>
              ) : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}

export default SARLifecycleTracker;
