"use client";

import React from "react";
import { motion } from "framer-motion";
import {
  GitMerge,
  FileSearch,
  ShieldCheck,
  BrainCircuit,
  MessageSquare,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface TimelineEventMetadata {
  source_celex?: string;
  [key: string]: unknown;
}

interface TimelineEvent {
  id: string;
  type: "finding_merged" | "ai_insight" | "decision" | "note" | "escalation";
  title: string;
  description: string;
  timestamp: string;
  metadata?: TimelineEventMetadata;
}

interface CaseTimelineProps {
  events: TimelineEvent[];
}

export function CaseTimeline({ events }: CaseTimelineProps) {
  return (
    <div className="relative space-y-8 pl-8 before:absolute before:left-3 before:top-2 before:bottom-2 before:w-[2px] before:bg-gradient-to-b before:from-aurora-500/40 before:via-cyan-500/40 before:to-transparent">
      {events.map((event, index) => (
        <motion.div
          key={event.id}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: index * 0.1 }}
          className="relative group"
        >
          {/* Connector Dot */}
          <div
            className={cn(
              "absolute -left-[2.35rem] top-1.5 h-4 w-4 rounded-full border-4 border-void-925",
              event.type === "finding_merged" &&
                "bg-cyan-500 shadow-[0_0_8px_rgba(0,212,255,0.6)]",
              event.type === "ai_insight" &&
                "bg-aurora-500 shadow-[0_0_8px_rgba(109,90,205,0.6)]",
              event.type === "decision" &&
                "bg-emerald-500 shadow-[0_0_8px_rgba(6,214,160,0.6)]",
              event.type === "escalation" &&
                "bg-risk-critical shadow-[0_0_8px_rgba(255,51,102,0.6)]",
              event.type === "note" && "bg-white/20",
            )}
          />

          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {event.type === "finding_merged" && (
                  <GitMerge size={14} className="text-cyan-400" />
                )}
                {event.type === "ai_insight" && (
                  <BrainCircuit size={14} className="text-aurora-400" />
                )}
                {event.type === "decision" && (
                  <ShieldCheck size={14} className="text-emerald-400" />
                )}
                {event.type === "note" && (
                  <MessageSquare size={14} className="text-white/40" />
                )}

                <h4 className="text-sm font-semibold text-white/90">
                  {event.title}
                </h4>
              </div>
              <span className="text-[10px] font-mono text-white/30">
                {event.timestamp}
              </span>
            </div>

            <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4 group-hover:bg-white/[0.04] group-hover:border-white/10 transition-all">
              <p className="text-xs text-white/50 leading-relaxed italic">
                {event.description}
              </p>

              {event.metadata?.source_celex && (
                <div className="mt-3 flex items-center gap-2 rounded-lg bg-cyan-500/5 px-2 py-1.5 border border-cyan-500/10">
                  <FileSearch size={12} className="text-cyan-400" />
                  <span className="text-[10px] font-medium text-cyan-400">
                    Reference: {event.metadata.source_celex}
                  </span>
                </div>
              )}
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  );
}

export default CaseTimeline;
