"use client";

import { Network } from "lucide-react";
import {
  GlassCard,
  GlassCardContent,
  GlassCardHeader,
  GlassCardTitle,
} from "@/components/ui/glass-card";
import type { EntityNetworkSummary } from "@/types/entity";

interface EntityNetworkProps {
  network: EntityNetworkSummary;
}

export function EntityNetwork({ network }: EntityNetworkProps) {
  return (
    <GlassCard>
      <GlassCardHeader>
        <GlassCardTitle className="flex items-center gap-2">
          <Network className="h-4 w-4" />
          Network Snapshot
        </GlassCardTitle>
      </GlassCardHeader>
      <GlassCardContent>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <div className="rounded-lg border border-border-subtle bg-bg-overlay p-3">
            <p className="text-xs uppercase tracking-wide text-foreground-tertiary">
              Alerts
            </p>
            <p className="text-xl font-semibold text-foreground">
              {network.alerts_count}
            </p>
          </div>
          <div className="rounded-lg border border-border-subtle bg-bg-overlay p-3">
            <p className="text-xs uppercase tracking-wide text-foreground-tertiary">
              Cases
            </p>
            <p className="text-xl font-semibold text-foreground">
              {network.cases_count}
            </p>
          </div>
          <div className="rounded-lg border border-border-subtle bg-bg-overlay p-3">
            <p className="text-xs uppercase tracking-wide text-foreground-tertiary">
              Transactions
            </p>
            <p className="text-xl font-semibold text-foreground">
              {network.transactions_count}
            </p>
          </div>
        </div>
      </GlassCardContent>
    </GlassCard>
  );
}

export default EntityNetwork;
