"use client";

import { useMemo } from "react";
import { Clock3 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
    <Card className="border-border shadow-sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-foreground">
          <Clock3 className="h-4 w-4 text-muted-foreground" />
          Timeline
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {timeline.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No timeline events available.
            </p>
          ) : (
            timeline.map((event, index) => (
              <div
                key={`${event.type}-${event.label}-${index}`}
                className="rounded-lg border border-border bg-slate-50 p-3"
              >
                <div className="flex items-center justify-between gap-2 border-b border-border/50 pb-2 mb-2">
                  <p className="text-sm font-medium text-foreground">
                    {event.type}: {event.label}
                  </p>
                  <p className="text-[11px] text-muted-foreground">
                    {new Date(event.at ?? "").toLocaleString()}
                  </p>
                </div>
                <p className="text-xs text-foreground/80">{event.detail}</p>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default EntityTimeline;
