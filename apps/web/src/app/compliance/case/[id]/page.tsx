"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle2,
  FileSearch,
  FileText,
  FolderOpen,
  ShieldAlert,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import toast from "react-hot-toast";
import { useCopilot } from "@/components/aml-officer/copilot-context";
import { LoadingBoundary } from "@/components/shared/LoadingBoundary";
import { EmptyState } from "@/components/ui/empty-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MetricCard } from "@/components/ui/metric-card";
import { Button } from "@/components/ui/button-horizon";
import { RiskBadge, StatusBadge } from "@/components/ui/badge-horizon";
import {
  useComplianceCase,
  useReviewComplianceCase,
  useScreenComplianceCase,
  useSetComplianceCDDLevel,
  useVerifyComplianceCaseDocuments,
} from "@/hooks/queries/useComplianceData";
import type { ComplianceProfile } from "@/types/compliance";

type WorkspaceTab = "overview" | "documents" | "risk" | "actions";

function asId(value: string | string[] | undefined): number | null {
  if (typeof value !== "string") return null;
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return null;
  return parsed;
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
  if (normalized === "approved") return "approved";
  if (normalized === "rejected") return "rejected";
  if (normalized === "manual_review") return "in_review";
  if (normalized === "pending") return "pending";
  return "pending";
}

function toProfileLabel(profile: ComplianceProfile) {
  if (profile.type === "kyb") {
    return profile.company_name || `Business ${profile.id}`;
  }

  const fullName =
    `${profile.first_name ?? ""} ${profile.last_name ?? ""}`.trim();
  return fullName || profile.email || `Customer ${profile.id}`;
}

function normalizeCDDLevel(
  value?: string | null,
): "simplified" | "standard" | "enhanced" {
  const normalized = value?.toLowerCase();
  if (normalized === "simplified") return "simplified";
  if (normalized === "enhanced") return "enhanced";
  return "standard";
}

function statusTimeline(profile: ComplianceProfile) {
  const status = profile.status.toLowerCase();
  const isFinal = status === "approved" || status === "rejected";

  return [
    {
      key: "submitted",
      label: "Submitted",
      state: "done" as const,
      timestamp: profile.created_at,
    },
    {
      key: "under_review",
      label: "Under Review",
      state:
        status === "pending" || status === "manual_review"
          ? ("current" as const)
          : ("done" as const),
      timestamp: profile.updated_at,
    },
    {
      key: "decision",
      label: "Decision",
      state: isFinal ? ("done" as const) : ("pending" as const),
      timestamp: isFinal ? profile.updated_at : null,
    },
  ];
}

export default function ComplianceCaseWorkspacePage() {
  const params = useParams<{ id: string }>();
  const caseNumericId = asId(params.id);

  const [activeTab, setActiveTab] = useState<WorkspaceTab>("overview");
  const [reviewNote, setReviewNote] = useState("");
  const [cddLevelOverride, setCddLevelOverride] = useState<
    "simplified" | "standard" | "enhanced" | null
  >(null);
  const [cddReason, setCddReason] = useState("");

  const { setPageContext } = useCopilot();
  useEffect(() => {
    if (caseNumericId) {
      setPageContext(`Compliance Workspace: Review case ${caseNumericId}`);
    }
  }, [caseNumericId, setPageContext]);

  const caseQuery = useComplianceCase(caseNumericId);
  const reviewMutation = useReviewComplianceCase();
  const screenMutation = useScreenComplianceCase();
  const verifyMutation = useVerifyComplianceCaseDocuments();
  const setCDDMutation = useSetComplianceCDDLevel();

  const profile = caseQuery.data;
  const cddLevel = cddLevelOverride ?? normalizeCDDLevel(profile?.cdd_level);

  const docStats = useMemo(() => {
    const docs = profile?.documents ?? [];
    const verified = docs.filter(
      (doc) => doc.verification_status === "verified",
    ).length;
    const rejected = docs.filter(
      (doc) => doc.verification_status === "rejected",
    ).length;
    return {
      total: docs.length,
      verified,
      rejected,
    };
  }, [profile?.documents]);

  const riskSignalsCount = profile?.risk_signals.length ?? 0;

  const handleReview = async (action: "approve" | "reject") => {
    if (!profile) return;

    try {
      const request = reviewMutation.mutateAsync({
        id: profile.id,
        action,
        reason: reviewNote.trim() || undefined,
      });

      await toast.promise(request, {
        loading: `${action === "approve" ? "Approving" : "Rejecting"} case...`,
        success: `Case ${action === "approve" ? "approved" : "rejected"}.`,
        error: `Failed to ${action} case`,
      });
    } catch {
      // toast handles display
    }
  };

  const handleRequestMoreInfo = async () => {
    if (!profile) return;

    try {
      const request = setCDDMutation.mutateAsync({
        id: profile.id,
        cddLevel: "enhanced",
        reason:
          cddReason.trim() ||
          reviewNote.trim() ||
          "Additional documents required for enhanced due diligence",
      });

      await toast.promise(request, {
        loading: "Requesting additional information...",
        success: "Enhanced due diligence requested.",
        error: "Failed to request additional information",
      });
    } catch {
      // toast handles display
    }
  };

  return (
    <div className="space-y-6 bg-background text-foreground">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <Link
            href="/compliance"
            className="inline-flex items-center gap-1 text-sm text-foreground-secondary hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Compliance Queue
          </Link>

          <h1 className="text-3xl font-display font-semibold">
            Compliance Case Workspace
          </h1>
          <p className="text-foreground-secondary">
            Consolidated review surface for KYC/KYB decisions.
          </p>
        </div>

        {profile ? (
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-sm text-foreground-secondary">
              Case {profile.id}
            </span>
            <StatusBadge status={toStatusBadgeStatus(profile.status)}>
              {profile.status.replaceAll("_", " ")}
            </StatusBadge>
            <RiskBadge level={profile.risk_level}>
              {profile.risk_level}
            </RiskBadge>
          </div>
        ) : null}
      </header>

      <LoadingBoundary
        loading={caseQuery.isLoading}
        error={caseQuery.error as Error | undefined}
        isEmpty={!profile}
        emptyMessage="Compliance case not found"
        emptyDescription="The selected application could not be loaded."
        minHeight="280px"
      >
        {profile ? (
          <>
            <section className="grid grid-cols-1 gap-4 md:grid-cols-4">
              <MetricCard
                title="Documents"
                value={docStats.total}
                color="cyan"
                icon={<FileText className="h-5 w-5" />}
              />
              <MetricCard
                title="Verified"
                value={docStats.verified}
                color="green"
                icon={<CheckCircle2 className="h-5 w-5" />}
              />
              <MetricCard
                title="Risk Signals"
                value={riskSignalsCount}
                color={riskSignalsCount > 0 ? "orange" : "blue"}
                icon={<ShieldAlert className="h-5 w-5" />}
              />
              <MetricCard
                title="CDD Level"
                value={(profile.cdd_level ?? "standard").toUpperCase()}
                color={
                  profile.cdd_level?.toLowerCase() === "enhanced"
                    ? "red"
                    : "blue"
                }
                icon={<ShieldCheck className="h-5 w-5" />}
              />
            </section>

            <section className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_340px]">
              <Card className="border-border shadow-sm bg-white">
                <CardHeader className="gap-3">
                  <CardTitle className="text-base font-semibold text-foreground">
                    {toProfileLabel(profile)}
                  </CardTitle>

                  <div className="flex flex-wrap gap-2">
                    {(
                      [
                        "overview",
                        "documents",
                        "risk",
                        "actions",
                      ] as WorkspaceTab[]
                    ).map((tab) => (
                      <Button
                        key={tab}
                        size="sm"
                        variant={activeTab === tab ? "primary" : "outline"}
                        onClick={() => setActiveTab(tab)}
                      >
                        {tab}
                      </Button>
                    ))}
                  </div>
                </CardHeader>

                <CardContent className="space-y-4">
                  {activeTab === "overview" ? (
                    <div className="grid gap-3 text-sm md:grid-cols-2">
                      <InfoField
                        label="Profile Type"
                        value={profile.type.toUpperCase()}
                      />
                      <InfoField
                        label="Status"
                        value={profile.status.replaceAll("_", " ")}
                      />
                      <InfoField label="Email" value={profile.email || "-"} />
                      <InfoField
                        label="Phone"
                        value={profile.phone_number || "-"}
                      />
                      <InfoField
                        label="Jurisdiction"
                        value={profile.jurisdiction || profile.country || "-"}
                      />
                      <InfoField
                        label="Source of Funds"
                        value={profile.source_of_funds || "-"}
                      />
                      <InfoField
                        label="Created"
                        value={new Date(profile.created_at).toLocaleString()}
                      />
                      <InfoField
                        label="Updated"
                        value={new Date(profile.updated_at).toLocaleString()}
                      />
                    </div>
                  ) : null}

                  {activeTab === "documents" ? (
                    (profile.documents ?? []).length === 0 ? (
                      <EmptyState
                        title="No documents uploaded"
                        description="Document verification results will appear once submissions are attached."
                        variant="no-data"
                        compact
                      />
                    ) : (
                      <div className="space-y-2">
                        {(profile.documents ?? []).map((document) => (
                          <div
                            key={document.id}
                            className="rounded-lg border border-border-subtle bg-background-overlay p-3"
                          >
                            <div className="mb-1 flex items-center justify-between gap-2">
                              <p className="text-sm font-medium text-foreground">
                                {document.document_type.replaceAll("_", " ")}
                              </p>
                              <StatusBadge
                                status={
                                  document.verification_status === "verified"
                                    ? "approved"
                                    : document.verification_status ===
                                        "rejected"
                                      ? "rejected"
                                      : "in_review"
                                }
                              >
                                {document.verification_status}
                              </StatusBadge>
                            </div>
                            <p className="text-xs text-foreground-secondary">
                              Uploaded{" "}
                              {new Date(document.uploaded_at).toLocaleString()}
                            </p>
                            <a
                              href={document.file_url}
                              target="_blank"
                              rel="noreferrer"
                              className="mt-2 inline-flex text-xs text-primary hover:underline"
                            >
                              Open document
                            </a>
                          </div>
                        ))}
                      </div>
                    )
                  ) : null}

                  {activeTab === "risk" ? (
                    (profile.risk_signals ?? []).length === 0 ? (
                      <EmptyState
                        title="No risk signals"
                        description="No risk signal has been generated for this profile yet."
                        variant="no-results"
                        compact
                      />
                    ) : (
                      <div className="space-y-2">
                        {(profile.risk_signals ?? []).map((signal) => (
                          <div
                            key={signal.id}
                            className="rounded-lg border border-border-subtle bg-background-overlay p-3"
                          >
                            <div className="mb-1 flex items-center justify-between gap-2">
                              <p className="text-sm font-medium text-foreground">
                                {signal.signal_type.replaceAll("_", " ")}
                              </p>
                              <span className="text-xs font-semibold text-risk-high">
                                Score {signal.score}
                              </span>
                            </div>
                            <p className="text-xs text-foreground-secondary">
                              {signal.description || "No additional detail."}
                            </p>
                            <p className="mt-1 text-[11px] text-foreground-tertiary">
                              Detected{" "}
                              {new Date(signal.detected_at).toLocaleString()}
                            </p>
                          </div>
                        ))}
                      </div>
                    )
                  ) : null}

                  {activeTab === "actions" ? (
                    <div className="space-y-3">
                      <label className="space-y-1 text-xs text-foreground-secondary">
                        <span>
                          Decision notes (required for rejection/request info)
                        </span>
                        <textarea
                          value={reviewNote}
                          onChange={(event) =>
                            setReviewNote(event.target.value)
                          }
                          rows={4}
                          className="w-full rounded-lg border border-border bg-background-overlay px-3 py-2 text-sm"
                        />
                      </label>

                      <div className="flex flex-wrap gap-2">
                        <Button
                          onClick={() => handleReview("approve")}
                          loading={reviewMutation.isPending}
                        >
                          Approve
                        </Button>
                        <Button
                          variant="secondary"
                          onClick={handleRequestMoreInfo}
                          loading={setCDDMutation.isPending}
                        >
                          Request More Info
                        </Button>
                        <Button
                          variant="destructive"
                          onClick={() => handleReview("reject")}
                          loading={reviewMutation.isPending}
                          disabled={reviewNote.trim().length === 0}
                        >
                          Reject
                        </Button>
                      </div>

                      <div className="rounded-lg border border-border-subtle bg-background-overlay p-3">
                        <p className="mb-2 text-xs uppercase tracking-wide text-foreground-tertiary">
                          Operational Actions
                        </p>
                        <div className="flex flex-wrap gap-2">
                          <Button
                            variant="outline"
                            onClick={() => {
                              if (!profile) return;
                              toast.promise(
                                screenMutation.mutateAsync(profile.id),
                                {
                                  loading: "Running screening...",
                                  success: "Screening completed",
                                  error: "Screening failed",
                                },
                              );
                            }}
                            loading={screenMutation.isPending}
                          >
                            <FileSearch className="h-4 w-4" />
                            Run Screening
                          </Button>
                          <Button
                            variant="outline"
                            onClick={() => {
                              if (!profile) return;
                              toast.promise(
                                verifyMutation.mutateAsync(profile.id),
                                {
                                  loading: "Verifying documents...",
                                  success: "Document verification completed",
                                  error: "Document verification failed",
                                },
                              );
                            }}
                            loading={verifyMutation.isPending}
                          >
                            <FolderOpen className="h-4 w-4" />
                            Verify Documents
                          </Button>
                        </div>
                      </div>
                    </div>
                  ) : null}
                </CardContent>
              </Card>

              <div className="space-y-4">
                <Card className="border-border shadow-sm bg-white">
                  <CardHeader>
                    <CardTitle className="text-base font-semibold text-foreground">
                      Verification Pipeline
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {statusTimeline(profile).map((step) => (
                      <div
                        key={step.key}
                        className="rounded-lg border border-border-subtle bg-background-overlay p-2"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-sm font-medium text-foreground">
                            {step.label}
                          </p>
                          <StatusBadge
                            status={
                              step.state === "done"
                                ? "approved"
                                : step.state === "current"
                                  ? "in_review"
                                  : "pending"
                            }
                          >
                            {step.state}
                          </StatusBadge>
                        </div>
                        {step.timestamp ? (
                          <p className="mt-1 text-[11px] text-foreground-tertiary">
                            {new Date(step.timestamp).toLocaleString()}
                          </p>
                        ) : null}
                      </div>
                    ))}
                  </CardContent>
                </Card>

                <Card className="border-border shadow-sm bg-white">
                  <CardHeader>
                    <CardTitle className="text-base font-semibold text-foreground">
                      Enhanced Due Diligence
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <label className="space-y-1 text-xs text-foreground-secondary">
                      <span>CDD Level</span>
                      <select
                        value={cddLevel}
                        onChange={(event) =>
                          setCddLevelOverride(
                            event.target.value as
                              | "simplified"
                              | "standard"
                              | "enhanced",
                          )
                        }
                        className="h-10 w-full rounded-lg border border-border bg-background-overlay px-3 text-sm"
                      >
                        <option value="simplified">Simplified</option>
                        <option value="standard">Standard</option>
                        <option value="enhanced">Enhanced</option>
                      </select>
                    </label>

                    <label className="space-y-1 text-xs text-foreground-secondary">
                      <span>Reason</span>
                      <textarea
                        value={cddReason}
                        onChange={(event) => setCddReason(event.target.value)}
                        rows={3}
                        className="w-full rounded-lg border border-border bg-background-overlay px-3 py-2 text-sm"
                      />
                    </label>

                    <Button
                      variant="secondary"
                      loading={setCDDMutation.isPending}
                      onClick={() => {
                        if (!profile) return;
                        toast.promise(
                          setCDDMutation.mutateAsync({
                            id: profile.id,
                            cddLevel,
                            reason: cddReason.trim() || undefined,
                          }),
                          {
                            loading: "Updating CDD level...",
                            success: "CDD level updated",
                            error: "Failed to update CDD level",
                          },
                        );
                      }}
                    >
                      Update CDD
                    </Button>

                    <div className="rounded-lg border border-border-subtle bg-background p-2 text-xs text-foreground-secondary">
                      Current sanctions status:{" "}
                      {profile.sanctions_status || "pending"}
                    </div>
                  </CardContent>
                </Card>

                <Card className="border-border shadow-sm bg-white">
                  <CardHeader>
                    <CardTitle className="text-base font-semibold text-foreground">
                      Case Metadata
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-1 text-xs text-foreground-secondary">
                    <p>
                      <span className="text-foreground-tertiary">Case ID:</span>{" "}
                      <span className="font-mono">{profile.id}</span>
                    </p>
                    <p>
                      <span className="text-foreground-tertiary">Entity:</span>{" "}
                      <span className="inline-flex items-center gap-1">
                        <UserRound className="h-3.5 w-3.5" />{" "}
                        {toProfileLabel(profile)}
                      </span>
                    </p>
                    <p>
                      <span className="text-foreground-tertiary">
                        Last Updated:
                      </span>{" "}
                      {new Date(profile.updated_at).toLocaleString()}
                    </p>
                  </CardContent>
                </Card>
              </div>
            </section>
          </>
        ) : null}
      </LoadingBoundary>
    </div>
  );
}

function InfoField({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border-subtle bg-background-overlay p-3">
      <p className="text-[11px] uppercase tracking-wide text-foreground-tertiary">
        {label}
      </p>
      <p className="mt-1 text-sm text-foreground">{value}</p>
    </div>
  );
}
