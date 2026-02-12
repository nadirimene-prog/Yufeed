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
            className="relative w-full max-w-md bg-white dark:bg-gray-900 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 p-6"
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {title}
              </h2>
              <button
                onClick={handleClose}
                className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition"
              >
                <X className="h-4 w-4 text-gray-400" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
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
                          ? "border-blue-500 bg-blue-50 text-blue-700 dark:border-blue-400 dark:bg-blue-950/40 dark:text-blue-300"
                          : "border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:border-gray-300 dark:hover:border-gray-600",
                      )}
                    >
                      {r.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  Comment
                </label>
                <textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  rows={3}
                  className="w-full rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500"
                  placeholder="Optional comment..."
                />
              </div>
            </div>

            <div className="flex gap-2 mt-6">
              <button
                onClick={handleClose}
                className="flex-1 text-sm px-4 py-2 rounded-xl border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={!reason}
                className={cn(
                  "flex-1 text-sm px-4 py-2 rounded-xl text-white transition",
                  reason
                    ? "bg-blue-600 hover:bg-blue-700"
                    : "bg-gray-300 dark:bg-gray-700 cursor-not-allowed",
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
