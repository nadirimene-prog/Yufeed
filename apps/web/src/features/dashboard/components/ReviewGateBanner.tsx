"use client";

import { ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ReviewRequirement } from "@/features/dashboard/types";

interface ReviewGateBannerProps {
  requirement: ReviewRequirement | null;
  submittedBy: string;
  reviewNotes: string;
  proposedAction: "close" | "approve";
  currentUserId?: string | null;
  pending?: boolean;
  onSubmittedByChange: (value: string) => void;
  onReviewNotesChange: (value: string) => void;
  onApprove: () => void;
  onReturn: () => void;
  onApproveAndNext?: () => void;
  onReturnAndNext?: () => void;
}

export function ReviewGateBanner({
  requirement,
  submittedBy,
  reviewNotes,
  proposedAction,
  currentUserId,
  pending = false,
  onSubmittedByChange,
  onReviewNotesChange,
  onApprove,
  onReturn,
  onApproveAndNext,
  onReturnAndNext,
}: ReviewGateBannerProps) {
  if (!requirement?.required) {
    return null;
  }

  const normalizedSubmittedBy = submittedBy.trim().toLowerCase();
  const normalizedCurrentUser = (currentUserId ?? "").trim().toLowerCase();
  const missingSubmittedBy = normalizedSubmittedBy.length === 0;
  const isSameUser =
    normalizedSubmittedBy.length > 0 &&
    normalizedCurrentUser.length > 0 &&
    normalizedSubmittedBy === normalizedCurrentUser;
  const hasValidationError = missingSubmittedBy || isSameUser;

  return (
    <section className="rounded-xl border border-orange-200 bg-orange-50 p-3 text-orange-900">
      <div className="mb-2 flex items-center gap-2 text-orange-700">
        <ShieldCheck className="h-4 w-4" />
        <h3 className="text-xs font-semibold uppercase tracking-wide">
          Risk-based 4-eyes review required
        </h3>
      </div>

      <p className="mb-2 text-xs font-medium">
        Action &quot;{proposedAction}&quot; is gated. Reviewer decision is
        required before final disposition.
      </p>
      <p className="mb-2 text-[11px] opacity-90">
        Reasons: {requirement.reasons.join(", ").replaceAll("_", " ")}
      </p>

      {missingSubmittedBy ? (
        <p className="mb-2 text-[11px] font-medium text-red-600">
          Reviewer is required before submitting the gate decision.
        </p>
      ) : null}
      {isSameUser ? (
        <p className="mb-2 text-[11px] font-medium text-red-600">
          4-eyes control failed: reviewer must differ from the current user.
        </p>
      ) : null}

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <input
          value={submittedBy}
          onChange={(event) => onSubmittedByChange(event.target.value)}
          placeholder="Maker user id"
          className="h-9 rounded-lg border border-orange-200 bg-white px-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-orange-500/20"
          aria-label="Submitted by"
        />
        <input
          value={reviewNotes}
          onChange={(event) => onReviewNotesChange(event.target.value)}
          placeholder="Reviewer notes"
          className="h-9 rounded-lg border border-orange-200 bg-white px-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-orange-500/20"
          aria-label="Review notes"
        />
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          className="border-orange-200 hover:bg-orange-100 hover:text-orange-900"
          onClick={onApprove}
          disabled={pending || hasValidationError}
        >
          Approve review
        </Button>
        {onApproveAndNext ? (
          <Button
            variant="outline"
            size="sm"
            data-dashboard-action-next="review-approve"
            data-dashboard-action-next-primary="true"
            className="border-orange-200 hover:bg-orange-100 hover:text-orange-900"
            onClick={onApproveAndNext}
            disabled={pending || hasValidationError}
          >
            Approve + Next
          </Button>
        ) : null}
        <Button
          variant="outline"
          size="sm"
          className="border-orange-200 hover:bg-orange-100 hover:text-orange-900"
          onClick={onReturn}
          disabled={pending || hasValidationError}
        >
          Return to analyst
        </Button>
        {onReturnAndNext ? (
          <Button
            variant="outline"
            size="sm"
            data-dashboard-action-next="review-return"
            className="border-orange-200 hover:bg-orange-100 hover:text-orange-900"
            onClick={onReturnAndNext}
            disabled={pending || hasValidationError}
          >
            Return + Next
          </Button>
        ) : null}
      </div>
    </section>
  );
}

export default ReviewGateBanner;
