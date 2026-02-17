"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowUpRight,
  ClipboardCheck,
  FileText,
  Gavel,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Brain,
  Eye,
  Clock,
} from "lucide-react";

import apiClient from "@/lib/http";
import { getAuthToken } from "@/lib/auth";
import { handleApiError } from "@/lib/api-error-handler";
import { MetricCard } from "@/components/ui/metric-card";
import {
  GlassCard,
  GlassCardHeader,
  GlassCardTitle,
  GlassCardContent,
} from "@/components/ui/glass-card";
import { BentoGrid, BentoItem } from "@/components/ui/bento-grid";
import { Button } from "@/components/ui/button";
import { StatusIndicator } from "@/components/ui/status-indicator";
import { CircularProgress } from "@/components/ui/progress";
import {
  Skeleton,
  SkeletonMetricCard,
  SkeletonCard,
} from "@/components/ui/skeleton";
import { EmptyStateInline } from "@/components/ui/empty-state";
import {
  staggerContainer,
  staggerItem,
  fadeInBlur,
  transitions,
  springs,
} from "@/lib/motion";
import { cn } from "@/lib/utils";
import { useFindings } from "@/hooks/queries/useWorkbenchData";
import type { Finding } from "@/types/workbench";
import { WorkbenchLayout } from "@/components/workbench/WorkbenchLayout";
import { ActivityHeatmap } from "@/components/dashboard/ActivityHeatmap";

interface Coverage {
  total_documents: number;
  celex_covered: number;
  celex_coverage_pct: number;
  rules_total: number;
  rules_with_celex: number;
  rules_coverage_pct: number;
}

interface CoverageDoc {
  id: number;
  celex: string;
  title: string;
  risk_level?: string;
  compliance_domain?: string;
}

interface CoverageRule {
  rule_id: string;
  name: string;
  severity?: string;
  category?: string;
}

interface CoverageGaps {
  celex_without_rules: CoverageDoc[];
  rules_without_celex: CoverageRule[];
}

interface RiskOps {
  pending_alerts: number;
  critical_alerts: number;
  open_cases: number;
}

interface Decisions {
  last_24h_total: number;
  breakdown: Record<string, number>;
  latest?: {
    decision_id: string;
    decision: string;
    event_id?: string | null;
    created_at: string;
    event_type?: string | null;
    entity_id?: string | null;
  } | null;
}

interface Reporting {
  sar_filed_30d: number;
  travel_pending: number;
  travel_submitted: number;
  onchain_checks_24h: number;
}

interface PolicyItem {
  id: number;
  policy_id: string;
  name: string;
  status: string;
  owner?: string | null;
  updated_at?: string | null;
}

interface PolicySummary {
  total: number;
  by_status: Record<string, number>;
  items: PolicyItem[];
}

interface IntakeDoc {
  id: number;
  celex: string;
  title: string;
  jurisdiction?: string | null;
  source_system?: string | null;
  publication_date?: string | null;
  last_modified?: string | null;
  oj_act_identifier?: string | null;
  oj_signature_identifier?: string | null;
}

interface PendingObligation {
  id: number;
  obligation_id: string;
  status: string;
  article_ref?: string | null;
  summary: string;
  doc_id: number;
  celex: string;
  doc_title: string;
  updated_at?: string | null;
}

interface RegulatoryIntake {
  new_documents: {
    total_7d: number;
    by_jurisdiction: Record<string, number>;
    items: IntakeDoc[];
  };
  pending_obligations: {
    total: number;
    items: PendingObligation[];
  };
}

interface HomeDashboard {
  coverage: Coverage;
  coverage_gaps: CoverageGaps;
  risk_ops: RiskOps;
  decisions: Decisions;
  reporting: Reporting;
  policy_summary?: PolicySummary;
  regulatory_intake?: RegulatoryIntake;
  official_journal?: {
    acts_total: number;
    latest_publication_date?: string | null;
    last_ingested_at?: string | null;
  };
}

const decisionOrder = ["allow", "step-up", "alert", "block"] as const;
const decisionConfig: Record<
  (typeof decisionOrder)[number],
  { label: string; color: string; bg: string }
> = {
  allow: { label: "Allow", color: "text-risk-low", bg: "bg-risk-low-soft" },
  "step-up": {
    label: "Step-up",
    color: "text-risk-medium",
    bg: "bg-risk-medium-soft",
  },
  alert: { label: "Alert", color: "text-risk-clear", bg: "bg-risk-clear-soft" },
  block: {
    label: "Block",
    color: "text-risk-critical",
    bg: "bg-risk-critical-soft",
  },
};

const formatDate = (value?: string | null) => {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return parsed.toLocaleDateString();
};

export default function DashboardPage() {
  const [data, setData] = useState<HomeDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [hasToken, setHasToken] = useState(false);
  const [intakeDays] = useState(7);
  const [intakeJurisdiction] = useState("all");
  const [intakeSource] = useState("all");
  const [obligationFilter] = useState("pending");
  const [scopeFilter, setScopeFilter] = useState("psp,eme,vasp");

  useEffect(() => {
    setHasToken(!!getAuthToken());
    setAuthReady(true);
  }, []);

  useEffect(() => {
    if (!hasToken) {
      setLoading(false);
      return;
    }

    let mounted = true;

    const fetchData = async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        params.set("intake_days", String(intakeDays));
        params.set("intake_limit", "8");
        params.set("obligation_limit", "8");
        if (intakeJurisdiction !== "all") {
          params.set("intake_jurisdiction", intakeJurisdiction);
        }
        if (intakeSource !== "all") {
          params.set("intake_source", intakeSource);
        }
        if (scopeFilter !== "all") {
          params.set("scope", scopeFilter);
        }
        if (obligationFilter !== "all") {
          const statusValue =
            obligationFilter === "pending"
              ? "draft,in_review"
              : obligationFilter;
          params.set("obligation_status", statusValue);
        }

        const response = await apiClient.get<HomeDashboard>(
          `/api/reporting/dashboard/home?${params.toString()}`,
        );
        if (!mounted) return;
        setData(response.data);
        setError(null);
      } catch (err) {
        const apiError = handleApiError(err, {
          context: "Dashboard home",
          customMessage: "Failed to load dashboard data",
        });
        if (mounted) {
          setError(apiError.message);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    fetchData();

    return () => {
      mounted = false;
    };
  }, [
    hasToken,
    intakeDays,
    intakeJurisdiction,
    intakeSource,
    obligationFilter,
    scopeFilter,
  ]);

  if (authReady && !hasToken) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <GlassCard className="max-w-md">
          <GlassCardContent className="text-center py-8">
            <div className="h-12 w-12 rounded-full bg-risk-critical-soft flex items-center justify-center mx-auto mb-4">
              <ShieldAlert className="h-6 w-6 text-risk-critical" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">
              Session Required
            </h3>
            <p className="text-white/50 text-sm mb-4">
              Please sign in to access the command center.
            </p>
            <Link href="/login">
              <Button variant="gradient">Sign In</Button>
            </Link>
          </GlassCardContent>
        </GlassCard>
      </div>
    );
  }

  if (loading) {
    return (
      <motion.div
        variants={staggerContainer}
        initial="initial"
        animate="animate"
        className="space-y-8"
      >
        {/* Header skeleton */}
        <motion.div variants={staggerItem} className="space-y-3">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-10 w-80" />
          <Skeleton className="h-5 w-[500px]" />
        </motion.div>

        {/* Metrics skeleton */}
        <motion.div
          variants={staggerItem}
          className="grid gap-4 md:grid-cols-2 xl:grid-cols-4"
        >
          {[1, 2, 3, 4].map((i) => (
            <SkeletonMetricCard key={i} />
          ))}
        </motion.div>

        {/* Cards skeleton */}
        <motion.div
          variants={staggerItem}
          className="grid gap-6 lg:grid-cols-2"
        >
          <SkeletonCard contentLines={4} hasFooter />
          <SkeletonCard contentLines={4} hasFooter />
        </motion.div>
      </motion.div>
    );
  }

  if (error) {
    return (
      <motion.div
        variants={fadeInBlur}
        initial="initial"
        animate="animate"
        className="flex min-h-[400px] items-center justify-center"
      >
        <GlassCard glow="critical" className="max-w-md">
          <GlassCardContent className="text-center py-8">
            <div className="h-12 w-12 rounded-full bg-risk-critical-soft flex items-center justify-center mx-auto mb-4">
              <AlertTriangle className="h-6 w-6 text-risk-critical" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">
              Error Loading Dashboard
            </h3>
            <p className="text-white/50 text-sm mb-4">{error}</p>
            <Button variant="glass" onClick={() => window.location.reload()}>
              Try Again
            </Button>
          </GlassCardContent>
        </GlassCard>
      </motion.div>
    );
  }

  const coverage = data?.coverage;
  const riskOps = data?.risk_ops;
  const decisions = data?.decisions;
  const reporting = data?.reporting;
  // Policy summary is reserved for future policy management features

  const _policySummary = data?.policy_summary;
  const intake = data?.regulatory_intake;
  const pendingObligations = intake?.pending_obligations.total ?? 0;
  const criticalAlerts = riskOps?.critical_alerts ?? 0;

  return (
    <WorkbenchLayout
      title="Compliance Command deck"
      discoveryRail={
        <div className="space-y-6">
          <div className="space-y-2">
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-white/40 px-2">
              Live Signals
            </h3>
            <div className="space-y-2">
              {data?.risk_ops && (
                <div className="grid grid-cols-2 gap-2 px-2">
                  <div className="rounded-xl bg-white/5 p-3 border border-white/5">
                    <div className="text-[10px] text-white/40">Alerts</div>
                    <div className="text-lg font-bold text-white font-mono">
                      {riskOps?.pending_alerts}
                    </div>
                  </div>
                  <div className="rounded-xl bg-white/5 p-3 border border-white/5">
                    <div className="text-[10px] text-white/40">Cases</div>
                    <div className="text-lg font-bold text-white font-mono">
                      {riskOps?.open_cases}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="px-2">
            <FindingsTriageWidget />
          </div>
        </div>
      }
      workspace={
        <motion.div
          variants={staggerContainer}
          initial="initial"
          animate="animate"
          className="space-y-8"
        >
          {/* Header */}
          <motion.header
            variants={staggerItem}
            className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between"
          >
            <div>
              <div className="flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-accent/70 mb-2">
                <Sparkles className="h-3.5 w-3.5" />
                Command Center
              </div>
              <h1 className="text-3xl font-bold tracking-tight text-white font-display">
                Compliance Briefing
              </h1>
            </div>

            <motion.div
              className="flex items-center gap-3"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={transitions.default}
            >
              <StatusIndicator status="live" label="Telemetry Active" />
            </motion.div>
          </motion.header>

          {/* Key Metrics */}
          <motion.div variants={staggerItem}>
            <BentoGrid columns={3} gap="md">
              <MetricCard
                title="New Texts (7d)"
                value={intake?.new_documents.total_7d ?? 0}
                icon={<FileText className="h-5 w-5" />}
                color="cyan"
              />
              <MetricCard
                title="Pending Obligations"
                value={pendingObligations}
                icon={<ClipboardCheck className="h-5 w-5" />}
                color="orange"
                glow={pendingObligations > 0}
              />
              <MetricCard
                title="Critical Alerts"
                value={criticalAlerts}
                icon={<ShieldAlert className="h-5 w-5" />}
                color="red"
                glow={criticalAlerts > 0}
                status={criticalAlerts > 0 ? "error" : "live"}
              />
            </BentoGrid>
          </motion.div>

          {/* Regulatory Intake */}
          <motion.div
            variants={staggerItem}
            className="grid gap-6 lg:grid-cols-1"
          >
            <GlassCard>
              <GlassCardHeader className="flex items-start justify-between">
                <div>
                  <GlassCardTitle>Regulatory Intake</GlassCardTitle>
                  <p className="text-xs text-white/40 mt-1">
                    New EU/FR texts ({intakeDays}d)
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={scopeFilter}
                    onChange={(event) => setScopeFilter(event.target.value)}
                    className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[11px] font-medium text-white/70 focus:outline-none"
                  >
                    <option value="psp,eme,vasp">PSP / EMI / VASP</option>
                    <option value="all">All scopes</option>
                  </select>
                </div>
              </GlassCardHeader>
              <GlassCardContent>
                <div className="grid gap-4 sm:grid-cols-2">
                  {intake?.new_documents.items?.length ? (
                    intake.new_documents.items.slice(0, 4).map((doc) => (
                      <Link
                        key={doc.id}
                        href={"/doc/" + doc.celex}
                        className="block p-4 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.04] hover:border-white/[0.08] transition-all"
                      >
                        <div className="text-sm font-medium text-white hover:text-accent transition-colors">
                          {doc.celex}
                        </div>
                        <p className="text-xs text-white/40 mt-1 line-clamp-2">
                          {doc.title ?? doc.celex ?? "Untitled document"}
                        </p>
                        <div className="flex items-center gap-2 mt-2 text-[10px] text-white/30">
                          <span>{doc.jurisdiction?.toUpperCase() ?? "EU"}</span>
                          <span>•</span>
                          <span>{formatDate(doc.publication_date)}</span>
                        </div>
                      </Link>
                    ))
                  ) : (
                    <EmptyStateInline message="No new documents captured." />
                  )}
                </div>
              </GlassCardContent>
            </GlassCard>
          </motion.div>

          {/* Reporting Section */}
          <motion.div
            variants={staggerItem}
            className="grid gap-6 lg:grid-cols-2"
          >
            <GlassCard variant="interactive">
              <GlassCardHeader>
                <GlassCardTitle>Evidence & SARs</GlassCardTitle>
              </GlassCardHeader>
              <GlassCardContent>
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                    <div className="text-[10px] uppercase text-white/30">
                      SAR Filed
                    </div>
                    <div className="text-lg font-bold text-white mt-1">
                      {reporting?.sar_filed_30d ?? 0}
                    </div>
                  </div>
                  <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                    <div className="text-[10px] uppercase text-white/30">
                      On-chain
                    </div>
                    <div className="text-lg font-bold text-white mt-1">
                      {reporting?.onchain_checks_24h ?? 0}
                    </div>
                  </div>
                </div>
              </GlassCardContent>
            </GlassCard>

            <GlassCard variant="interactive">
              <GlassCardHeader>
                <GlassCardTitle>Coverage</GlassCardTitle>
              </GlassCardHeader>
              <GlassCardContent>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-white/40">EU Mapped</span>
                  <span className="text-sm font-bold text-cyan-400">
                    {coverage?.celex_coverage_pct ?? 0}%
                  </span>
                </div>
                <div className="mt-2 h-1 w-full bg-white/5 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-cyan-500 shadow-[0_0_8px_rgba(0,212,255,0.4)]"
                    style={{ width: `${coverage?.celex_coverage_pct ?? 0}%` }}
                  />
                </div>
              </GlassCardContent>
            </GlassCard>
          </motion.div>

          {/* ════════════════════════════════════════════════════════════════
                    COVERAGE & REPORTING
                    ════════════════════════════════════════════════════════════════ */}
          <motion.div
            variants={staggerItem}
            className="grid gap-6 lg:grid-cols-2"
          >
            {/* Coverage */}
            <GlassCard variant="interactive">
              <GlassCardHeader className="flex items-center justify-between">
                <div>
                  <GlassCardTitle>Regulatory Coverage</GlassCardTitle>
                  <p className="text-sm text-white/40 mt-1">
                    CELEX = EU anchor. Each rule must be linked to a source.
                  </p>
                </div>
                <Link href="/transaction-monitoring/rules/lab">
                  <Button
                    variant="ghost"
                    size="sm"
                    rightIcon={<ArrowUpRight className="h-4 w-4" />}
                  >
                    Map
                  </Button>
                </Link>
              </GlassCardHeader>
              <GlassCardContent>
                <div className="grid gap-4 sm:grid-cols-2 mb-4">
                  <div className="p-4 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs uppercase tracking-wider text-white/30">
                        CELEX Mapped
                      </span>
                      <CircularProgress
                        value={coverage?.celex_coverage_pct ?? 0}
                        size={48}
                        color="cyan"
                        showLabel
                      />
                    </div>
                    <div className="text-xl font-bold text-white font-mono">
                      {coverage?.celex_covered ?? 0}
                      <span className="text-sm text-white/40 font-normal">
                        {" "}
                        / {coverage?.total_documents ?? 0}
                      </span>
                    </div>
                  </div>
                  <div className="p-4 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs uppercase tracking-wider text-white/30">
                        Rules Mapped
                      </span>
                      <CircularProgress
                        value={coverage?.rules_coverage_pct ?? 0}
                        size={48}
                        color="aurora"
                        showLabel
                      />
                    </div>
                    <div className="text-xl font-bold text-white font-mono">
                      {coverage?.rules_with_celex ?? 0}
                      <span className="text-sm text-white/40 font-normal">
                        {" "}
                        / {coverage?.rules_total ?? 0}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-primary/5 border border-primary/10">
                  <p className="text-xs text-primary">
                    CELEX ensures EU regulatory traceability; for France we use
                    JORF/NOR.
                  </p>
                </div>
              </GlassCardContent>
            </GlassCard>

            {/* Reporting */}
            <GlassCard variant="interactive">
              <GlassCardHeader className="flex items-center justify-between">
                <div>
                  <GlassCardTitle>Evidence & Reporting</GlassCardTitle>
                  <p className="text-sm text-white/40 mt-1">
                    Filing tracking and audit checkpoints.
                  </p>
                </div>
                <Link href="/sar/prepare">
                  <Button
                    variant="ghost"
                    size="sm"
                    rightIcon={<ArrowUpRight className="h-4 w-4" />}
                  >
                    Prepare SAR
                  </Button>
                </Link>
              </GlassCardHeader>
              <GlassCardContent>
                <div className="grid gap-4 sm:grid-cols-2 mb-4">
                  <div className="p-4 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                    <div className="text-xs uppercase tracking-wider text-white/30">
                      SAR Filed (30d)
                    </div>
                    <div className="text-2xl font-bold text-white font-mono mt-2">
                      {reporting?.sar_filed_30d ?? 0}
                    </div>
                  </div>
                  <div className="p-4 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                    <div className="text-xs uppercase tracking-wider text-white/30">
                      On-chain Checks (24h)
                    </div>
                    <div className="text-2xl font-bold text-white font-mono mt-2">
                      {reporting?.onchain_checks_24h ?? 0}
                    </div>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2">
                  <Link href="/travel-rule">
                    <Button
                      variant="glass"
                      size="sm"
                      leftIcon={<FileText className="h-4 w-4" />}
                    >
                      Travel Rule Inbox
                    </Button>
                  </Link>
                  <Link href="/onchain-risk">
                    <Button
                      variant="glass"
                      size="sm"
                      leftIcon={<ShieldAlert className="h-4 w-4" />}
                    >
                      On-chain Risk
                    </Button>
                  </Link>
                </div>
              </GlassCardContent>
            </GlassCard>
          </motion.div>

          {/* ════════════════════════════════════════════════════════════════
                    QUICK ACTIONS
                    ════════════════════════════════════════════════════════════════ */}
          <motion.div variants={staggerItem}>
            <BentoGrid columns={4} gap="md">
              {[
                {
                  title: "Rules Lab",
                  description:
                    "Edit rules, propose updates, submit for approval.",
                  href: "/transaction-monitoring/rules/lab",
                  icon: ClipboardCheck,
                  color: "#6d5acd",
                },
                {
                  title: "Decisioning",
                  description: "Review decisions, evidence, and appeal trails.",
                  href: "/decisioning",
                  icon: Gavel,
                  color: "#00d4ff",
                },
                {
                  title: "Case Management",
                  description: "Track open cases and escalate investigations.",
                  href: "/cases",
                  icon: FileText,
                  color: "#ffd166",
                },
                {
                  title: "Audit Trail",
                  description: "Search for evidence, actions, and approvals.",
                  href: "/audit",
                  icon: ShieldCheck,
                  color: "#06d6a0",
                },
              ].map((action) => (
                <BentoItem key={action.title} hover>
                  <Link href={action.href} className="block h-full">
                    <motion.div
                      className="h-full p-5 rounded-xl glass-interactive group"
                      whileHover={{ y: -4 }}
                      transition={springs.snappy}
                    >
                      <div className="flex items-center justify-between mb-4">
                        <div
                          className="h-10 w-10 rounded-lg flex items-center justify-center"
                          style={{ backgroundColor: `${action.color}15` }}
                        >
                          <action.icon
                            className="h-5 w-5"
                            style={{ color: action.color }}
                          />
                        </div>
                        <ArrowUpRight className="h-4 w-4 text-white/20 group-hover:text-white/60 transition-colors" />
                      </div>
                      <h3 className="text-sm font-semibold text-white">
                        {action.title}
                      </h3>
                      <p className="text-xs text-white/40 mt-1">
                        {action.description}
                      </p>
                    </motion.div>
                  </Link>
                </BentoItem>
              ))}
            </BentoGrid>
          </motion.div>
        </motion.div>
      }
      intelligencePanel={
        <div className="space-y-8">
          <div className="rounded-2xl border border-aurora-500/30 bg-aurora-500/10 p-5 shadow-[var(--shadow-glow-primary)]">
            <div className="mb-3 flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-aurora-500 text-white shadow-lg">
                <Brain size={18} />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-white">
                  AI Compliance Officer
                </h4>
                <div className="text-[10px] text-aurora-300 font-medium">
                  System Intelligence v4.2
                </div>
              </div>
            </div>
            <p className="text-xs text-white/70 leading-relaxed italic">
              &ldquo;Attention: I&apos;ve detected a {criticalAlerts}{" "}
              high-priority signals in the discovery rail that may require
              immediate SAR preparation.&rdquo;
            </p>
            <div className="mt-4 flex gap-2">
              <Link href="/aml-officer" className="flex-1">
                <Button
                  variant="gradient"
                  size="sm"
                  className="w-full text-[10px]"
                >
                  Consult AI
                </Button>
              </Link>
            </div>
          </div>

          <div className="space-y-4">
            <h4 className="text-[10px] font-bold uppercase tracking-widest text-white/40 px-2">
              Compliance Velocity
            </h4>
            <div className="space-y-3 px-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-white/50">KYC Backlog</span>
                <div className="h-1.5 w-24 rounded-full bg-white/5 overflow-hidden">
                  <div className="h-full bg-amber-500 w-[65%]" />
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-white/50">SAR Quality</span>
                <div className="h-1.5 w-24 rounded-full bg-white/5 overflow-hidden">
                  <div className="h-full bg-emerald-500 w-[92%]" />
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <h4 className="text-[10px] font-bold uppercase tracking-widest text-white/40 px-2">
              Recent Decisions
            </h4>
            <div className="space-y-2 px-2">
              {decisionOrder.slice(0, 3).map((key) => (
                <div
                  key={key}
                  className="flex items-center justify-between rounded-xl bg-white/5 p-3"
                >
                  <span
                    className={cn(
                      "text-[10px] font-bold px-2 py-0.5 rounded-lg",
                      decisionConfig[key].bg,
                      decisionConfig[key].color,
                    )}
                  >
                    {decisionConfig[key].label}
                  </span>
                  <span className="text-xs font-mono text-white/40">
                    {decisions?.breakdown?.[key] ?? 0}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <ActivityHeatmap />
        </div>
      }
    />
  );
}

/* ════════════════════════════════════════════════════════════════
          FINDINGS TRIAGE WIDGET
          ════════════════════════════════════════════════════════════════ */

const findingSeverityDot: Record<string, string> = {
  critical: "bg-red-500",
  high: "bg-orange-500",
  medium: "bg-amber-500",
  low: "bg-blue-500",
  info: "bg-gray-400",
};

function FindingsTriageWidget() {
  const { data: findings = [], isLoading } = useFindings({
    limit: 8,
    status: "open",
  });

  const openCount = findings.length;
  const criticalCount = findings.filter(
    (f) => f.severity === "critical",
  ).length;

  return (
    <GlassCard variant="interactive">
      <GlassCardHeader className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <GlassCardTitle className="flex items-center gap-2">
            <Eye className="h-5 w-5 text-blue-400" />
            Findings Triage
          </GlassCardTitle>
          <p className="text-sm text-white/40 mt-1">
            Open findings requiring action.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="text-lg font-bold text-white font-mono">
              {openCount}
            </div>
            <div className="text-[10px] uppercase tracking-wider text-white/30">
              Open
            </div>
          </div>
          {criticalCount > 0 && (
            <div className="text-right">
              <div className="text-lg font-bold text-red-400 font-mono">
                {criticalCount}
              </div>
              <div className="text-[10px] uppercase tracking-wider text-white/30">
                Critical
              </div>
            </div>
          )}
          <Link href="/findings">
            <Button
              variant="gradient"
              size="sm"
              rightIcon={<ArrowUpRight className="h-3 w-3" />}
            >
              View All
            </Button>
          </Link>
        </div>
      </GlassCardHeader>
      <GlassCardContent>
        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-14 w-full rounded-lg" />
            ))}
          </div>
        ) : findings.length === 0 ? (
          <EmptyStateInline message="No open findings. All clear!" />
        ) : (
          <div className="space-y-2">
            {findings.slice(0, 6).map((finding: Finding) => (
              <Link
                key={finding.id}
                href={`/findings/${finding.id}`}
                className="block p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.04] hover:border-white/[0.08] transition-all group"
              >
                <div className="flex items-start gap-3">
                  <div
                    className={cn(
                      "mt-1.5 h-2 w-2 rounded-full shrink-0",
                      findingSeverityDot[finding.severity] ?? "bg-gray-400",
                    )}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-white/50">
                        {finding.severity}
                      </span>
                      <span className="text-[10px] text-white/30">
                        {finding.finding_type.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-white line-clamp-1 group-hover:text-accent transition-colors">
                      {finding.title}
                    </p>
                    <p className="text-xs text-white/30 mt-0.5 line-clamp-1">
                      {finding.summary}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 text-[10px] text-white/30 shrink-0">
                    <Clock className="h-3 w-3" />
                    {new Date(finding.created_at).toLocaleDateString()}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </GlassCardContent>
    </GlassCard>
  );
}
