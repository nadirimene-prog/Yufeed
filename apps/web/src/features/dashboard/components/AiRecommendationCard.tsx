"use client";

import { Bot, FileText, Gauge } from "lucide-react";
import { cn } from "@/lib/utils";
import { WorkItemAiRecommendation } from "@/features/dashboard/types";

interface AiRecommendationCardProps {
  recommendation: WorkItemAiRecommendation | null;
  className?: string;
}

export function AiRecommendationCard({
  recommendation,
  className,
}: AiRecommendationCardProps) {
  if (!recommendation) {
    return (
      <div
        className={cn(
          "rounded-xl border border-white/10 bg-white/5 p-3",
          className,
        )}
      >
        <p className="text-xs text-white/60">No AI recommendation available.</p>
      </div>
    );
  }

  const confidence = Math.round(
    Math.max(0, Math.min(1, recommendation.confidence)) * 100,
  );

  return (
    <section
      className={cn(
        "rounded-xl border border-white/10 bg-white/5 p-3",
        className,
      )}
    >
      <div className="mb-2 flex items-center justify-between">
        <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-aurora-300">
          <Bot className="h-4 w-4" />
          AI Recommendation
        </h3>
        <span className="inline-flex items-center gap-1 rounded-full border border-aurora-500/30 bg-aurora-500/10 px-2 py-1 text-[10px] text-aurora-200">
          <Gauge className="h-3 w-3" />
          {confidence}% confidence
        </span>
      </div>

      <p className="mb-3 text-sm text-white/90">{recommendation.summary}</p>

      <div className="space-y-1">
        <p className="text-[10px] uppercase tracking-wide text-white/50">
          Rationale
        </p>
        <ul className="space-y-1 text-xs text-white/75">
          {recommendation.rationale.map((reason) => (
            <li key={reason} className="flex items-start gap-1.5">
              <FileText className="mt-0.5 h-3.5 w-3.5 shrink-0 text-white/40" />
              <span>{reason.replaceAll("_", " ")}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

export default AiRecommendationCard;
