"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Eye, EyeOff, Sparkles, FileText, Target, Link2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface LegalSection {
  id: string;
  title: string;
  content: string;
  isObligation: boolean;
  mappings?: string[];
}

interface SpotlightExplorerProps {
  sections: LegalSection[];
  title?: string;
  documentId?: string;
}

export function SpotlightExplorer({
  sections,
  title,
  documentId,
}: SpotlightExplorerProps) {
  const [isFocusMode, setIsFocusMode] = useState(false);
  const [activeSection, setActiveSection] = useState<string | null>(null);

  return (
    <div className="flex flex-col gap-6 rounded-2xl border border-white/10 bg-void-950/20 backdrop-blur-sm p-6">
      <div className="flex items-center justify-between border-b border-white/5 pb-4">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-cyan-500/10 p-2 border border-cyan-500/20">
            <FileText size={18} className="text-cyan-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white/90">
              {title || "Regulatory Document"}
            </h3>
            <p className="text-[10px] text-white/30 font-mono">
              {documentId || "CELEX:32015L0849"}
            </p>
          </div>
        </div>

        <button
          onClick={() => setIsFocusMode(!isFocusMode)}
          className={cn(
            "flex items-center gap-2 rounded-full px-3 py-1.5 transition-all duration-500",
            isFocusMode
              ? "bg-aurora-500 text-white shadow-[0_0_15px_rgba(109,90,205,0.4)]"
              : "bg-white/5 text-white/40 hover:bg-white/10",
          )}
        >
          {isFocusMode ? <Eye size={12} /> : <EyeOff size={12} />}
          <span className="text-[10px] font-bold uppercase tracking-wider">
            {isFocusMode ? "Focus Active" : "Normal Mode"}
          </span>
        </button>
      </div>

      <div className="space-y-4">
        {sections.map((section) => (
          <motion.div
            key={section.id}
            layout
            onMouseEnter={() => setActiveSection(section.id)}
            onMouseLeave={() => setActiveSection(null)}
            className={cn(
              "group relative rounded-xl border p-4 transition-all duration-500",
              isFocusMode && !section.isObligation
                ? "opacity-20 blur-[1px] grayscale"
                : "opacity-100",
              section.isObligation && "border-aurora-500/20 bg-aurora-500/5",
              !section.isObligation &&
                "border-white/5 hover:border-white/10 hover:bg-white/[0.02]",
              activeSection === section.id &&
                section.isObligation &&
                "shadow-[0_0_20px_rgba(109,90,205,0.1)]",
            )}
          >
            {section.isObligation && (
              <div className="absolute -left-2 top-4 flex items-center justify-center">
                <div className="h-4 w-4 rounded-full bg-aurora-500 shadow-[0_0_10px_rgba(109,90,205,0.8)] flex items-center justify-center">
                  <Target size={10} className="text-white" />
                </div>
              </div>
            )}

            <div className="flex items-start justify-between gap-4 mb-2">
              <h4
                className={cn(
                  "text-xs font-bold uppercase tracking-tight",
                  section.isObligation ? "text-aurora-400" : "text-white/40",
                )}
              >
                {section.title}
              </h4>

              {section.isObligation && (
                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-1 rounded-md bg-cyan-400/10 px-1.5 py-0.5 border border-cyan-400/20">
                    <Sparkles size={8} className="text-cyan-400" />
                    <span className="text-[8px] font-bold text-cyan-400 uppercase">
                      AI Detected
                    </span>
                  </div>
                </div>
              )}
            </div>

            <p
              className={cn(
                "text-xs leading-relaxed",
                section.isObligation
                  ? "text-white/80"
                  : "text-white/40 font-light",
              )}
            >
              {section.content}
            </p>

            <AnimatePresence>
              {activeSection === section.id && section.mappings && (
                <motion.div
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 5 }}
                  className="mt-4 flex flex-wrap gap-2 pt-4 border-t border-white/5"
                >
                  <span className="text-[9px] text-white/20 font-mono w-full mb-1 flex items-center gap-1">
                    <Link2 size={10} /> Mapped internal rules:
                  </span>
                  {section.mappings.map((m) => (
                    <span
                      key={m}
                      className="rounded-md bg-white/5 px-2 py-0.5 text-[9px] text-white/50 border border-white/10 hover:border-aurora-500/30 transition-colors cursor-pointer"
                    >
                      {m}
                    </span>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

export default SpotlightExplorer;
