"use client";

import { LineChart } from "lucide-react";
import {
  GlassCard,
  GlassCardContent,
  GlassCardHeader,
  GlassCardTitle,
} from "@/components/ui/glass-card";
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
    <GlassCard>
      <GlassCardHeader>
        <GlassCardTitle className="flex items-center gap-2">
          <LineChart className="h-4 w-4" />
          Risk History
        </GlassCardTitle>
      </GlassCardHeader>
      <GlassCardContent>
        {series.length === 0 ? (
          <p className="text-sm text-foreground-secondary">
            Risk history unavailable.
          </p>
        ) : (
          <div className="rounded-lg border border-border-subtle bg-bg-overlay p-4">
            <Sparkline
              data={series.reverse()}
              width={560}
              height={120}
              color="aurora"
              ariaLabel="Entity risk history"
            />
          </div>
        )}
      </GlassCardContent>
    </GlassCard>
  );
}

export default EntityRiskHistory;
