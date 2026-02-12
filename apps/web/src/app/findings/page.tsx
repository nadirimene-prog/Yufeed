"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  Search,
  Filter,
  Eye,
  Clock,
  CheckCircle,
  ArrowUpRight,
} from "lucide-react";
import { useFindings } from "@/hooks/queries/useWorkbenchData";
import { FindingCard } from "@/components/workbench/FindingCard";
import { GlassCard, GlassCardContent } from "@/components/ui/glass-card";
import { staggerContainer, staggerItem, fadeInBlur } from "@/lib/motion";
import { cn } from "@/lib/utils";
import type { Finding } from "@/types/workbench";

export default function FindingsPage() {
  const router = useRouter();
  const [filters, setFilters] = useState({
    status: "all",
    severity: "all",
    finding_type: "all",
    search: "",
  });

  const findingsQuery = useFindings({
    limit: 100,
    ...(filters.status !== "all" ? { status: filters.status } : {}),
    ...(filters.severity !== "all" ? { severity: filters.severity } : {}),
    ...(filters.finding_type !== "all"
      ? { finding_type: filters.finding_type }
      : {}),
  });

  const findings = findingsQuery.data ?? [];
  const loading = findingsQuery.isLoading;

  const filteredFindings = findings.filter((f) => {
    if (!filters.search) return true;
    const q = filters.search.toLowerCase();
    return (
      f.title.toLowerCase().includes(q) ||
      f.summary.toLowerCase().includes(q) ||
      f.fingerprint.toLowerCase().includes(q)
    );
  });

  // Stats
  const stats = {
    total: findings.length,
    open: findings.filter((f) => f.status === "open").length,
    escalated: findings.filter((f) => f.status === "escalated").length,
    overdue: findings.filter(
      (f) =>
        f.sla_due_at &&
        new Date(f.sla_due_at) < new Date() &&
        f.status !== "closed",
    ).length,
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="h-8 w-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Loading findings…
          </p>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      variants={fadeInBlur}
      initial="initial"
      animate="animate"
      className="space-y-6"
    >
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">
          Findings Triage
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Review, acknowledge, and escalate compliance findings.
        </p>
      </div>

      {/* Stats Row — glass cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <GlassCard variant="surface" className="p-4">
          <GlassCardContent className="p-0">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-0.5">
                  Total
                </p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">
                  {stats.total}
                </p>
              </div>
              <div className="p-2 rounded-lg bg-gray-100 dark:bg-gray-800">
                <Eye className="h-4 w-4 text-gray-600 dark:text-gray-400" />
              </div>
            </div>
          </GlassCardContent>
        </GlassCard>

        <GlassCard variant="surface" className="p-4">
          <GlassCardContent className="p-0">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-0.5">
                  Open
                </p>
                <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  {stats.open}
                </p>
              </div>
              <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-950/30">
                <Clock className="h-4 w-4 text-blue-600 dark:text-blue-400" />
              </div>
            </div>
          </GlassCardContent>
        </GlassCard>

        <GlassCard variant="surface" className="p-4">
          <GlassCardContent className="p-0">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-0.5">
                  Escalated
                </p>
                <p className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                  {stats.escalated}
                </p>
              </div>
              <div className="p-2 rounded-lg bg-orange-50 dark:bg-orange-950/30">
                <ArrowUpRight className="h-4 w-4 text-orange-600 dark:text-orange-400" />
              </div>
            </div>
          </GlassCardContent>
        </GlassCard>

        <GlassCard
          variant="surface"
          glow={stats.overdue > 0 ? "critical" : "none"}
          className="p-4"
        >
          <GlassCardContent className="p-0">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-0.5">
                  Overdue
                </p>
                <p
                  className={cn(
                    "text-2xl font-bold",
                    stats.overdue > 0
                      ? "text-red-600 dark:text-red-400"
                      : "text-emerald-600 dark:text-emerald-400",
                  )}
                >
                  {stats.overdue}
                </p>
              </div>
              <div
                className={cn(
                  "p-2 rounded-lg",
                  stats.overdue > 0
                    ? "bg-red-50 dark:bg-red-950/30"
                    : "bg-emerald-50 dark:bg-emerald-950/30",
                )}
              >
                <AlertTriangle
                  className={cn(
                    "h-4 w-4",
                    stats.overdue > 0
                      ? "text-red-600 dark:text-red-400"
                      : "text-emerald-600 dark:text-emerald-400",
                  )}
                />
              </div>
            </div>
          </GlassCardContent>
        </GlassCard>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search findings…"
            value={filters.search}
            onChange={(e) =>
              setFilters((p) => ({ ...p, search: e.target.value }))
            }
            className="w-full pl-9 pr-4 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-sm text-gray-900 dark:text-white placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500"
          />
        </div>

        <select
          value={filters.severity}
          onChange={(e) =>
            setFilters((p) => ({ ...p, severity: e.target.value }))
          }
          className="px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30"
        >
          <option value="all">All Severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>

        <select
          value={filters.status}
          onChange={(e) =>
            setFilters((p) => ({ ...p, status: e.target.value }))
          }
          className="px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30"
        >
          <option value="all">All Statuses</option>
          <option value="open">Open</option>
          <option value="acknowledged">Acknowledged</option>
          <option value="escalated">Escalated</option>
          <option value="closed">Closed</option>
        </select>

        <select
          value={filters.finding_type}
          onChange={(e) =>
            setFilters((p) => ({ ...p, finding_type: e.target.value }))
          }
          className="px-3 py-2 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/30"
        >
          <option value="all">All Types</option>
          <option value="aml">AML</option>
          <option value="kyc">KYC</option>
          <option value="sanctions">Sanctions</option>
          <option value="fraud">Fraud</option>
          <option value="regulatory">Regulatory</option>
          <option value="operational">Operational</option>
        </select>
      </div>

      {/* Findings List */}
      {filteredFindings.length === 0 ? (
        <div className="text-center py-16">
          <CheckCircle className="h-12 w-12 mx-auto mb-3 text-emerald-400 opacity-60" />
          <p className="text-sm font-medium text-gray-900 dark:text-white">
            No findings match your filters
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Try adjusting your search or filter criteria.
          </p>
        </div>
      ) : (
        <motion.div
          variants={staggerContainer}
          initial="initial"
          animate="animate"
          className="space-y-2"
        >
          {filteredFindings.map((finding) => (
            <FindingCard
              key={finding.id}
              finding={finding}
              onClick={() => router.push(`/findings/${finding.id}`)}
            />
          ))}
        </motion.div>
      )}
    </motion.div>
  );
}
