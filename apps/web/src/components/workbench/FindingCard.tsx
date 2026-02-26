"use client";

import {
  ShieldAlert,
  Clock,
  User,
  CheckCircle2,
  Zap,
  Shield,
} from "lucide-react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { Finding } from "@/types/workbench";
import { Button } from "@/components/ui/button";

interface FindingCardProps {
  finding: Finding;
  onClick?: () => void;
  onAcknowledge?: (id: string | number) => void;
  onEscalate?: (id: string | number) => void;
}

const severityConfig: Record<
  string,
  {
    icon: typeof Shield;
    color: string;
    bg: string;
    border: string;
    glow: string;
  }
> = {
  critical: {
    icon: ShieldAlert,
    color: "text-risk-critical",
    bg: "bg-risk-critical/10",
    border: "border-risk-critical/30",
    glow: "var(--surface-glow-error)",
  },
  high: {
    icon: Shield,
    color: "text-risk-high",
    bg: "bg-risk-high/10",
    border: "border-risk-high/30",
    glow: "var(--surface-glow-accent)",
  },
  medium: {
    icon: Shield,
    color: "text-risk-medium",
    bg: "bg-risk-medium/10",
    border: "border-risk-medium/30",
    glow: "var(--surface-glow-accent)",
  },
  low: {
    icon: Shield,
    color: "text-risk-low",
    bg: "bg-risk-low/10",
    border: "border-risk-low/30",
    glow: "var(--surface-glow-accent)",
  },
  info: {
    icon: Shield,
    color: "text-info",
    bg: "bg-info/10",
    border: "border-info/30",
    glow: "var(--surface-glow-primary)",
  },
};

const statusConfig: Record<
  string,
  { label: string; color: string; bg: string }
> = {
  new: { label: "New", color: "text-cyan-400", bg: "bg-cyan-400/10" },
  open: { label: "Open", color: "text-amber-400", bg: "bg-amber-400/10" },
  triaged: { label: "Triaged", color: "text-blue-400", bg: "bg-blue-400/10" },
  escalated: {
    label: "Escalated",
    color: "text-blue-400",
    bg: "bg-blue-400/10",
  },
  closed: {
    label: "Closed",
    color: "text-emerald-400",
    bg: "bg-emerald-400/10",
  },
};

function timeAgo(dateStr: string): string {
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function FindingCard({
  finding,
  onClick,
  onAcknowledge,
  onEscalate,
}: FindingCardProps) {
  const severity = severityConfig[finding.severity] ?? severityConfig.info;
  const status = statusConfig[finding.status] ?? statusConfig.open;

  return (
    <motion.div
      layoutId={`finding-${finding.id}`}
      whileHover={{ y: -2, scale: 1.01 }}
      className={cn(
        "group relative flex flex-col gap-3 rounded-2xl border p-4 transition-all duration-300",
        "bg-white border-border shadow-sm hover:border-primary/20",
        finding.severity === "critical" && "hover:shadow-sm",
      )}
      onClick={onClick}
    >
      {/* Risk Indicator Bar */}
      <div
        className={cn(
          "absolute left-0 top-4 bottom-4 w-1 rounded-r-full transition-colors",
          severity.color.replace("text-", "bg-"),
        )}
      />

      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-1 items-start gap-3 pl-2">
          <div
            className={cn(
              "mt-0.5 rounded-lg p-2 flex items-center justify-center border",
              severity.bg,
              severity.border,
            )}
          >
            <severity.icon className={cn("h-4 w-4", severity.color)} />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span
                className={cn(
                  "text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full",
                  status.color,
                  status.bg,
                )}
              >
                {status.label}
              </span>
              <span className="text-[10px] text-white/30 uppercase tracking-tighter">
                {finding.finding_type}
              </span>
            </div>
            <h3 className="text-sm font-semibold text-foreground line-clamp-1 transition-colors">
              {finding.title}
            </h3>
          </div>
        </div>
        <div className="text-[10px] text-muted-foreground font-mono flex items-center gap-1">
          <Clock size={10} />
          {timeAgo(finding.created_at)}
        </div>
      </div>

      <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed pl-11">
        {finding.summary}
      </p>

      <div className="mt-2 flex items-center justify-between pl-11">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <User size={12} className="text-muted-foreground" />
            <span className="text-[11px] text-muted-foreground">
              {finding.assigned_to || "Unassigned"}
            </span>
          </div>
        </div>

        {/* Action micro-interactions */}
        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity translate-x-2 group-hover:translate-x-0 transition-transform">
          {finding.status === "open" && (
            <Button
              variant="outline"
              size="sm"
              className="h-7 px-2 text-[10px] bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border-emerald-500/20"
              onClick={(e) => {
                e.stopPropagation();
                onAcknowledge?.(finding.id);
              }}
              leftIcon={<CheckCircle2 size={12} />}
            >
              Acknowledge
            </Button>
          )}
          {finding.status !== "escalated" && (
            <Button
              variant="outline"
              size="sm"
              className="h-7 px-2 text-[10px] bg-primary/10 hover:bg-primary/20 text-primary border-primary/20"
              onClick={(e) => {
                e.stopPropagation();
                onEscalate?.(finding.id);
              }}
              leftIcon={<Zap size={12} />}
            >
              Escalate
            </Button>
          )}
        </div>
      </div>
    </motion.div>
  );
}

export default FindingCard;
