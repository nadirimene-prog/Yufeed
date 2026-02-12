"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowLeft, Plus, Gavel } from "lucide-react";
import {
  useCaseDecisions,
  useCreateDecision,
  useSubmitDecision,
  useApproveDecision,
  useRejectDecision,
} from "@/hooks/queries/useWorkbenchData";
import { DecisionTimeline } from "@/components/workbench/DecisionTimeline";
import { fadeInBlur, modalAnimation, overlayAnimation } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { AnimatePresence } from "framer-motion";
import { X } from "lucide-react";

export default function CaseDecisionsPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const caseId = params.id;

  const { data: decisions = [], isLoading } = useCaseDecisions(caseId);
  const createMutation = useCreateDecision(caseId);
  const submitMutation = useSubmitDecision(caseId);
  const approveMutation = useApproveDecision(caseId);
  const rejectMutation = useRejectDecision(caseId);

  const [showCreate, setShowCreate] = useState(false);
  const [newDisposition, setNewDisposition] = useState("escalate");
  const [newRationale, setNewRationale] = useState("");
  const [rejectDialog, setRejectDialog] = useState<number | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  const handleCreate = () => {
    if (!newRationale.trim()) return;
    createMutation.mutate(
      { disposition: newDisposition, rationale: newRationale },
      {
        onSuccess: () => {
          setShowCreate(false);
          setNewRationale("");
        },
      },
    );
  };

  const handleReject = () => {
    if (rejectDialog === null || !rejectReason.trim()) return;
    rejectMutation.mutate(
      { decisionId: rejectDialog, reason: rejectReason },
      {
        onSuccess: () => {
          setRejectDialog(null);
          setRejectReason("");
        },
      },
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="h-8 w-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <>
      <motion.div
        variants={fadeInBlur}
        initial="initial"
        animate="animate"
        className="space-y-6"
      >
        {/* Header */}
        <div>
          <button
            onClick={() => router.push(`/cases/${caseId}`)}
            className="flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition mb-4"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Case {caseId}
          </button>

          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight flex items-center gap-2">
                <Gavel className="h-5 w-5 text-violet-500" />
                Decisions
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                4-eyes governance: decisions require separate approval.
              </p>
            </div>

            <button
              onClick={() => setShowCreate(true)}
              className="text-sm px-4 py-2 rounded-xl bg-violet-600 text-white hover:bg-violet-700 transition flex items-center gap-1.5"
            >
              <Plus className="h-4 w-4" />
              New Decision
            </button>
          </div>
        </div>

        {/* Timeline */}
        <DecisionTimeline
          decisions={decisions}
          onSubmit={(id) => submitMutation.mutate(id)}
          onApprove={(id) => approveMutation.mutate(id)}
          onReject={(id) => {
            setRejectDialog(id);
            setRejectReason("");
          }}
        />
      </motion.div>

      {/* Create Decision Dialog */}
      <AnimatePresence>
        {showCreate && (
          <div className="fixed inset-0 z-50 flex items-center justify-center">
            <motion.div
              variants={overlayAnimation}
              initial="initial"
              animate="animate"
              exit="exit"
              onClick={() => setShowCreate(false)}
              className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            />
            <motion.div
              variants={modalAnimation}
              initial="initial"
              animate="animate"
              exit="exit"
              className="relative w-full max-w-lg bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 p-6"
            >
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  New Decision
                </h2>
                <button
                  onClick={() => setShowCreate(false)}
                  className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition"
                >
                  <X className="h-4 w-4 text-gray-400" />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                    Disposition
                  </label>
                  <select
                    value={newDisposition}
                    onChange={(e) => setNewDisposition(e.target.value)}
                    className="w-full rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/30 text-gray-900 dark:text-white"
                  >
                    <option value="escalate">Escalate</option>
                    <option value="close_no_action">Close — No Action</option>
                    <option value="close_with_sar">Close — SAR Filed</option>
                    <option value="refer_external">Refer External</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                    Rationale
                  </label>
                  <textarea
                    value={newRationale}
                    onChange={(e) => setNewRationale(e.target.value)}
                    rows={4}
                    className="w-full rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-violet-500/30"
                    placeholder="Explain the rationale for this decision…"
                  />
                </div>
              </div>

              <div className="flex gap-2 mt-6">
                <button
                  onClick={() => setShowCreate(false)}
                  className="flex-1 text-sm px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreate}
                  disabled={!newRationale.trim()}
                  className={cn(
                    "flex-1 text-sm px-4 py-2 rounded-xl text-white transition",
                    newRationale.trim()
                      ? "bg-violet-600 hover:bg-violet-700"
                      : "bg-gray-300 dark:bg-gray-700 cursor-not-allowed",
                  )}
                >
                  Create Draft
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Reject Decision Dialog */}
      <AnimatePresence>
        {rejectDialog !== null && (
          <div className="fixed inset-0 z-50 flex items-center justify-center">
            <motion.div
              variants={overlayAnimation}
              initial="initial"
              animate="animate"
              exit="exit"
              onClick={() => setRejectDialog(null)}
              className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            />
            <motion.div
              variants={modalAnimation}
              initial="initial"
              animate="animate"
              exit="exit"
              className="relative w-full max-w-md bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 p-6"
            >
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Reject Decision
              </h2>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                rows={3}
                className="w-full rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-red-500/30"
                placeholder="Reason for rejection…"
              />
              <div className="flex gap-2 mt-4">
                <button
                  onClick={() => setRejectDialog(null)}
                  className="flex-1 text-sm px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
                >
                  Cancel
                </button>
                <button
                  onClick={handleReject}
                  disabled={!rejectReason.trim()}
                  className={cn(
                    "flex-1 text-sm px-4 py-2 rounded-xl text-white transition",
                    rejectReason.trim()
                      ? "bg-red-600 hover:bg-red-700"
                      : "bg-gray-300 dark:bg-gray-700 cursor-not-allowed",
                  )}
                >
                  Reject
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
}
