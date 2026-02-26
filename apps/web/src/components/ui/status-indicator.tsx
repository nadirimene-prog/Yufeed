"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { statusPulse } from "@/lib/motion";

/**
 * ═══════════════════════════════════════════════════════════════════
 * STATUS INDICATOR - Horizon Design System
 * Living status indicators with glow effects
 * ═══════════════════════════════════════════════════════════════════
 */

export type StatusState =
  | "live"
  | "active"
  | "idle"
  | "warning"
  | "error"
  | "success"
  | "connecting";
export type StatusSize = "sm" | "md" | "lg";

interface StatusIndicatorProps {
  /** Status state */
  status: StatusState;
  /** Optional label text */
  label?: string;
  /** Show the label */
  showLabel?: boolean;
  /** Indicator size */
  size?: StatusSize;
  /** Override pulse animation */
  pulse?: boolean;
  /** Timestamp to display */
  timestamp?: string;
  /** Additional className */
  className?: string;
}

// Status configuration with Horizon colors
const statusConfig: Record<
  StatusState,
  {
    label: string;
    color: string;
    bg: string;
    glow: string;
    textColor: string;
    shouldPulse: boolean;
  }
> = {
  live: {
    label: "Live",
    color: "bg-risk-low",
    bg: "bg-risk-low/10",
    glow: "",
    textColor: "text-risk-low",
    shouldPulse: true,
  },
  active: {
    label: "Active",
    color: "bg-risk-low",
    bg: "bg-risk-low/10",
    glow: "",
    textColor: "text-risk-low",
    shouldPulse: false,
  },
  idle: {
    label: "Idle",
    color: "bg-foreground-disabled",
    bg: "bg-foreground-disabled/10",
    glow: "",
    textColor: "text-foreground-disabled",
    shouldPulse: false,
  },
  warning: {
    label: "Warning",
    color: "bg-risk-medium",
    bg: "bg-risk-medium/10",
    glow: "",
    textColor: "text-risk-medium",
    shouldPulse: true,
  },
  error: {
    label: "Error",
    color: "bg-risk-critical",
    bg: "bg-risk-critical/10",
    glow: "",
    textColor: "text-risk-critical",
    shouldPulse: true,
  },
  success: {
    label: "Success",
    color: "bg-risk-low",
    bg: "bg-risk-low/10",
    glow: "",
    textColor: "text-risk-low",
    shouldPulse: false,
  },
  connecting: {
    label: "Connecting",
    color: "bg-primary",
    bg: "bg-primary/10",
    glow: "",
    textColor: "text-primary",
    shouldPulse: true,
  },
};

const sizeConfig = {
  sm: {
    dot: "h-2 w-2",
    text: "text-[10px]",
    gap: "gap-1.5",
  },
  md: {
    dot: "h-2.5 w-2.5",
    text: "text-xs",
    gap: "gap-2",
  },
  lg: {
    dot: "h-3 w-3",
    text: "text-sm",
    gap: "gap-2.5",
  },
};

export function StatusIndicator({
  status,
  label,
  showLabel = true,
  size = "md",
  pulse,
  timestamp,
  className,
}: StatusIndicatorProps) {
  const config = statusConfig[status];
  const sizes = sizeConfig[size];
  const displayLabel = label || config.label;
  const shouldPulse = pulse ?? config.shouldPulse;

  return (
    <div className={cn("inline-flex items-center", sizes.gap, className)}>
      <StatusDot status={status} size={size} pulse={shouldPulse} />

      {showLabel && (
        <div className="flex flex-col">
          <span
            className={cn(
              "font-medium uppercase tracking-wider",
              config.textColor,
              sizes.text,
            )}
          >
            {displayLabel}
          </span>
          {timestamp && (
            <span className="text-[10px] text-muted-foreground">
              {timestamp}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Simple dot-only status indicator
 */
interface StatusDotProps {
  status: StatusState;
  size?: StatusSize;
  pulse?: boolean;
  className?: string;
}

export function StatusDot({
  status,
  size = "md",
  pulse,
  className,
}: StatusDotProps) {
  const config = statusConfig[status];
  const sizes = sizeConfig[size];
  const shouldPulse = pulse ?? config.shouldPulse;

  // Use motion for pulsing states
  if (shouldPulse) {
    return (
      <div className={cn("relative inline-flex", className)}>
        {/* Glow ring */}
        <motion.span
          className={cn(
            "absolute inset-0 rounded-full",
            config.color,
            "opacity-40",
          )}
          animate={{
            scale: [1, 1.8, 1],
            opacity: [0.4, 0, 0.4],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
        {/* Core dot */}
        <motion.span
          className={cn(
            "relative rounded-full",
            sizes.dot,
            config.color,
            config.glow,
          )}
          animate={
            status === "connecting" ? { opacity: [1, 0.5, 1] } : statusPulse
          }
        />
      </div>
    );
  }

  // Static dot
  return (
    <span
      className={cn(
        "inline-block rounded-full",
        sizes.dot,
        config.color,
        config.glow,
        className,
      )}
      title={config.label}
    />
  );
}

/**
 * Inline status badge with background
 */
interface StatusBadgeProps {
  status: StatusState;
  label?: string;
  size?: StatusSize;
  className?: string;
}

export function StatusBadge({
  status,
  label,
  size = "md",
  className,
}: StatusBadgeProps) {
  const config = statusConfig[status];
  const sizes = sizeConfig[size];
  const displayLabel = label || config.label;

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border",
        sizes.gap,
        config.bg,
        config.textColor,
        "border-current/20",
        size === "sm" && "px-2 py-0.5",
        size === "md" && "px-2.5 py-1",
        size === "lg" && "px-3 py-1.5",
        className,
      )}
    >
      <StatusDot status={status} size="sm" pulse={false} />
      <span className={cn("font-medium uppercase tracking-wider", sizes.text)}>
        {displayLabel}
      </span>
    </span>
  );
}

/**
 * Connection status indicator (for WebSocket, etc.)
 */
interface ConnectionStatusProps {
  connected: boolean;
  connecting?: boolean;
  className?: string;
}

export function ConnectionStatus({
  connected,
  connecting = false,
  className,
}: ConnectionStatusProps) {
  const status: StatusState = connecting
    ? "connecting"
    : connected
      ? "live"
      : "error";

  return (
    <StatusIndicator
      status={status}
      label={connecting ? "Connecting..." : connected ? "Live" : "Disconnected"}
      size="sm"
      className={className}
    />
  );
}

export default StatusIndicator;
