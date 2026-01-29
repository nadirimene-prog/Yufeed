"use client";

import { cn } from "@/lib/utils";

/**
 * ═══════════════════════════════════════════════════════════════════
 * SKELETON - Sentinel Design System
 * Glass-styled loading placeholders with shimmer effect
 * ═══════════════════════════════════════════════════════════════════
 */

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Skeleton variant */
  variant?: "default" | "text" | "circular" | "rectangular";
  /** Animation type */
  animation?: "shimmer" | "pulse" | "none";
  /** Width (for non-full-width skeletons) */
  width?: number | string;
  /** Height */
  height?: number | string;
}

function Skeleton({
  className,
  variant = "default",
  animation = "shimmer",
  width,
  height,
  style,
  ...props
}: SkeletonProps) {
  const variantStyles = {
    default: "rounded-lg",
    text: "rounded h-4",
    circular: "rounded-full",
    rectangular: "rounded-none",
  };

  const animationStyles = {
    shimmer: "animate-shimmer bg-gradient-to-r from-white/[0.03] via-white/[0.08] to-white/[0.03] bg-[length:200%_100%]",
    pulse: "animate-pulse bg-white/[0.05]",
    none: "bg-white/[0.05]",
  };

  return (
    <div
      className={cn(
        "relative overflow-hidden",
        variantStyles[variant],
        animationStyles[animation],
        className
      )}
      style={{
        width: width,
        height: height,
        ...style,
      }}
      {...props}
    />
  );
}

/**
 * Skeleton Text - For loading text content
 */
interface SkeletonTextProps {
  /** Number of lines */
  lines?: number;
  /** Last line width percentage */
  lastLineWidth?: string;
  /** Gap between lines */
  gap?: "sm" | "md" | "lg";
  /** Line height */
  lineHeight?: "sm" | "md" | "lg";
  className?: string;
}

function SkeletonText({
  lines = 3,
  lastLineWidth = "70%",
  gap = "md",
  lineHeight = "md",
  className,
}: SkeletonTextProps) {
  const gapClasses = {
    sm: "space-y-1.5",
    md: "space-y-2",
    lg: "space-y-3",
  };

  const heightClasses = {
    sm: "h-3",
    md: "h-4",
    lg: "h-5",
  };

  return (
    <div className={cn(gapClasses[gap], className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          variant="text"
          className={heightClasses[lineHeight]}
          style={{
            width: i === lines - 1 ? lastLineWidth : "100%",
          }}
        />
      ))}
    </div>
  );
}

/**
 * Skeleton Avatar - For loading user avatars
 */
interface SkeletonAvatarProps {
  size?: "sm" | "md" | "lg" | "xl";
  className?: string;
}

function SkeletonAvatar({ size = "md", className }: SkeletonAvatarProps) {
  const sizeClasses = {
    sm: "h-8 w-8",
    md: "h-10 w-10",
    lg: "h-12 w-12",
    xl: "h-16 w-16",
  };

  return (
    <Skeleton
      variant="circular"
      className={cn(sizeClasses[size], className)}
    />
  );
}

/**
 * Skeleton Card - For loading card content
 */
interface SkeletonCardProps {
  /** Show header section */
  hasHeader?: boolean;
  /** Show avatar in header */
  hasAvatar?: boolean;
  /** Number of content lines */
  contentLines?: number;
  /** Show footer */
  hasFooter?: boolean;
  className?: string;
}

function SkeletonCard({
  hasHeader = true,
  hasAvatar = false,
  contentLines = 3,
  hasFooter = false,
  className,
}: SkeletonCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-white/[0.06] bg-white/[0.02] p-5",
        className
      )}
    >
      {/* Header */}
      {hasHeader && (
        <div className="flex items-start gap-3 mb-4">
          {hasAvatar && <SkeletonAvatar />}
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-3 w-1/4" />
          </div>
        </div>
      )}

      {/* Content */}
      <SkeletonText lines={contentLines} />

      {/* Footer */}
      {hasFooter && (
        <div className="flex items-center gap-2 mt-4 pt-4 border-t border-white/[0.06]">
          <Skeleton className="h-8 w-20" />
          <Skeleton className="h-8 w-20" />
        </div>
      )}
    </div>
  );
}

/**
 * Skeleton Metric Card - For loading metric displays
 */
interface SkeletonMetricCardProps {
  size?: "sm" | "md" | "lg";
  className?: string;
}

function SkeletonMetricCard({ size = "md", className }: SkeletonMetricCardProps) {
  const sizeConfig = {
    sm: { padding: "p-4", title: "h-3 w-16", value: "h-6 w-20", icon: "h-8 w-8" },
    md: { padding: "p-5", title: "h-3 w-20", value: "h-8 w-24", icon: "h-10 w-10" },
    lg: { padding: "p-6", title: "h-4 w-24", value: "h-10 w-28", icon: "h-12 w-12" },
  };

  const config = sizeConfig[size];

  return (
    <div
      className={cn(
        "rounded-xl border border-white/[0.06] bg-white/[0.02]",
        config.padding,
        className
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 space-y-3">
          <Skeleton className={config.title} />
          <Skeleton className={config.value} />
          <Skeleton className="h-3 w-16" />
        </div>
        <Skeleton className={cn(config.icon, "rounded-lg")} />
      </div>
    </div>
  );
}

/**
 * Skeleton Table - For loading table data
 */
interface SkeletonTableProps {
  /** Number of rows */
  rows?: number;
  /** Number of columns */
  columns?: number;
  /** Show header */
  hasHeader?: boolean;
  className?: string;
}

function SkeletonTable({
  rows = 5,
  columns = 4,
  hasHeader = true,
  className,
}: SkeletonTableProps) {
  return (
    <div className={cn("rounded-xl border border-white/[0.06] overflow-hidden", className)}>
      {/* Header */}
      {hasHeader && (
        <div className="flex gap-4 p-4 border-b border-white/[0.06] bg-white/[0.02]">
          {Array.from({ length: columns }).map((_, i) => (
            <Skeleton
              key={i}
              className="h-4 flex-1"
              style={{ maxWidth: i === 0 ? "30%" : `${100 / columns}%` }}
            />
          ))}
        </div>
      )}

      {/* Rows */}
      <div className="divide-y divide-white/[0.04]">
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <div key={rowIndex} className="flex gap-4 p-4">
            {Array.from({ length: columns }).map((_, colIndex) => (
              <Skeleton
                key={colIndex}
                className="h-4 flex-1"
                style={{ maxWidth: colIndex === 0 ? "30%" : `${100 / columns}%` }}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Skeleton List - For loading list items
 */
interface SkeletonListProps {
  /** Number of items */
  items?: number;
  /** Show avatar */
  hasAvatar?: boolean;
  /** Show description line */
  hasDescription?: boolean;
  /** Show action button */
  hasAction?: boolean;
  className?: string;
}

function SkeletonList({
  items = 5,
  hasAvatar = true,
  hasDescription = true,
  hasAction = false,
  className,
}: SkeletonListProps) {
  return (
    <div className={cn("space-y-3", className)}>
      {Array.from({ length: items }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-3 p-3 rounded-lg border border-white/[0.04] bg-white/[0.01]"
        >
          {hasAvatar && <SkeletonAvatar size="sm" />}
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-2/5" />
            {hasDescription && <Skeleton className="h-3 w-3/5" />}
          </div>
          {hasAction && <Skeleton className="h-8 w-16 rounded-lg" />}
        </div>
      ))}
    </div>
  );
}

/**
 * Legacy exports for backward compatibility
 */
function CardSkeleton() {
  return <SkeletonCard />;
}

function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return <SkeletonTable rows={rows} />;
}

function GraphSkeleton() {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-6">
      <Skeleton className="h-6 w-48 mb-6" />
      <div className="h-64 flex items-end justify-between gap-2">
        {Array.from({ length: 12 }).map((_, i) => (
          <Skeleton
            key={i}
            className="flex-1 rounded-t-md"
            style={{ height: `${20 + Math.random() * 80}%` }}
          />
        ))}
      </div>
      <div className="flex justify-between mt-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-3 w-12" />
        ))}
      </div>
    </div>
  );
}

function TextSkeleton({ lines = 3 }: { lines?: number }) {
  return <SkeletonText lines={lines} />;
}

export {
  Skeleton,
  SkeletonText,
  SkeletonAvatar,
  SkeletonCard,
  SkeletonMetricCard,
  SkeletonTable,
  SkeletonList,
  // Legacy exports
  CardSkeleton,
  TableSkeleton,
  GraphSkeleton,
  TextSkeleton,
};
