"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/**
 * Horizon Badge System
 * Status indicators, labels, and tags
 */

/* ─────────────────────────────────────────────────────────────────────────────
   Badge Variants
   ───────────────────────────────────────────────────────────────────────────── */

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full font-medium transition-colors",
  {
    variants: {
      /* Color variants */
      variant: {
        default:
          "bg-muted text-foreground-secondary border border-border-subtle",
        primary: "bg-primary/10 text-primary border border-primary/20",
        secondary: "bg-secondary/10 text-secondary border border-secondary/20",
        success:
          "bg-success-500/10 text-success-400 border border-success-500/20",
        warning:
          "bg-warning-500/10 text-warning-400 border border-warning-500/20",
        critical:
          "bg-risk-critical/10 text-risk-critical border border-risk-critical/20",
        info: "bg-info-500/10 text-info-400 border border-info-500/20",
      },
      /* Size variants */
      size: {
        sm: "px-2 py-0.5 text-xs",
        md: "px-2.5 py-0.5 text-xs",
        lg: "px-3 py-1 text-sm",
      },
      /* Visual style */
      mode: {
        subtle: "",
        solid: "border-transparent",
        dot: "pl-2",
      },
    },
    compoundVariants: [
      /* Solid mode overrides */
      {
        variant: "default",
        mode: "solid",
        class: "bg-secondary text-foreground",
      },
      {
        variant: "primary",
        mode: "solid",
        class: "bg-primary text-primary-foreground",
      },
      {
        variant: "secondary",
        mode: "solid",
        class: "bg-secondary text-foreground",
      },
      {
        variant: "success",
        mode: "solid",
        class: "bg-success-500 text-primary-foreground",
      },
      {
        variant: "warning",
        mode: "solid",
        class: "bg-warning-500 text-primary-foreground",
      },
      {
        variant: "critical",
        mode: "solid",
        class: "bg-risk-critical text-primary-foreground",
      },
      {
        variant: "info",
        mode: "solid",
        class: "bg-info-500 text-primary-foreground",
      },
    ],
    defaultVariants: {
      variant: "default",
      size: "md",
      mode: "subtle",
    },
  },
);

/* ─────────────────────────────────────────────────────────────────────────────
   Status Dot Component
   ───────────────────────────────────────────────────────────────────────────── */

const statusDotVariants = cva("h-2 w-2 rounded-full", {
  variants: {
    status: {
      online: "bg-success-500",
      away: "bg-warning-500",
      busy: "bg-risk-critical",
      offline: "bg-foreground-tertiary",
      new: "bg-primary",
    },
    pulse: {
      true: "animate-pulse-soft",
      false: "",
    },
  },
  defaultVariants: {
    status: "online",
    pulse: false,
  },
});

/* ─────────────────────────────────────────────────────────────────────────────
   Badge Component
   ───────────────────────────────────────────────────────────────────────────── */

export interface BadgeProps
  extends
    React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {
  dot?: boolean;
  dotStatus?: VariantProps<typeof statusDotVariants>["status"];
  dotPulse?: boolean;
  dismissible?: boolean;
  onDismiss?: () => void;
}

const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  (
    {
      className,
      variant,
      size,
      mode,
      dot,
      dotStatus,
      dotPulse = false,
      dismissible,
      onDismiss,
      children,
      ...props
    },
    ref,
  ) => {
    return (
      <span
        ref={ref}
        className={cn(badgeVariants({ variant, size, mode, className }))}
        {...props}
      >
        {dot && (
          <span
            className={cn(
              statusDotVariants({ status: dotStatus, pulse: dotPulse }),
            )}
            aria-hidden="true"
          />
        )}
        {children}
        {dismissible && (
          <button
            type="button"
            onClick={onDismiss}
            className="ml-1 rounded-full p-0.5 hover:bg-current hover:bg-opacity-20 focus-ring"
            aria-label="Remove badge"
          >
            <svg
              className="h-3 w-3"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        )}
      </span>
    );
  },
);
Badge.displayName = "Badge";

/* ─────────────────────────────────────────────────────────────────────────────
   Status Badge Component
   Pre-configured badges for common status states
   ───────────────────────────────────────────────────────────────────────────── */

interface StatusBadgeProps extends Omit<
  BadgeProps,
  "variant" | "dot" | "dotStatus"
> {
  status:
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
    | "archived";
}

const statusConfig: Record<
  StatusBadgeProps["status"],
  {
    variant: VariantProps<typeof badgeVariants>["variant"];
    label: string;
    dotStatus: VariantProps<typeof statusDotVariants>["status"];
  }
> = {
  draft: { variant: "default", label: "Draft", dotStatus: "offline" },
  pending: { variant: "warning", label: "Pending", dotStatus: "away" },
  in_review: { variant: "info", label: "In Review", dotStatus: "away" },
  approved: { variant: "success", label: "Approved", dotStatus: "online" },
  rejected: { variant: "critical", label: "Rejected", dotStatus: "busy" },
  active: { variant: "success", label: "Active", dotStatus: "online" },
  inactive: { variant: "default", label: "Inactive", dotStatus: "offline" },
  critical: { variant: "critical", label: "Critical", dotStatus: "busy" },
  warning: { variant: "warning", label: "Warning", dotStatus: "away" },
  expired: { variant: "critical", label: "Expired", dotStatus: "busy" },
  archived: { variant: "default", label: "Archived", dotStatus: "offline" },
};

const StatusBadge = React.forwardRef<HTMLSpanElement, StatusBadgeProps>(
  ({ status, children, ...props }, ref) => {
    const config = statusConfig[status];
    return (
      <Badge
        ref={ref}
        variant={config.variant}
        dot
        dotStatus={config.dotStatus}
        {...props}
      >
        {children || config.label}
      </Badge>
    );
  },
);
StatusBadge.displayName = "StatusBadge";

/* ─────────────────────────────────────────────────────────────────────────────
   Risk Badge Component
   Pre-configured badges for risk levels
   ───────────────────────────────────────────────────────────────────────────── */

interface RiskBadgeProps extends Omit<BadgeProps, "variant"> {
  level: "critical" | "high" | "medium" | "low" | "info";
  showDot?: boolean;
}

const riskConfig: Record<
  RiskBadgeProps["level"],
  { variant: VariantProps<typeof badgeVariants>["variant"]; label: string }
> = {
  critical: { variant: "critical", label: "Critical" },
  high: { variant: "warning", label: "High" },
  medium: { variant: "warning", label: "Medium" },
  low: { variant: "success", label: "Low" },
  info: { variant: "info", label: "Info" },
};

const RiskBadge = React.forwardRef<HTMLSpanElement, RiskBadgeProps>(
  ({ level, showDot = true, children, ...props }, ref) => {
    const config = riskConfig[level];
    return (
      <Badge
        ref={ref}
        variant={config.variant}
        dot={showDot}
        dotPulse={level === "critical"}
        {...props}
      >
        {children || config.label}
      </Badge>
    );
  },
);
RiskBadge.displayName = "RiskBadge";

/* ─────────────────────────────────────────────────────────────────────────────
   Count Badge Component
   Small numeric indicator
   ───────────────────────────────────────────────────────────────────────────── */

interface CountBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  count: number;
  max?: number;
  variant?: "default" | "primary" | "critical";
}

const CountBadge = React.forwardRef<HTMLSpanElement, CountBadgeProps>(
  ({ count, max = 99, variant = "default", className, ...props }, ref) => {
    const displayCount = count > max ? `${max}+` : count;

    const variantClasses = {
      default: "bg-secondary text-foreground-secondary",
      primary: "bg-primary text-primary-foreground",
      critical: "bg-risk-critical text-primary-foreground",
    }[variant];

    return (
      <span
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1 rounded-full text-xs font-medium",
          variantClasses,
          className,
        )}
        {...props}
      >
        {displayCount}
      </span>
    );
  },
);
CountBadge.displayName = "CountBadge";

/* ─────────────────────────────────────────────────────────────────────────────
   Exports
   ───────────────────────────────────────────────────────────────────────────── */

export {
  Badge,
  StatusBadge,
  RiskBadge,
  CountBadge,
  badgeVariants,
  statusDotVariants,
};
