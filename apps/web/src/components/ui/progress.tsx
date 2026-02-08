"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { springs, transitions } from "@/lib/motion";

/**
 * ═══════════════════════════════════════════════════════════════════
 * PROGRESS - Sentinel Design System
 * Gradient progress bars with glass effects and animations
 * ═══════════════════════════════════════════════════════════════════
 */

type ProgressColor =
  | "aurora"
  | "cyan"
  | "green"
  | "yellow"
  | "orange"
  | "red"
  | "purple"
  | "gray";

interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
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
  aurora: {
    gradient: "from-[#6d5acd] to-[#00d4ff]",
    glow: "shadow-[0_0_20px_rgba(109,90,205,0.4)]",
  },
  cyan: {
    gradient: "from-[#00d4ff] to-[#6d5acd]",
    glow: "shadow-[0_0_20px_rgba(0,212,255,0.4)]",
  },
  green: {
    gradient: "from-[#06d6a0] to-[#00d4ff]",
    glow: "shadow-[0_0_20px_rgba(6,214,160,0.4)]",
  },
  yellow: {
    gradient: "from-[#ffd166] to-[#ff8c42]",
    glow: "shadow-[0_0_20px_rgba(255,209,102,0.4)]",
  },
  orange: {
    gradient: "from-[#ff8c42] to-[#ffd166]",
    glow: "shadow-[0_0_20px_rgba(255,140,66,0.4)]",
  },
  red: {
    gradient: "from-[#ff3366] to-[#ff8c42]",
    glow: "shadow-[0_0_20px_rgba(255,51,102,0.4)]",
  },
  purple: {
    gradient: "from-purple-500 to-pink-500",
    glow: "shadow-[0_0_20px_rgba(168,85,247,0.4)]",
  },
  gray: {
    gradient: "from-gray-400 to-gray-500",
    glow: "shadow-[0_0_15px_rgba(148,163,184,0.2)]",
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
  color = "aurora",
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
      <span className={cn("font-mono font-medium text-white/70", sizes.label)}>
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
            "bg-white/[0.06]",
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
interface CircularProgressProps {
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
  color = "aurora",
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
    aurora: { start: "#6d5acd", end: "#00d4ff" },
    cyan: { start: "#00d4ff", end: "#6d5acd" },
    green: { start: "#06d6a0", end: "#00d4ff" },
    yellow: { start: "#ffd166", end: "#ff8c42" },
    orange: { start: "#ff8c42", end: "#ffd166" },
    red: { start: "#ff3366", end: "#ff8c42" },
    purple: { start: "#a855f7", end: "#ec4899" },
    gray: { start: "#94a3b8", end: "#64748b" },
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
          stroke="rgba(255, 255, 255, 0.06)"
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
            filter: "drop-shadow(0 0 8px rgba(109, 90, 205, 0.4))",
          }}
        />
      </svg>

      {/* Center content */}
      <div className="absolute inset-0 flex items-center justify-center">
        {children ||
          (showLabel && (
            <span className="text-sm font-bold font-mono text-white">
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
interface Step {
  label: string;
  description?: string;
}

interface StepProgressProps {
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
  color = "aurora",
  orientation = "horizontal",
  className,
}: StepProgressProps) {
  const colors = colorConfig[color];
  const gradientColors = {
    aurora: "#6d5acd",
    cyan: "#00d4ff",
    green: "#06d6a0",
    yellow: "#ffd166",
    orange: "#ff8c42",
    red: "#ff3366",
    purple: "#a855f7",
    gray: "#94a3b8",
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
                    "border-white/20 bg-transparent text-white/40",
                )}
                style={{
                  background:
                    isCompleted || isCurrent
                      ? `linear-gradient(135deg, ${gradientColors[color]} 0%, #00d4ff 100%)`
                      : undefined,
                  boxShadow: isCurrent
                    ? `0 0 20px ${gradientColors[color]}50`
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
                    "relative overflow-hidden rounded-full bg-white/10",
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
                  isCompleted || isCurrent ? "text-white" : "text-white/40",
                )}
              >
                {step.label}
              </p>
              {step.description && (
                <p className="text-xs text-white/30 mt-0.5 truncate">
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
