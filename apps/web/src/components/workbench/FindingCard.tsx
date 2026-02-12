"use client";

import { motion } from "framer-motion";
import { Clock, Shield, User, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { staggerItem } from "@/lib/motion";
import type { Finding } from "@/types/workbench";

interface FindingCardProps {
  finding: Finding;
  onClick?: () => void;
}

const severityConfig = {
  critical: {
    color: "text-red-500",
    bg: "bg-red-50 dark:bg-red-950/30",
    border: "border-red-200 dark:border-red-900/50",
    dot: "bg-red-500",
  },
  high: {
    color: "text-orange-500",
    bg: "bg-orange-50 dark:bg-orange-950/30",
    border: "border-orange-200 dark:border-orange-900/50",
    dot: "bg-orange-500",
  },
  medium: {
    color: "text-amber-500",
    bg: "bg-amber-50 dark:bg-amber-950/30",
    border: "border-amber-200 dark:border-amber-900/50",
    dot: "bg-amber-500",
  },
  low: {
    color: "text-blue-500",
    bg: "bg-blue-50 dark:bg-blue-950/30",
    border: "border-blue-200 dark:border-blue-900/50",
    dot: "bg-blue-500",
  },
  info: {
    color: "text-gray-500",
    bg: "bg-gray-50 dark:bg-gray-950/30",
    border: "border-gray-200 dark:border-gray-800",
    dot: "bg-gray-400",
  },
} as const;

const statusConfig = {
  open: {
    label: "Open",
    color: "text-blue-600 dark:text-blue-400",
    bg: "bg-blue-50 dark:bg-blue-950/40",
  },
  acknowledged: {
    label: "Acknowledged",
    color: "text-amber-600 dark:text-amber-400",
    bg: "bg-amber-50 dark:bg-amber-950/40",
  },
  escalated: {
    label: "Escalated",
    color: "text-orange-600 dark:text-orange-400",
    bg: "bg-orange-50 dark:bg-orange-950/40",
  },
  closed: {
    label: "Closed",
    color: "text-gray-500 dark:text-gray-400",
    bg: "bg-gray-100 dark:bg-gray-800",
  },
} as const;

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

export function FindingCard({ finding, onClick }: FindingCardProps) {
  const severity = severityConfig[finding.severity] ?? severityConfig.info;
  const status = statusConfig[finding.status] ?? statusConfig.open;

  const isOverdue =
    finding.sla_due_at && new Date(finding.sla_due_at) < new Date();

  return (
    <motion.div
      variants={staggerItem}
      onClick={onClick}
      className={cn(
        "group relative rounded-xl border bg-white dark:bg-gray-900/60 p-4",
        "transition-all duration-200 hover:shadow-md hover:border-gray-300 dark:hover:border-gray-600",
        onClick && "cursor-pointer",
        severity.border,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        {/* Left: severity dot + content */}
        <div className="flex items-start gap-3 min-w-0 flex-1">
          <div
            className={cn(
              "mt-1 h-2.5 w-2.5 rounded-full shrink-0",
              severity.dot,
            )}
          />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span
                className={cn(
                  "text-xs font-medium px-2 py-0.5 rounded-full",
                  severity.bg,
                  severity.color,
                )}
              >
                {finding.severity.toUpperCase()}
              </span>
              <span
                className={cn(
                  "text-xs font-medium px-2 py-0.5 rounded-full",
                  status.bg,
                  status.color,
                )}
              >
                {status.label}
              </span>
              {isOverdue && (
                <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-red-100 text-red-700 dark:bg-red-950/50 dark:text-red-400">
                  Overdue
                </span>
              )}
            </div>

            <h3 className="text-sm font-semibold text-gray-900 dark:text-white truncate">
              {finding.title}
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-1">
              {finding.summary}
            </p>

            {/* Metadata row */}
            <div className="flex items-center gap-3 mt-2 text-xs text-gray-400 dark:text-gray-500">
              <span className="flex items-center gap-1">
                <Shield className="h-3 w-3" />
                {finding.finding_type.toUpperCase()}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {timeAgo(finding.created_at)}
              </span>
              {finding.assigned_to && (
                <span className="flex items-center gap-1">
                  <User className="h-3 w-3" />
                  {finding.assigned_to}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Right: chevron */}
        <ChevronRight className="h-4 w-4 text-gray-300 dark:text-gray-600 group-hover:text-gray-500 dark:group-hover:text-gray-400 transition shrink-0 mt-1" />
      </div>
    </motion.div>
  );
}

export default FindingCard;
