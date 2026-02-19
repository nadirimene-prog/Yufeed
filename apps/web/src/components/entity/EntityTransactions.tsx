"use client";

import DataTable, { type Column } from "@/components/ui/data-table-horizon";
import { RiskBadge } from "@/components/ui/badge-horizon";
import type { EntityTransaction } from "@/types/entity";

interface EntityTransactionsProps {
  transactions: EntityTransaction[];
}

function toRiskLevel(
  score: number,
): "critical" | "high" | "medium" | "low" | "info" {
  if (score >= 80) return "critical";
  if (score >= 60) return "high";
  if (score >= 40) return "medium";
  if (score > 0) return "low";
  return "info";
}

export function EntityTransactions({ transactions }: EntityTransactionsProps) {
  const columns: Column<EntityTransaction>[] = [
    {
      key: "transaction_id",
      header: "Transaction",
      accessor: (transaction) => (
        <span className="font-mono text-xs">{transaction.transaction_id}</span>
      ),
    },
    {
      key: "amount",
      header: "Amount",
      accessor: (transaction) => (
        <span className="text-xs text-foreground-secondary">
          {transaction.amount.toLocaleString()} {transaction.currency}
        </span>
      ),
    },
    {
      key: "type",
      header: "Type",
      accessor: (transaction) => (
        <span className="text-xs text-foreground-secondary">
          {transaction.transaction_type}
        </span>
      ),
    },
    {
      key: "risk",
      header: "Risk",
      accessor: (transaction) => (
        <RiskBadge level={toRiskLevel(transaction.risk_score)}>
          {Math.round(transaction.risk_score)}
        </RiskBadge>
      ),
    },
    {
      key: "timestamp",
      header: "Timestamp",
      accessor: (transaction) => (
        <span className="text-xs text-foreground-secondary">
          {new Date(transaction.timestamp ?? "").toLocaleString()}
        </span>
      ),
    },
  ];

  return (
    <DataTable
      data={transactions}
      columns={columns}
      keyExtractor={(transaction) => String(transaction.id)}
      emptyTitle="No linked transactions"
      emptyDescription="No transaction records were found for this entity."
      captionText="Entity transactions"
      pagination
      pageSize={8}
      bordered
      striped
    />
  );
}

export default EntityTransactions;
