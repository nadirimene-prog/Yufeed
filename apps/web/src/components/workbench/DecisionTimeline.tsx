"use client";

import { motion } from "framer-motion";
import {
  FileEdit,
  Send,
  CheckCircle2,
  XCircle,
  Clock,
  ChevronDown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { staggerContainer, staggerItem } from "@/lib/motion";
import type { CaseDecision } from "@/types/workbench";
import { useState } from "react";

interface DecisionTimelineProps {
  decisions: CaseDecision[];
  onSubmit?: (id: number, rationale: string) => void;
  onApprove?: (id: number) => void;
  onReject?: (id: number) => void;
}

const statusIcons = {
  draft: FileEdit,
  submitted: Send,
  approved: CheckCircle2,
  rejected: XCircle,
} as const;

const statusStyles = {
  draft: {
    ring: "ring-gray-300 dark:ring-gray-600",
    bg: "bg-gray-100 dark:bg-gray-800",
    text: "text-gray-600 dark:text-gray-400",
  },
  submitted: {
    ring: "ring-blue-300 dark:ring-blue-700",
    bg: "bg-blue-50 dark:bg-blue-950/40",
    text: "text-blue-600 dark:text-blue-400",
  },
  approved: {
    ring: "ring-emerald-300 dark:ring-emerald-700",
    bg: "bg-emerald-50 dark:bg-emerald-950/40",
    text: "text-emerald-600 dark:text-emerald-400",
  },
  rejected: {
    ring: "ring-red-300 dark:ring-red-700",
    bg: "bg-red-50 dark:bg-red-950/40",
    text: "text-red-600 dark:text-red-400",
  },
} as const;

const dispositionLabels: Record<string, string> = {
  escalate: "Escalate",
  close_no_action: "Close — No Action",
  close_with_sar: "Close — SAR Filed",
  refer_external: "Refer External",
};

export function DecisionTimeline({
  decisions,
  onSubmit,
  onApprove,
  onReject,
}: DecisionTimelineProps) {
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [submitRationale, setSubmitRationale] = useState<
    Record<number, string>
  >({});

  if (decisions.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400 dark:text-gray-500">
        <FileEdit className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No decisions yet</p>
      </div>
    );
  }

  return (
    <motion.div
      variants={staggerContainer}
      initial="initial"
      animate="animate"
      className="relative"
    >
      {/* Vertical line */}
      <div className="absolute left-5 top-0 bottom-0 w-px bg-gray-200 dark:bg-gray-700" />

      <div className="space-y-4">
        {decisions.map((decision) => {
          const Icon = statusIcons[decision.status] ?? Clock;
          const style = statusStyles[decision.status] ?? statusStyles.draft;
          const isExpanded = expandedId === decision.id;

          return (
            <motion.div
              key={decision.id}
              variants={staggerItem}
              className="relative pl-12"
            >
              {/* Timeline dot */}
              <div
                className={cn(
                  "absolute left-3 top-3 h-5 w-5 rounded-full ring-2 flex items-center justify-center",
                  style.ring,
                  style.bg,
                )}
              >
                <Icon className={cn("h-3 w-3", style.text)} />
              </div>

              {/* Card */}
              <div
                className={cn(
                  "rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/60 p-4",
                  "transition-colors",
                )}
              >
                <div className="flex items-start justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={cn(
                          "text-xs font-medium px-2 py-0.5 rounded-full",
                          style.bg,
                          style.text,
                        )}
                      >
                        {decision.status.toUpperCase()}
                      </span>
                      <span className="text-xs text-gray-400 dark:text-gray-500">
                        v{decision.version}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {dispositionLabels[decision.disposition] ??
                        decision.disposition}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      by {decision.created_by} ·{" "}
                      {new Date(decision.created_at).toLocaleDateString()}
                    </p>
                  </div>

                  <button
                    onClick={() =>
                      setExpandedId(isExpanded ? null : decision.id)
                    }
                    className="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition"
                  >
                    <ChevronDown
                      className={cn(
                        "h-4 w-4 text-gray-400 transition-transform",
                        isExpanded && "rotate-180",
                      )}
                    />
                  </button>
                </div>

                {isExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-800"
                  >
                    <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                      {decision.rationale}
                    </p>

                    {decision.approver_id && (
                      <p className="text-xs text-gray-400 mt-2">
                        Approved by {decision.approver_id} on{" "}
                        {decision.approved_at
                          ? new Date(decision.approved_at).toLocaleDateString()
                          : "—"}
                      </p>
                    )}

                    {decision.rejection_reason && (
                      <div className="mt-2 p-2 rounded-lg bg-red-50 dark:bg-red-950/20 text-sm text-red-700 dark:text-red-400">
                        Rejection: {decision.rejection_reason}
                      </div>
                    )}

                    {/* Action buttons */}
                    <div className="space-y-2 mt-3">
                      {decision.status === "draft" && onSubmit && (
                        <div className="space-y-2">
                          <textarea
                            value={
                              submitRationale[decision.id] ??
                              decision.rationale ??
                              ""
                            }
                            onChange={(e) =>
                              setSubmitRationale((prev) => ({
                                ...prev,
                                [decision.id]: e.target.value,
                              }))
                            }
                            rows={2}
                            className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-3 py-2 text-xs text-gray-900 dark:text-white placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
                            placeholder="Rationale for submission (min 10 chars)…"
                          />
                          <button
                            onClick={() => {
                              const rationale =
                                submitRationale[decision.id] ??
                                decision.rationale ??
                                "";
                              if (rationale.trim().length >= 10) {
                                onSubmit(decision.id, rationale.trim());
                              }
                            }}
                            disabled={
                              (
                                submitRationale[decision.id] ??
                                decision.rationale ??
                                ""
                              ).trim().length < 10
                            }
                            className={cn(
                              "text-xs px-3 py-1.5 rounded-lg text-white transition",
                              (
                                submitRationale[decision.id] ??
                                decision.rationale ??
                                ""
                              ).trim().length >= 10
                                ? "bg-blue-600 hover:bg-blue-700"
                                : "bg-gray-300 dark:bg-gray-700 cursor-not-allowed",
                            )}
                          >
                            Submit for Approval
                          </button>
                        </div>
                      )}
                      {decision.status === "submitted" &&
                        (onApprove || onReject) && (
                          <div className="flex gap-2">
                            {onApprove && (
                              <button
                                onClick={() => onApprove(decision.id)}
                                className="text-xs px-3 py-1.5 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 transition"
                              >
                                Approve
                              </button>
                            )}
                            {onReject && (
                              <button
                                onClick={() => onReject(decision.id)}
                                className="text-xs px-3 py-1.5 rounded-lg bg-red-600 text-white hover:bg-red-700 transition"
                              >
                                Reject
                              </button>
                            )}
                          </div>
                        )}
                    </div>
                  </motion.div>
                )}
              </div>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}

export default DecisionTimeline;
