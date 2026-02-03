"use client";

import { ReactNode } from "react";
import { motion } from "framer-motion";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";
import { Sparkline } from "./sparkline";
import { AnimatedNumber } from "./animated-number";
import { staggerItem, transitions } from "@/lib/motion";

/**
 * ═══════════════════════════════════════════════════════════════════
 * METRIC CARD - Sentinel Design System
 * Premium dashboard metric display with glass effects
 * ═══════════════════════════════════════════════════════════════════
 */

export type MetricCardSize = "sm" | "md" | "lg";
export type MetricCardVariant = "default" | "hero" | "compact";
export type TrendDirection = "up" | "down" | "neutral";
export type MetricColor = "aurora" | "cyan" | "green" | "yellow" | "orange" | "red" | "purple" | "gray" | "blue";
export type StatusType = "live" | "stale" | "error";

interface MetricCardProps {
  /** Card title/label */
  title: string;
  /** The metric value (number or string) */
  value: string | number;
  /** Icon to display */
  icon?: ReactNode;
  /** Trend information */
  trend?: {
    direction: TrendDirection;
    value: string;
    label?: string;
  };
  /** Sparkline data points */
  sparklineData?: { value: number }[];
  /** Color theme */
  color?: MetricColor;
  /** Card size */
  size?: MetricCardSize;
  /** Card variant */
  variant?: MetricCardVariant;
  /** Enable glow effect based on importance */
  glow?: boolean;
  /** Progress value (0-100) for optional progress bar */
  progress?: number;
  /** Animate number changes */
  animate?: boolean;
  /** Live status indicator */
  status?: StatusType;
  /** Additional className */
  className?: string;
  /** Loading state */
  loading?: boolean;
}

const colorConfig: Record<MetricColor, {
  icon: string;
  glow: string;
  progress: string;
  sparkline: string;
}> = {
  aurora: {
    icon: "text-[#6d5acd] bg-[#6d5acd]/10",
    glow: "shadow-[0_0_20px_rgba(109,90,205,0.3)]",
    progress: "from-[#6d5acd] to-[#00d4ff]",
    sparkline: "#6d5acd",
  },
  blue: {
    icon: "text-blue-500 bg-blue-500/10",
    glow: "shadow-[0_0_20px_rgba(59,130,246,0.25)]",
    progress: "from-blue-500 to-cyan-400",
    sparkline: "#3b82f6",
  },
  cyan: {
    icon: "text-[#00d4ff] bg-[#00d4ff]/10",
    glow: "shadow-[0_0_20px_rgba(0,212,255,0.3)]",
    progress: "from-[#00d4ff] to-[#6d5acd]",
    sparkline: "#00d4ff",
  },
  green: {
    icon: "text-[#06d6a0] bg-[#06d6a0]/10",
    glow: "shadow-[0_0_20px_rgba(6,214,160,0.3)]",
    progress: "from-[#06d6a0] to-[#00d4ff]",
    sparkline: "#06d6a0",
  },
  yellow: {
    icon: "text-[#ffd166] bg-[#ffd166]/10",
    glow: "shadow-[0_0_20px_rgba(255,209,102,0.3)]",
    progress: "from-[#ffd166] to-[#ff8c42]",
    sparkline: "#ffd166",
  },
  orange: {
    icon: "text-[#ff8c42] bg-[#ff8c42]/10",
    glow: "shadow-[0_0_20px_rgba(255,140,66,0.3)]",
    progress: "from-[#ff8c42] to-[#ffd166]",
    sparkline: "#ff8c42",
  },
  red: {
    icon: "text-[#ff3366] bg-[#ff3366]/10",
    glow: "shadow-[0_0_20px_rgba(255,51,102,0.3)]",
    progress: "from-[#ff3366] to-[#ff8c42]",
    sparkline: "#ff3366",
  },
  purple: {
    icon: "text-purple-500 bg-purple-500/10",
    glow: "shadow-[0_0_20px_rgba(168,85,247,0.3)]",
    progress: "from-purple-500 to-pink-500",
    sparkline: "#a855f7",
  },
  gray: {
    icon: "text-gray-400 bg-gray-400/10",
    glow: "shadow-[0_0_15px_rgba(148,163,184,0.2)]",
    progress: "from-gray-400 to-gray-500",
    sparkline: "#94a3b8",
  },
};

const sizeConfig = {
  sm: {
    container: "p-4",
    title: "text-xs",
    value: "text-xl",
    icon: "h-8 w-8 p-1.5",
    iconSize: "h-4 w-4",
  },
  md: {
    container: "p-5",
    title: "text-xs",
    value: "text-3xl",
    icon: "h-10 w-10 p-2",
    iconSize: "h-5 w-5",
  },
  lg: {
    container: "p-6",
    title: "text-sm",
    value: "text-4xl",
    icon: "h-12 w-12 p-2.5",
    iconSize: "h-6 w-6",
  },
};

const statusColors = {
  live: "bg-[#06d6a0]",
  stale: "bg-[#ffd166]",
  error: "bg-[#ff3366]",
};

export function MetricCard({
  title,
  value,
  icon,
  trend,
  sparklineData,
  color = "aurora",
  size = "md",
  variant = "default",
  glow = false,
  progress,
  animate = true,
  status,
  className,
  loading = false,
}: MetricCardProps) {
  const sizes = sizeConfig[size];
  const colors = colorConfig[color] ?? colorConfig.aurora;

  if (loading) {
    return <MetricCardSkeleton size={size} className={className} />;
  }

  const TrendIcon =
    trend?.direction === "up"
      ? TrendingUp
      : trend?.direction === "down"
        ? TrendingDown
        : Minus;

  const trendColor =
    trend?.direction === "up"
      ? "text-[#06d6a0]"
      : trend?.direction === "down"
        ? "text-[#ff3366]"
        : "text-gray-400";

  // Parse value for animation
  const numericValue = typeof value === "number" ? value : parseFloat(String(value).replace(/[^0-9.-]/g, ""));
  const isPercentage = String(value).includes("%");
  const hasDecimal = String(value).includes(".");
  const decimals = hasDecimal ? String(value).split(".")[1]?.replace(/[^0-9]/g, "").length || 1 : 0;

  // Render the value
  const renderValue = () => {
    if (animate && !isNaN(numericValue)) {
      return (
        <AnimatedNumber
          value={numericValue}
          format={isPercentage ? "percentage" : "number"}
          decimals={isPercentage ? 1 : decimals}
          className={cn(
            "font-bold tracking-tight",
            sizes.value
          )}
        />
      );
    }
    return (
      <span className={cn("font-bold font-mono tracking-tight", sizes.value)}>
        {value}
      </span>
    );
  };

  return (
    <motion.div
      variants={variant === "hero" ? undefined : staggerItem}
      whileHover="hover"
      whileTap="tap"
      className={cn(
        "relative overflow-hidden rounded-xl",
        "glass-interactive",
        glow && colors.glow,
        sizes.container,
        variant === "hero" && "col-span-2 row-span-2",
        variant === "compact" && "flex items-center gap-4",
        className
      )}
    >
      {/* Subtle top gradient highlight */}
      <div
        className="absolute inset-x-0 top-0 h-px"
        style={{
          background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent)",
        }}
      />

      {/* Status indicator */}
      {status && (
        <div className="absolute top-3 right-3 flex items-center gap-1.5">
          <span
            className={cn(
              "h-2 w-2 rounded-full",
              statusColors[status],
              status === "live" && "animate-status-pulse"
            )}
          />
          <span className="text-[10px] uppercase tracking-widest text-muted-foreground">
            {status}
          </span>
        </div>
      )}

      <div className={cn(
        "flex items-start justify-between",
        variant === "compact" && "flex-1"
      )}>
        <div className="flex-1 min-w-0">
          {/* Label */}
          <p
            className={cn(
              "text-label text-muted-foreground",
              sizes.title
            )}
          >
            {title}
          </p>

          {/* Value + Sparkline row */}
          <div className="flex items-end gap-3 mt-2">
            {renderValue()}

            {sparklineData && sparklineData.length > 0 && (
              <div className="mb-1 flex-shrink-0">
                <Sparkline
                  data={sparklineData}
                  color={colors.sparkline}
                  width={variant === "hero" ? 120 : 80}
                  height={variant === "hero" ? 40 : 28}
                />
              </div>
            )}
          </div>

          {/* Progress bar */}
          {typeof progress === "number" && (
            <div className="mt-3 h-1.5 w-full rounded-full bg-white/5 overflow-hidden">
              <motion.div
                className={cn("h-full rounded-full bg-gradient-to-r", colors.progress)}
                initial={{ width: 0 }}
                animate={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
                transition={transitions.slow}
              />
            </div>
          )}

          {/* Trend */}
          {trend && (
            <div className={cn("flex items-center gap-1.5 mt-2", trendColor)}>
              <TrendIcon className="h-3.5 w-3.5" />
              <span className="text-sm font-medium font-mono">{trend.value}</span>
              {trend.label && (
                <span className="text-xs text-muted-foreground ml-1">
                  {trend.label}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Icon */}
        {icon && variant !== "compact" && (
          <div className={cn("rounded-lg flex-shrink-0", colors.icon, sizes.icon)}>
            <div className={sizes.iconSize}>{icon}</div>
          </div>
        )}
      </div>

      {/* Compact variant icon */}
      {icon && variant === "compact" && (
        <div className={cn("rounded-lg flex-shrink-0", colors.icon, sizes.icon)}>
          <div className={sizes.iconSize}>{icon}</div>
        </div>
      )}
    </motion.div>
  );
}

/**
 * Skeleton loading state
 */
function MetricCardSkeleton({
  size = "md",
  className,
}: {
  size?: MetricCardSize;
  className?: string;
}) {
  const sizes = sizeConfig[size];

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-xl glass-surface",
        sizes.container,
        className
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 space-y-3">
          <div className="h-3 w-20 rounded bg-white/5 animate-shimmer" />
          <div className="h-8 w-24 rounded bg-white/5 animate-shimmer" />
          <div className="h-3 w-16 rounded bg-white/5 animate-shimmer" />
        </div>
        <div
          className={cn(
            "rounded-lg bg-white/5 animate-shimmer",
            sizes.icon
          )}
        />
      </div>
    </div>
  );
}

export default MetricCard;
