"use client";

import { useMemo } from "react";
import { cn } from "@/lib/utils";

type SparklineColor =
  | "blue"
  | "cyan"
  | "green"
  | "yellow"
  | "orange"
  | "red"
  | "purple"
  | "gray";

interface SparklineProps {
  data: { value: number }[];
  color?: string | SparklineColor;
  width?: number;
  height?: number;
  className?: string;
  filled?: boolean;
  animate?: boolean;
  showTrend?: boolean;
  ariaLabel?: string;
}

interface SparkbarProps {
  data: { value: number }[];
  color?: string | SparklineColor;
  width?: number;
  height?: number;
  className?: string;
  ariaLabel?: string;
}

interface SparkProgressProps {
  value: number;
  max?: number;
  color?: string | SparklineColor;
  width?: number;
  height?: number;
  className?: string;
  ariaLabel?: string;
}

const colorMap: Record<SparklineColor, string> = {
  blue: "var(--color-primary)",
  cyan: "var(--color-accent-secondary)",
  green: "var(--color-risk-low)",
  yellow: "var(--color-risk-medium)",
  orange: "var(--color-risk-high)",
  red: "var(--color-risk-critical)",
  purple: "var(--color-primary)",
  gray: "var(--color-slate-400)",
};

function resolveColor(color: string | SparklineColor): string {
  return typeof color === "string" && color in colorMap
    ? colorMap[color as SparklineColor]
    : color;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

export function Sparkline({
  data,
  color = "blue",
  width = 100,
  height = 40,
  className,
  filled = true,
  animate = true,
  showTrend = false,
  ariaLabel = "Trend chart",
}: SparklineProps) {
  const safeData = useMemo(() => data ?? [], [data]);
  const strokeColor = resolveColor(color);

  const trend = useMemo(() => {
    if (safeData.length < 2) return 0;
    const first = safeData[0]?.value ?? 0;
    const last = safeData[safeData.length - 1]?.value ?? 0;
    if (first === 0) {
      if (last === 0) return 0;
      return last > 0 ? 100 : -100;
    }
    return ((last - first) / Math.abs(first)) * 100;
  }, [safeData]);

  const points = useMemo(() => {
    if (safeData.length === 0) return [] as Array<{ x: number; y: number }>;
    const values = safeData.map((item) => item.value);
    const min = Math.min(...values);
    const max = Math.max(...values);

    return safeData.map((item, index) => {
      const x =
        safeData.length === 1
          ? width / 2
          : (index / (safeData.length - 1)) * (width - 2) + 1;
      const normalized = max === min ? 0.5 : (item.value - min) / (max - min);
      const y = height - normalized * (height - 4) - 2;
      return { x, y };
    });
  }, [safeData, width, height]);

  if (safeData.length === 0 || points.length === 0) {
    return null;
  }

  const linePoints = points.map((point) => `${point.x},${point.y}`).join(" ");
  const first = points[0];
  const last = points[points.length - 1];
  const areaPath = `M ${first.x} ${height} L ${linePoints.replace(/,/g, " ")} L ${last.x} ${height} Z`;

  return (
    <div className={cn("relative", className)} style={{ width, height }}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        width={width}
        height={height}
        role="img"
        aria-label={ariaLabel}
      >
        <title>{ariaLabel}</title>
        {filled && (
          <path
            d={areaPath}
            fill={strokeColor}
            opacity={0.18}
            className={animate ? "transition-all duration-700" : undefined}
          />
        )}
        <polyline
          fill="none"
          stroke={strokeColor}
          strokeWidth={2}
          points={linePoints}
          strokeLinecap="round"
          strokeLinejoin="round"
          className={animate ? "transition-all duration-700" : undefined}
        />
      </svg>

      {showTrend && safeData.length >= 2 && (
        <div
          className={cn(
            "absolute -right-1 -top-1 rounded px-1.5 py-0.5 text-[10px] font-bold",
            trend > 0 && "bg-risk-low-soft text-risk-low",
            trend < 0 && "bg-risk-critical-soft text-risk-critical",
            trend === 0 && "bg-muted text-foreground-tertiary",
          )}
        >
          {trend > 0 ? "+" : ""}
          {trend.toFixed(1)}%
        </div>
      )}
    </div>
  );
}

export function Sparkbar({
  data,
  color = "blue",
  width = 80,
  height = 24,
  className,
  ariaLabel = "Bar chart",
}: SparkbarProps) {
  if (!data || data.length === 0) return null;

  const barColor = resolveColor(color);
  const max = Math.max(...data.map((item) => item.value), 1);
  const barWidth = width / data.length - 1;

  return (
    <div
      role="img"
      aria-label={ariaLabel}
      className={cn("flex items-end gap-px", className)}
      style={{ width, height }}
    >
      {data.map((item, index) => {
        const intensity = clamp(item.value / max, 0, 1);
        const barHeight = max > 0 ? intensity * height : 0;
        return (
          <div
            key={index}
            className="rounded-t-sm transition-all duration-300"
            style={{
              width: barWidth,
              height: barHeight,
              backgroundColor: barColor,
              opacity: 0.3 + intensity * 0.7,
            }}
          />
        );
      })}
    </div>
  );
}

export function SparkProgress({
  value,
  max = 100,
  color = "blue",
  width = 60,
  height = 4,
  className,
  ariaLabel = "Progress",
}: SparkProgressProps) {
  const barColor = resolveColor(color);
  const percentage = clamp((value / Math.max(max, 1)) * 100, 0, 100);

  return (
    <div
      role="progressbar"
      aria-label={ariaLabel}
      aria-valuenow={Math.round(percentage)}
      aria-valuemin={0}
      aria-valuemax={100}
      className={cn("overflow-hidden rounded-full bg-muted", className)}
      style={{ width, height }}
    >
      <div
        className="h-full rounded-full transition-all duration-500 ease-out"
        style={{
          width: `${percentage}%`,
          backgroundColor: barColor,
          boxShadow: `0 0 8px ${barColor}`,
        }}
      />
    </div>
  );
}

export default Sparkline;
