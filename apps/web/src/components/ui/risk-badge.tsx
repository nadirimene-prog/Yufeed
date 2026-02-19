"use client";

import { motion } from "framer-motion";
import {
  AlertTriangle,
  AlertCircle,
  AlertOctagon,
  CheckCircle,
  HelpCircle,
  ShieldCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { criticalPulse } from "@/lib/motion";

/**
 * ═══════════════════════════════════════════════════════════════════
 * RISK BADGE - Sentinel Design System
 * Glowing, pulsing risk level indicators
 * ═══════════════════════════════════════════════════════════════════
 */

export type RiskLevel =
  | "critical"
  | "high"
  | "medium"
  | "low"
  | "clear"
  | "unknown";
export type BadgeSize = "sm" | "md" | "lg";
export type GlowIntensity = "none" | "subtle" | "strong";

interface RiskBadgeProps {
  /** Risk level */
  level: RiskLevel | string;
  /** Badge size */
  size?: BadgeSize;
  /** Show icon */
  showIcon?: boolean;
  /** Override pulse animation behavior */
  animate?: boolean;
  /** Glow intensity */
  glow?: GlowIntensity;
  /** Custom label (overrides default) */
  label?: string;
  /** Additional className */
  className?: string;
}

// Risk level configuration with Sentinel colors
const riskConfig: Record<
  RiskLevel,
  {
    label: string;
    icon: typeof AlertTriangle;
    bg: string;
    border: string;
    text: string;
    glow: string;
    glowStrong: string;
    shouldPulse: boolean;
  }
> = {
  critical: {
    label: "Critical",
    icon: AlertOctagon,
    bg: "bg-risk-critical-soft",
    border: "border-risk-critical/40",
    text: "text-risk-critical",
    glow: "shadow-[0_0_12px_rgba(255,51,102,0.3)]",
    glowStrong: "shadow-[0_0_20px_rgba(255,51,102,0.5)]",
    shouldPulse: true,
  },
  high: {
    label: "High",
    icon: AlertTriangle,
    bg: "bg-risk-high-soft",
    border: "border-risk-high/40",
    text: "text-risk-high",
    glow: "shadow-[0_0_10px_rgba(255,140,66,0.25)]",
    glowStrong: "shadow-[0_0_16px_rgba(255,140,66,0.4)]",
    shouldPulse: true,
  },
  medium: {
    label: "Medium",
    icon: AlertCircle,
    bg: "bg-risk-medium-soft",
    border: "border-risk-medium/40",
    text: "text-risk-medium",
    glow: "shadow-[0_0_8px_rgba(255,209,102,0.2)]",
    glowStrong: "shadow-[0_0_14px_rgba(255,209,102,0.35)]",
    shouldPulse: false,
  },
  low: {
    label: "Low",
    icon: CheckCircle,
    bg: "bg-risk-low-soft",
    border: "border-risk-low/40",
    text: "text-risk-low",
    glow: "shadow-[0_0_6px_rgba(6,214,160,0.15)]",
    glowStrong: "shadow-[0_0_12px_rgba(6,214,160,0.3)]",
    shouldPulse: false,
  },
  clear: {
    label: "Clear",
    icon: ShieldCheck,
    bg: "bg-risk-clear-soft",
    border: "border-risk-clear/30",
    text: "text-risk-clear",
    glow: "shadow-[0_0_6px_rgba(0,212,255,0.15)]",
    glowStrong: "shadow-[0_0_12px_rgba(0,212,255,0.25)]",
    shouldPulse: false,
  },
  unknown: {
    label: "Unknown",
    icon: HelpCircle,
    bg: "bg-gray-500/10",
    border: "border-gray-500/30",
    text: "text-gray-400",
    glow: "",
    glowStrong: "",
    shouldPulse: false,
  },
};

const sizeConfig = {
  sm: {
    padding: "px-2 py-0.5",
    text: "text-[10px]",
    icon: "h-3 w-3",
    gap: "gap-1",
  },
  md: {
    padding: "px-2.5 py-1",
    text: "text-xs",
    icon: "h-3.5 w-3.5",
    gap: "gap-1.5",
  },
  lg: {
    padding: "px-3 py-1.5",
    text: "text-sm",
    icon: "h-4 w-4",
    gap: "gap-2",
  },
};

// Normalize risk level string to RiskLevel type
function normalizeRiskLevel(level: string): RiskLevel {
  const normalized = level.toLowerCase().trim();
  if (normalized in riskConfig) {
    return normalized as RiskLevel;
  }
  // Handle common variations
  if (normalized === "very high" || normalized === "severe") return "critical";
  if (normalized === "elevated") return "high";
  if (normalized === "moderate") return "medium";
  if (normalized === "minimal" || normalized === "safe") return "low";
  if (normalized === "none" || normalized === "verified") return "clear";
  return "unknown";
}

export function RiskBadge({
  level,
  size = "md",
  showIcon = true,
  animate = false,
  glow = "subtle",
  label,
  className,
}: RiskBadgeProps) {
  const normalizedLevel = normalizeRiskLevel(String(level));
  const config = riskConfig[normalizedLevel];
  const sizes = sizeConfig[size];

  // Determine if should pulse
  const shouldPulse = animate && config.shouldPulse;

  // Determine glow class
  const glowClass =
    glow === "strong"
      ? config.glowStrong
      : glow === "subtle"
        ? config.glow
        : "";

  const Icon = config.icon;

  const badgeContent = (
    <>
      {showIcon && (
        <Icon className={cn(sizes.icon, shouldPulse && "animate-pulse")} />
      )}
      <span className="font-semibold tracking-wide">
        {label || config.label}
      </span>
    </>
  );

  // Use motion for critical/high with pulse
  if (
    shouldPulse &&
    (normalizedLevel === "critical" || normalizedLevel === "high")
  ) {
    return (
      <motion.span
        animate={normalizedLevel === "critical" ? criticalPulse : undefined}
        className={cn(
          "inline-flex items-center rounded-full border",
          sizes.padding,
          sizes.text,
          sizes.gap,
          config.bg,
          config.border,
          config.text,
          glowClass,
          className,
        )}
        title={`Risk Level: ${config.label}`}
      >
        {badgeContent}
      </motion.span>
    );
  }

  // Static badge for other levels
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border transition-shadow duration-300",
        sizes.padding,
        sizes.text,
        sizes.gap,
        config.bg,
        config.border,
        config.text,
        glowClass,
        className,
      )}
      title={`Risk Level: ${config.label}`}
    >
      {badgeContent}
    </span>
  );
}

/**
 * Risk Score Badge - Shows numeric risk score with automatic level
 */
interface RiskScoreBadgeProps {
  /** Risk score (0-100) */
  score: number;
  /** Show the label alongside score */
  showLabel?: boolean;
  /** Badge size */
  size?: BadgeSize;
  /** Additional className */
  className?: string;
}

export function RiskScoreBadge({
  score,
  showLabel = true,
  size = "md",
  className,
}: RiskScoreBadgeProps) {
  // Map score to risk level
  const level: RiskLevel =
    score >= 80
      ? "critical"
      : score >= 60
        ? "high"
        : score >= 40
          ? "medium"
          : score >= 20
            ? "low"
            : "clear";

  const config = riskConfig[level];

  return (
    <div className={cn("inline-flex items-center gap-2", className)}>
      <span
        className={cn(
          "inline-flex items-center justify-center font-bold font-mono rounded-full",
          config.bg,
          config.text,
          config.glow,
          size === "sm" && "h-8 w-8 text-sm",
          size === "md" && "h-10 w-10 text-base",
          size === "lg" && "h-12 w-12 text-lg",
        )}
      >
        {score}
      </span>
      {showLabel && <RiskBadge level={level} size={size} showIcon={false} />}
    </div>
  );
}

/**
 * Compact Risk Indicator - Just a colored dot
 */
interface RiskIndicatorProps {
  level: RiskLevel | string;
  size?: "sm" | "md" | "lg";
  pulse?: boolean;
  className?: string;
}

export function RiskIndicator({
  level,
  size = "md",
  pulse,
  className,
}: RiskIndicatorProps) {
  const normalizedLevel = normalizeRiskLevel(String(level));
  const config = riskConfig[normalizedLevel];
  const shouldPulse = pulse ?? config.shouldPulse;

  const sizeClasses = {
    sm: "h-2 w-2",
    md: "h-2.5 w-2.5",
    lg: "h-3 w-3",
  };

  const bgColors: Record<RiskLevel, string> = {
    critical: "bg-risk-critical",
    high: "bg-risk-high",
    medium: "bg-risk-medium",
    low: "bg-risk-low",
    clear: "bg-risk-clear",
    unknown: "bg-gray-400",
  };

  return (
    <span
      className={cn(
        "inline-block rounded-full",
        sizeClasses[size],
        bgColors[normalizedLevel],
        shouldPulse && "animate-status-pulse",
        className,
      )}
      title={config.label}
    />
  );
}

export default RiskBadge;
