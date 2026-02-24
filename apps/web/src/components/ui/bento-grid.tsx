"use client";

import { ReactNode } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { staggerContainer, staggerItem } from "@/lib/motion";

/**
 * ═══════════════════════════════════════════════════════════════════
 * BENTO GRID - Horizon Design System
 * Flexible asymmetric grid layout for dashboards
 * ═══════════════════════════════════════════════════════════════════
 */

interface BentoGridProps {
  /** Number of columns (default: 4) */
  columns?: 2 | 3 | 4 | 6;
  /** Gap between items */
  gap?: "sm" | "md" | "lg";
  /** Enable stagger animation on mount */
  animate?: boolean;
  /** Additional className */
  className?: string;
  /** Grid items */
  children: ReactNode;
}

const gapClasses = {
  sm: "gap-3",
  md: "gap-4",
  lg: "gap-6",
};

const columnClasses = {
  2: "grid-cols-1 md:grid-cols-2",
  3: "grid-cols-1 md:grid-cols-2 lg:grid-cols-3",
  4: "grid-cols-1 md:grid-cols-2 lg:grid-cols-4",
  6: "grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6",
};

export function BentoGrid({
  columns = 4,
  gap = "md",
  animate = true,
  className,
  children,
}: BentoGridProps) {
  const Wrapper = animate ? motion.div : "div";
  const wrapperProps = animate
    ? {
        variants: staggerContainer,
        initial: "initial",
        animate: "animate",
      }
    : {};

  return (
    <Wrapper
      className={cn(
        "grid auto-rows-[minmax(120px,auto)]",
        columnClasses[columns],
        gapClasses[gap],
        className,
      )}
      {...wrapperProps}
    >
      {children}
    </Wrapper>
  );
}

/**
 * Individual Bento Grid Item
 */
interface BentoItemProps {
  /** Column span (1-4) */
  colSpan?: 1 | 2 | 3 | 4;
  /** Row span (1-3) */
  rowSpan?: 1 | 2 | 3;
  /** Enable hover effects */
  hover?: boolean;
  /** Additional className */
  className?: string;
  /** Item content */
  children: ReactNode;
}

const colSpanClasses = {
  1: "",
  2: "md:col-span-2",
  3: "md:col-span-2 lg:col-span-3",
  4: "md:col-span-2 lg:col-span-4",
};

const rowSpanClasses = {
  1: "",
  2: "row-span-2",
  3: "row-span-3",
};

export function BentoItem({
  colSpan = 1,
  rowSpan = 1,
  hover = false,
  className,
  children,
}: BentoItemProps) {
  return (
    <motion.div
      variants={staggerItem}
      className={cn(
        colSpanClasses[colSpan],
        rowSpanClasses[rowSpan],
        hover && "hover-lift cursor-pointer",
        className,
      )}
    >
      {children}
    </motion.div>
  );
}

/**
 * Pre-styled Bento Card (combines BentoItem + Card styling)
 */
interface BentoCardProps extends BentoItemProps {
  /** Card title */
  title?: string;
  /** Card description */
  description?: string;
  /** Icon element */
  icon?: ReactNode;
  /** Header action element */
  action?: ReactNode;
  /** Card accent shadow */
  glow?: "none" | "primary" | "cyan";
}

export function BentoCard({
  colSpan = 1,
  rowSpan = 1,
  hover = true,
  title,
  description,
  icon,
  action,
  glow = "none",
  className,
  children,
}: BentoCardProps) {
  const glowClasses = {
    none: "",
    primary: "hover:shadow-accent",
    cyan: "hover:shadow-md",
  };

  return (
    <BentoItem colSpan={colSpan} rowSpan={rowSpan} className={className}>
      <motion.div
        whileHover={hover ? { y: -4 } : undefined}
        className={cn(
          "h-full rounded-xl border border-border-subtle bg-card p-5 hover:border-border-default hover:shadow-sm",
          glowClasses[glow],
          "transition-shadow duration-300",
        )}
      >
        {/* Header */}
        {(title || icon || action) && (
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-3">
              {icon && (
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  {icon}
                </div>
              )}
              {title && (
                <div>
                  <h3 className="text-sm font-semibold text-foreground">
                    {title}
                  </h3>
                  {description && (
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {description}
                    </p>
                  )}
                </div>
              )}
            </div>
            {action && <div>{action}</div>}
          </div>
        )}

        {/* Content */}
        <div className="flex-1">{children}</div>
      </motion.div>
    </BentoItem>
  );
}

/**
 * Bento Stat Card - For displaying metrics
 */
interface BentoStatProps {
  /** Metric label */
  label: string;
  /** Metric value */
  value: string | number;
  /** Trend indicator */
  trend?: {
    value: string;
    positive?: boolean;
  };
  /** Icon element */
  icon?: ReactNode;
  /** Column span */
  colSpan?: 1 | 2;
  /** Additional className */
  className?: string;
}

export function BentoStat({
  label,
  value,
  trend,
  icon,
  colSpan = 1,
  className,
}: BentoStatProps) {
  return (
    <BentoItem colSpan={colSpan} className={className}>
      <div className="flex h-full flex-col justify-between rounded-xl border border-border-subtle bg-card p-5">
        <div className="flex items-center justify-between">
          <span className="text-label">{label}</span>
          {icon && <span className="text-muted-foreground">{icon}</span>}
        </div>
        <div className="mt-2">
          <span className="text-metric text-foreground">{value}</span>
          {trend && (
            <span
              className={cn(
                "ml-2 text-sm font-medium",
                trend.positive ? "text-trend-up" : "text-trend-down",
              )}
            >
              {trend.value}
            </span>
          )}
        </div>
      </div>
    </BentoItem>
  );
}

export default BentoGrid;
