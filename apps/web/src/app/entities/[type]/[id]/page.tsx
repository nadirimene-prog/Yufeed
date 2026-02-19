"use client";

import { useEffect } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { LoadingBoundary } from "@/components/shared/LoadingBoundary";
import { EmptyState } from "@/components/ui/empty-state";
import { GlassCard, GlassCardContent } from "@/components/ui/glass-card";
import { useCopilot } from "@/components/aml-officer/copilot-context";
import { useEntityProfile } from "@/hooks/queries/useEntityData";
import EntityHeader from "@/components/entity/EntityHeader";
import EntityAlerts from "@/components/entity/EntityAlerts";
import EntityCases from "@/components/entity/EntityCases";
import EntityTransactions from "@/components/entity/EntityTransactions";
import EntityNetwork from "@/components/entity/EntityNetwork";
import EntityRiskHistory from "@/components/entity/EntityRiskHistory";
import EntityTimeline from "@/components/entity/EntityTimeline";

function DocumentsPlaceholder() {
  return (
    <GlassCard>
      <GlassCardContent>
        <EmptyState
          title="Documents Coming Soon"
          description="Document and evidence bundle integration will be added in the next iteration."
          variant="no-data"
          compact
        />
      </GlassCardContent>
    </GlassCard>
  );
}

export default function EntityProfilePage() {
  const params = useParams<{ type: string; id: string }>();
  const searchParams = useSearchParams();
  const tab = searchParams.get("tab") ?? "overview";

  const entityType = typeof params.type === "string" ? params.type : "";
  const entityId = typeof params.id === "string" ? params.id : "";

  const entityQuery = useEntityProfile(entityType, entityId);
  const { setPageContext } = useCopilot();

  useEffect(() => {
    const entityName = entityQuery.data?.user_id ?? entityId;
    setPageContext(`Entity Profile: ${entityName}`);
  }, [entityId, entityQuery.data?.user_id, setPageContext]);

  return (
    <LoadingBoundary
      loading={entityQuery.isLoading}
      error={entityQuery.error as Error | undefined}
      isEmpty={!entityQuery.data}
      emptyMessage="Entity not found"
      emptyDescription="The requested entity could not be loaded."
      minHeight="260px"
    >
      {entityQuery.data ? (
        <div className="space-y-4">
          <EntityHeader entity={entityQuery.data} />

          {tab === "alerts" ? (
            <EntityAlerts alerts={entityQuery.data.alerts} />
          ) : null}
          {tab === "cases" ? (
            <EntityCases cases={entityQuery.data.cases} />
          ) : null}
          {tab === "transactions" ? (
            <EntityTransactions transactions={entityQuery.data.transactions} />
          ) : null}
          {tab === "network" ? (
            <EntityNetwork network={entityQuery.data.network} />
          ) : null}
          {tab === "risk" ? (
            <EntityRiskHistory entity={entityQuery.data} />
          ) : null}
          {tab === "timeline" ? (
            <EntityTimeline entity={entityQuery.data} />
          ) : null}
          {tab === "documents" ? <DocumentsPlaceholder /> : null}

          {tab === "overview" ? (
            <div className="grid gap-4 lg:grid-cols-2">
              <EntityAlerts alerts={entityQuery.data.alerts.slice(0, 8)} />
              <EntityCases cases={entityQuery.data.cases.slice(0, 8)} />
              <EntityRiskHistory entity={entityQuery.data} />
              <EntityNetwork network={entityQuery.data.network} />
            </div>
          ) : null}
        </div>
      ) : null}
    </LoadingBoundary>
  );
}
