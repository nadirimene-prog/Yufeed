"use client";

import { formatDate } from "@/app/compliance/obligations/[id]/components/utils";

export default function ObligationReview({
  reviewNotes,
  reviewNote,
  onReviewNoteChange,
  canUseEnhancedApproval,
  onEnhancedApproval,
  actions,
  actionLoading,
  onUpdateStatus,
  onViewSourceDoc,
  createdBy,
  reviewedBy,
  approvedBy,
  approvedAt,
}: {
  reviewNotes?: string | null;
  reviewNote: string;
  onReviewNoteChange: (value: string) => void;
  canUseEnhancedApproval: boolean;
  onEnhancedApproval: () => void;
  actions: Array<{ label: string; status: string }>;
  actionLoading: string | null;
  onUpdateStatus: (status: string) => void;
  onViewSourceDoc: () => void;
  createdBy?: string | null;
  reviewedBy?: string | null;
  approvedBy?: string | null;
  approvedAt?: string | null;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <div className="text-sm font-semibold text-slate-900">
        Head of compliance validation
      </div>
      <p className="mt-1 text-xs text-slate-500">
        Mark the obligation as reviewed/approved or send back for changes.
      </p>

      <div className="mt-4">
        <div className="text-xs font-semibold text-slate-600">Review notes</div>
        {reviewNotes ? (
          <div className="mt-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600 whitespace-pre-wrap">
            {reviewNotes}
          </div>
        ) : (
          <div className="mt-2 text-xs text-slate-500">No notes yet.</div>
        )}
        <textarea
          value={reviewNote}
          onChange={(event) => onReviewNoteChange(event.target.value)}
          placeholder="Add a review note (optional)"
          rows={3}
          className="mt-3 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700"
        />
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {canUseEnhancedApproval && (
          <button
            onClick={onEnhancedApproval}
            className="rounded-full bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-700"
          >
            Enhanced Review & Approve
          </button>
        )}
        {actions.map((action) => (
          <button
            key={action.status}
            onClick={() => onUpdateStatus(action.status)}
            disabled={actionLoading === action.status}
            className="rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-semibold text-slate-600 hover:border-slate-300 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {action.label}
          </button>
        ))}
        <button
          onClick={onViewSourceDoc}
          className="rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-semibold text-slate-600 hover:border-slate-300"
        >
          View source document
        </button>
      </div>

      <div className="mt-4 grid gap-2 text-xs text-slate-500">
        <div>Created by: {createdBy ?? "—"}</div>
        <div>Reviewed by: {reviewedBy ?? "—"}</div>
        <div>Approved by: {approvedBy ?? "—"}</div>
        <div>Approved at: {formatDate(approvedAt)}</div>
      </div>
    </div>
  );
}
