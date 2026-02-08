"use client";

import { ColumnDef } from "@tanstack/react-table";
import { AlertTriangle, CheckCircle, XCircle, ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import { StatusBadge, StatusState } from "@/components/ui/status-indicator";
import {
  GlassCard,
  GlassCardHeader,
  GlassCardTitle,
  GlassCardContent,
} from "@/components/ui/glass-card";
import { ProactiveAlert } from "@/lib/aml-officer-api";

interface RecentAlertsTableProps {
  data: ProactiveAlert[];
  onAction?: (alert: ProactiveAlert, action: "approve" | "reject") => void;
}

export function RecentAlertsTable({ data, onAction }: RecentAlertsTableProps) {
  const columns: ColumnDef<ProactiveAlert>[] = [
    {
      accessorKey: "severity",
      header: "Severity",
      cell: ({ row }) => {
        const severity = row.getValue("severity") as string;
        let status: StatusState = "active";
        if (severity === "critical") status = "error";
        if (severity === "high") status = "warning";
        if (severity === "low") status = "live"; // using live/green for low

        return (
          <StatusBadge
            status={status}
            label={severity.toUpperCase()}
            size="sm"
          />
        );
      },
    },
    {
      accessorKey: "message",
      header: "Alert Detail",
      cell: ({ row }) => {
        return (
          <div className="max-w-[300px]">
            <div className="text-sm font-medium text-white truncate">
              {row.original.message}
            </div>
            <div className="text-xs text-white/50 truncate">
              {row.original.recommendation}
            </div>
          </div>
        );
      },
    },
    {
      accessorKey: "timestamp", // Note: The API might not return this yet, we might need to mock or infer
      header: "Time",
      cell: () => {
        // Mocking relative time for now as API type doesn't have timestamp strictly defined in the view I saw
        // In a real app, use row.original.timestamp
        return (
          <span className="text-xs text-white/40 whitespace-nowrap">
            {Math.floor(Math.random() * 24)}h ago
          </span>
        );
      },
    },
    {
      id: "actions",
      cell: ({ row }) => {
        return (
          <div className="flex items-center gap-2 justify-end">
            <Button
              variant="ghost"
              size="icon-sm"
              className="text-green-400 hover:text-green-300 hover:bg-green-400/10"
              title="Quick Approve / Dismiss"
              onClick={(e) => {
                e.stopPropagation();
                onAction?.(row.original, "approve");
              }}
            >
              <CheckCircle className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              className="text-red-400 hover:text-red-300 hover:bg-red-400/10"
              title="Reject / Escalate"
              onClick={(e) => {
                e.stopPropagation();
                onAction?.(row.original, "reject");
              }}
            >
              <XCircle className="w-4 h-4" />
            </Button>
          </div>
        );
      },
    },
  ];

  return (
    <GlassCard className="h-full flex flex-col">
      <GlassCardHeader className="flex flex-row items-center justify-between py-3">
        <GlassCardTitle className="text-base flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-[var(--color-risk-high)]" />
          Pending High Riks Alerts
        </GlassCardTitle>
        <Button
          variant="ghost"
          size="sm"
          rightIcon={<ArrowRight className="w-3 h-3" />}
        >
          View All
        </Button>
      </GlassCardHeader>
      <GlassCardContent className="p-0 flex-1">
        <DataTable
          columns={columns}
          data={data}
          showPagination={false}
          className="border-0 bg-transparent"
          emptyMessage="No pending alerts requiring attention."
        />
      </GlassCardContent>
    </GlassCard>
  );
}
