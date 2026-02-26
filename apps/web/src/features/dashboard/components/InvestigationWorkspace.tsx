"use client";

import { useEffect, useMemo, useRef, useState } from "react";
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
import DataFreshnessBadge from "@/features/dashboard/components/DataFreshnessBadge";
import DecisionTraceCard from "@/features/dashboard/components/DecisionTraceCard";
import ReviewGateBanner from "@/features/dashboard/components/ReviewGateBanner";
import ReviewProvenanceCard from "@/features/dashboard/components/ReviewProvenanceCard";
import WorkspaceTabs from "@/features/dashboard/components/WorkspaceTabs";
import {
  readDashboardLocalDraft,
  useDashboardDraftAutosave,
} from "@/features/dashboard/hooks/useDashboardDraftAutosave";
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
  onActionAndNext?: (payload: WorkItemActionRequest) => void;
  onReviewAndNext?: (payload: ReviewActionRequest) => void;
  onSaveDraft: (
    payload: { narrative: string; notes: string },
    options?: { silent?: boolean; source?: "manual" | "autosave" },
  ) => Promise<void>;
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

function formatAutosaveStatusLabel(
  status: "idle" | "saved" | "saving" | "retrying" | "error",
  lastSavedAt: string | null,
) {
  if (status === "saving") return "Saving…";
  if (status === "retrying") return "Retrying autosave…";
  if (status === "error") return "Autosave failed";
  if (status === "saved") {
    if (!lastSavedAt) return "Saved";
    const parsed = new Date(lastSavedAt);
    if (Number.isNaN(parsed.valueOf())) return "Saved";
    return `Saved ${parsed.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`;
  }
  return "Draft changes are local";
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
  onActionAndNext,
  onReviewAndNext,
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
  const [narrativeDirty, setNarrativeDirty] = useState(false);
  const [notesDirty, setNotesDirty] = useState(false);
  const hasLocalDraftForCurrentItemRef = useRef(false);
  const workspaceUsersQuery = useWorkspaceUsers();
  const selectedItemId = selectedItem?.item_id ?? null;
  const selectedItemOwner = selectedItem?.owner ?? "";
  const detailOwner = detail?.work_item.owner ?? "";
  const detailNarrative = detail?.narrative ?? "";

  useEffect(() => {
    const persistedDraft = readDashboardLocalDraft(selectedItemId);
    hasLocalDraftForCurrentItemRef.current = Boolean(persistedDraft);
    let cancelled = false;

    queueMicrotask(() => {
      if (cancelled) return;
      setSubmittedBy("");
      setReviewNotes("");
      setActiveTab("overview");
      setProposedAction("close");
      setSnoozeHours(24);
      setSnoozeReason("");
      setAssignee(selectedItemOwner);
      setNarrativeDraft(persistedDraft?.narrative ?? "");
      setNotes(persistedDraft?.notes ?? "");
      setNarrativeDirty(Boolean(persistedDraft));
      setNotesDirty(Boolean(persistedDraft));
    });

    return () => {
      cancelled = true;
    };
  }, [selectedItemId, selectedItemOwner]);

  useEffect(() => {
    if (!selectedItemId || !detail) return;

    let cancelled = false;
    queueMicrotask(() => {
      if (cancelled) return;
      setAssignee(detailOwner || selectedItemOwner);
      setNarrativeDraft((current) => {
        if (hasLocalDraftForCurrentItemRef.current) return current;
        if (narrativeDirty) return current;
        return detailNarrative;
      });
    });

    return () => {
      cancelled = true;
    };
  }, [
    detail,
    detailNarrative,
    detailOwner,
    selectedItemId,
    selectedItemOwner,
    narrativeDirty,
  ]);

  const draftAutosave = useDashboardDraftAutosave({
    itemId: selectedItem?.item_id ?? null,
    narrative: narrativeDraft,
    notes,
    enabled: Boolean(selectedItem),
    dirty: narrativeDirty || notesDirty,
    onSaveDraft,
    onSaved: () => {
      setNarrativeDirty(false);
      setNotesDirty(false);
    },
  });

  const autosaveStatusLabel = formatAutosaveStatusLabel(
    draftAutosave.status,
    draftAutosave.lastSavedAt,
  );

  const handleTabChange = (nextTab: string) => {
    if ((narrativeDirty || notesDirty) && selectedItem) {
      void draftAutosave.saveNow({
        silent: true,
        source: "autosave",
      });
    }
    setActiveTab(nextTab);
  };

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
    <section
      data-dashboard-workspace-panel
      tabIndex={-1}
      className="flex h-full min-h-0 flex-col rounded-2xl border border-border bg-white p-3 shadow-sm sm:p-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/20"
    >
      <div className="mb-3 flex items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-foreground">
            Investigation Workspace
          </h2>
          <p className="text-xs text-muted-foreground">
            Decision-ready context and controlled actions.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <DataFreshnessBadge
            freshness={detail?.freshness ?? null}
            label="Detail"
            compact
          />
          {mobileOpen && onCloseMobile ? (
            <Button variant="outline" size="sm" onClick={onCloseMobile}>
              Close
            </Button>
          ) : null}
        </div>
      </div>

      {!selectedItem ? (
        <div className="flex flex-1 items-center justify-center rounded-xl border border-dashed border-border bg-slate-50 text-sm text-muted-foreground">
          Select a work item to open context.
        </div>
      ) : loading ? (
        <div
          className="flex flex-1 items-center justify-center rounded-xl text-sm text-muted-foreground bg-slate-50"
          role="status"
        >
          Loading workspace...
        </div>
      ) : error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-600">
          {error}
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col">
          <div className="mb-3 rounded-xl border border-border bg-slate-50 p-3">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <p className="text-sm font-semibold text-foreground">
                {selectedItem.ref_id}
              </p>
              <span
                className={cn(
                  "rounded-full px-2 py-1 text-[10px] uppercase border border-border/50 bg-white",
                  severityBadgeClass(selectedItem.severity),
                )}
              >
                {selectedItem.severity}
              </span>
              <span
                className={cn(
                  "rounded-full px-2 py-1 text-[10px] uppercase border border-border/50 bg-white",
                  slaBadgeClass(selectedItem.sla_status),
                )}
              >
                SLA {selectedItem.sla_status}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-[11px] text-foreground">
              <div className="rounded-lg border border-border bg-white p-2">
                <p className="text-muted-foreground font-medium">Status</p>
                <p>{selectedItem.status}</p>
              </div>
              <div className="rounded-lg border border-border bg-white p-2">
                <p className="text-muted-foreground font-medium">Type</p>
                <p>{selectedItem.type_label}</p>
              </div>
              <div className="rounded-lg border border-border bg-white p-2">
                <p className="text-muted-foreground font-medium">Timer</p>
                <p>{formatAgeMinutes(selectedItem.age_minutes)}</p>
              </div>
              <div className="rounded-lg border border-border bg-white p-2">
                <p className="text-muted-foreground font-medium">Owner</p>
                <p>{selectedItem.owner ?? "Unassigned"}</p>
              </div>
            </div>
          </div>

          {message ? (
            <div
              className={cn(
                "mb-3 rounded-lg border p-2 text-xs",
                message.type === "success"
                  ? "border-green-200 bg-green-50 text-green-700"
                  : "border-red-200 bg-red-50 text-red-600",
              )}
              aria-live="assertive"
            >
              {message.text}
            </div>
          ) : null}

          <WorkspaceTabs
            activeTab={activeTab}
            onTabChange={handleTabChange}
            tabs={[
              {
                id: "overview",
                label: "Overview",
                content: (
                  <div className="rounded-xl border border-border bg-slate-50 p-3">
                    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                      <section>
                        <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-foreground">
                          <Link2 className="h-4 w-4 text-muted-foreground" />
                          Linked Entities
                        </h3>
                        <div className="space-y-1 text-xs text-muted-foreground">
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
                            <p className="text-muted-foreground">
                              No linked entities
                            </p>
                          )}
                        </div>
                      </section>

                      <section className="md:border-l md:border-border md:pl-3">
                        <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-foreground">
                          <ExternalLink className="h-4 w-4 text-muted-foreground" />
                          Linked Transactions
                        </h3>
                        <div className="space-y-1 text-xs text-muted-foreground">
                          {(detail?.linked_transactions ?? []).length > 0 ? (
                            detail?.linked_transactions.map((tx) => (
                              <p key={tx} className="truncate">
                                • {tx}
                              </p>
                            ))
                          ) : (
                            <p className="text-muted-foreground">
                              No linked transactions
                            </p>
                          )}
                        </div>
                      </section>
                    </div>

                    <div className="mt-3 border-t border-border pt-3">
                      <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-foreground">
                        <NotebookPen className="h-4 w-4 text-muted-foreground" />
                        Narrative Draft
                      </h3>
                      <textarea
                        value={narrativeDraft}
                        onChange={(event) => {
                          hasLocalDraftForCurrentItemRef.current = true;
                          setNarrativeDirty(true);
                          setNarrativeDraft(event.target.value);
                        }}
                        className="h-28 w-full rounded-lg border border-border bg-white p-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
                        placeholder="Editable rationale for case notes / SAR narrative"
                      />
                      <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
                        <p
                          className={cn(
                            "text-[11px]",
                            draftAutosave.status === "error"
                              ? "text-red-600"
                              : "text-muted-foreground",
                          )}
                          aria-live="polite"
                        >
                          {autosaveStatusLabel}
                        </p>
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={draftPending}
                          onClick={() => {
                            void draftAutosave.saveNow({
                              source: "manual",
                            });
                          }}
                        >
                          {draftPending ? "Saving..." : "Save Draft"}
                        </Button>
                      </div>
                    </div>

                    <div className="mt-3 border-t border-border pt-3">
                      <DecisionTraceCard
                        trace={detail?.decision_trace ?? null}
                        compact
                      />
                    </div>
                  </div>
                ),
              },
              {
                id: "timeline",
                label: "Timeline",
                content: (
                  <div className="rounded-xl border border-border bg-slate-50 p-3">
                    <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-foreground">
                      <FileClock className="h-4 w-4 text-muted-foreground" />
                      Context Timeline
                    </h3>
                    <div className="space-y-1 text-xs text-foreground">
                      {(detail?.context_timeline ?? []).map((event) => (
                        <div
                          key={`${event.at}-${event.label}`}
                          className="rounded-lg border border-border bg-white p-2"
                        >
                          <p className="font-medium text-foreground">
                            {event.label}
                          </p>
                          <p className="text-muted-foreground">
                            {event.detail ?? "-"}
                          </p>
                          <p className="text-[11px] text-muted-foreground mt-1">
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
                  <div className="rounded-xl border border-border bg-slate-50 p-3">
                    <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-foreground">
                      Evidence Checklist
                    </h3>
                    <div className="space-y-1 text-xs text-muted-foreground">
                      {(detail?.evidence_checklist ?? []).map((item) => (
                        <p key={item.id} className="flex items-center gap-1.5">
                          <ShieldCheck
                            className={cn(
                              "h-3.5 w-3.5",
                              item.completed
                                ? "text-green-600"
                                : "text-muted-foreground/40",
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
                    <div className="rounded-xl border border-border bg-slate-50 p-3 text-xs text-muted-foreground">
                      <p className="mb-1 flex items-center gap-2 text-foreground font-medium">
                        <Sparkles className="h-4 w-4 text-primary" />
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
                    <div className="rounded-xl border border-border bg-slate-50 p-3">
                      <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-foreground">
                        <Clock3 className="h-4 w-4 text-muted-foreground" />
                        Actions
                      </h3>

                      <div className="mb-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                        <div>
                          <label
                            htmlFor="assignee-input"
                            className="mb-1 block text-[11px] text-muted-foreground"
                          >
                            Assignee
                          </label>
                          <input
                            id="assignee-input"
                            data-dashboard-assignee-input
                            value={assignee}
                            onChange={(event) =>
                              setAssignee(event.target.value)
                            }
                            placeholder="Assignee user id"
                            list="workspace-user-list"
                            className="h-9 w-full rounded-lg border border-border bg-white px-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
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
                            className="mb-1 block text-[11px] text-muted-foreground"
                          >
                            Notes
                          </label>
                          <input
                            id="notes-input"
                            value={notes}
                            onChange={(event) => {
                              hasLocalDraftForCurrentItemRef.current = true;
                              setNotesDirty(true);
                              setNotes(event.target.value);
                            }}
                            placeholder="Action notes"
                            className="h-9 w-full rounded-lg border border-border bg-white px-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
                          />
                        </div>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        {actionButtons.map((entry) => {
                          const disabled =
                            actionPending ||
                            (entry.key === "assign" &&
                              assignee.trim().length === 0);
                          const payload = {
                            action: entry.key,
                            assignee:
                              entry.key === "assign" ? assignee : undefined,
                            notes,
                            sar_required: selectedItem.sar_required,
                          } satisfies WorkItemActionRequest;

                          return (
                            <div
                              key={entry.key}
                              className="flex items-center gap-2"
                            >
                              <Button
                                variant="outline"
                                size="sm"
                                data-dashboard-action={entry.key}
                                disabled={disabled}
                                onClick={() => {
                                  if (entry.key === "close")
                                    setProposedAction("close");
                                  if (entry.key === "create_case")
                                    setProposedAction("approve");
                                  onAction(payload);
                                }}
                              >
                                {entry.label}
                              </Button>
                              {onActionAndNext ? (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  data-dashboard-action-next={entry.key}
                                  data-dashboard-action-next-primary={
                                    entry.key === "close" ||
                                    entry.key === "create_case"
                                      ? "true"
                                      : undefined
                                  }
                                  disabled={disabled}
                                  onClick={() => {
                                    if (entry.key === "close")
                                      setProposedAction("close");
                                    if (entry.key === "create_case")
                                      setProposedAction("approve");
                                    onActionAndNext(payload);
                                  }}
                                >
                                  + Next
                                </Button>
                              ) : null}
                            </div>
                          );
                        })}
                      </div>

                      {selectedItem.kind === "alert" && onSnoozeAlert ? (
                        <div className="mt-3 rounded-lg border border-border bg-white p-2">
                          <p className="mb-2 text-[11px] uppercase tracking-wide text-muted-foreground font-medium">
                            Cool-off / Snooze
                          </p>
                          <div className="grid grid-cols-1 gap-2 sm:grid-cols-[120px_1fr_auto]">
                            <select
                              value={String(snoozeHours)}
                              onChange={(event) =>
                                setSnoozeHours(Number(event.target.value))
                              }
                              className="h-9 rounded-lg border border-border bg-slate-50 px-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
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
                              className="h-9 rounded-lg border border-border bg-slate-50 px-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
                            />
                            <Button
                              variant="outline"
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

                    <ReviewProvenanceCard
                      provenance={detail?.review_provenance ?? null}
                    />

                    <DecisionTraceCard trace={detail?.decision_trace ?? null} />

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
                      onApproveAndNext={
                        onReviewAndNext
                          ? () =>
                              onReviewAndNext({
                                proposed_action: proposedAction,
                                decision: "approve",
                                submitted_by: submittedBy,
                                review_notes: reviewNotes,
                                sar_required: selectedItem.sar_required,
                              })
                          : undefined
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
                      onReturnAndNext={
                        onReviewAndNext
                          ? () =>
                              onReviewAndNext({
                                proposed_action: proposedAction,
                                decision: "return",
                                submitted_by: submittedBy,
                                review_notes: reviewNotes,
                                sar_required: selectedItem.sar_required,
                              })
                          : undefined
                      }
                    />

                    <div className="rounded-xl border border-border bg-slate-50 p-3">
                      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-foreground">
                        Action History
                      </h3>
                      <div className="space-y-1 text-xs text-muted-foreground">
                        {(detail?.action_history ?? []).length > 0 ? (
                          detail?.action_history.map((item) => (
                            <p key={`${item.at}-${item.action}`}>
                              <span className="text-muted-foreground/60">
                                {relativeTime(item.at)}:
                              </span>{" "}
                              <span className="font-medium text-foreground">
                                {item.actor}
                              </span>{" "}
                              • {item.action}
                            </p>
                          ))
                        ) : (
                          <p className="text-muted-foreground">
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
                    <div className="rounded-xl border border-border bg-slate-50 p-3 text-xs text-muted-foreground text-center">
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
