"use client";

import { ShieldAlert } from "lucide-react";
import { MetricCard } from "@/components/ui/metric-card";
import { StatusBadge } from "@/components/ui/badge-horizon";
import type { EntityProfile } from "@/types/entity";

interface EntityHeaderProps {
  entity: EntityProfile;
}

export function EntityHeader({ entity }: EntityHeaderProps) {
  const score = Math.round(entity.risk?.overall_score ?? 0);
  const riskLevel = entity.risk?.risk_level ?? "unknown";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="text-2xl font-display font-semibold text-foreground">
          Entity {entity.user_id ?? entity.id}
        </h1>
        <StatusBadge status="active">{entity.type}</StatusBadge>
        {entity.compliance?.status ? (
          <StatusBadge status="in_review">
            {entity.compliance.status}
          </StatusBadge>
        ) : null}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <MetricCard
          title="Overall Risk"
          value={score}
          color={score >= 70 ? "red" : score >= 40 ? "orange" : "green"}
          icon={<ShieldAlert className="h-5 w-5" />}
        />
        <MetricCard
          title="Risk Level"
          value={riskLevel.toUpperCase()}
          color="blue"
        />
        <MetricCard
          title="KYC Status"
          value={entity.risk?.kyc_status ?? "N/A"}
          color="purple"
        />
      </div>
    </div>
  );
}

export default EntityHeader;
