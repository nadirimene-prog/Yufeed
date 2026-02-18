"use client";

import { ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ReviewRequirement } from "@/features/dashboard/types";

interface ReviewGateBannerProps {
  requirement: ReviewRequirement | null;
  submittedBy: string;
  reviewNotes: string;
  pending?: boolean;
  onSubmittedByChange: (value: string) => void;
  onReviewNotesChange: (value: string) => void;
  onApprove: () => void;
  onReturn: () => void;
}

export function ReviewGateBanner({
  requirement,
  submittedBy,
  reviewNotes,
  pending = false,
  onSubmittedByChange,
  onReviewNotesChange,
  onApprove,
  onReturn,
}: ReviewGateBannerProps) {
  if (!requirement?.required) {
    return null;
  }

  return (
    <section className="rounded-xl border border-risk-high/40 bg-risk-high-soft p-3 text-risk-high">
      <div className="mb-2 flex items-center gap-2">
        <ShieldCheck className="h-4 w-4" />
        <h3 className="text-xs font-semibold uppercase tracking-wide">
          Risk-based 4-eyes review required
        </h3>
      </div>

      <p className="mb-2 text-xs text-white/80">
        Closure is gated. Reviewer decision is required before final
        disposition.
      </p>
      <p className="mb-2 text-[11px] text-white/70">
        Reasons: {requirement.reasons.join(", ").replaceAll("_", " ")}
      </p>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <input
          value={submittedBy}
          onChange={(event) => onSubmittedByChange(event.target.value)}
          placeholder="Maker user id"
          className="h-9 rounded-lg border border-white/20 bg-black/20 px-2 text-xs text-white placeholder:text-white/50"
          aria-label="Submitted by"
        />
        <input
          value={reviewNotes}
          onChange={(event) => onReviewNotesChange(event.target.value)}
          placeholder="Reviewer notes"
          className="h-9 rounded-lg border border-white/20 bg-black/20 px-2 text-xs text-white placeholder:text-white/50"
          aria-label="Review notes"
        />
      </div>

      <div className="mt-2 flex items-center gap-2">
        <Button
          variant="glass"
          size="sm"
          onClick={onApprove}
          disabled={pending || submittedBy.trim().length === 0}
        >
          Approve review
        </Button>
        <Button
          variant="glass"
          size="sm"
          onClick={onReturn}
          disabled={pending || submittedBy.trim().length === 0}
        >
          Return to analyst
        </Button>
      </div>
    </section>
  );
}

export default ReviewGateBanner;
