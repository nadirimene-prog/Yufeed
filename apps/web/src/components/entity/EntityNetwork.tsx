"use client";

import { Network } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { EntityNetworkSummary } from "@/types/entity";

interface EntityNetworkProps {
  network: EntityNetworkSummary;
}

export function EntityNetwork({ network }: EntityNetworkProps) {
  return (
    <Card className="border-border shadow-sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-foreground">
          <Network className="h-4 w-4 text-muted-foreground" />
          Network Snapshot
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <div className="rounded-lg border border-border bg-slate-50 p-3">
            <p className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">
              Alerts
            </p>
            <p className="text-2xl font-semibold text-foreground">
              {network.alerts_count}
            </p>
          </div>
          <div className="rounded-lg border border-border bg-slate-50 p-3">
            <p className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">
              Cases
            </p>
            <p className="text-2xl font-semibold text-foreground">
              {network.cases_count}
            </p>
          </div>
          <div className="rounded-lg border border-border bg-slate-50 p-3">
            <p className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">
              Transactions
            </p>
            <p className="text-2xl font-semibold text-foreground">
              {network.transactions_count}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default EntityNetwork;
