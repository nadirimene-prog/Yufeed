"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertCircle,
  ChevronDown,
  ChevronRight,
  Sparkles,
  User,
} from "lucide-react";
import toast from "react-hot-toast";
import { useMonitoringAlerts } from "@/hooks/queries/useMonitoringData";
import { useWorkspaceUsers } from "@/hooks/queries/useSpecializedData";
import { LoadingBoundary } from "@/components/shared/LoadingBoundary";
import EmptyState from "@/components/ui/empty-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MetricCard } from "@/components/ui/metric-card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button-horizon";
import { RiskBadge, StatusBadge } from "@/components/ui/badge-horizon";
import { ExportButton } from "@/components/ui/export-button";
import CreateCaseModal from "@/components/workbench/CreateCaseModal";
import { staggerContainer, staggerItem } from "@/lib/motion";
import apiClient from "@/lib/http";
import type { MonitoringAlert } from "@/types/monitoring";
import type { ExportColumn } from "@/lib/export";
import { useCopilot } from "@/components/aml-officer/copilot-context";

const alertExportColumns: ExportColumn<Record<string, unknown>>[] = [
  { key: "alert_id", label: "Alert ID" },
  { key: "user_id", label: "User ID" },
  { key: "alert_type", label: "Alert Type" },
  { key: "severity", label: "Severity" },
  { key: "status", label: "Status" },
  { key: "risk_score", label: "Risk Score" },
  { key: "priority", label: "Priority" },
  { key: "assigned_to", label: "Assigned To" },
  { key: "triggered_rule_name", label: "Triggered Rule" },
  { key: "created_at", label: "Created At" },
];

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
  if (normalized === "pending") return "pending";
  if (normalized === "in_review") return "in_review";
  if (normalized === "approved") return "approved";
  if (normalized === "rejected") return "rejected";
  if (normalized === "active") return "active";
  if (normalized === "inactive") return "inactive";
  if (normalized === "critical") return "critical";
  if (normalized === "warning") return "warning";
  if (normalized === "expired") return "expired";
  if (normalized === "archived") return "archived";
  if (normalized === "draft") return "draft";
  return "pending";
}

function parseDate(value?: string | null) {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.valueOf())) return null;
  return parsed;
}

function isSnoozed(alert: MonitoringAlert) {
  const until = parseDate(alert.snoozed_until);
  if (!until) return false;
  return until.getTime() > Date.now();
}

export default function TransactionAlertsPage() {
  const [selectedAlertId, setSelectedAlertId] = useState<number | null>(null);
  const [selectedAlerts, setSelectedAlerts] = useState<Set<number>>(new Set());
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>(
    {},
  );
  const [bulkAssignee, setBulkAssignee] = useState("");
  const [createCaseOpen, setCreateCaseOpen] = useState(false);
  const [filters, setFilters] = useState({
    status: "all",
    severity: "all",
    search: "",
    groupByEntity: false,
    hideSnoozed: true,
  });
  const [snoozeHours, setSnoozeHours] = useState("24");
  const [snoozeReason, setSnoozeReason] = useState("");

  const alertsQuery = useMonitoringAlerts({
    limit: 100,
    include_snoozed: !filters.hideSnoozed,
    ...(filters.status !== "all" ? { status: filters.status } : {}),
    ...(filters.severity !== "all" ? { severity: filters.severity } : {}),
  });
  const usersQuery = useWorkspaceUsers();
  const alerts = useMemo(() => alertsQuery.data ?? [], [alertsQuery.data]);

  const { setPageContext } = useCopilot();

  useEffect(() => {
    setPageContext("Transaction Alerts: Triage AML/CFT alerts");
  }, [setPageContext]);

  const filteredAlerts = useMemo(() => {
    const search = filters.search.trim().toLowerCase();
    if (!search) return alerts;
    return alerts.filter((alert) => {
      if (filters.hideSnoozed && isSnoozed(alert)) return false;
      return (
        alert.alert_id.toLowerCase().includes(search) ||
        alert.user_id.toLowerCase().includes(search) ||
        alert.alert_type.toLowerCase().includes(search) ||
        (alert.triggered_rule_name ?? "").toLowerCase().includes(search)
      );
    });
  }, [alerts, filters.hideSnoozed, filters.search]);

  const groupedAlerts = useMemo(() => {
    if (!filters.groupByEntity)
      return [] as Array<{ userId: string; alerts: MonitoringAlert[] }>;

    const byUser = new Map<string, MonitoringAlert[]>();
    for (const alert of filteredAlerts) {
      const key = alert.user_id || "unknown";
      if (!byUser.has(key)) byUser.set(key, []);
      byUser.get(key)?.push(alert);
    }

    return Array.from(byUser.entries())
      .map(([userId, entityAlerts]) => ({ userId, alerts: entityAlerts }))
      .sort((a, b) => b.alerts.length - a.alerts.length);
  }, [filteredAlerts, filters.groupByEntity]);

  const selectedAlert = useMemo(() => {
    if (filteredAlerts.length === 0) return null;
    if (selectedAlertId == null) return filteredAlerts[0];
    return (
      filteredAlerts.find((alert) => alert.id === selectedAlertId) ??
      filteredAlerts[0]
    );
  }, [filteredAlerts, selectedAlertId]);

  const canBulkAssign =
    selectedAlerts.size > 0 && bulkAssignee.trim().length > 0;

  const toggleSelectedAlert = (id: number, checked: boolean) => {
    setSelectedAlerts((current) => {
      const next = new Set(current);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  };

  const handleBulkTriage = async () => {
    if (selectedAlerts.size === 0) return;
    const alertIds = Array.from(selectedAlerts);
    const request = apiClient.post("/api/ai/triage/batch", {
      alert_ids: alertIds,
    });
    await toast.promise(request, {
      loading: `Triaging ${alertIds.length} alerts...`,
      success: `Triaged ${alertIds.length} alerts`,
      error: "Failed to triage alerts",
    });
    setSelectedAlerts(new Set());
    await alertsQuery.refetch();
  };

  const handleBulkAssign = async () => {
    if (!canBulkAssign) return;
    const selected = alerts.filter((alert) => selectedAlerts.has(alert.id));
    const request = Promise.all(
      selected.map((alert) =>
        apiClient.post(
          `/api/alerts/${encodeURIComponent(alert.alert_id)}/assign`,
          null,
          {
            params: { assigned_to: bulkAssignee },
          },
        ),
      ),
    );

    await toast.promise(request, {
      loading: `Assigning ${selected.length} alerts...`,
      success: `Assigned ${selected.length} alerts to ${bulkAssignee}`,
      error: "Failed to assign alerts",
    });

    setSelectedAlerts(new Set());
    await alertsQuery.refetch();
  };

  const handleSnoozeSelected = async () => {
    if (!selectedAlert) return;
    const durationHours = Number.parseInt(snoozeHours, 10);
    if (Number.isNaN(durationHours) || durationHours <= 0) {
      toast.error("Select a valid snooze duration.");
      return;
    }

    const request = apiClient.post(
      `/api/alerts/${encodeURIComponent(selectedAlert.alert_id)}/snooze`,
      {
        duration_hours: durationHours,
        reason: snoozeReason.trim() || undefined,
        snoozed_by: bulkAssignee || selectedAlert.assigned_to || undefined,
      },
    );

    await toast.promise(request, {
      loading: `Snoozing ${selectedAlert.alert_id}...`,
      success: `Snoozed ${selectedAlert.alert_id} for ${durationHours}h`,
      error: "Failed to snooze alert",
    });
    setSnoozeReason("");
    await alertsQuery.refetch();
  };

  return (
    <motion.div
      variants={staggerContainer}
      initial="initial"
      animate="animate"
      className="space-y-6 bg-background text-foreground"
    >
      <motion.div variants={staggerItem} className="space-y-1">
        <h1 className="text-3xl font-display font-semibold">
          Transaction Alerts
        </h1>
        <p className="text-foreground-secondary">
          Triage, investigate, and action AML/CFT alerts.
        </p>
      </motion.div>

      <motion.div
        variants={staggerItem}
        className="grid grid-cols-1 gap-4 md:grid-cols-4"
      >
        <MetricCard
          title="Total"
          value={alerts.length}
          color="blue"
          icon={<AlertCircle className="h-5 w-5" />}
        />
        <MetricCard
          title="Pending"
          value={alerts.filter((a) => a.status === "pending").length}
          color="yellow"
        />
        <MetricCard
          title="Critical"
          value={alerts.filter((a) => a.severity === "critical").length}
          color="red"
          glow
        />
        <MetricCard
          title="High Risk"
          value={alerts.filter((a) => Number(a.risk_score) >= 70).length}
          color="orange"
        />
      </motion.div>

      <motion.div
        variants={staggerItem}
        className="grid gap-4 lg:grid-cols-[420px_1fr]"
      >
        <Card className="h-[calc(100vh-16rem)] overflow-hidden border-border shadow-sm bg-white flex flex-col">
          <CardHeader className="space-y-3 pb-4">
            <CardTitle className="text-base text-foreground font-semibold">
              Alert Queue
            </CardTitle>
            <div className="grid grid-cols-1 gap-2">
              <Input
                placeholder="Search by alert, entity, rule..."
                value={filters.search}
                onChange={(event) =>
                  setFilters((current) => ({
                    ...current,
                    search: event.target.value,
                  }))
                }
              />
              <div className="grid grid-cols-2 gap-2">
                <select
                  className="h-10 rounded-lg border border-border bg-background-overlay px-3 text-sm"
                  aria-label="Status filter"
                  value={filters.status}
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      status: event.target.value,
                    }))
                  }
                >
                  <option value="all">All status</option>
                  <option value="pending">Pending</option>
                  <option value="in_review">In Review</option>
                  <option value="resolved">Resolved</option>
                  <option value="escalated">Escalated</option>
                </select>
                <select
                  className="h-10 rounded-lg border border-border bg-background-overlay px-3 text-sm"
                  aria-label="Severity filter"
                  value={filters.severity}
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      severity: event.target.value,
                    }))
                  }
                >
                  <option value="all">All severity</option>
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>

              <div className="flex flex-wrap items-center gap-3 text-xs text-foreground-secondary">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={filters.groupByEntity}
                    onChange={(event) =>
                      setFilters((current) => ({
                        ...current,
                        groupByEntity: event.target.checked,
                      }))
                    }
                  />
                  Group by Entity
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={filters.hideSnoozed}
                    onChange={(event) =>
                      setFilters((current) => ({
                        ...current,
                        hideSnoozed: event.target.checked,
                      }))
                    }
                  />
                  Hide Snoozed
                </label>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={handleBulkTriage}
                disabled={selectedAlerts.size === 0}
              >
                <Sparkles className="h-4 w-4" />
                AI Triage
              </Button>
              <select
                className="h-9 min-w-[140px] rounded-lg border border-border bg-background-overlay px-2 text-xs"
                aria-label="Bulk assignee"
                value={bulkAssignee}
                onChange={(event) => setBulkAssignee(event.target.value)}
              >
                <option value="">Assign to...</option>
                {(usersQuery.data ?? []).map((user) => (
                  <option key={user.user_id} value={user.user_id}>
                    {user.user_id}
                  </option>
                ))}
              </select>
              <Button
                size="sm"
                variant="secondary"
                onClick={handleBulkAssign}
                disabled={!canBulkAssign}
              >
                Bulk Assign
              </Button>
              <ExportButton
                data={filteredAlerts as unknown as Record<string, unknown>[]}
                filename="transaction-alerts"
                pdfTitle="Transaction Alerts"
                columns={alertExportColumns}
                loading={alertsQuery.isLoading}
              />
            </div>
          </CardHeader>

          <CardContent className="h-[calc(100%-13rem)] overflow-auto pt-0">
            <LoadingBoundary
              loading={alertsQuery.isLoading}
              error={alertsQuery.error as Error | undefined}
              isEmpty={filteredAlerts.length === 0}
              emptyMessage="No alerts found"
              emptyDescription="Try changing filters or search terms."
              minHeight="220px"
            >
              {filters.groupByEntity ? (
                <div className="space-y-2">
                  {groupedAlerts.map((group) => {
                    const latest = group.alerts[0];
                    const criticalCount = group.alerts.filter(
                      (alert) => alert.severity === "critical",
                    ).length;
                    const highCount = group.alerts.filter(
                      (alert) => alert.severity === "high",
                    ).length;
                    const expanded = Boolean(expandedGroups[group.userId]);

                    return (
                      <div key={group.userId} className="space-y-2">
                        <button
                          type="button"
                          className="w-full rounded-lg border border-border-subtle bg-background-overlay px-3 py-2 text-left text-sm"
                          onClick={() =>
                            setExpandedGroups((current) => ({
                              ...current,
                              [group.userId]: !expanded,
                            }))
                          }
                        >
                          <div className="flex items-center gap-2">
                            {expanded ? (
                              <ChevronDown className="h-4 w-4" />
                            ) : (
                              <ChevronRight className="h-4 w-4" />
                            )}
                            <span className="font-medium">
                              Entity {group.userId}
                            </span>
                          </div>
                          <p className="mt-1 text-xs text-foreground-secondary">
                            {group.alerts.length} alerts ({criticalCount}{" "}
                            critical, {highCount} high) • Latest{" "}
                            {new Date(latest.created_at).toLocaleString()}
                          </p>
                        </button>

                        <AnimatePresence initial={false}>
                          {expanded && (
                            <motion.div
                              initial={{ opacity: 0, height: 0 }}
                              animate={{ opacity: 1, height: "auto" }}
                              exit={{ opacity: 0, height: 0 }}
                              className="space-y-2 overflow-hidden pl-4"
                            >
                              {group.alerts.map((alert) => (
                                <QueueRow
                                  key={alert.id}
                                  alert={alert}
                                  selected={selectedAlerts.has(alert.id)}
                                  active={selectedAlert?.id === alert.id}
                                  onToggleSelected={toggleSelectedAlert}
                                  onSelect={setSelectedAlertId}
                                />
                              ))}
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredAlerts.map((alert) => (
                    <QueueRow
                      key={alert.id}
                      alert={alert}
                      selected={selectedAlerts.has(alert.id)}
                      active={selectedAlert?.id === alert.id}
                      onToggleSelected={toggleSelectedAlert}
                      onSelect={setSelectedAlertId}
                    />
                  ))}
                </div>
              )}
            </LoadingBoundary>
          </CardContent>
        </Card>

        <Card className="h-[calc(100vh-16rem)] overflow-auto border-border shadow-sm bg-white">
          <CardHeader>
            <CardTitle className="text-base text-foreground font-semibold">
              Alert Detail
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!selectedAlert ? (
              <EmptyState
                title="No alert selected"
                description="Pick an alert from the queue to review details and actions."
                variant="no-results"
                compact
              />
            ) : (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-sm font-semibold">
                    {selectedAlert.alert_id}
                  </span>
                  <RiskBadge level={toRiskLevel(selectedAlert.severity)}>
                    {selectedAlert.severity}
                  </RiskBadge>
                  <StatusBadge
                    status={toStatusBadgeStatus(selectedAlert.status)}
                  >
                    {selectedAlert.status}
                  </StatusBadge>
                  {isSnoozed(selectedAlert) ? (
                    <StatusBadge status="inactive">
                      Snoozed until{" "}
                      {parseDate(selectedAlert.snoozed_until)?.toLocaleString()}
                    </StatusBadge>
                  ) : null}
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <Info
                    label="Entity"
                    value={
                      <Link
                        className="text-primary hover:underline"
                        href={`/entities/user/${selectedAlert.user_id}`}
                      >
                        {selectedAlert.user_id}
                      </Link>
                    }
                  />
                  <Info label="Type" value={selectedAlert.alert_type} />
                  <Info
                    label="Priority"
                    value={String(selectedAlert.priority)}
                  />
                  <Info
                    label="Risk Score"
                    value={String(selectedAlert.risk_score ?? 0)}
                  />
                  <Info
                    label="Assigned"
                    value={selectedAlert.assigned_to || "Unassigned"}
                  />
                  <Info
                    label="Created"
                    value={new Date(selectedAlert.created_at).toLocaleString()}
                  />
                </div>

                {selectedAlert.triggered_rule_name &&
                selectedAlert.triggered_rule_id ? (
                  <div className="rounded-lg border border-border-subtle bg-background-overlay p-3 text-sm">
                    Triggered by:{" "}
                    <Link
                      href={`/transaction-monitoring/rules/${selectedAlert.triggered_rule_id}`}
                      className="font-medium text-primary hover:underline"
                    >
                      {selectedAlert.triggered_rule_name}
                    </Link>
                  </div>
                ) : null}

                {selectedAlert.description ? (
                  <div className="rounded-lg border border-border-subtle bg-background-overlay p-3 text-sm text-foreground-secondary">
                    {selectedAlert.description}
                  </div>
                ) : null}

                <div className="rounded-lg border border-border-subtle bg-background-overlay p-3">
                  <p className="mb-2 text-xs uppercase tracking-wide text-foreground-tertiary">
                    Alert Cool-off
                  </p>
                  <div className="grid gap-2 md:grid-cols-[140px_1fr_auto]">
                    <select
                      className="h-10 rounded-lg border border-border bg-background px-3 text-sm"
                      value={snoozeHours}
                      onChange={(event) => setSnoozeHours(event.target.value)}
                      aria-label="Snooze duration"
                    >
                      <option value="1">1 hour</option>
                      <option value="4">4 hours</option>
                      <option value="24">24 hours</option>
                      <option value="168">7 days</option>
                    </select>
                    <Input
                      value={snoozeReason}
                      onChange={(event) => setSnoozeReason(event.target.value)}
                      placeholder="Reason (optional)"
                    />
                    <Button variant="secondary" onClick={handleSnoozeSelected}>
                      Snooze
                    </Button>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="primary"
                    onClick={() => setCreateCaseOpen(true)}
                  >
                    Create Case
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() =>
                      apiClient
                        .patch(
                          `/api/alerts/${encodeURIComponent(selectedAlert.alert_id)}`,
                          {
                            status: "in_review",
                          },
                        )
                        .then(() => alertsQuery.refetch())
                    }
                  >
                    Mark In Review
                  </Button>
                  <Link href={`/transaction-alerts/${selectedAlert.alert_id}`}>
                    <Button variant="outline">Open Full Page</Button>
                  </Link>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>

      <CreateCaseModal
        open={createCaseOpen}
        onOpenChange={setCreateCaseOpen}
        entityId={selectedAlert?.user_id}
        onCreated={(caseId) => {
          toast.success(`Case created: ${caseId}`);
        }}
      />
    </motion.div>
  );
}

function Info({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border-subtle bg-background-overlay p-3 text-sm">
      <p className="mb-1 text-xs uppercase tracking-wide text-foreground-tertiary">
        {label}
      </p>
      <p className="text-foreground">{value}</p>
    </div>
  );
}

function QueueRow({
  alert,
  selected,
  active,
  onToggleSelected,
  onSelect,
}: {
  alert: MonitoringAlert;
  selected: boolean;
  active: boolean;
  onToggleSelected: (id: number, checked: boolean) => void;
  onSelect: (id: number) => void;
}) {
  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`Alert row ${alert.alert_id}`}
      onClick={() => onSelect(alert.id)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect(alert.id);
        }
      }}
      className={`w-full rounded-lg border p-3 text-left transition ${
        active
          ? "border-primary/60 bg-primary/10"
          : "border-border-subtle bg-background-overlay hover:border-border"
      }`}
    >
      <div className="flex items-start gap-3">
        <input
          type="checkbox"
          checked={selected}
          aria-label={`Select alert ${alert.alert_id}`}
          onChange={(event) => onToggleSelected(alert.id, event.target.checked)}
          onClick={(event) => event.stopPropagation()}
          className="mt-1"
        />
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex items-center justify-between gap-2">
            <p className="truncate font-mono text-sm font-medium">
              {alert.alert_id}
            </p>
            <RiskBadge level={toRiskLevel(alert.severity)}>
              {alert.severity}
            </RiskBadge>
          </div>
          {isSnoozed(alert) ? (
            <p className="text-[11px] text-foreground-tertiary">
              Snoozed until {parseDate(alert.snoozed_until)?.toLocaleString()}
            </p>
          ) : null}
          <p className="truncate text-xs text-foreground-secondary">
            {alert.alert_type}
          </p>
          <div className="flex items-center gap-2 text-xs text-foreground-tertiary">
            <User className="h-3.5 w-3.5" />
            <Link
              href={`/entities/user/${alert.user_id}`}
              className="truncate hover:text-primary hover:underline"
              onClick={(event) => event.stopPropagation()}
            >
              {alert.user_id}
            </Link>
            {alert.triggered_rule_name ? (
              <span>• {alert.triggered_rule_name}</span>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
