"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

/**
 * Horizon Skeleton System
 * Loading placeholders that reduce layout shift and improve perceived performance
 */

/* ─────────────────────────────────────────────────────────────────────────────
   Base Skeleton Component
   ───────────────────────────────────────────────────────────────────────────── */

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  /**
   * Enable pulse animation
   */
  animate?: boolean;
  /**
   * Skeleton variant
   */
  variant?: "default" | "circle" | "text" | "rect";
  /**
   * Width of skeleton (can be any CSS value)
   */
  width?: string | number;
  /**
   * Height of skeleton (can be any CSS value)
   */
  height?: string | number;
}

function Skeleton({
  className,
  animate = true,
  variant = "default",
  width,
  height,
  style,
  ...props
}: SkeletonProps) {
  const variantClasses = {
    default: "rounded-md",
    circle: "rounded-full",
    text: "rounded h-4 w-full",
    rect: "rounded-none",
  }[variant];

  const styles: React.CSSProperties = {
    width: typeof width === "number" ? `${width}px` : width,
    height: typeof height === "number" ? `${height}px` : height,
    ...style,
  };

  return (
    <div
      className={cn(
        "bg-bg-floating",
        animate && "animate-pulse",
        variantClasses,
        className,
      )}
      style={styles}
      {...props}
    />
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Skeleton Text (for multi-line text)
   ───────────────────────────────────────────────────────────────────────────── */

export interface SkeletonTextProps extends React.HTMLAttributes<HTMLDivElement> {
  lines?: number;
  lineHeight?: number;
  lastLineWidth?: string;
  animate?: boolean;
}

function SkeletonText({
  className,
  lines = 3,
  lineHeight = 16,
  lastLineWidth = "60%",
  animate = true,
  ...props
}: SkeletonTextProps) {
  return (
    <div className={cn("space-y-2", className)} {...props}>
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton
          key={index}
          variant="text"
          height={lineHeight}
          width={index === lines - 1 ? lastLineWidth : "100%"}
          animate={animate}
        />
      ))}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Skeleton Avatar
   ───────────────────────────────────────────────────────────────────────────── */

export interface SkeletonAvatarProps {
  size?: "xs" | "sm" | "md" | "lg" | "xl";
  animate?: boolean;
  className?: string;
}

function SkeletonAvatar({
  size = "md",
  animate = true,
  className,
}: SkeletonAvatarProps) {
  const sizeClasses = {
    xs: "h-6 w-6",
    sm: "h-8 w-8",
    md: "h-10 w-10",
    lg: "h-12 w-12",
    xl: "h-16 w-16",
  }[size];

  return (
    <Skeleton
      variant="circle"
      className={cn(sizeClasses, className)}
      animate={animate}
    />
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Skeleton Card
   ───────────────────────────────────────────────────────────────────────────── */

export interface SkeletonCardProps {
  header?: boolean;
  content?: boolean;
  footer?: boolean;
  /** @deprecated Use footer instead */
  hasFooter?: boolean;
  lines?: number;
  /** @deprecated Use lines instead */
  contentLines?: number;
  animate?: boolean;
  className?: string;
}

function SkeletonCard({
  header = true,
  content = true,
  footer = false,
  hasFooter,
  lines = 3,
  contentLines,
  animate = true,
  className,
}: SkeletonCardProps) {
  // Support both lines and contentLines for backward compatibility
  const lineCount = contentLines ?? lines;
  // Support both footer and hasFooter for backward compatibility
  const showFooter = hasFooter ?? footer;
  return (
    <Card variant="default" className={className}>
      {header && (
        <CardHeader>
          <Skeleton width="60%" height={20} animate={animate} />
          <Skeleton
            width="40%"
            height={14}
            animate={animate}
            className="mt-2"
          />
        </CardHeader>
      )}
      {content && (
        <CardContent>
          <SkeletonText lines={lineCount} animate={animate} />
        </CardContent>
      )}
      {showFooter && (
        <div className="px-5 pb-5 pt-0 flex items-center gap-2">
          <Skeleton width={80} height={32} animate={animate} />
          <Skeleton width={80} height={32} animate={animate} />
        </div>
      )}
    </Card>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Skeleton Metric Card
   ───────────────────────────────────────────────────────────────────────────── */

function SkeletonMetricCard({ className }: { className?: string }) {
  return (
    <Card variant="default" className={className}>
      <CardContent>
        <div className="flex items-start justify-between">
          <div className="space-y-2 flex-1">
            <Skeleton width="50%" height={14} />
            <Skeleton width="40%" height={32} />
            <Skeleton width="30%" height={16} />
          </div>
          <Skeleton variant="circle" className="h-10 w-10" />
        </div>
      </CardContent>
    </Card>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Skeleton Table
   ───────────────────────────────────────────────────────────────────────────── */

export interface SkeletonTableProps {
  rows?: number;
  columns?: number;
  hasHeader?: boolean;
  animate?: boolean;
  className?: string;
}

function SkeletonTable({
  rows = 5,
  columns = 4,
  hasHeader = true,
  animate = true,
  className,
}: SkeletonTableProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border-subtle overflow-hidden",
        className,
      )}
    >
      <table className="w-full">
        {hasHeader && (
          <thead className="bg-bg-overlay border-b border-border-subtle">
            <tr>
              {Array.from({ length: columns }).map((_, index) => (
                <th key={index} className="px-4 py-3">
                  <Skeleton
                    width={`${60 + ((index * 17) % 30)}%`}
                    height={14}
                    animate={animate}
                  />
                </th>
              ))}
            </tr>
          </thead>
        )}
        <tbody className="divide-y divide-border-subtle">
          {Array.from({ length: rows }).map((_, rowIndex) => (
            <tr
              key={rowIndex}
              className={rowIndex % 2 === 1 ? "bg-bg-overlay/50" : ""}
            >
              {Array.from({ length: columns }).map((_, colIndex) => (
                <td key={colIndex} className="px-4 py-4">
                  <Skeleton
                    width={`${40 + (((rowIndex * columns + colIndex) * 13) % 50)}%`}
                    height={16}
                    animate={animate}
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Skeleton List
   ───────────────────────────────────────────────────────────────────────────── */

export interface SkeletonListProps {
  items?: number;
  avatar?: boolean;
  lines?: number;
  animate?: boolean;
  className?: string;
}

function SkeletonList({
  items = 5,
  avatar = true,
  lines = 2,
  animate = true,
  className,
}: SkeletonListProps) {
  return (
    <div className={cn("space-y-3", className)}>
      {Array.from({ length: items }).map((_, index) => (
        <div
          key={index}
          className="flex items-start gap-3 p-3 rounded-lg bg-bg-elevated"
        >
          {avatar && <SkeletonAvatar size="md" animate={animate} />}
          <div className="flex-1 min-w-0 space-y-2">
            <Skeleton width="70%" height={16} animate={animate} />
            {lines > 1 && (
              <Skeleton width="90%" height={14} animate={animate} />
            )}
            {lines > 2 && (
              <Skeleton width="50%" height={14} animate={animate} />
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Skeleton Page
   ─────────────────────────────────────────────────────────────────────────────
   Full page skeleton layout for initial loading states
   ───────────────────────────────────────────────────────────────────────────── */

function SkeletonPage() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="space-y-2">
        <Skeleton width="30%" height={32} />
        <Skeleton width="50%" height={16} />
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonMetricCard key={i} />
        ))}
      </div>

      {/* Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <SkeletonCard lines={4} />
          <SkeletonTable rows={5} columns={4} />
        </div>
        <div className="space-y-4">
          <SkeletonCard lines={3} />
          <SkeletonCard lines={2} footer />
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Exports
   ───────────────────────────────────────────────────────────────────────────── */

export {
  Skeleton,
  SkeletonText,
  SkeletonAvatar,
  SkeletonCard,
  SkeletonMetricCard,
  SkeletonTable,
  SkeletonList,
  SkeletonPage,
};

// Aliases for backward compatibility
export { SkeletonTable as TableSkeleton };

export default Skeleton;
