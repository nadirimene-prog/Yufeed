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
            className="absolute inset-0 bg-black/40"
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
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-orange-50">
                  <ArrowUpRight className="h-4 w-4 text-orange-600" />
                </div>
                <h2 className="text-lg font-semibold text-slate-900">
                  {title}
                </h2>
              </div>
              <button
                onClick={handleClose}
                className="p-1.5 rounded-lg hover:bg-slate-100 transition"
              >
                <X className="h-4 w-4 text-slate-400" />
              </button>
            </div>

            <p className="text-sm text-slate-500 mb-4">
              Link this finding to an existing case for further investigation.
            </p>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                Case ID
              </label>
              <input
                type="text"
                value={caseId}
                onChange={(e) => setCaseId(e.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-orange-500/30 focus:border-orange-500"
                placeholder="Enter case ID (e.g., CASE-001)"
              />
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
                disabled={!caseId.trim()}
                className={cn(
                  "flex-1 text-sm px-4 py-2 rounded-xl text-white transition",
                  caseId.trim()
                    ? "bg-orange-600 hover:bg-orange-700"
                    : "bg-slate-300 cursor-not-allowed",
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
