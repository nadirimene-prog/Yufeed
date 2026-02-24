"use client";

import { LineChart } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Sparkline } from "@/components/ui/sparkline";
import type { EntityProfile } from "@/types/entity";

interface EntityRiskHistoryProps {
  entity: EntityProfile;
}

export function EntityRiskHistory({ entity }: EntityRiskHistoryProps) {
  const series = [
    ...entity.transactions
      .slice(0, 8)
      .map((transaction) => ({ value: transaction.risk_score })),
  ];

  if (series.length === 0 && entity.risk) {
    series.push({ value: entity.risk.overall_score });
  }

  return (
    <Card className="border-border shadow-sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-foreground">
          <LineChart className="h-4 w-4 text-muted-foreground" />
          Risk History
        </CardTitle>
      </CardHeader>
      <CardContent>
        {series.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Risk history unavailable.
          </p>
        ) : (
          <div className="rounded-lg border border-border bg-slate-50 p-4">
            <Sparkline
              data={series.reverse()}
              width={560}
              height={120}
              color="blue"
              ariaLabel="Entity risk history"
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default EntityRiskHistory;
