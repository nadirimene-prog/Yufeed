"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertTriangle, CheckCircle2, Clock3, ShieldCheck } from "lucide-react";
import { useComplianceCases } from "@/hooks/queries/useComplianceData";
import { useCopilot } from "@/components/aml-officer/copilot-context";
import { LoadingBoundary } from "@/components/shared/LoadingBoundary";
import { EmptyState } from "@/components/ui/empty-state";
import {
  GlassCard,
  GlassCardContent,
  GlassCardHeader,
  GlassCardTitle,
} from "@/components/ui/glass-card";
import { MetricCard } from "@/components/ui/metric-card";
import { Button } from "@/components/ui/button-horizon";
import DataTable, { type Column } from "@/components/ui/data-table-horizon";
import { RiskBadge, StatusBadge } from "@/components/ui/badge-horizon";
import type { ComplianceProfile } from "@/types/compliance";

function toStatusBadgeStatus(
  status: string,
):
  | "draft"
  | "pending"
  | "in_review"
  | "approved"
  | "rejected"
  | "active"
  | "inactive"
  | "critical"
  | "warning"
  | "expired"
  | "archived" {
  const normalized = status.toLowerCase();
  if (normalized === "approved") return "approved";
  if (normalized === "rejected") return "rejected";
  if (normalized === "manual_review") return "in_review";
  if (normalized === "pending") return "pending";
  return "pending";
}

function toEntityName(profile: ComplianceProfile) {
  if (profile.type === "kyb") {
    return profile.company_name || `Business ${profile.id}`;
  }
  const fullName =
    `${profile.first_name ?? ""} ${profile.last_name ?? ""}`.trim();
  return fullName || profile.email || `Customer ${profile.id}`;
}

export default function ComplianceDashboardPage() {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState<
    "all" | "pending" | "manual_review" | "approved" | "rejected"
  >("all");
  const [search, setSearch] = useState("");

  const { setPageContext } = useCopilot();
  useEffect(() => {
    setPageContext("Compliance Dashboard: Review KYC/KYB applications");
  }, [setPageContext]);

  const casesQuery = useComplianceCases(
    statusFilter === "all"
      ? { limit: 200 }
      : { status: statusFilter, limit: 200 },
  );

  const allCases = useMemo(() => casesQuery.data ?? [], [casesQuery.data]);

  const filteredCases = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return allCases;

    return allCases.filter((profile) => {
      return (
        String(profile.id).includes(q) ||
        toEntityName(profile).toLowerCase().includes(q) ||
        (profile.email ?? "").toLowerCase().includes(q) ||
        (profile.registration_number ?? "").toLowerCase().includes(q) ||
        (profile.company_name ?? "").toLowerCase().includes(q)
      );
    });
  }, [allCases, search]);

  const columns = useMemo<Column<ComplianceProfile>[]>(
    () => [
      {
        key: "entity",
        header: "Entity",
        accessor: (profile) => (
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-foreground">
              {toEntityName(profile)}
            </p>
            <p className="truncate text-xs text-foreground-secondary">
              {profile.type === "kyb"
                ? profile.registration_number || "-"
                : profile.email || "-"}
            </p>
          </div>
        ),
      },
      {
        key: "type",
        header: "Type",
        accessor: (profile) => (
          <StatusBadge status="active">
            {profile.type.toUpperCase()}
          </StatusBadge>
        ),
      },
      {
        key: "created",
        header: "Submitted",
        sortable: true,
        accessor: (profile) => (
          <span className="text-sm text-foreground-secondary">
            {new Date(profile.created_at).toLocaleDateString()}
          </span>
        ),
      },
      {
        key: "risk",
        header: "Risk",
        accessor: (profile) => (
          <RiskBadge level={profile.risk_level}>{profile.risk_level}</RiskBadge>
        ),
      },
      {
        key: "status",
        header: "Status",
        accessor: (profile) => (
          <StatusBadge status={toStatusBadgeStatus(profile.status)}>
            {profile.status.replaceAll("_", " ")}
          </StatusBadge>
        ),
      },
      {
        key: "action",
        header: "Action",
        align: "right",
        accessor: (profile) => (
          <Link
            href={`/compliance/case/${profile.id}`}
            className="text-sm text-primary hover:underline"
          >
            View
          </Link>
        ),
      },
    ],
    [],
  );

  return (
    <div className="space-y-6 bg-bg-base text-foreground">
      <header className="space-y-1">
        <h1 className="text-3xl font-display font-semibold">
          Compliance Dashboard
        </h1>
        <p className="text-foreground-secondary">
          Review and disposition KYC/KYB applications in one queue.
        </p>
      </header>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <MetricCard
          title="Pending"
          value={
            allCases.filter((profile) => profile.status === "pending").length
          }
          color="yellow"
          icon={<Clock3 className="h-5 w-5" />}
        />
        <MetricCard
          title="Manual Review"
          value={
            allCases.filter((profile) => profile.status === "manual_review")
              .length
          }
          color="orange"
          icon={<AlertTriangle className="h-5 w-5" />}
        />
        <MetricCard
          title="Approved"
          value={
            allCases.filter((profile) => profile.status === "approved").length
          }
          color="green"
          icon={<CheckCircle2 className="h-5 w-5" />}
        />
        <MetricCard
          title="High Risk"
          value={
            allCases.filter(
              (profile) =>
                profile.risk_level === "high" ||
                profile.risk_level === "critical",
            ).length
          }
          color="red"
          icon={<ShieldCheck className="h-5 w-5" />}
          glow
        />
      </section>

      <GlassCard>
        <GlassCardHeader className="gap-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <GlassCardTitle className="text-base">Applications</GlassCardTitle>
            <div className="flex flex-wrap items-center gap-2">
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search by entity, id, email..."
                className="h-10 min-w-[220px] rounded-lg border border-border-default bg-bg-overlay px-3 text-sm"
              />
              <Button variant="secondary">Export Report</Button>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {[
              { key: "all", label: "All" },
              { key: "pending", label: "Pending" },
              { key: "manual_review", label: "Manual Review" },
              { key: "approved", label: "Approved" },
              { key: "rejected", label: "Rejected" },
            ].map((option) => (
              <Button
                key={option.key}
                size="sm"
                variant={statusFilter === option.key ? "primary" : "glass"}
                onClick={() =>
                  setStatusFilter(option.key as typeof statusFilter)
                }
              >
                {option.label}
              </Button>
            ))}
          </div>
        </GlassCardHeader>

        <GlassCardContent>
          <LoadingBoundary
            loading={casesQuery.isLoading}
            error={casesQuery.error as Error | undefined}
            isEmpty={filteredCases.length === 0}
            emptyMessage="No compliance applications"
            emptyDescription="No records match your selected filters."
            minHeight="260px"
          >
            {filteredCases.length === 0 ? (
              <EmptyState
                title="No compliance applications"
                description="Try changing filters or searching with a different entity identifier."
                variant="no-results"
                compact
              />
            ) : (
              <DataTable
                data={filteredCases}
                columns={columns}
                keyExtractor={(profile) => String(profile.id)}
                loading={casesQuery.isFetching}
                searchable={false}
                pagination
                pageSize={10}
                striped
                bordered
                captionText="Compliance applications table"
                onRowClick={(profile) =>
                  router.push(`/compliance/case/${profile.id}`)
                }
              />
            )}
          </LoadingBoundary>
        </GlassCardContent>
      </GlassCard>
    </div>
  );
}
