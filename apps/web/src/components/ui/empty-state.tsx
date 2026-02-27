"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button-horizon";
import {
  Search,
  FileX,
  FolderOpen,
  Inbox,
  AlertCircle,
  Plus,
  LucideIcon,
} from "lucide-react";

/**
 * Horizon Empty State System
 * Consistent, helpful empty states for all scenarios
 */

/* ─────────────────────────────────────────────────────────────────────────────
   Types
   ───────────────────────────────────────────────────────────────────────────── */

export interface EmptyStateProps {
  /**
   * Icon to display
   */
  icon?: LucideIcon;
  /**
   * Predefined icon variant
   */
  variant?:
    | "default"
    | "search"
    | "data"
    | "inbox"
    | "error"
    | "no-results"
    | "no-data";
  /**
   * Title text
   */
  title: string;
  /**
   * Description text
   */
  description?: string;
  /**
   * Primary action button
   */
  action?: {
    label: string;
    onClick: () => void;
    icon?: LucideIcon;
  };
  /**
   * Secondary action button
   */
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
  /**
   * Custom content below description
   */
  children?: React.ReactNode;
  /**
   * Container className
   */
  className?: string;
  /**
   * Compact mode (smaller padding)
   */
  compact?: boolean;
}

/* ─────────────────────────────────────────────────────────────────────────────
   Icon mapping
   ───────────────────────────────────────────────────────────────────────────── */

const variantIcons: Record<string, LucideIcon> = {
  default: FolderOpen,
  search: Search,
  data: FileX,
  inbox: Inbox,
  error: AlertCircle,
  "no-results": Search, // Alias for backward compatibility
  "no-data": FileX, // Alias for backward compatibility
};

const variantIconClasses: Record<string, string> = {
  default: "bg-primary/10 text-primary",
  search: "bg-info-500/10 text-info-400",
  data: "bg-foreground-tertiary/10 text-foreground-tertiary",
  inbox: "bg-foreground-tertiary/10 text-foreground-tertiary",
  error: "bg-risk-critical/10 text-risk-critical",
  "no-results": "bg-info-500/10 text-info-400", // Alias for backward compatibility
  "no-data": "bg-foreground-tertiary/10 text-foreground-tertiary", // Alias for backward compatibility
};

/* ─────────────────────────────────────────────────────────────────────────────
   Empty State Component
   ───────────────────────────────────────────────────────────────────────────── */

export function EmptyState({
  icon: CustomIcon,
  variant = "default",
  title,
  description,
  action,
  secondaryAction,
  children,
  className,
  compact = false,
}: EmptyStateProps) {
  const Icon = CustomIcon || variantIcons[variant];
  const iconClass = variantIconClasses[variant];

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center",
        compact ? "py-8 px-4" : "py-16 px-4",
        className,
      )}
    >
      {/* Icon */}
      <div
        className={cn(
          "flex items-center justify-center rounded-full",
          compact ? "h-12 w-12 mb-4" : "h-16 w-16 mb-6",
          iconClass,
        )}
      >
        <Icon className={cn(compact ? "h-6 w-6" : "h-8 w-8")} />
      </div>

      {/* Title */}
      <h3
        className={cn(
          "font-display font-semibold text-foreground",
          compact ? "text-base" : "text-lg",
        )}
      >
        {title}
      </h3>

      {/* Description */}
      {description && (
        <p
          className={cn(
            "mt-2 text-foreground-secondary max-w-sm",
            compact ? "text-sm" : "text-base",
          )}
        >
          {description}
        </p>
      )}

      {/* Custom content */}
      {children && <div className="mt-4">{children}</div>}

      {/* Actions */}
      {(action || secondaryAction) && (
        <div className="mt-6 flex flex-col sm:flex-row items-center gap-3">
          {action && (
            <Button
              variant="primary"
              onClick={action.onClick}
              leftIcon={action.icon && <action.icon className="h-4 w-4" />}
              size={compact ? "sm" : "md"}
            >
              {action.label}
            </Button>
          )}
          {secondaryAction && (
            <Button
              variant="secondary"
              onClick={secondaryAction.onClick}
              size={compact ? "sm" : "md"}
            >
              {secondaryAction.label}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Predefined Empty States
   ───────────────────────────────────────────────────────────────────────────── */

/**
 * Empty state for search results
 */
export function EmptySearch({
  query,
  onClear,
  className,
}: {
  query?: string;
  onClear?: () => void;
  className?: string;
}) {
  return (
    <EmptyState
      variant="search"
      title={query ? `No matches for "${query}"` : "No results found"}
      description="Try broadening your search or adjusting filters. You can also check for typos in your query."
      action={
        onClear
          ? {
              label: "Clear search",
              onClick: onClear,
            }
          : undefined
      }
      className={className}
    />
  );
}

/**
 * Empty state for data tables/lists
 */
export function EmptyData({
  title = "Nothing here yet",
  description = "Items will appear here once they're created or imported.",
  onCreate,
  createLabel = "Create new",
  className,
}: {
  title?: string;
  description?: string;
  onCreate?: () => void;
  createLabel?: string;
  className?: string;
}) {
  return (
    <EmptyState
      variant="data"
      title={title}
      description={description}
      action={
        onCreate
          ? {
              label: createLabel,
              onClick: onCreate,
              icon: Plus,
            }
          : undefined
      }
      className={className}
    />
  );
}

/**
 * Empty state for inbox/notifications
 */
export function EmptyInbox({
  title = "You're all caught up",
  description = "No pending items right now. New notifications will appear here.",
  className,
}: {
  title?: string;
  description?: string;
  className?: string;
}) {
  return (
    <EmptyState
      variant="inbox"
      title={title}
      description={description}
      className={className}
    />
  );
}

/**
 * Empty state for errors
 */
export function EmptyError({
  title = "Unable to load data",
  description = "Something went wrong on our end. Please try again, and contact support if the issue persists.",
  onRetry,
  className,
}: {
  title?: string;
  description?: string;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <EmptyState
      variant="error"
      title={title}
      description={description}
      action={
        onRetry
          ? {
              label: "Try again",
              onClick: onRetry,
            }
          : undefined
      }
      className={className}
    />
  );
}

/**
 * Compact inline empty state (for tables, lists)
 */
export function EmptyInline({
  message = "No items to display",
  className,
}: {
  message?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex items-center justify-center py-8 text-sm text-foreground-secondary",
        className,
      )}
    >
      {message}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Exports
   ───────────────────────────────────────────────────────────────────────────── */

// Alias for backward compatibility
export { EmptyInline as EmptyStateInline };

export default EmptyState;
