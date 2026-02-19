"use client";

import Link from "next/link";
import DataTable, { type Column } from "@/components/ui/data-table-horizon";
import { RiskBadge, StatusBadge } from "@/components/ui/badge-horizon";
import type { EntityAlert } from "@/types/entity";

interface EntityAlertsProps {
  alerts: EntityAlert[];
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
  if (normalized === "in_review") return "in_review";
  if (normalized === "resolved") return "approved";
  if (normalized === "escalated") return "warning";
  if (normalized === "closed") return "approved";
  if (normalized === "pending") return "pending";
  return "pending";
}

export function EntityAlerts({ alerts }: EntityAlertsProps) {
  const columns: Column<EntityAlert>[] = [
    {
      key: "alert_id",
      header: "Alert",
      accessor: (alert) => (
        <span className="font-mono text-xs">{alert.alert_id}</span>
      ),
    },
    {
      key: "severity",
      header: "Severity",
      accessor: (alert) => (
        <RiskBadge level={toRiskLevel(alert.severity)}>
          {alert.severity}
        </RiskBadge>
      ),
    },
    {
      key: "status",
      header: "Status",
      accessor: (alert) => (
        <StatusBadge status={toStatusBadgeStatus(alert.status)}>
          {alert.status}
        </StatusBadge>
      ),
    },
    {
      key: "rule",
      header: "Rule",
      accessor: (alert) =>
        alert.triggered_rule_id ? (
          <Link
            className="text-primary hover:underline"
            href={`/transaction-monitoring/rules/${alert.triggered_rule_id}`}
          >
            {alert.triggered_rule_name ?? alert.triggered_rule_id}
          </Link>
        ) : (
          <span className="text-foreground-tertiary">-</span>
        ),
    },
    {
      key: "created",
      header: "Created",
      accessor: (alert) => (
        <span className="text-xs text-foreground-secondary">
          {new Date(alert.created_at ?? "").toLocaleString()}
        </span>
      ),
    },
  ];

  return (
    <DataTable
      data={alerts}
      columns={columns}
      keyExtractor={(alert) => String(alert.id)}
      emptyTitle="No linked alerts"
      emptyDescription="No alert records were found for this entity."
      captionText="Entity alerts"
      pagination
      pageSize={8}
      bordered
      striped
    />
  );
}

export default EntityAlerts;
