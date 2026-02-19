"use client";

import { useMemo } from "react";
import { Clock3 } from "lucide-react";
import {
  GlassCard,
  GlassCardContent,
  GlassCardHeader,
  GlassCardTitle,
} from "@/components/ui/glass-card";
import type { EntityProfile } from "@/types/entity";

interface EntityTimelineProps {
  entity: EntityProfile;
}

export function EntityTimeline({ entity }: EntityTimelineProps) {
  const timeline = useMemo(() => {
    const alertEvents = entity.alerts.map((alert) => ({
      type: "Alert",
      label: alert.alert_id,
      detail: `${alert.severity} • ${alert.status}`,
      at: alert.created_at,
    }));

    const caseEvents = entity.cases.map((caseItem) => ({
      type: "Case",
      label: caseItem.case_id,
      detail: `${caseItem.severity} • ${caseItem.status}`,
      at: caseItem.opened_at,
    }));

    const transactionEvents = entity.transactions.map((transaction) => ({
      type: "Transaction",
      label: transaction.transaction_id,
      detail: `${transaction.amount} ${transaction.currency}`,
      at: transaction.timestamp,
    }));

    return [...alertEvents, ...caseEvents, ...transactionEvents]
      .filter((event) => Boolean(event.at))
      .sort(
        (a, b) => new Date(b.at ?? 0).getTime() - new Date(a.at ?? 0).getTime(),
      )
      .slice(0, 30);
  }, [entity.alerts, entity.cases, entity.transactions]);

  return (
    <GlassCard>
      <GlassCardHeader>
        <GlassCardTitle className="flex items-center gap-2">
          <Clock3 className="h-4 w-4" />
          Timeline
        </GlassCardTitle>
      </GlassCardHeader>
      <GlassCardContent>
        <div className="space-y-2">
          {timeline.length === 0 ? (
            <p className="text-sm text-foreground-secondary">
              No timeline events available.
            </p>
          ) : (
            timeline.map((event, index) => (
              <div
                key={`${event.type}-${event.label}-${index}`}
                className="rounded-lg border border-border-subtle bg-bg-overlay p-3"
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium text-foreground">
                    {event.type}: {event.label}
                  </p>
                  <p className="text-xs text-foreground-tertiary">
                    {new Date(event.at ?? "").toLocaleString()}
                  </p>
                </div>
                <p className="mt-1 text-xs text-foreground-secondary">
                  {event.detail}
                </p>
              </div>
            ))
          )}
        </div>
      </GlassCardContent>
    </GlassCard>
  );
}

export default EntityTimeline;
