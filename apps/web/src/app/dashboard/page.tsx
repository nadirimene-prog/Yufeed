"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowUpRight,
  BadgeCheck,
  ClipboardCheck,
  FileText,
  Gavel,
  Scale,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import apiClient from "@/lib/http";
import { getAuthToken } from "@/lib/auth";
import { handleApiError } from "@/lib/api-error-handler";
import { MetricCard } from "@/components/ui/metric-card";
import { EmptyStateInline } from "@/components/ui/empty-state";
import { ComplianceDomainBadge, RiskBadge } from "@/components/compliance-badges";

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
}

interface Reporting {
  sar_filed_30d: number;
  travel_pending: number;
  travel_submitted: number;
  onchain_checks_24h: number;
}

interface HomeDashboard {
  coverage: Coverage;
  coverage_gaps: CoverageGaps;
  risk_ops: RiskOps;
  decisions: Decisions;
  reporting: Reporting;
}

const decisionOrder = ["allow", "step-up", "alert", "block"] as const;
const decisionLabel: Record<(typeof decisionOrder)[number], string> = {
  allow: "Allow",
  "step-up": "Step-up",
  alert: "Alert",
  block: "Block",
};

const decisionStyle: Record<(typeof decisionOrder)[number], string> = {
  allow: "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
  "step-up": "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  alert: "bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300",
  block: "bg-rose-50 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300",
};

const severityStyle = (severity?: string) => {
  const value = (severity || "unrated").toLowerCase();
  if (value === "critical") return "bg-rose-50 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300";
  if (value === "high") return "bg-orange-50 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300";
  if (value === "medium") return "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300";
  if (value === "low") return "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300";
  return "bg-slate-50 text-slate-700 dark:bg-slate-800 dark:text-slate-300";
};

const formatPct = (value?: number) => (value ?? 0).toFixed(1) + "%";

export default function DashboardPage() {
  const [data, setData] = useState<HomeDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [hasToken, setHasToken] = useState(false);

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
        const response = await apiClient.get<HomeDashboard>("/api/reporting/dashboard/home");
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
  }, [hasToken]);

  if (authReady && !hasToken) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center p-6">
        <div className="text-sm text-gray-500 dark:text-gray-400">
          No session found. Please sign in at /login.
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="space-y-8 animate-fade-in">
        <div className="space-y-2">
          <div className="h-4 w-40 bg-gray-200 dark:bg-slate-700 rounded animate-pulse" />
          <div className="h-9 w-72 bg-gray-200 dark:bg-slate-700 rounded animate-pulse" />
          <div className="h-5 w-96 bg-gray-100 dark:bg-slate-800 rounded animate-pulse" />
        </div>

        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <MetricCard key={i} title="" value={0} loading />
          ))}
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <div className="h-64 rounded-lg border border-gray-200 dark:border-slate-800 bg-gray-100 dark:bg-slate-800/30 animate-pulse" />
          <div className="h-64 rounded-lg border border-gray-200 dark:border-slate-800 bg-gray-100 dark:bg-slate-800/30 animate-pulse" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 dark:border-red-800 dark:bg-red-900/10">
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400" />
            <div>
              <h3 className="font-semibold text-red-900 dark:text-red-200">Error Loading Dashboard</h3>
              <p className="mt-1 text-sm text-red-700 dark:text-red-300">{error}</p>
              <button
                onClick={() => window.location.reload()}
                className="mt-3 text-sm font-medium text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
              >
                Try again
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const coverage = data?.coverage;
  const coverageGaps = data?.coverage_gaps;
  const riskOps = data?.risk_ops;
  const decisions = data?.decisions;
  const reporting = data?.reporting;

  return (
    <div className="space-y-8 animate-slide-up">
      <header className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.3em] text-gray-400">
            <Sparkles className="h-3.5 w-3.5" />
            YuFeed Risk OS
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white">
            Compliance Officer Home
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2 max-w-3xl">
            CELEX coverage, rules mapping, and risk operations visibility in one audit-ready view.
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-gray-200 bg-white px-4 py-2 text-xs text-gray-500 shadow-sm dark:border-slate-800 dark:bg-slate-900 dark:text-gray-400">
          <BadgeCheck className="h-4 w-4 text-emerald-500" />
          Live compliance telemetry
        </div>
      </header>

      <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
        <MetricCard
          title="CELEX Coverage"
          value={formatPct(coverage?.celex_coverage_pct)}
          icon={<Scale className="h-5 w-5" />}
          color="blue"
        />
        <MetricCard
          title="Rules Linked to CELEX"
          value={formatPct(coverage?.rules_coverage_pct)}
          icon={<ShieldCheck className="h-5 w-5" />}
          color="green"
        />
        <MetricCard
          title="Pending Alerts"
          value={riskOps?.pending_alerts ?? 0}
          icon={<AlertTriangle className="h-5 w-5" />}
          color="yellow"
        />
        <MetricCard
          title="Critical Alerts"
          value={riskOps?.critical_alerts ?? 0}
          icon={<ShieldAlert className="h-5 w-5" />}
          color="red"
        />
        <MetricCard
          title="Open Cases"
          value={riskOps?.open_cases ?? 0}
          icon={<ClipboardCheck className="h-5 w-5" />}
          color="purple"
        />
        <MetricCard
          title="Decisions (24h)"
          value={decisions?.last_24h_total ?? 0}
          icon={<Gavel className="h-5 w-5" />}
          color="gray"
        />
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-lg border border-gray-200 bg-white p-4 text-sm text-gray-600 shadow-sm dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300">
          <div className="text-xs uppercase text-gray-400">CELEX mapped</div>
          <div className="mt-2 text-2xl font-semibold text-gray-900 dark:text-white">
            {coverage?.celex_covered ?? 0}
            <span className="text-base text-gray-400"> / {coverage?.total_documents ?? 0}</span>
          </div>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4 text-sm text-gray-600 shadow-sm dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300">
          <div className="text-xs uppercase text-gray-400">Rules mapped</div>
          <div className="mt-2 text-2xl font-semibold text-gray-900 dark:text-white">
            {coverage?.rules_with_celex ?? 0}
            <span className="text-base text-gray-400"> / {coverage?.rules_total ?? 0}</span>
          </div>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4 text-sm text-gray-600 shadow-sm dark:border-slate-800 dark:bg-slate-900 dark:text-gray-300">
          <div className="text-xs uppercase text-gray-400">Travel rule status</div>
          <div className="mt-2 flex items-center gap-3 text-sm">
            <span className="rounded-full bg-amber-50 px-3 py-1 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
              Pending: {reporting?.travel_pending ?? 0}
            </span>
            <span className="rounded-full bg-emerald-50 px-3 py-1 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
              Submitted: {reporting?.travel_submitted ?? 0}
            </span>
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-blue-200 bg-blue-50/60 p-5 text-sm text-blue-900 shadow-sm dark:border-blue-900/40 dark:bg-blue-950/40 dark:text-blue-200">
        <div className="flex items-start gap-3">
          <Scale className="h-5 w-5 mt-0.5" />
          <div>
            <div className="font-semibold">CELEX is the regulatory anchor</div>
            <p className="mt-1 text-blue-800/90 dark:text-blue-200/90">
              CELEX identifiers map every EU legal document to its monitoring rules. Each rule should link to a CELEX entry to
              keep audit coverage provable and explainable.
            </p>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">CELEX without rules</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">Top regulatory docs with no linked monitoring rule.</p>
            </div>
            <Link
              href="/transaction-monitoring/rules/lab"
              className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700"
            >
              Map rules
              <ArrowUpRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="mt-4 space-y-3">
            {coverageGaps?.celex_without_rules?.length ? (
              coverageGaps.celex_without_rules.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-start justify-between gap-3 rounded-lg border border-gray-100 bg-gray-50/60 p-3 dark:border-slate-800 dark:bg-slate-800/40"
                >
                  <div className="min-w-0">
                    <Link href={"/doc/" + doc.celex} className="text-sm font-semibold text-gray-900 hover:underline dark:text-white">
                      {doc.celex}
                    </Link>
                    <p className="mt-1 text-xs text-gray-500 line-clamp-2 dark:text-gray-400">{doc.title}</p>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    {doc.risk_level ? <RiskBadge level={doc.risk_level} /> : null}
                    {doc.compliance_domain ? <ComplianceDomainBadge domain={doc.compliance_domain} /> : null}
                  </div>
                </div>
              ))
            ) : (
              <EmptyStateInline message="All CELEX entries are mapped to rules." />
            )}
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Rules without CELEX</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">Rules missing a regulatory source link.</p>
            </div>
            <Link
              href="/transaction-monitoring/rules"
              className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700"
            >
              Review rules
              <ArrowUpRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="mt-4 space-y-3">
            {coverageGaps?.rules_without_celex?.length ? (
              coverageGaps.rules_without_celex.map((rule) => (
                <div
                  key={rule.rule_id}
                  className="flex items-start justify-between gap-3 rounded-lg border border-gray-100 bg-gray-50/60 p-3 dark:border-slate-800 dark:bg-slate-800/40"
                >
                  <div>
                    <p className="text-sm font-semibold text-gray-900 dark:text-white">{rule.name}</p>
                    <p className="text-xs text-gray-500 font-mono dark:text-gray-400">{rule.rule_id}</p>
                  </div>
                  <span className={"rounded-full px-3 py-1 text-xs font-semibold " + severityStyle(rule.severity)}>
                    {(rule.severity || "unrated").toUpperCase()}
                  </span>
                </div>
              ))
            ) : (
              <EmptyStateInline message="All active rules are linked to CELEX." />
            )}
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Decisioning (last 24h)</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">Outcome mix for recent decisions.</p>
            </div>
            <Link
              href="/decisioning"
              className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700"
            >
              Open decisioning
              <ArrowUpRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="mt-4 space-y-3">
            {decisionOrder.map((key) => (
              <div key={key} className="flex items-center justify-between rounded-lg border border-gray-100 px-4 py-3 dark:border-slate-800">
                <span className={"rounded-full px-3 py-1 text-xs font-semibold " + decisionStyle[key]}>
                  {decisionLabel[key]}
                </span>
                <span className="text-sm font-semibold text-gray-900 dark:text-white">
                  {decisions?.breakdown?.[key] ?? 0}
                </span>
              </div>
            ))}
            <div className="text-xs text-gray-500 dark:text-gray-400">
              Total decisions: {decisions?.last_24h_total ?? 0}
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Reporting & Evidence</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">Recent filings and evidence checkpoints.</p>
            </div>
            <Link
              href="/sar/prepare"
              className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700"
            >
              Prepare SAR
              <ArrowUpRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div className="rounded-lg border border-gray-100 bg-gray-50/60 p-4 dark:border-slate-800 dark:bg-slate-800/40">
              <div className="text-xs uppercase text-gray-400">SAR filed (30d)</div>
              <div className="mt-2 text-2xl font-semibold text-gray-900 dark:text-white">
                {reporting?.sar_filed_30d ?? 0}
              </div>
            </div>
            <div className="rounded-lg border border-gray-100 bg-gray-50/60 p-4 dark:border-slate-800 dark:bg-slate-800/40">
              <div className="text-xs uppercase text-gray-400">On-chain checks (24h)</div>
              <div className="mt-2 text-2xl font-semibold text-gray-900 dark:text-white">
                {reporting?.onchain_checks_24h ?? 0}
              </div>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <Link
              href="/travel-rule"
              className="inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white px-4 py-2 text-xs font-medium text-gray-700 hover:border-gray-300 dark:border-slate-700 dark:bg-slate-900 dark:text-gray-300"
            >
              <FileText className="h-4 w-4" />
              Travel Rule inbox
            </Link>
            <Link
              href="/onchain-risk"
              className="inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white px-4 py-2 text-xs font-medium text-gray-700 hover:border-gray-300 dark:border-slate-700 dark:bg-slate-900 dark:text-gray-300"
            >
              <ShieldAlert className="h-4 w-4" />
              On-chain risk
            </Link>
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          {
            title: "Rules lab",
            description: "Edit rules, propose updates, and submit for approval.",
            href: "/transaction-monitoring/rules/lab",
            icon: ClipboardCheck,
          },
          {
            title: "Decisioning",
            description: "Review decisions, evidence, and appeal trails.",
            href: "/decisioning",
            icon: Gavel,
          },
          {
            title: "Case management",
            description: "Track open cases and escalate investigations.",
            href: "/cases",
            icon: FileText,
          },
          {
            title: "Audit trail",
            description: "Search for evidence, actions, and approvals.",
            href: "/audit",
            icon: ShieldCheck,
          },
        ].map((action) => (
          <Link
            key={action.title}
            href={action.href}
            className="group rounded-lg border border-gray-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:border-gray-300 hover:shadow-md dark:border-slate-800 dark:bg-slate-900"
          >
            <div className="flex items-center justify-between">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-50 text-blue-600 dark:bg-blue-900/40 dark:text-blue-300">
                <action.icon className="h-5 w-5" />
              </div>
              <ArrowUpRight className="h-4 w-4 text-gray-400 group-hover:text-gray-600 dark:text-gray-500" />
            </div>
            <div className="mt-4 text-sm font-semibold text-gray-900 dark:text-white">{action.title}</div>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{action.description}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
