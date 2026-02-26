"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { springs, transitions } from "@/lib/motion";

/**
 * ═══════════════════════════════════════════════════════════════════
 * PROGRESS - Horizon Design System
 * Gradient progress bars with clean surfaces and animations
 * ═══════════════════════════════════════════════════════════════════
 */

type ProgressColor =
  | "blue"
  | "cyan"
  | "green"
  | "yellow"
  | "orange"
  | "red"
  | "purple"
  | "gray";

export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Progress value (0-100) */
  value: number;
  /** Maximum value */
  max?: number;
  /** Color theme */
  color?: ProgressColor;
  /** Size variant */
  size?: "sm" | "md" | "lg";
  /** Show percentage label */
  showLabel?: boolean;
  /** Label position */
  labelPosition?: "top" | "right" | "inside";
  /** Animate the progress bar */
  animate?: boolean;
  /** Indeterminate loading state */
  indeterminate?: boolean;
  /** Glow effect */
  glow?: boolean;
}

const colorConfig: Record<ProgressColor, { gradient: string; glow: string }> = {
  blue: {
    gradient: "from-primary to-accent-secondary",
    glow: "",
  },
  cyan: {
    gradient: "from-accent-secondary to-primary",
    glow: "",
  },
  green: {
    gradient: "from-risk-low to-accent-secondary",
    glow: "",
  },
  yellow: {
    gradient: "from-risk-medium to-risk-high",
    glow: "",
  },
  orange: {
    gradient: "from-risk-high to-risk-medium",
    glow: "",
  },
  red: {
    gradient: "from-risk-critical to-risk-high",
    glow: "",
  },
  purple: {
    gradient: "from-primary to-accent-secondary",
    glow: "",
  },
  gray: {
    gradient: "from-foreground-disabled to-foreground-tertiary",
    glow: "",
  },
};

const sizeConfig = {
  sm: { track: "h-1", label: "text-xs" },
  md: { track: "h-2", label: "text-sm" },
  lg: { track: "h-3", label: "text-sm" },
};

function Progress({
  value,
  max = 100,
  color = "blue",
  size = "md",
  showLabel = false,
  labelPosition = "right",
  animate = true,
  indeterminate = false,
  glow = false,
  className,
  ...props
}: ProgressProps) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));
  const colors = colorConfig[color];
  const sizes = sizeConfig[size];

  const renderLabel = () => {
    if (!showLabel) return null;
    return (
      <span
        className={cn(
          "font-mono font-medium text-foreground-secondary",
          sizes.label,
        )}
      >
        {Math.round(percentage)}%
      </span>
    );
  };

  return (
    <div
      className={cn(
        "w-full",
        labelPosition === "top" && "space-y-1.5",
        className,
      )}
      {...props}
    >
      {/* Top label */}
      {labelPosition === "top" && showLabel && (
        <div className="flex justify-end">{renderLabel()}</div>
      )}

      {/* Progress container */}
      <div
        className={cn(
          "flex items-center gap-3",
          labelPosition === "right" && showLabel && "gap-3",
        )}
      >
        {/* Track */}
        <div
          className={cn(
            "relative flex-1 overflow-hidden rounded-full",
            "bg-muted",
            sizes.track,
          )}
        >
          {/* Fill */}
          {indeterminate ? (
            <motion.div
              className={cn(
                "absolute inset-y-0 w-1/3 rounded-full bg-gradient-to-r",
                colors.gradient,
                glow && colors.glow,
              )}
              animate={{
                x: ["-100%", "400%"],
              }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                ease: "easeInOut",
              }}
            />
          ) : (
            <motion.div
              className={cn(
                "h-full rounded-full bg-gradient-to-r",
                colors.gradient,
                glow && colors.glow,
              )}
              initial={animate ? { width: 0 } : false}
              animate={{ width: `${percentage}%` }}
              transition={transitions.slow}
            >
              {/* Shine effect */}
              <div
                className="absolute inset-0 rounded-full"
                style={{
                  background:
                    "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.2) 50%, transparent 100%)",
                }}
              />

              {/* Inside label */}
              {labelPosition === "inside" && showLabel && percentage > 15 && (
                <div className="absolute inset-0 flex items-center justify-end pr-2">
                  <span className="text-[10px] font-bold text-white drop-shadow-sm">
                    {Math.round(percentage)}%
                  </span>
                </div>
              )}
            </motion.div>
          )}
        </div>

        {/* Right label */}
        {labelPosition === "right" && showLabel && renderLabel()}
      </div>
    </div>
  );
}

/**
 * Circular Progress - Ring-style progress indicator
 */
export interface CircularProgressProps {
  /** Progress value (0-100) */
  value: number;
  /** Size in pixels */
  size?: number;
  /** Stroke width */
  strokeWidth?: number;
  /** Color theme */
  color?: ProgressColor;
  /** Show center label */
  showLabel?: boolean;
  /** Custom center content */
  children?: React.ReactNode;
  /** Animate the progress */
  animate?: boolean;
  className?: string;
}

function CircularProgress({
  value,
  size = 64,
  strokeWidth = 4,
  color = "blue",
  showLabel = false,
  children,
  animate = true,
  className,
}: CircularProgressProps) {
  const percentage = Math.min(100, Math.max(0, value));
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (percentage / 100) * circumference;

  const gradientId = React.useId();
  // Get gradient colors
  const gradientColors = {
    blue: {
      start: "var(--color-primary)",
      end: "var(--color-accent-secondary)",
    },
    cyan: {
      start: "var(--color-accent-secondary)",
      end: "var(--color-primary)",
    },
    green: {
      start: "var(--color-risk-low)",
      end: "var(--color-accent-secondary)",
    },
    yellow: {
      start: "var(--color-risk-medium)",
      end: "var(--color-risk-high)",
    },
    orange: {
      start: "var(--color-risk-high)",
      end: "var(--color-risk-medium)",
    },
    red: {
      start: "var(--color-risk-critical)",
      end: "var(--color-risk-high)",
    },
    purple: {
      start: "var(--color-primary)",
      end: "var(--color-accent-secondary)",
    },
    gray: {
      start: "var(--color-slate-400)",
      end: "var(--color-slate-500)",
    },
  };

  return (
    <div
      className={cn(
        "relative inline-flex items-center justify-center",
        className,
      )}
    >
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="-rotate-90"
      >
        {/* Gradient definition */}
        <defs>
          <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={gradientColors[color].start} />
            <stop offset="100%" stopColor={gradientColors[color].end} />
          </linearGradient>
        </defs>

        {/* Track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(0, 0, 0, 0.06)"
          strokeWidth={strokeWidth}
        />

        {/* Progress */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={`url(#${gradientId})`}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={animate ? { strokeDashoffset: circumference } : false}
          animate={{ strokeDashoffset: offset }}
          transition={transitions.slow}
          style={{
            filter: "drop-shadow(0 0 6px rgba(0, 82, 255, 0.3))",
          }}
        />
      </svg>

      {/* Center content */}
      <div className="absolute inset-0 flex items-center justify-center">
        {children ??
          (showLabel && (
            <span className="text-sm font-bold font-mono text-foreground">
              {Math.round(percentage)}%
            </span>
          ))}
      </div>
    </div>
  );
}

/**
 * Step Progress - For multi-step workflows
 */
export interface Step {
  label: string;
  description?: string;
}

export interface StepProgressProps {
  /** Steps configuration */
  steps: Step[];
  /** Current step (0-indexed) */
  currentStep: number;
  /** Color theme */
  color?: ProgressColor;
  /** Orientation */
  orientation?: "horizontal" | "vertical";
  className?: string;
}

function StepProgress({
  steps,
  currentStep,
  color = "blue",
  orientation = "horizontal",
  className,
}: StepProgressProps) {
  const colors = colorConfig[color];
  const gradientColors = {
    blue: "var(--color-primary)",
    cyan: "var(--color-accent-secondary)",
    green: "var(--color-risk-low)",
    yellow: "var(--color-risk-medium)",
    orange: "var(--color-risk-high)",
    red: "var(--color-risk-critical)",
    purple: "var(--color-primary)",
    gray: "var(--color-slate-400)",
  };
  const gradientEndColors = {
    blue: "var(--color-accent-secondary)",
    cyan: "var(--color-accent-secondary)",
    green: "var(--color-accent-secondary)",
    yellow: "var(--color-accent-secondary)",
    orange: "var(--color-accent-secondary)",
    red: "var(--color-accent-secondary)",
    purple: "var(--color-accent-secondary)",
    gray: "var(--color-slate-500)",
  };
  const gradientGlowColors = {
    blue: "rgba(0, 82, 255, 0.3)",
    cyan: "rgba(77, 124, 255, 0.3)",
    green: "rgba(16, 185, 129, 0.3)",
    yellow: "rgba(245, 158, 11, 0.3)",
    orange: "rgba(249, 115, 22, 0.3)",
    red: "rgba(220, 38, 38, 0.3)",
    purple: "rgba(0, 82, 255, 0.3)",
    gray: "rgba(148, 163, 184, 0.2)",
  };

  return (
    <div
      className={cn(
        orientation === "horizontal" ? "flex items-start" : "flex flex-col",
        className,
      )}
    >
      {steps.map((step, index) => {
        const isCompleted = index < currentStep;
        const isCurrent = index === currentStep;
        const isLast = index === steps.length - 1;

        return (
          <div
            key={index}
            className={cn(
              orientation === "horizontal"
                ? "flex-1 flex items-start"
                : "flex gap-3",
              !isLast && orientation === "horizontal" && "flex-1",
            )}
          >
            <div
              className={cn(
                "flex items-center",
                orientation === "horizontal" ? "flex-col" : "flex-row",
              )}
            >
              {/* Step circle */}
              <motion.div
                className={cn(
                  "relative flex items-center justify-center rounded-full border-2 transition-colors",
                  "h-8 w-8 text-sm font-medium",
                  isCompleted && "border-transparent",
                  isCurrent && "border-transparent",
                  !isCompleted &&
                    !isCurrent &&
                    "border-border bg-transparent text-foreground-tertiary",
                )}
                style={{
                  background:
                    isCompleted || isCurrent
                      ? `linear-gradient(135deg, ${gradientColors[color]} 0%, ${gradientEndColors[color]} 100%)`
                      : undefined,
                  boxShadow: isCurrent
                    ? `0 0 20px ${gradientGlowColors[color]}`
                    : undefined,
                }}
                initial={false}
                animate={{
                  scale: isCurrent ? 1.1 : 1,
                }}
                transition={springs.snappy}
              >
                {isCompleted ? (
                  <svg
                    className="h-4 w-4 text-white"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                ) : (
                  <span
                    className={cn(isCompleted || isCurrent ? "text-white" : "")}
                  >
                    {index + 1}
                  </span>
                )}
              </motion.div>

              {/* Connector line */}
              {!isLast && (
                <div
                  className={cn(
                    orientation === "horizontal"
                      ? "h-0.5 flex-1 mx-2"
                      : "w-0.5 h-8 my-2",
                    "relative overflow-hidden rounded-full bg-border-subtle",
                  )}
                >
                  <motion.div
                    className={cn(
                      "absolute inset-0 bg-gradient-to-r",
                      colors.gradient,
                    )}
                    initial={{ scaleX: 0 }}
                    animate={{ scaleX: isCompleted ? 1 : 0 }}
                    transition={transitions.slow}
                    style={{ transformOrigin: "left" }}
                  />
                </div>
              )}
            </div>

            {/* Label */}
            <div
              className={cn(
                orientation === "horizontal"
                  ? "mt-2 text-center"
                  : "flex-1 pt-1",
                "min-w-0",
              )}
            >
              <p
                className={cn(
                  "text-sm font-medium truncate",
                  isCompleted || isCurrent
                    ? "text-foreground"
                    : "text-foreground-tertiary",
                )}
              >
                {step.label}
              </p>
              {step.description && (
                <p className="mt-0.5 text-xs text-foreground-tertiary truncate">
                  {step.description}
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export { Progress, CircularProgress, StepProgress };
export type { ProgressColor };
