"use client";

import { CheckCircle2, RotateCcw, ShieldCheck } from "lucide-react";
import { ReviewProvenance } from "@/features/dashboard/types";

interface ReviewProvenanceCardProps {
  provenance?: ReviewProvenance | null;
  className?: string;
}

function formatDateTime(value?: string | null) {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.valueOf())) return value;
  return parsed.toLocaleString();
}

export function ReviewProvenanceCard({
  provenance = null,
  className,
}: ReviewProvenanceCardProps) {
  const outcome = provenance?.review_outcome ?? null;

  return (
    <section
      className={`rounded-xl border border-border bg-slate-50 p-3 ${className ?? ""}`.trim()}
      aria-label="Review provenance"
    >
      <div className="mb-2 flex items-center gap-2">
        <ShieldCheck className="h-4 w-4 text-muted-foreground" />
        <h3 className="text-xs font-semibold uppercase tracking-wide text-foreground">
          Review Provenance
        </h3>
      </div>

      {!provenance ? (
        <p className="text-xs text-muted-foreground">
          Review provenance unavailable for this work item.
        </p>
      ) : (
        <div className="space-y-2 text-xs">
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <div className="rounded-lg border border-border bg-white p-2">
              <p className="text-muted-foreground">Submitted by</p>
              <p className="font-medium text-foreground">
                {provenance.submitted_by || "—"}
              </p>
              <p className="text-muted-foreground/80">
                {formatDateTime(provenance.submitted_at)}
              </p>
            </div>
            <div className="rounded-lg border border-border bg-white p-2">
              <p className="text-muted-foreground">Reviewed by</p>
              <p className="font-medium text-foreground">
                {provenance.reviewed_by || "—"}
              </p>
              <p className="text-muted-foreground/80">
                {formatDateTime(provenance.reviewed_at)}
              </p>
            </div>
          </div>

          <div className="rounded-lg border border-border bg-white p-2">
            <p className="mb-1 text-muted-foreground">Review outcome</p>
            {outcome === "approved" ? (
              <p className="inline-flex items-center gap-1 text-risk-clear font-medium">
                <CheckCircle2 className="h-3.5 w-3.5" />
                Approved
              </p>
            ) : outcome === "returned" ? (
              <p className="inline-flex items-center gap-1 text-risk-high font-medium">
                <RotateCcw className="h-3.5 w-3.5" />
                Returned
              </p>
            ) : (
              <p className="text-muted-foreground">
                No review outcome recorded
              </p>
            )}
            {provenance.return_reason ? (
              <p className="mt-1 text-muted-foreground">
                Return reason: {provenance.return_reason}
              </p>
            ) : null}
          </div>
        </div>
      )}
    </section>
  );
}

export default ReviewProvenanceCard;
