"use client";

import Link from "next/link";
import DataTable, { type Column } from "@/components/ui/data-table-horizon";
import { RiskBadge, StatusBadge } from "@/components/ui/badge-horizon";
import type { MonitoringCase } from "@/types/monitoring";

interface EntityCasesProps {
  cases: MonitoringCase[];
}

function toRiskLevel(
  severity: string,
): "critical" | "high" | "medium" | "low" | "info" {
  const normalized = severity.toLowerCase();
  if (normalized === "critical") return "critical";
  if (normalized === "high") return "high";
  if (normalized === "medium") return "medium";
  if (normalized === "low") return "low";
  return "info";
}

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
  if (normalized === "under_investigation") return "in_review";
  if (normalized === "escalated") return "warning";
  if (normalized === "sar_filed") return "critical";
  if (normalized === "closed") return "approved";
  if (normalized === "open") return "pending";
  return "pending";
}

export function EntityCases({ cases }: EntityCasesProps) {
  const columns: Column<MonitoringCase>[] = [
    {
      key: "case_id",
      header: "Case",
      accessor: (caseItem) => (
        <Link
          className="font-mono text-primary hover:underline"
          href={`/cases/${caseItem.case_id}`}
        >
          {caseItem.case_id}
        </Link>
      ),
    },
    {
      key: "severity",
      header: "Severity",
      accessor: (caseItem) => (
        <RiskBadge level={toRiskLevel(caseItem.severity)}>
          {caseItem.severity}
        </RiskBadge>
      ),
    },
    {
      key: "status",
      header: "Status",
      accessor: (caseItem) => (
        <StatusBadge status={toStatusBadgeStatus(caseItem.status)}>
          {caseItem.status}
        </StatusBadge>
      ),
    },
    {
      key: "opened",
      header: "Opened",
      accessor: (caseItem) => (
        <span className="text-xs text-foreground-secondary">
          {new Date(caseItem.opened_at).toLocaleString()}
        </span>
      ),
    },
    {
      key: "assigned",
      header: "Assigned",
      accessor: (caseItem) => (
        <span className="text-xs text-foreground-secondary">
          {caseItem.assigned_to ?? "Unassigned"}
        </span>
      ),
    },
  ];

  return (
    <DataTable
      data={cases}
      columns={columns}
      keyExtractor={(caseItem) => String(caseItem.id)}
      emptyTitle="No linked cases"
      emptyDescription="No case records were found for this entity."
      captionText="Entity cases"
      pagination
      pageSize={8}
      bordered
      striped
    />
  );
}

export default EntityCases;
