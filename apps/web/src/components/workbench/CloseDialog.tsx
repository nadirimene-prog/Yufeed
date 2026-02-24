"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";
import { modalAnimation, overlayAnimation } from "@/lib/motion";

interface CloseDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (reason: string, comment: string) => void;
  title?: string;
}

const CLOSE_REASONS = [
  { value: "false_positive", label: "False Positive" },
  { value: "no_action_needed", label: "No Action Needed" },
  { value: "duplicate", label: "Duplicate" },
  { value: "resolved", label: "Resolved" },
  { value: "other", label: "Other" },
];

export function CloseDialog({
  open,
  onClose,
  onConfirm,
  title = "Close Finding",
}: CloseDialogProps) {
  const [reason, setReason] = useState("");
  const [comment, setComment] = useState("");

  const handleClose = () => {
    setReason("");
    setComment("");
    onClose();
  };

  const handleSubmit = () => {
    if (!reason) return;
    onConfirm(reason, comment);
    setReason("");
    setComment("");
  };

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* Backdrop */}
          <motion.div
            variants={overlayAnimation}
            initial="initial"
            animate="animate"
            exit="exit"
            onClick={handleClose}
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
          />

          {/* Dialog */}
          <motion.div
            variants={modalAnimation}
            initial="initial"
            animate="animate"
            exit="exit"
            className="relative w-full max-w-md bg-white rounded-2xl shadow-2xl border border-slate-200 p-6"
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
              <button
                onClick={handleClose}
                className="p-1.5 rounded-lg hover:bg-slate-100 transition"
              >
                <X className="h-4 w-4 text-slate-400" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Reason
                </label>
                <div className="flex flex-wrap gap-2">
                  {CLOSE_REASONS.map((r) => (
                    <button
                      key={r.value}
                      onClick={() => setReason(r.value)}
                      className={cn(
                        "text-xs px-3 py-1.5 rounded-full border transition",
                        reason === r.value
                          ? "border-[#0052FF] bg-blue-50 text-[#0052FF]"
                          : "border-slate-200 text-slate-600 hover:border-slate-300",
                      )}
                    >
                      {r.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Comment
                </label>
                <textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  rows={3}
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#0052FF]/30 focus:border-[#0052FF]"
                  placeholder="Optional comment..."
                />
              </div>
            </div>

            <div className="flex gap-2 mt-6">
              <button
                onClick={handleClose}
                className="flex-1 text-sm px-4 py-2 rounded-xl border border-slate-200 text-slate-700 hover:bg-slate-50 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={!reason}
                className={cn(
                  "flex-1 text-sm px-4 py-2 rounded-xl text-white transition",
                  reason
                    ? "bg-[#0052FF] hover:bg-[#0052FF]/90"
                    : "bg-slate-300 cursor-not-allowed",
                )}
              >
                Confirm
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

export default CloseDialog;
