"use client";

import { type ReactNode, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AlertTriangle, Clock3, FileText, Folder } from "lucide-react";
import { useMonitoringCases } from "@/hooks/queries/useMonitoringData";
import { useCopilot } from "@/components/aml-officer/copilot-context";
import { LoadingBoundary } from "@/components/shared/LoadingBoundary";
import { EmptyState } from "@/components/ui/empty-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MetricCard } from "@/components/ui/metric-card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button-horizon";
import { RiskBadge, StatusBadge } from "@/components/ui/badge-horizon";
import SARPrepDrawer from "@/components/workbench/SARPrepDrawer";
import type { MonitoringCase } from "@/types/monitoring";

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
  if (normalized === "pending") return "pending";
  return "pending";
}

function relativeDays(value?: string) {
  if (!value) return "-";
  const timestamp = new Date(value).getTime();
  if (Number.isNaN(timestamp)) return "-";
  const days = Math.max(
    0,
    Math.floor((Date.now() - timestamp) / (1000 * 60 * 60 * 24)),
  );
  return `${days}d`;
}

export default function CasesPage() {
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [sarDrawerOpen, setSarDrawerOpen] = useState(false);
  const [filters, setFilters] = useState({
    status: "all",
    severity: "all",
    search: "",
  });

  const { setPageContext } = useCopilot();
  useEffect(() => {
    setPageContext("Case Management: Review investigation cases");
  }, [setPageContext]);

  const casesQuery = useMonitoringCases({
    limit: 100,
    ...(filters.status !== "all" ? { status: filters.status } : {}),
    ...(filters.severity !== "all" ? { priority: filters.severity } : {}),
  });

  const cases = useMemo(() => casesQuery.data ?? [], [casesQuery.data]);

  const filteredCases = useMemo(() => {
    const search = filters.search.trim().toLowerCase();
    if (!search) return cases;

    return cases.filter((caseItem) => {
      return (
        caseItem.case_id.toLowerCase().includes(search) ||
        (caseItem.subject_id ?? "").toLowerCase().includes(search) ||
        (caseItem.description ?? "").toLowerCase().includes(search) ||
        (caseItem.summary ?? "").toLowerCase().includes(search)
      );
    });
  }, [cases, filters.search]);

  const selectedCase = useMemo(() => {
    if (filteredCases.length === 0) return null;
    if (!selectedCaseId) return filteredCases[0];
    return (
      filteredCases.find((item) => item.case_id === selectedCaseId) ??
      filteredCases[0]
    );
  }, [filteredCases, selectedCaseId]);

  return (
    <div className="space-y-6 bg-background text-foreground">
      <header className="space-y-1">
        <h1 className="text-3xl font-display font-semibold">Case Management</h1>
        <p className="text-foreground-secondary">
          Review, escalate, and resolve investigation cases.
        </p>
      </header>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <MetricCard
          title="Total Cases"
          value={cases.length}
          color="blue"
          icon={<Folder className="h-5 w-5" />}
        />
        <MetricCard
          title="Open"
          value={
            cases.filter(
              (c) => c.status === "open" || c.status === "under_investigation",
            ).length
          }
          color="yellow"
          icon={<Clock3 className="h-5 w-5" />}
        />
        <MetricCard
          title="Escalated"
          value={cases.filter((c) => c.status === "escalated").length}
          color="orange"
          icon={<AlertTriangle className="h-5 w-5" />}
        />
        <MetricCard
          title="SAR Filed"
          value={cases.filter((c) => c.status === "sar_filed").length}
          color="red"
          icon={<FileText className="h-5 w-5" />}
          glow
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-[420px_1fr]">
        <Card className="h-[calc(100vh-16rem)] overflow-hidden border-border shadow-sm bg-white flex flex-col">
          <CardHeader className="space-y-3 pb-4">
            <CardTitle className="text-base text-foreground font-semibold">
              Case Queue
            </CardTitle>
            <div className="grid gap-2">
              <Input
                placeholder="Search by case, entity, description..."
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
                  className="h-10 rounded-lg border border-border-default bg-bg-overlay px-3 text-sm"
                  value={filters.status}
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      status: event.target.value,
                    }))
                  }
                >
                  <option value="all">All statuses</option>
                  <option value="open">Open</option>
                  <option value="under_investigation">
                    Under Investigation
                  </option>
                  <option value="escalated">Escalated</option>
                  <option value="closed">Closed</option>
                  <option value="sar_filed">SAR Filed</option>
                </select>

                <select
                  className="h-10 rounded-lg border border-border-default bg-bg-overlay px-3 text-sm"
                  value={filters.severity}
                  onChange={(event) =>
                    setFilters((current) => ({
                      ...current,
                      severity: event.target.value,
                    }))
                  }
                >
                  <option value="all">All severities</option>
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>
            </div>
          </CardHeader>

          <CardContent className="h-[calc(100%-12rem)] overflow-auto pt-0">
            <LoadingBoundary
              loading={casesQuery.isLoading}
              error={casesQuery.error as Error | undefined}
              isEmpty={filteredCases.length === 0}
              emptyMessage="No cases found"
              emptyDescription="Try adjusting filters or search terms."
              minHeight="220px"
            >
              <div className="space-y-2">
                {filteredCases.map((caseItem) => (
                  <CaseQueueRow
                    key={caseItem.case_id}
                    caseItem={caseItem}
                    active={selectedCase?.case_id === caseItem.case_id}
                    onSelect={setSelectedCaseId}
                  />
                ))}
              </div>
            </LoadingBoundary>
          </CardContent>
        </Card>

        <Card className="h-[calc(100vh-16rem)] overflow-auto border-border shadow-sm bg-white">
          <CardHeader>
            <CardTitle className="text-base text-foreground font-semibold">
              Case Detail
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!selectedCase ? (
              <EmptyState
                title="No case selected"
                description="Select a case from the queue to inspect details and actions."
                variant="no-results"
                compact
              />
            ) : (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-sm font-semibold">
                    {selectedCase.case_id}
                  </span>
                  <RiskBadge level={toRiskLevel(selectedCase.severity)}>
                    {selectedCase.severity}
                  </RiskBadge>
                  <StatusBadge
                    status={toStatusBadgeStatus(selectedCase.status)}
                  >
                    {selectedCase.status.replaceAll("_", " ")}
                  </StatusBadge>
                  {selectedCase.outcome ? (
                    <StatusBadge status="active">
                      {selectedCase.outcome}
                    </StatusBadge>
                  ) : null}
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <Info
                    label="Type"
                    value={selectedCase.case_type.replaceAll("_", " ")}
                  />
                  <Info
                    label="Opened"
                    value={new Date(selectedCase.opened_at).toLocaleString()}
                  />
                  <Info
                    label="Entity"
                    value={
                      selectedCase.subject_id ? (
                        <Link
                          href={`/entities/user/${selectedCase.subject_id}`}
                          className="text-primary hover:underline"
                        >
                          {selectedCase.subject_id}
                        </Link>
                      ) : (
                        "-"
                      )
                    }
                  />
                  <Info
                    label="Subject Type"
                    value={selectedCase.subject_type ?? "-"}
                  />
                  <Info
                    label="Assigned To"
                    value={selectedCase.assigned_to ?? "Unassigned"}
                  />
                  <Info
                    label="Open Duration"
                    value={relativeDays(selectedCase.opened_at)}
                  />
                </div>

                {(selectedCase.summary || selectedCase.description) && (
                  <div className="rounded-lg border border-border-subtle bg-bg-overlay p-3 text-sm text-foreground-secondary">
                    {selectedCase.summary ?? selectedCase.description}
                  </div>
                )}

                <div className="grid gap-3 md:grid-cols-2">
                  <Info
                    label="Linked Alerts"
                    value={selectedCase.related_alert_ids?.length ?? 0}
                  />
                  <Info
                    label="Linked Transactions"
                    value={selectedCase.related_transaction_ids?.length ?? 0}
                  />
                </div>

                <div className="flex flex-wrap gap-2">
                  <Link href={`/cases/${selectedCase.case_id}`}>
                    <Button variant="outline">Open Full Case</Button>
                  </Link>
                  <Button
                    variant="secondary"
                    onClick={() => setSarDrawerOpen(true)}
                  >
                    Prepare SAR
                  </Button>
                  {selectedCase.subject_id ? (
                    <Link href={`/entities/user/${selectedCase.subject_id}`}>
                      <Button variant="secondary">Open Entity Profile</Button>
                    </Link>
                  ) : null}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      <SARPrepDrawer
        open={sarDrawerOpen}
        onOpenChange={setSarDrawerOpen}
        caseId={selectedCase?.case_id}
        entityId={selectedCase?.subject_id}
      />
    </div>
  );
}

function Info({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-lg border border-border-subtle bg-bg-overlay p-3 text-sm">
      <p className="mb-1 text-xs uppercase tracking-wide text-foreground-tertiary">
        {label}
      </p>
      <p className="text-foreground">{value}</p>
    </div>
  );
}

function CaseQueueRow({
  caseItem,
  active,
  onSelect,
}: {
  caseItem: MonitoringCase;
  active: boolean;
  onSelect: (caseId: string) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(caseItem.case_id)}
      className={`w-full rounded-lg border p-3 text-left transition ${
        active
          ? "border-primary/60 bg-primary/10"
          : "border-border-subtle bg-bg-overlay hover:border-border-default"
      }`}
    >
      <div className="space-y-1">
        <div className="flex items-center justify-between gap-2">
          <p className="truncate font-mono text-sm font-medium">
            {caseItem.case_id}
          </p>
          <RiskBadge level={toRiskLevel(caseItem.severity)}>
            {caseItem.severity}
          </RiskBadge>
        </div>
        <p className="truncate text-xs text-foreground-secondary">
          {caseItem.case_type.replaceAll("_", " ")}
        </p>
        <div className="flex items-center justify-between gap-2 text-xs text-foreground-tertiary">
          <span className="truncate">
            {caseItem.subject_id ?? "No subject"}
          </span>
          <span>{relativeDays(caseItem.opened_at)}</span>
        </div>
      </div>
    </button>
  );
}
