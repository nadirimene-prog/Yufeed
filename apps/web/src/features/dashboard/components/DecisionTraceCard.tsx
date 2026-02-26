"use client";

import { Brain, FileText, Gavel } from "lucide-react";
import { DecisionTrace } from "@/features/dashboard/types";

interface DecisionTraceCardProps {
  trace?: DecisionTrace | null;
  compact?: boolean;
  className?: string;
}

export function DecisionTraceCard({
  trace = null,
  compact = false,
  className,
}: DecisionTraceCardProps) {
  return (
    <section
      className={`rounded-xl border border-border bg-slate-50 p-3 ${className ?? ""}`.trim()}
      aria-label="Decision trace"
    >
      <div className="mb-2 flex items-center gap-2">
        <Gavel className="h-4 w-4 text-muted-foreground" />
        <h3 className="text-xs font-semibold uppercase tracking-wide text-foreground">
          Decision Trace
        </h3>
      </div>

      {!trace ? (
        <p className="text-xs text-muted-foreground">
          Decision trace unavailable for this work item.
        </p>
      ) : (
        <div className="space-y-2 text-xs">
          <div className="rounded-lg border border-border bg-white p-2">
            <p className="mb-1 inline-flex items-center gap-1 text-muted-foreground">
              <Brain className="h-3.5 w-3.5" />
              AI recommendation
            </p>
            <p className="text-foreground">
              {trace.ai_summary || "Unavailable"}
            </p>
            {typeof trace.ai_confidence === "number" ? (
              <p className="text-muted-foreground">
                Confidence: {Math.round(trace.ai_confidence * 100)}%
              </p>
            ) : null}
          </div>

          <div className="rounded-lg border border-border bg-white p-2">
            <p className="mb-1 inline-flex items-center gap-1 text-muted-foreground">
              <FileText className="h-3.5 w-3.5" />
              Human decision
            </p>
            <p className="text-foreground">
              {trace.human_decision || "Unavailable"}
            </p>
            {trace.override_reason ? (
              <p className="mt-1 text-muted-foreground">
                Override reason: {trace.override_reason}
              </p>
            ) : null}
          </div>

          {!compact ? (
            <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
              <div className="rounded-lg border border-border bg-white p-2">
                <p className="mb-1 text-muted-foreground">Facts used</p>
                {(trace.facts_used ?? []).length > 0 ? (
                  <ul className="space-y-1 text-foreground">
                    {(trace.facts_used ?? []).slice(0, 6).map((fact) => (
                      <li key={fact}>• {fact}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-muted-foreground">No facts listed</p>
                )}
              </div>
              <div className="rounded-lg border border-border bg-white p-2">
                <p className="mb-1 text-muted-foreground">Policy triggers</p>
                {(trace.policy_rules_triggered ?? []).length > 0 ? (
                  <ul className="space-y-1 text-foreground">
                    {(trace.policy_rules_triggered ?? [])
                      .slice(0, 6)
                      .map((rule) => (
                        <li key={rule}>• {rule.replaceAll("_", " ")}</li>
                      ))}
                  </ul>
                ) : (
                  <p className="text-muted-foreground">
                    No policy triggers recorded
                  </p>
                )}
              </div>
            </div>
          ) : null}
        </div>
      )}
    </section>
  );
}

export default DecisionTraceCard;
