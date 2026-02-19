"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import {
  Clock3,
  ExternalLink,
  FileClock,
  Link2,
  NotebookPen,
  ShieldCheck,
  Sparkles,
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
import WorkspaceTabs from "@/features/dashboard/components/WorkspaceTabs";
import { cn } from "@/lib/utils";
import { useWorkspaceUsers } from "@/hooks/queries/useSpecializedData";
import CaseComments from "@/components/workbench/CaseComments";

interface InvestigationWorkspaceProps {
  selectedItem: DashboardWorkQueueItem | null;
  detail: WorkItemDetailResponse | null;
  loading?: boolean;
  error?: string | null;
  message?: { text: string; type: "success" | "error" } | null;
  actionPending?: boolean;
  reviewPending?: boolean;
  draftPending?: boolean;
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
  currentUserId?: string | null;
  onAction: (payload: WorkItemActionRequest) => void;
  onReview: (payload: ReviewActionRequest) => void;
  onSaveDraft: (payload: { narrative: string; notes: string }) => void;
  onSnoozeAlert?: (payload: { durationHours: number; reason?: string }) => void;
}

function formatDateTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  return date.toLocaleString();
}

function relativeTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  const diffMs = Date.now() - date.getTime();
  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function InvestigationWorkspace({
  selectedItem,
  detail,
  loading = false,
  error = null,
  message = null,
  actionPending = false,
  reviewPending = false,
  draftPending = false,
  mobileOpen = false,
  onCloseMobile,
  currentUserId,
  onAction,
  onReview,
  onSaveDraft,
  onSnoozeAlert,
}: InvestigationWorkspaceProps) {
  const [notes, setNotes] = useState("");
  const [assignee, setAssignee] = useState(detail?.work_item.owner ?? "");
  const [narrativeDraft, setNarrativeDraft] = useState(detail?.narrative ?? "");
  const [submittedBy, setSubmittedBy] = useState("");
  const [reviewNotes, setReviewNotes] = useState("");
  const [activeTab, setActiveTab] = useState("overview");
  const [proposedAction, setProposedAction] = useState<"close" | "approve">(
    "close",
  );
  const [snoozeHours, setSnoozeHours] = useState(24);
  const [snoozeReason, setSnoozeReason] = useState("");
  const workspaceUsersQuery = useWorkspaceUsers();

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
    <section className="glass-surface flex h-full min-h-0 flex-col rounded-2xl border border-white/10 p-3 sm:p-4">
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
        <div
          className="flex flex-1 items-center justify-center text-sm text-white/60"
          role="status"
        >
          Loading workspace...
        </div>
      ) : error ? (
        <div className="rounded-xl border border-risk-critical/40 bg-risk-critical-soft p-3 text-sm text-risk-critical">
          {error}
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col">
          <div className="mb-3 rounded-xl border border-white/10 bg-white/5 p-3">
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

          {message ? (
            <div
              className={cn(
                "mb-3 rounded-lg border p-2 text-xs",
                message.type === "success"
                  ? "border-risk-clear/40 bg-risk-clear-soft text-risk-clear"
                  : "border-risk-critical/40 bg-risk-critical-soft text-risk-critical",
              )}
              aria-live="assertive"
            >
              {message.text}
            </div>
          ) : null}

          <WorkspaceTabs
            activeTab={activeTab}
            onTabChange={setActiveTab}
            tabs={[
              {
                id: "overview",
                label: "Overview",
                content: (
                  <div className="space-y-3">
                    <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                      <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                        <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-white/70">
                          <Link2 className="h-4 w-4" />
                          Linked Entities
                        </h3>
                        <div className="space-y-1 text-xs text-white/75">
                          {(detail?.linked_entities ?? []).length > 0 ? (
                            detail?.linked_entities.map((entity) => (
                              <Link
                                key={entity}
                                href={`/entities/user/${entity}`}
                                className="block truncate text-primary hover:underline"
                              >
                                • {entity}
                              </Link>
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
                            <p className="text-white/50">
                              No linked transactions
                            </p>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                      <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-white/70">
                        <NotebookPen className="h-4 w-4" />
                        Narrative Draft
                      </h3>
                      <textarea
                        value={narrativeDraft}
                        onChange={(event) =>
                          setNarrativeDraft(event.target.value)
                        }
                        className="h-28 w-full rounded-lg border border-white/10 bg-black/20 p-2 text-xs text-white placeholder:text-white/40"
                        placeholder="Editable rationale for case notes / SAR narrative"
                      />
                      <div className="mt-2 flex justify-end">
                        <Button
                          variant="glass"
                          size="sm"
                          disabled={draftPending}
                          onClick={() =>
                            onSaveDraft({ narrative: narrativeDraft, notes })
                          }
                        >
                          {draftPending ? "Saving..." : "Save Draft"}
                        </Button>
                      </div>
                    </div>
                  </div>
                ),
              },
              {
                id: "timeline",
                label: "Timeline",
                content: (
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
                          <p className="font-medium text-white">
                            {event.label}
                          </p>
                          <p>{event.detail ?? "-"}</p>
                          <p className="text-[11px] text-white/50">
                            {formatDateTime(event.at)}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                ),
              },
              {
                id: "evidence",
                label: "Evidence",
                content: (
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
                              item.completed
                                ? "text-risk-clear"
                                : "text-white/40",
                            )}
                          />
                          {item.label}
                        </p>
                      ))}
                    </div>
                  </div>
                ),
              },
              {
                id: "ai",
                label: "AI Analysis",
                content: (
                  <div className="space-y-3">
                    <AiRecommendationCard
                      recommendation={detail?.ai_recommendation ?? null}
                    />
                    <div className="rounded-xl border border-white/10 bg-white/5 p-3 text-xs text-white/70">
                      <p className="mb-1 flex items-center gap-2 text-white/80">
                        <Sparkles className="h-4 w-4" />
                        AI recommendation rationale
                      </p>
                      <p>
                        Use the Actions tab to execute disposition decisions
                        with review controls.
                      </p>
                    </div>
                  </div>
                ),
              },
              {
                id: "actions",
                label: "Actions",
                content: (
                  <div className="space-y-3">
                    <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                      <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-white/70">
                        <Clock3 className="h-4 w-4" />
                        Actions
                      </h3>

                      <div className="mb-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                        <div>
                          <label
                            htmlFor="assignee-input"
                            className="mb-1 block text-[11px] text-white/60"
                          >
                            Assignee
                          </label>
                          <input
                            id="assignee-input"
                            value={assignee}
                            onChange={(event) =>
                              setAssignee(event.target.value)
                            }
                            placeholder="Assignee user id"
                            list="workspace-user-list"
                            className="h-9 w-full rounded-lg border border-white/10 bg-black/20 px-2 text-xs text-white placeholder:text-white/40"
                          />
                          <datalist id="workspace-user-list">
                            {(workspaceUsersQuery.data ?? []).map((user) => (
                              <option key={user.user_id} value={user.user_id}>
                                {user.user_id}
                              </option>
                            ))}
                          </datalist>
                        </div>
                        <div>
                          <label
                            htmlFor="notes-input"
                            className="mb-1 block text-[11px] text-white/60"
                          >
                            Notes
                          </label>
                          <input
                            id="notes-input"
                            value={notes}
                            onChange={(event) => setNotes(event.target.value)}
                            placeholder="Action notes"
                            className="h-9 w-full rounded-lg border border-white/10 bg-black/20 px-2 text-xs text-white placeholder:text-white/40"
                          />
                        </div>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        {actionButtons.map((entry) => (
                          <Button
                            key={entry.key}
                            variant="glass"
                            size="sm"
                            disabled={
                              actionPending ||
                              (entry.key === "assign" &&
                                assignee.trim().length === 0)
                            }
                            onClick={() => {
                              if (entry.key === "close")
                                setProposedAction("close");
                              if (entry.key === "create_case")
                                setProposedAction("approve");
                              onAction({
                                action: entry.key,
                                assignee:
                                  entry.key === "assign" ? assignee : undefined,
                                notes,
                                sar_required: selectedItem.sar_required,
                              });
                            }}
                          >
                            {entry.label}
                          </Button>
                        ))}
                      </div>

                      {selectedItem.kind === "alert" && onSnoozeAlert ? (
                        <div className="mt-3 rounded-lg border border-white/10 bg-black/20 p-2">
                          <p className="mb-2 text-[11px] uppercase tracking-wide text-white/60">
                            Cool-off / Snooze
                          </p>
                          <div className="grid grid-cols-1 gap-2 sm:grid-cols-[120px_1fr_auto]">
                            <select
                              value={String(snoozeHours)}
                              onChange={(event) =>
                                setSnoozeHours(Number(event.target.value))
                              }
                              className="h-9 rounded-lg border border-white/10 bg-black/20 px-2 text-xs text-white"
                              aria-label="Snooze duration"
                            >
                              <option value="1">1 hour</option>
                              <option value="4">4 hours</option>
                              <option value="24">24 hours</option>
                              <option value="168">7 days</option>
                            </select>
                            <input
                              value={snoozeReason}
                              onChange={(event) =>
                                setSnoozeReason(event.target.value)
                              }
                              placeholder="Reason (optional)"
                              className="h-9 rounded-lg border border-white/10 bg-black/20 px-2 text-xs text-white placeholder:text-white/40"
                            />
                            <Button
                              variant="glass"
                              size="sm"
                              onClick={() =>
                                onSnoozeAlert({
                                  durationHours: snoozeHours,
                                  reason: snoozeReason.trim() || undefined,
                                })
                              }
                            >
                              Snooze
                            </Button>
                          </div>
                        </div>
                      ) : null}
                    </div>

                    <ReviewGateBanner
                      requirement={detail?.review_requirement ?? null}
                      submittedBy={submittedBy}
                      reviewNotes={reviewNotes}
                      proposedAction={proposedAction}
                      currentUserId={currentUserId}
                      pending={reviewPending}
                      onSubmittedByChange={setSubmittedBy}
                      onReviewNotesChange={setReviewNotes}
                      onApprove={() =>
                        onReview({
                          proposed_action: proposedAction,
                          decision: "approve",
                          submitted_by: submittedBy,
                          review_notes: reviewNotes,
                          sar_required: selectedItem.sar_required,
                        })
                      }
                      onReturn={() =>
                        onReview({
                          proposed_action: proposedAction,
                          decision: "return",
                          submitted_by: submittedBy,
                          review_notes: reviewNotes,
                          sar_required: selectedItem.sar_required,
                        })
                      }
                    />

                    <div className="rounded-xl border border-white/10 bg-white/5 p-3">
                      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-white/70">
                        Action History
                      </h3>
                      <div className="space-y-1 text-xs text-white/75">
                        {(detail?.action_history ?? []).length > 0 ? (
                          detail?.action_history.map((item) => (
                            <p key={`${item.at}-${item.action}`}>
                              <span className="text-white/50">
                                {relativeTime(item.at)}:
                              </span>{" "}
                              {item.actor} • {item.action}
                            </p>
                          ))
                        ) : (
                          <p className="text-white/50">
                            No actions recorded yet.
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ),
              },
              {
                id: "comments",
                label: "Comments",
                content:
                  selectedItem.kind === "case" ? (
                    <CaseComments caseId={selectedItem.ref_id} />
                  ) : (
                    <div className="rounded-xl border border-white/10 bg-white/5 p-3 text-xs text-white/60">
                      Comments are available for case work items.
                    </div>
                  ),
              },
            ]}
          />
        </div>
      )}
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
