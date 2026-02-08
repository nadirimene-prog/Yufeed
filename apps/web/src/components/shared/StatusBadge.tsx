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
    color:
      "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
    label: "Pending",
  },
  in_review: {
    color: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    label: "In Review",
  },
  in_progress: {
    color: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    label: "In Progress",
  },
  approved: {
    color: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
    label: "Approved",
  },
  rejected: {
    color: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
    label: "Rejected",
  },
  resolved: {
    color: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200",
    label: "Resolved",
  },
  closed: {
    color: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200",
    label: "Closed",
  },
  active: {
    color: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
    label: "Active",
  },
  inactive: {
    color: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200",
    label: "Inactive",
  },
  open: {
    color: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    label: "Open",
  },

  // Alert-specific
  false_positive: {
    color: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200",
    label: "False Positive",
  },
  confirmed: {
    color: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
    label: "Confirmed",
  },
  escalated: {
    color:
      "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
    label: "Escalated",
  },

  // Case-specific
  investigating: {
    color: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    label: "Investigating",
  },
  sar_filed: {
    color:
      "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
    label: "SAR Filed",
  },
  no_action: {
    color: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200",
    label: "No Action",
  },

  // Transaction-specific
  completed: {
    color: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
    label: "Completed",
  },
  failed: {
    color: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
    label: "Failed",
  },
  blocked: {
    color: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
    label: "Blocked",
  },

  // Compliance-specific
  draft: {
    color: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200",
    label: "Draft",
  },
  pending_review: {
    color:
      "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
    label: "Pending Review",
  },
  implemented: {
    color: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
    label: "Implemented",
  },

  // Decision outcomes
  allow: {
    color: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
    label: "Allow",
  },
  block: {
    color: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
    label: "Block",
  },
  review: {
    color:
      "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
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
    color: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200",
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
