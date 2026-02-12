"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, ArrowUpRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { modalAnimation, overlayAnimation } from "@/lib/motion";

interface EscalateDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (caseId: string) => void;
  title?: string;
}

export function EscalateDialog({
  open,
  onClose,
  onConfirm,
  title = "Escalate to Case",
}: EscalateDialogProps) {
  const [caseId, setCaseId] = useState("");

  const handleClose = () => {
    setCaseId("");
    onClose();
  };

  const handleSubmit = () => {
    if (!caseId.trim()) return;
    onConfirm(caseId.trim());
    setCaseId("");
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
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-orange-50 dark:bg-orange-950/30">
                  <ArrowUpRight className="h-4 w-4 text-orange-600 dark:text-orange-400" />
                </div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  {title}
                </h2>
              </div>
              <button
                onClick={handleClose}
                className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition"
              >
                <X className="h-4 w-4 text-gray-400" />
              </button>
            </div>

            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Link this finding to an existing case for further investigation.
            </p>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Case ID
              </label>
              <input
                type="text"
                value={caseId}
                onChange={(e) => setCaseId(e.target.value)}
                className="w-full rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-orange-500/30 focus:border-orange-500"
                placeholder="Enter case ID (e.g., CASE-001)"
              />
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
                disabled={!caseId.trim()}
                className={cn(
                  "flex-1 text-sm px-4 py-2 rounded-xl text-white transition",
                  caseId.trim()
                    ? "bg-orange-600 hover:bg-orange-700"
                    : "bg-gray-300 dark:bg-gray-700 cursor-not-allowed",
                )}
              >
                Escalate
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

export default EscalateDialog;
