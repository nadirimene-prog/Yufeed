/**
 * StatusBadge Component
 *
 * A reusable badge component for displaying status across the application.
 * Replaces 15+ inline status badge implementations with a single, consistent component.
 *
 * Features:
 * - Predefined color schemes for common statuses
 * - Compact and default size variants
 * - Accessible with proper ARIA attributes
 * - Extensible for custom statuses
 *
 * Usage:
 * ```tsx
 * <StatusBadge status="pending" />
 * <StatusBadge status="approved" variant="compact" />
 * <StatusBadge status="custom_status" label="Custom Label" color="bg-purple-100 text-purple-800" />
 * ```
 */

import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  status: string;
  variant?: "default" | "compact";
  label?: string;
  color?: string;
  className?: string;
}

interface StatusConfig {
  color: string;
  label: string;
}

const statusConfig: Record<string, StatusConfig> = {
  // General statuses
  pending: {
    color: "bg-amber-50 text-amber-800",
    label: "Pending",
  },
  in_review: {
    color: "bg-blue-50 text-blue-800",
    label: "In Review",
  },
  in_progress: {
    color: "bg-blue-50 text-blue-800",
    label: "In Progress",
  },
  approved: {
    color: "bg-emerald-50 text-emerald-800",
    label: "Approved",
  },
  rejected: {
    color: "bg-red-50 text-red-800",
    label: "Rejected",
  },
  resolved: {
    color: "bg-slate-100 text-slate-700",
    label: "Resolved",
  },
  closed: {
    color: "bg-slate-100 text-slate-700",
    label: "Closed",
  },
  active: {
    color: "bg-emerald-50 text-emerald-800",
    label: "Active",
  },
  inactive: {
    color: "bg-slate-100 text-slate-700",
    label: "Inactive",
  },
  open: {
    color: "bg-blue-50 text-blue-800",
    label: "Open",
  },

  // Alert-specific
  false_positive: {
    color: "bg-slate-100 text-slate-700",
    label: "False Positive",
  },
  confirmed: {
    color: "bg-red-50 text-red-800",
    label: "Confirmed",
  },
  escalated: {
    color: "bg-orange-50 text-orange-800",
    label: "Escalated",
  },

  // Case-specific
  investigating: {
    color: "bg-blue-50 text-blue-800",
    label: "Investigating",
  },
  sar_filed: {
    color: "bg-violet-50 text-violet-800",
    label: "SAR Filed",
  },
  no_action: {
    color: "bg-slate-100 text-slate-700",
    label: "No Action",
  },

  // Transaction-specific
  completed: {
    color: "bg-emerald-50 text-emerald-800",
    label: "Completed",
  },
  failed: {
    color: "bg-red-50 text-red-800",
    label: "Failed",
  },
  blocked: {
    color: "bg-red-50 text-red-800",
    label: "Blocked",
  },

  // Compliance-specific
  draft: {
    color: "bg-slate-100 text-slate-700",
    label: "Draft",
  },
  pending_review: {
    color: "bg-amber-50 text-amber-800",
    label: "Pending Review",
  },
  implemented: {
    color: "bg-emerald-50 text-emerald-800",
    label: "Implemented",
  },

  // Decision outcomes
  allow: {
    color: "bg-emerald-50 text-emerald-800",
    label: "Allow",
  },
  block: {
    color: "bg-red-50 text-red-800",
    label: "Block",
  },
  review: {
    color: "bg-amber-50 text-amber-800",
    label: "Review",
  },
};

export function StatusBadge({
  status,
  variant = "default",
  label,
  color,
  className,
}: StatusBadgeProps) {
  const config = statusConfig[status] || {
    color: "bg-slate-100 text-slate-700",
    label: status.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
  };

  const displayLabel = label || config.label;
  const displayColor = color || config.color;

  const sizeClass =
    variant === "compact" ? "text-xs px-2 py-0.5" : "text-sm px-3 py-1";

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full font-medium",
        displayColor,
        sizeClass,
        className,
      )}
      role="status"
      aria-label={`Status: ${displayLabel}`}
    >
      {displayLabel}
    </span>
  );
}

/**
 * Export default for convenient imports
 */
export default StatusBadge;
