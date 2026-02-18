"use client";

import { useMemo, useState } from "react";
import {
  Clock3,
  ExternalLink,
  FileClock,
  Link2,
  NotebookPen,
  ShieldCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DashboardWorkQueueItem,
  ReviewActionRequest,
  WorkItemActionRequest,
  WorkItemDetailResponse,
  WorkItemActionType,
} from "@/features/dashboard/types";
import {
  formatAgeMinutes,
  severityBadgeClass,
  slaBadgeClass,
} from "@/features/dashboard/utils";
import AiRecommendationCard from "@/features/dashboard/components/AiRecommendationCard";
import ReviewGateBanner from "@/features/dashboard/components/ReviewGateBanner";
import { cn } from "@/lib/utils";

interface InvestigationWorkspaceProps {
  selectedItem: DashboardWorkQueueItem | null;
  detail: WorkItemDetailResponse | null;
  loading?: boolean;
  error?: string | null;
  message?: string | null;
  actionPending?: boolean;
  reviewPending?: boolean;
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
  onAction: (payload: WorkItemActionRequest) => void;
  onReview: (payload: ReviewActionRequest) => void;
}

function formatDateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  return date.toLocaleString();
}

export function InvestigationWorkspace({
  selectedItem,
  detail,
  loading = false,
  error = null,
  message = null,
  actionPending = false,
  reviewPending = false,
  mobileOpen = false,
  onCloseMobile,
  onAction,
  onReview,
}: InvestigationWorkspaceProps) {
  const [notes, setNotes] = useState("");
  const [assignee, setAssignee] = useState("");
  const [narrativeDraft, setNarrativeDraft] = useState(detail?.narrative ?? "");
  const [submittedBy, setSubmittedBy] = useState(detail?.work_item.owner ?? "");
  const [reviewNotes, setReviewNotes] = useState("");

  const allowedActions = useMemo(
    () => detail?.allowed_actions ?? [],
    [detail?.allowed_actions],
  );

  const allActions: Array<{ key: WorkItemActionType; label: string }> = [
    { key: "assign", label: "Assign" },
    { key: "escalate", label: "Escalate" },
    { key: "mark_in_progress", label: "Mark In Progress" },
    { key: "create_case", label: "Create Case" },
    { key: "close", label: "Close" },
  ];

  const actionButtons = allActions.filter((entry) =>
    allowedActions.includes(entry.key),
  );

  const content = (
    <section className="glass-surface flex h-full min-h-[420px] flex-col rounded-2xl border border-white/10 p-3 sm:p-4">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-white">
            Investigation Workspace
          </h2>
          <p className="text-xs text-white/60">
            Decision-ready context and controlled actions.
          </p>
        </div>
        {mobileOpen && onCloseMobile ? (
          <Button variant="glass" size="sm" onClick={onCloseMobile}>
            Close
          </Button>
        ) : null}
      </div>

      {!selectedItem ? (
        <div className="flex flex-1 items-center justify-center rounded-xl border border-dashed border-white/20 text-sm text-white/60">
          Select a work item to open context.
        </div>
      ) : loading ? (
        <div className="flex flex-1 items-center justify-center text-sm text-white/60">
          Loading workspace...
        </div>
      ) : error ? (
        <div className="rounded-xl border border-risk-critical/40 bg-risk-critical-soft p-3 text-sm text-risk-critical">
          {error}
        </div>
      ) : (
        <div className="flex-1 space-y-3 overflow-auto pb-20 md:pb-0">
          <div className="rounded-xl border border-white/10 bg-white/5 p-3">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <p className="text-sm font-semibold text-white">
                {selectedItem.ref_id}
              </p>
              <span
                className={cn(
                  "rounded-full px-2 py-1 text-[10px] uppercase",
                  severityBadgeClass(selectedItem.severity),
                )}
              >
                {selectedItem.severity}
              </span>
              <span
                className={cn(
                  "rounded-full px-2 py-1 text-[10px] uppercase",
                  slaBadgeClass(selectedItem.sla_status),
                )}
              >
                SLA {selectedItem.sla_status}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-[11px] text-white/75">
              <div className="rounded-lg border border-white/10 bg-black/20 p-2">
                <p className="text-white/50">Status</p>
                <p>{selectedItem.status}</p>
              </div>
              <div className="rounded-lg border border-white/10 bg-black/20 p-2">
                <p className="text-white/50">Type</p>
                <p>{selectedItem.type_label}</p>
              </div>
              <div className="rounded-lg border border-white/10 bg-black/20 p-2">
                <p className="text-white/50">Timer</p>
                <p>{formatAgeMinutes(selectedItem.age_minutes)}</p>
              </div>
              <div className="rounded-lg border border-white/10 bg-black/20 p-2">
                <p className="text-white/50">Owner</p>
                <p>{selectedItem.owner ?? "Unassigned"}</p>
              </div>
            </div>
          </div>

          <ReviewGateBanner
            requirement={detail?.review_requirement ?? null}
            submittedBy={submittedBy}
            reviewNotes={reviewNotes}
            pending={reviewPending}
            onSubmittedByChange={setSubmittedBy}
            onReviewNotesChange={setReviewNotes}
            onApprove={() =>
              onReview({
                proposed_action: "close",
                decision: "approve",
                submitted_by: submittedBy,
                review_notes: reviewNotes,
                sar_required: selectedItem.sar_required,
              })
            }
            onReturn={() =>
              onReview({
                proposed_action: "close",
                decision: "return",
                submitted_by: submittedBy,
                review_notes: reviewNotes,
                sar_required: selectedItem.sar_required,
              })
            }
          />

          {message ? (
            <div className="rounded-lg border border-white/15 bg-white/5 p-2 text-xs text-white/80">
              {message}
            </div>
          ) : null}

          <div className="rounded-xl border border-white/10 bg-white/5 p-3">
            <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-white/70">
              <FileClock className="h-4 w-4" />
              Context Timeline
            </h3>
            <div className="space-y-1 text-xs text-white/75">
              {(detail?.context_timeline ?? []).map((event) => (
                <div
                  key={`${event.at}-${event.label}`}
                  className="rounded-lg border border-white/10 bg-black/20 p-2"
                >
                  <p className="font-medium text-white">{event.label}</p>
                  <p>{event.detail ?? "-"}</p>
                  <p className="text-[11px] text-white/50">
                    {formatDateTime(event.at)}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            <div className="rounded-xl border border-white/10 bg-white/5 p-3">
              <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-white/70">
                <Link2 className="h-4 w-4" />
                Linked Entities
              </h3>
              <div className="space-y-1 text-xs text-white/75">
                {(detail?.linked_entities ?? []).length > 0 ? (
                  detail?.linked_entities.map((entity) => (
                    <p key={entity} className="truncate">
                      • {entity}
                    </p>
                  ))
                ) : (
                  <p className="text-white/50">No linked entities</p>
                )}
              </div>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/5 p-3">
              <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-white/70">
                <ExternalLink className="h-4 w-4" />
                Linked Transactions
              </h3>
              <div className="space-y-1 text-xs text-white/75">
                {(detail?.linked_transactions ?? []).length > 0 ? (
                  detail?.linked_transactions.map((tx) => (
                    <p key={tx} className="truncate">
                      • {tx}
                    </p>
                  ))
                ) : (
                  <p className="text-white/50">No linked transactions</p>
                )}
              </div>
            </div>
          </div>

          <AiRecommendationCard
            recommendation={detail?.ai_recommendation ?? null}
          />

          <div className="rounded-xl border border-white/10 bg-white/5 p-3">
            <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-white/70">
              <NotebookPen className="h-4 w-4" />
              Narrative Draft
            </h3>
            <textarea
              value={narrativeDraft}
              onChange={(event) => setNarrativeDraft(event.target.value)}
              className="h-24 w-full rounded-lg border border-white/10 bg-black/20 p-2 text-xs text-white placeholder:text-white/40"
              placeholder="Editable rationale for case notes / SAR narrative"
            />
          </div>

          <div className="grid grid-cols-1 gap-2 lg:grid-cols-2">
            <div className="rounded-xl border border-white/10 bg-white/5 p-3">
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-white/70">
                Evidence Checklist
              </h3>
              <div className="space-y-1 text-xs text-white/75">
                {(detail?.evidence_checklist ?? []).map((item) => (
                  <p key={item.id} className="flex items-center gap-1.5">
                    <ShieldCheck
                      className={cn(
                        "h-3.5 w-3.5",
                        item.completed ? "text-risk-clear" : "text-white/40",
                      )}
                    />
                    {item.label}
                  </p>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-white/10 bg-white/5 p-3">
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-white/70">
                Action History
              </h3>
              <div className="space-y-1 text-xs text-white/75">
                {(detail?.action_history ?? []).length > 0 ? (
                  detail?.action_history.map((item) => (
                    <p key={`${item.at}-${item.action}`}>
                      <span className="text-white/50">
                        {formatDateTime(item.at)}:
                      </span>{" "}
                      {item.actor} • {item.action}
                    </p>
                  ))
                ) : (
                  <p className="text-white/50">No actions recorded yet.</p>
                )}
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-white/10 bg-white/5 p-3">
            <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-white/70">
              <Clock3 className="h-4 w-4" />
              Actions
            </h3>

            <div className="mb-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
              <input
                value={assignee}
                onChange={(event) => setAssignee(event.target.value)}
                placeholder="Assignee user id"
                className="h-9 rounded-lg border border-white/10 bg-black/20 px-2 text-xs text-white placeholder:text-white/40"
                aria-label="Assignee"
              />
              <input
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                placeholder="Action notes"
                className="h-9 rounded-lg border border-white/10 bg-black/20 px-2 text-xs text-white placeholder:text-white/40"
                aria-label="Action notes"
              />
            </div>

            <div className="flex flex-wrap gap-2">
              {actionButtons.map((entry) => (
                <Button
                  key={entry.key}
                  variant="glass"
                  size="sm"
                  disabled={
                    actionPending ||
                    (entry.key === "assign" && assignee.trim().length === 0)
                  }
                  onClick={() =>
                    onAction({
                      action: entry.key,
                      assignee: entry.key === "assign" ? assignee : undefined,
                      notes,
                      sar_required: selectedItem.sar_required,
                    })
                  }
                >
                  {entry.label}
                </Button>
              ))}
            </div>
          </div>
        </div>
      )}

      {selectedItem ? (
        <div className="fixed inset-x-0 bottom-0 z-30 border-t border-white/10 bg-[#0b1020]/95 p-2 backdrop-blur md:hidden">
          <div className="flex gap-2">
            <Button
              variant="glass"
              size="sm"
              className="flex-1"
              disabled={actionPending}
              onClick={() =>
                onAction({
                  action: "mark_in_progress",
                  notes,
                })
              }
            >
              In Progress
            </Button>
            <Button
              variant="glass"
              size="sm"
              className="flex-1"
              disabled={actionPending}
              onClick={() =>
                onAction({
                  action: "escalate",
                  notes,
                })
              }
            >
              Escalate
            </Button>
          </div>
        </div>
      ) : null}
    </section>
  );

  if (!mobileOpen) {
    return content;
  }

  return (
    <div className="fixed inset-0 z-40 bg-[#090d1a] p-3 md:hidden">
      {content}
    </div>
  );
}

export default InvestigationWorkspace;
