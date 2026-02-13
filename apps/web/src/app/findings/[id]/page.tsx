"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Shield,
  Clock,
  User,
  CheckCircle2,
  XCircle,
  ArrowUpRight,
  Eye,
  Brain,
} from "lucide-react";
import {
  useFinding,
  useCloseFinding,
  useEscalateFinding,
  useAcknowledgeFinding,
} from "@/hooks/queries/useWorkbenchData";
import { CloseDialog } from "@/components/workbench/CloseDialog";
import { EscalateDialog } from "@/components/workbench/EscalateDialog";
import { fadeInBlur } from "@/lib/motion";
import { cn } from "@/lib/utils";

const severityConfig = {
  critical: {
    color: "text-red-600 dark:text-red-400",
    bg: "bg-red-50 dark:bg-red-950/30",
    border: "border-red-200 dark:border-red-800",
  },
  high: {
    color: "text-orange-600 dark:text-orange-400",
    bg: "bg-orange-50 dark:bg-orange-950/30",
    border: "border-orange-200 dark:border-orange-800",
  },
  medium: {
    color: "text-amber-600 dark:text-amber-400",
    bg: "bg-amber-50 dark:bg-amber-950/30",
    border: "border-amber-200 dark:border-amber-800",
  },
  low: {
    color: "text-blue-600 dark:text-blue-400",
    bg: "bg-blue-50 dark:bg-blue-950/30",
    border: "border-blue-200 dark:border-blue-800",
  },
  info: {
    color: "text-gray-600 dark:text-gray-400",
    bg: "bg-gray-50 dark:bg-gray-800",
    border: "border-gray-200 dark:border-gray-700",
  },
} as const;

const statusLabels: Record<string, string> = {
  open: "Open",
  acknowledged: "Acknowledged",
  escalated: "Escalated",
  closed: "Closed",
};

export default function FindingDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const findingId = Number(params.id);

  const { data: finding, isLoading } = useFinding(findingId);
  const closeMutation = useCloseFinding();
  const escalateMutation = useEscalateFinding();
  const acknowledgeMutation = useAcknowledgeFinding();

  const [closeDialogOpen, setCloseDialogOpen] = useState(false);
  const [escalateDialogOpen, setEscalateDialogOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="h-8 w-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Loading finding…
          </p>
        </div>
      </div>
    );
  }

  if (!finding) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <XCircle className="h-12 w-12 mx-auto mb-3 text-red-400" />
          <p className="text-sm font-medium text-gray-900 dark:text-white">
            Finding not found
          </p>
        </div>
      </div>
    );
  }

  const severity = severityConfig[finding.severity] ?? severityConfig.info;
  const isActionable = finding.status !== "closed";

  return (
    <>
      <motion.div
        variants={fadeInBlur}
        initial="initial"
        animate="animate"
        className="space-y-6"
      >
        {/* Back button */}
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Findings
        </button>

        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span
                className={cn(
                  "text-xs font-semibold px-2.5 py-1 rounded-full border",
                  severity.bg,
                  severity.color,
                  severity.border,
                )}
              >
                {finding.severity.toUpperCase()}
              </span>
              <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
                {statusLabels[finding.status] ?? finding.status}
              </span>
              <span className="text-xs text-gray-400 dark:text-gray-500 font-mono">
                {finding.fingerprint}
              </span>
            </div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white tracking-tight">
              {finding.title}
            </h1>
          </div>

          {/* Action buttons */}
          {isActionable && (
            <div className="flex gap-2 shrink-0">
              {finding.status === "open" && (
                <button
                  onClick={() => acknowledgeMutation.mutate(finding.id)}
                  className="text-xs px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition flex items-center gap-1"
                >
                  <Eye className="h-3 w-3" />
                  Acknowledge
                </button>
              )}
              <button
                onClick={() => setEscalateDialogOpen(true)}
                className="text-xs px-3 py-1.5 rounded-lg bg-orange-600 text-white hover:bg-orange-700 transition flex items-center gap-1"
              >
                <ArrowUpRight className="h-3 w-3" />
                Escalate
              </button>
              <button
                onClick={() => setCloseDialogOpen(true)}
                className="text-xs px-3 py-1.5 rounded-lg bg-gray-800 dark:bg-gray-200 text-white dark:text-gray-900 hover:bg-gray-900 dark:hover:bg-gray-100 transition flex items-center gap-1"
              >
                <CheckCircle2 className="h-3 w-3" />
                Close
              </button>
            </div>
          )}
        </div>

        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Summary */}
            <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/60 p-5">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
                Summary
              </h2>
              <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                {finding.summary}
              </p>
            </div>

            {/* Explainability */}
            {Object.keys(finding.explainability).length > 0 && (
              <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/60 p-5">
                <div className="flex items-center gap-2 mb-3">
                  <Brain className="h-4 w-4 text-violet-500" />
                  <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
                    AI Explainability
                  </h2>
                </div>
                <pre className="text-xs text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-800 rounded-lg p-3 overflow-x-auto">
                  {JSON.stringify(finding.explainability, null, 2)}
                </pre>
              </div>
            )}

            {/* Source References */}
            {Object.keys(finding.source_refs).length > 0 && (
              <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/60 p-5">
                <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
                  Source References
                </h2>
                <pre className="text-xs text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-800 rounded-lg p-3 overflow-x-auto">
                  {JSON.stringify(finding.source_refs, null, 2)}
                </pre>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            {/* Metadata card */}
            <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/60 p-5 space-y-3">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                Details
              </h3>

              <div className="space-y-2.5">
                <div className="flex items-center gap-2 text-sm">
                  <Shield className="h-3.5 w-3.5 text-gray-400" />
                  <span className="text-gray-500 dark:text-gray-400">Type</span>
                  <span className="ml-auto font-medium text-gray-900 dark:text-white">
                    {finding.finding_type.toUpperCase()}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <Clock className="h-3.5 w-3.5 text-gray-400" />
                  <span className="text-gray-500 dark:text-gray-400">
                    Created
                  </span>
                  <span className="ml-auto text-gray-900 dark:text-white">
                    {new Date(finding.created_at).toLocaleDateString()}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <Clock className="h-3.5 w-3.5 text-gray-400" />
                  <span className="text-gray-500 dark:text-gray-400">
                    Updated
                  </span>
                  <span className="ml-auto text-gray-900 dark:text-white">
                    {new Date(finding.updated_at).toLocaleDateString()}
                  </span>
                </div>
                {finding.assigned_to != null &&
                  finding.assigned_to.length > 0 && (
                    <div className="flex items-center gap-2 text-sm">
                      <User className="h-3.5 w-3.5 text-gray-400" />
                      <span className="text-gray-500 dark:text-gray-400">
                        Assigned
                      </span>
                      <span className="ml-auto text-gray-900 dark:text-white">
                        {finding.assigned_to}
                      </span>
                    </div>
                  )}
                {finding.sla_due_at != null &&
                  finding.sla_due_at.length > 0 && (
                    <div className="flex items-center gap-2 text-sm">
                      <Clock className="h-3.5 w-3.5 text-gray-400" />
                      <span className="text-gray-500 dark:text-gray-400">
                        SLA Due
                      </span>
                      <span
                        className={cn(
                          "ml-auto font-medium",
                          new Date(finding.sla_due_at) < new Date()
                            ? "text-red-600 dark:text-red-400"
                            : "text-gray-900 dark:text-white",
                        )}
                      >
                        {new Date(finding.sla_due_at).toLocaleDateString()}
                      </span>
                    </div>
                  )}
              </div>
            </div>

            {/* Closed info */}
            {finding.status === "closed" && (
              <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 p-5 space-y-2">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                  Closure Details
                </h3>
                {finding.closed_reason != null &&
                  finding.closed_reason.length > 0 && (
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      <span className="font-medium">Reason:</span>{" "}
                      {finding.closed_reason.replace(/_/g, " ")}
                    </p>
                  )}
                {finding.closed_comment != null &&
                  finding.closed_comment.length > 0 && (
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {finding.closed_comment}
                    </p>
                  )}
              </div>
            )}
          </div>
        </div>
      </motion.div>

      {/* Dialogs */}
      <CloseDialog
        open={closeDialogOpen}
        onClose={() => setCloseDialogOpen(false)}
        onConfirm={(reason, comment) => {
          closeMutation.mutate(
            { id: finding.id, reason, comment },
            { onSuccess: () => setCloseDialogOpen(false) },
          );
        }}
      />
      <EscalateDialog
        open={escalateDialogOpen}
        onClose={() => setEscalateDialogOpen(false)}
        onConfirm={(caseId) => {
          escalateMutation.mutate(
            { id: finding.id, case_id: caseId },
            { onSuccess: () => setEscalateDialogOpen(false) },
          );
        }}
      />
    </>
  );
}
