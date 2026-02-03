"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowUpRight,
  BadgeCheck,
  ClipboardCheck,
  FileText,
  ScrollText,
  Gavel,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Brain,
  Zap,
} from "lucide-react";

import apiClient from "@/lib/http";
import { getAuthToken } from "@/lib/auth";
import { handleApiError } from "@/lib/api-error-handler";
import { MetricCard } from "@/components/ui/metric-card";
import { GlassCard, GlassCardHeader, GlassCardTitle, GlassCardContent } from "@/components/ui/glass-card";
import { BentoGrid, BentoItem } from "@/components/ui/bento-grid";
import { Button } from "@/components/ui/button";
import { StatusIndicator } from "@/components/ui/status-indicator";
import { CircularProgress } from "@/components/ui/progress";
import { Skeleton, SkeletonMetricCard, SkeletonCard } from "@/components/ui/skeleton";
import { EmptyStateInline } from "@/components/ui/empty-state";
import { staggerContainer, staggerItem, fadeInBlur, transitions, springs } from "@/lib/motion";
import { cn } from "@/lib/utils";

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
const decisionConfig: Record<(typeof decisionOrder)[number], { label: string; color: string; bg: string }> = {
  allow: { label: "Allow", color: "text-[#06d6a0]", bg: "bg-[#06d6a0]/10" },
  "step-up": { label: "Step-up", color: "text-[#ffd166]", bg: "bg-[#ffd166]/10" },
  alert: { label: "Alert", color: "text-[#00d4ff]", bg: "bg-[#00d4ff]/10" },
  block: { label: "Block", color: "text-[#ff3366]", bg: "bg-[#ff3366]/10" },
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
          `/api/reporting/dashboard/home?${params.toString()}`
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
  }, [hasToken, intakeDays, intakeJurisdiction, intakeSource, obligationFilter, scopeFilter]);


  if (authReady && !hasToken) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <GlassCard className="max-w-md">
          <GlassCardContent className="text-center py-8">
            <div className="h-12 w-12 rounded-full bg-[#ff3366]/10 flex items-center justify-center mx-auto mb-4">
              <ShieldAlert className="h-6 w-6 text-[#ff3366]" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">Session Required</h3>
            <p className="text-white/50 text-sm mb-4">Please sign in to access the command center.</p>
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
        <motion.div variants={staggerItem} className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <SkeletonMetricCard key={i} />
          ))}
        </motion.div>

        {/* Cards skeleton */}
        <motion.div variants={staggerItem} className="grid gap-6 lg:grid-cols-2">
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
            <div className="h-12 w-12 rounded-full bg-[#ff3366]/10 flex items-center justify-center mx-auto mb-4">
              <AlertTriangle className="h-6 w-6 text-[#ff3366]" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">Error Loading Dashboard</h3>
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
  const policySummary = data?.policy_summary;
  const intake = data?.regulatory_intake;
  const officialJournal = data?.official_journal;
  const pendingObligations = intake?.pending_obligations.total ?? 0;
  const pendingObligationItems = intake?.pending_obligations.items ?? [];
  const policyItems = policySummary?.items ?? [];
  const policiesInReview =
    (policySummary?.by_status?.draft ?? 0) + (policySummary?.by_status?.in_review ?? 0);
  const criticalAlerts = riskOps?.critical_alerts ?? 0;
  const openCases = riskOps?.open_cases ?? 0;

  return (
    <motion.div
      variants={staggerContainer}
      initial="initial"
      animate="animate"
      className="space-y-8"
    >
      {/* ════════════════════════════════════════════════════════════════
          HEADER - Command Center Title
          ════════════════════════════════════════════════════════════════ */}
      <motion.header variants={staggerItem} className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-[#00d4ff]/70 mb-2">
            <Sparkles className="h-3.5 w-3.5" />
            Command Center
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white font-display">
            Compliance Briefing
          </h1>
          <p className="text-white/50 mt-2 max-w-2xl">
            Regulation → Internal Controls → Auditable Evidence. Operational overview for PSP / EME / VASP.
          </p>
        </div>

        <motion.div
          className="flex items-center gap-3"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={transitions.default}
        >
          <StatusIndicator status="live" label="Telemetry Active" />
          <Link href="/aml-officer">
            <Button variant="gradient" size="sm" leftIcon={<Brain className="h-4 w-4" />}>
              AI Officer
            </Button>
          </Link>
        </motion.div>
      </motion.header>

      {/* ════════════════════════════════════════════════════════════════
          KEY METRICS - Primary KPIs
          ════════════════════════════════════════════════════════════════ */}
      <motion.div variants={staggerItem}>
        <BentoGrid columns={4} gap="md">
          <MetricCard
            title="New Texts (7d)"
            value={intake?.new_documents.total_7d ?? 0}
            icon={<FileText className="h-5 w-5" />}
            color="cyan"
            trend={{
              direction: (intake?.new_documents.total_7d ?? 0) > 0 ? "up" : "neutral",
              value: String(intake?.new_documents.total_7d ?? 0),
            }}
          />
          <MetricCard
            title="Pending Obligations"
            value={pendingObligations}
            icon={<ClipboardCheck className="h-5 w-5" />}
            color="orange"
            trend={{
              direction: pendingObligations > 0 ? "up" : "neutral",
              value: String(pendingObligations),
            }}
            glow={pendingObligations > 0}
          />
          <MetricCard
            title="Policies in Review"
            value={policiesInReview}
            icon={<BadgeCheck className="h-5 w-5" />}
            color="purple"
            trend={{
              direction: policiesInReview > 0 ? "up" : "neutral",
              value: String(policiesInReview),
            }}
          />
          <MetricCard
            title="Critical Alerts"
            value={criticalAlerts}
            icon={<ShieldAlert className="h-5 w-5" />}
            color="red"
            trend={{
              direction: criticalAlerts > 0 ? "up" : "neutral",
              value: String(criticalAlerts),
            }}
            glow={criticalAlerts > 0}
            status={criticalAlerts > 0 ? "error" : "live"}
          />
          <MetricCard
            title="OJ Acts"
            value={officialJournal?.acts_total ?? 0}
            icon={<ScrollText className="h-5 w-5" />}
            color="blue"
            trend={{
              direction: "neutral",
              value: formatDate(officialJournal?.latest_publication_date),
              label: "Latest OJ",
            }}
          />
        </BentoGrid>
      </motion.div>

      {/* ════════════════════════════════════════════════════════════════
          REGULATORY INTAKE + OBLIGATIONS/POLICIES
          ════════════════════════════════════════════════════════════════ */}
      <motion.div variants={staggerItem} className="grid gap-6 lg:grid-cols-[1.35fr_0.65fr]">
        <GlassCard>
          <GlassCardHeader className="flex items-start justify-between">
            <div>
              <GlassCardTitle>Regulatory Intake</GlassCardTitle>
              <p className="text-xs text-white/40 mt-1">New EU/FR texts ({intakeDays}d)</p>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-white font-mono">
                {intake?.new_documents.total_7d ?? 0}
              </div>
              <div className="text-[10px] uppercase tracking-wider text-white/30">Total</div>
            </div>
          </GlassCardHeader>
          <GlassCardContent>
            <div className="flex flex-wrap items-center gap-2 mb-4">
              <span className="text-[10px] uppercase tracking-[0.2em] text-white/30">Scope</span>
              <select
                value={scopeFilter}
                onChange={(event) => setScopeFilter(event.target.value)}
                className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-[11px] font-medium text-white/70 focus:outline-none"
              >
                <option value="psp,eme,vasp">PSP / EMI / VASP</option>
                <option value="psp">PSP</option>
                <option value="eme">EMI</option>
                <option value="vasp">VASP</option>
                <option value="all">All scopes</option>
              </select>
              <div className="flex flex-wrap gap-2">
                {intake?.new_documents.by_jurisdiction
                  ? Object.entries(intake.new_documents.by_jurisdiction).map(([jurisdiction, count]) => (
                      <span
                        key={jurisdiction}
                        className="px-2.5 py-1 rounded-full text-[11px] font-medium bg-white/[0.05] text-white/70 border border-white/[0.08]"
                      >
                        {jurisdiction.toUpperCase()}: {count}
                      </span>
                    ))
                  : null}
              </div>
            </div>

            <div className="space-y-2 max-h-[320px] overflow-y-auto scrollbar-thin scrollbar-thumb-white/10">
              {intake?.new_documents.items?.length ? (
                intake.new_documents.items.slice(0, 6).map((doc) => (
                  <Link
                    key={doc.id}
                    href={"/doc/" + doc.celex}
                    className="block p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.04] hover:border-white/[0.08] transition-all"
                  >
                    <div className="text-sm font-medium text-white hover:text-[#00d4ff] transition-colors">
                      {doc.celex}
                    </div>
                    <p className="text-xs text-white/40 mt-1 line-clamp-2">
                      {(doc.title || doc.celex || "Untitled document")}
                    </p>
                    <div className="flex items-center gap-2 mt-2 text-[10px] text-white/30">
                      <span>{doc.jurisdiction?.toUpperCase() || "EU"}</span>
                      <span>•</span>
                      <span>{formatDate(doc.publication_date)}</span>
                      {doc.oj_act_identifier ? (
                        <>
                          <span>•</span>
                          <span>OJ {doc.oj_act_identifier}</span>
                        </>
                      ) : null}
                    </div>
                  </Link>
                ))
              ) : (
                <EmptyStateInline message="No new documents captured." />
              )}
            </div>
          </GlassCardContent>
        </GlassCard>

        <GlassCard variant="interactive">
          <GlassCardHeader className="flex items-center justify-between">
            <div>
              <GlassCardTitle>Obligations & Policies</GlassCardTitle>
              <p className="text-xs text-white/40 mt-1">Draft → Review → Approved</p>
            </div>
            <div className="flex items-center gap-2">
              <Link href="/compliance/obligations">
                <Button variant="ghost" size="sm">Review obligations</Button>
              </Link>
              <Link href="/compliance/policies">
                <Button variant="gradient" size="sm">Create policy</Button>
              </Link>
            </div>
          </GlassCardHeader>
          <GlassCardContent className="space-y-5">
            <div>
              <div className="flex items-center justify-between text-[11px] uppercase tracking-wider text-white/30 mb-3">
                <span>Pending obligations</span>
                <span className="text-white/60">{pendingObligations}</span>
              </div>
              <div className="space-y-2">
                {pendingObligationItems.length ? (
                  pendingObligationItems.slice(0, 4).map((item) => (
                    <div
                      key={item.id}
                      className="rounded-lg border border-white/[0.05] bg-white/[0.02] p-3"
                    >
                      <div className="text-xs font-semibold text-white line-clamp-1">{item.doc_title}</div>
                      <p className="text-[11px] text-white/40 mt-1 line-clamp-2">{item.summary}</p>
                    </div>
                  ))
                ) : (
                  <EmptyStateInline message="No pending obligations." />
                )}
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between text-[11px] uppercase tracking-wider text-white/30 mb-3">
                <span>Policies in review</span>
                <span className="text-white/60">{policiesInReview}</span>
              </div>
              <div className="space-y-2">
                {policyItems.length ? (
                  policyItems.map((policy) => (
                    <div
                      key={policy.id}
                      className="rounded-lg border border-white/[0.05] bg-white/[0.02] p-3"
                    >
                      <div className="text-xs font-semibold text-white line-clamp-1">{policy.name}</div>
                      <div className="text-[11px] text-white/40 mt-1">
                        {policy.policy_id} • {policy.status}
                      </div>
                    </div>
                  ))
                ) : (
                  <EmptyStateInline message="No policies in review." />
                )}
              </div>
            </div>
          </GlassCardContent>
        </GlassCard>
      </motion.div>

      {/* ════════════════════════════════════════════════════════════════
          OPS CONTROL ROOM
          ════════════════════════════════════════════════════════════════ */}
      <motion.div variants={staggerItem} className="grid gap-6 lg:grid-cols-3">
        <GlassCard variant="interactive" className="lg:col-span-2">
          <GlassCardHeader className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <GlassCardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-[#ffd166]" />
                Ops Control Room
              </GlassCardTitle>
              <p className="text-sm text-white/40 mt-1">Real-time alerts, cases, and decisioning.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {[
                { label: "Alerts", href: "/transaction-alerts" },
                { label: "Cases", href: "/cases" },
                { label: "Monitoring", href: "/transaction-monitoring/dashboard" },
              ].map((link) => (
                <Link key={link.href} href={link.href}>
                  <Button variant="glass" size="sm">{link.label}</Button>
                </Link>
              ))}
            </div>
          </GlassCardHeader>
          <GlassCardContent>
            <div className="grid gap-4 lg:grid-cols-2">
              {/* Ops Snapshot */}
              <div className="p-4 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <div className="text-[10px] uppercase tracking-[0.15em] text-white/30 mb-3">Ops Snapshot</div>
                <div className="grid gap-3 sm:grid-cols-2">
                  {[
                    { label: "Pending Alerts", value: riskOps?.pending_alerts ?? 0, color: "cyan" },
                    { label: "Critical Alerts", value: riskOps?.critical_alerts ?? 0, color: "red" },
                    { label: "Open Cases", value: riskOps?.open_cases ?? 0, color: "yellow" },
                    { label: "Travel Rule Pending", value: reporting?.travel_pending ?? 0, color: "purple" },
                  ].map((stat) => (
                    <div
                      key={stat.label}
                      className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]"
                    >
                      <div className="text-[10px] uppercase tracking-wider text-white/30">{stat.label}</div>
                      <div className="text-xl font-bold text-white mt-1 font-mono">{stat.value}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Decisioning */}
              <div className="p-4 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <div className="text-sm font-medium text-white">Decisioning (24h)</div>
                    <div className="text-xs text-white/40">Recent decision breakdown</div>
                  </div>
                  <Link href="/decisioning">
                    <Button variant="ghost" size="sm" rightIcon={<ArrowUpRight className="h-3 w-3" />}>
                      Open
                    </Button>
                  </Link>
                </div>

                <div className="space-y-2">
                  {decisionOrder.map((key) => (
                    <div
                      key={key}
                      className="flex items-center justify-between p-2 rounded-lg bg-white/[0.01] border border-white/[0.03]"
                    >
                      <span className={cn(
                        "px-2.5 py-1 rounded-full text-[11px] font-semibold",
                        decisionConfig[key].bg,
                        decisionConfig[key].color
                      )}>
                        {decisionConfig[key].label}
                      </span>
                      <span className="text-sm font-bold text-white font-mono">
                        {decisions?.breakdown?.[key] ?? 0}
                      </span>
                    </div>
                  ))}
                </div>

                <div className="mt-3 pt-3 border-t border-white/[0.04] flex items-center justify-between">
                  <span className="text-xs text-white/40">Total decisions</span>
                  <span className="text-sm font-bold text-white">{decisions?.last_24h_total ?? 0}</span>
                </div>
              </div>
            </div>
          </GlassCardContent>
        </GlassCard>

        <GlassCard>
          <GlassCardHeader>
            <GlassCardTitle>Risk Radar</GlassCardTitle>
            <p className="text-xs text-white/40 mt-1">Live operational posture</p>
          </GlassCardHeader>
          <GlassCardContent className="space-y-4">
            <div className="grid gap-3">
              {[
                { label: "Open cases", value: openCases },
                { label: "Decisions (24h)", value: decisions?.last_24h_total ?? 0 },
                { label: "Travel Rule pending", value: reporting?.travel_pending ?? 0 },
              ].map((item) => (
                <div
                  key={item.label}
                  className="flex items-center justify-between rounded-lg border border-white/[0.05] bg-white/[0.02] px-3 py-2"
                >
                  <span className="text-xs text-white/50">{item.label}</span>
                  <span className="text-sm font-semibold text-white font-mono">{item.value}</span>
                </div>
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              <Link href="/cases">
                <Button variant="glass" size="sm">Cases</Button>
              </Link>
              <Link href="/transaction-alerts">
                <Button variant="glass" size="sm">Alerts</Button>
              </Link>
            </div>
          </GlassCardContent>
        </GlassCard>
      </motion.div>

      {/* ════════════════════════════════════════════════════════════════
          COVERAGE & REPORTING
          ════════════════════════════════════════════════════════════════ */}
      <motion.div variants={staggerItem} className="grid gap-6 lg:grid-cols-2">
        {/* Coverage */}
        <GlassCard variant="interactive">
          <GlassCardHeader className="flex items-center justify-between">
            <div>
              <GlassCardTitle>Regulatory Coverage</GlassCardTitle>
              <p className="text-sm text-white/40 mt-1">CELEX = EU anchor. Each rule must be linked to a source.</p>
            </div>
            <Link href="/transaction-monitoring/rules/lab">
              <Button variant="ghost" size="sm" rightIcon={<ArrowUpRight className="h-4 w-4" />}>
                Map
              </Button>
            </Link>
          </GlassCardHeader>
          <GlassCardContent>
            <div className="grid gap-4 sm:grid-cols-2 mb-4">
              <div className="p-4 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs uppercase tracking-wider text-white/30">CELEX Mapped</span>
                  <CircularProgress value={coverage?.celex_coverage_pct ?? 0} size={48} color="cyan" showLabel />
                </div>
                <div className="text-xl font-bold text-white font-mono">
                  {coverage?.celex_covered ?? 0}
                  <span className="text-sm text-white/40 font-normal"> / {coverage?.total_documents ?? 0}</span>
                </div>
              </div>
              <div className="p-4 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs uppercase tracking-wider text-white/30">Rules Mapped</span>
                  <CircularProgress value={coverage?.rules_coverage_pct ?? 0} size={48} color="aurora" showLabel />
                </div>
                <div className="text-xl font-bold text-white font-mono">
                  {coverage?.rules_with_celex ?? 0}
                  <span className="text-sm text-white/40 font-normal"> / {coverage?.rules_total ?? 0}</span>
                </div>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-[#6d5acd]/5 border border-[#6d5acd]/10">
              <p className="text-xs text-[#6d5acd]">
                CELEX ensures EU regulatory traceability; for France we use JORF/NOR.
              </p>
            </div>
          </GlassCardContent>
        </GlassCard>

        {/* Reporting */}
        <GlassCard variant="interactive">
          <GlassCardHeader className="flex items-center justify-between">
            <div>
              <GlassCardTitle>Evidence & Reporting</GlassCardTitle>
              <p className="text-sm text-white/40 mt-1">Filing tracking and audit checkpoints.</p>
            </div>
            <Link href="/sar/prepare">
              <Button variant="ghost" size="sm" rightIcon={<ArrowUpRight className="h-4 w-4" />}>
                Prepare SAR
              </Button>
            </Link>
          </GlassCardHeader>
          <GlassCardContent>
            <div className="grid gap-4 sm:grid-cols-2 mb-4">
              <div className="p-4 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <div className="text-xs uppercase tracking-wider text-white/30">SAR Filed (30d)</div>
                <div className="text-2xl font-bold text-white font-mono mt-2">
                  {reporting?.sar_filed_30d ?? 0}
                </div>
              </div>
              <div className="p-4 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <div className="text-xs uppercase tracking-wider text-white/30">On-chain Checks (24h)</div>
                <div className="text-2xl font-bold text-white font-mono mt-2">
                  {reporting?.onchain_checks_24h ?? 0}
                </div>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <Link href="/travel-rule">
                <Button variant="glass" size="sm" leftIcon={<FileText className="h-4 w-4" />}>
                  Travel Rule Inbox
                </Button>
              </Link>
              <Link href="/onchain-risk">
                <Button variant="glass" size="sm" leftIcon={<ShieldAlert className="h-4 w-4" />}>
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
              description: "Edit rules, propose updates, submit for approval.",
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
                      <action.icon className="h-5 w-5" style={{ color: action.color }} />
                    </div>
                    <ArrowUpRight className="h-4 w-4 text-white/20 group-hover:text-white/60 transition-colors" />
                  </div>
                  <h3 className="text-sm font-semibold text-white">{action.title}</h3>
                  <p className="text-xs text-white/40 mt-1">{action.description}</p>
                </motion.div>
              </Link>
            </BentoItem>
          ))}
        </BentoGrid>
      </motion.div>
    </motion.div>
  );
}
