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
    <div className="relative space-y-8 pl-8 before:absolute before:left-3 before:top-2 before:bottom-2 before:w-[2px] before:bg-gradient-to-b before:from-[#0052FF]/40 before:via-[#4D7CFF]/40 before:to-transparent">
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
              "absolute -left-[2.35rem] top-1.5 h-4 w-4 rounded-full border-4 border-white",
              event.type === "finding_merged" && "bg-[#4D7CFF] shadow-sm",
              event.type === "ai_insight" && "bg-[#0052FF] shadow-sm",
              event.type === "decision" && "bg-emerald-500 shadow-sm",
              event.type === "escalation" && "bg-[#DC2626] shadow-sm",
              event.type === "note" && "bg-slate-300",
            )}
          />

          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {event.type === "finding_merged" && (
                  <GitMerge size={14} className="text-[#4D7CFF]" />
                )}
                {event.type === "ai_insight" && (
                  <BrainCircuit size={14} className="text-[#0052FF]" />
                )}
                {event.type === "decision" && (
                  <ShieldCheck size={14} className="text-emerald-500" />
                )}
                {event.type === "note" && (
                  <MessageSquare size={14} className="text-slate-400" />
                )}

                <h4 className="text-sm font-semibold text-slate-900">
                  {event.title}
                </h4>
              </div>
              <span className="text-[10px] font-mono text-slate-400">
                {event.timestamp}
              </span>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-4 group-hover:bg-slate-50 group-hover:border-slate-300 transition-all">
              <p className="text-xs text-slate-500 leading-relaxed italic">
                {event.description}
              </p>

              {event.metadata?.source_celex && (
                <div className="mt-3 flex items-center gap-2 rounded-lg bg-[#0052FF]/5 px-2 py-1.5 border border-[#0052FF]/10">
                  <FileSearch size={12} className="text-[#0052FF]" />
                  <span className="text-[10px] font-medium text-[#0052FF]">
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
