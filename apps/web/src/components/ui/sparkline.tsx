"use client";

import { useMemo } from "react";
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Area,
  AreaChart,
} from "recharts";
import { cn } from "@/lib/utils";

/**
 * ═══════════════════════════════════════════════════════════════════
 * SPARKLINE - Sentinel Design System
 * Miniature inline charts with gradient fills
 * ═══════════════════════════════════════════════════════════════════
 */

type SparklineColor =
  | "aurora"
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
  /** Fill area under the line */
  filled?: boolean;
  /** Animate on mount */
  animate?: boolean;
  /** Show value change indicator */
  showTrend?: boolean;
}

const colorMap: Record<SparklineColor, { stroke: string; fill: string }> = {
  aurora: { stroke: "#6d5acd", fill: "url(#aurora-gradient)" },
  cyan: { stroke: "#00d4ff", fill: "url(#cyan-gradient)" },
  green: { stroke: "#06d6a0", fill: "url(#green-gradient)" },
  yellow: { stroke: "#ffd166", fill: "url(#yellow-gradient)" },
  orange: { stroke: "#ff8c42", fill: "url(#orange-gradient)" },
  red: { stroke: "#ff3366", fill: "url(#red-gradient)" },
  purple: { stroke: "#a855f7", fill: "url(#purple-gradient)" },
  gray: { stroke: "#94a3b8", fill: "url(#gray-gradient)" },
};

const EMPTY_DATA: { value: number }[] = [];

export function Sparkline({
  data,
  color = "aurora",
  width = 100,
  height = 40,
  className,
  filled = true,
  animate = true,
  showTrend = false,
}: SparklineProps) {
  const safeData = data ?? EMPTY_DATA;

  // Determine if color is a preset or custom
  const isPreset = typeof color === "string" && color in colorMap;
  const strokeColor = isPreset
    ? colorMap[color as SparklineColor].stroke
    : color;

  // Calculate trend
  const trend = useMemo(() => {
    if (safeData.length < 2) return 0;
    const first = safeData[0].value;
    const last = safeData[safeData.length - 1].value;
    return ((last - first) / first) * 100;
  }, [safeData]);

  if (!safeData || safeData.length === 0) return null;

  const gradientId = `sparkline-gradient-${color}`;

  return (
    <div className={cn("relative", className)} style={{ width, height }}>
      <ResponsiveContainer width="100%" height="100%">
        {filled ? (
          <AreaChart
            data={safeData}
            margin={{ top: 0, right: 0, bottom: 0, left: 0 }}
          >
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={strokeColor} stopOpacity={0.3} />
                <stop offset="100%" stopColor={strokeColor} stopOpacity={0} />
              </linearGradient>
            </defs>
            <Area
              type="monotone"
              dataKey="value"
              stroke={strokeColor}
              strokeWidth={2}
              fill={`url(#${gradientId})`}
              isAnimationActive={animate}
              animationDuration={1000}
              animationEasing="ease-out"
            />
          </AreaChart>
        ) : (
          <LineChart
            data={safeData}
            margin={{ top: 0, right: 0, bottom: 0, left: 0 }}
          >
            <Line
              type="monotone"
              dataKey="value"
              stroke={strokeColor}
              strokeWidth={2}
              dot={false}
              isAnimationActive={animate}
              animationDuration={1000}
              animationEasing="ease-out"
            />
          </LineChart>
        )}
      </ResponsiveContainer>

      {/* Trend indicator */}
      {showTrend && safeData.length >= 2 && (
        <div
          className={cn(
            "absolute -top-1 -right-1 px-1.5 py-0.5 rounded text-[10px] font-bold",
            trend > 0 && "bg-[#06d6a0]/20 text-[#06d6a0]",
            trend < 0 && "bg-[#ff3366]/20 text-[#ff3366]",
            trend === 0 && "bg-white/10 text-white/50",
          )}
        >
          {trend > 0 ? "+" : ""}
          {trend.toFixed(1)}%
        </div>
      )}
    </div>
  );
}

/**
 * Sparkbar - Mini bar chart variant
 */
interface SparkbarProps {
  data: { value: number }[];
  color?: string | SparklineColor;
  width?: number;
  height?: number;
  className?: string;
}

export function Sparkbar({
  data,
  color = "aurora",
  width = 80,
  height = 24,
  className,
}: SparkbarProps) {
  if (!data || data.length === 0) return null;

  const isPreset = typeof color === "string" && color in colorMap;
  const barColor = isPreset ? colorMap[color as SparklineColor].stroke : color;

  const max = Math.max(...data.map((d) => d.value));
  const barWidth = width / data.length - 1;

  return (
    <div
      className={cn("flex items-end gap-px", className)}
      style={{ width, height }}
    >
      {data.map((d, i) => {
        const barHeight = max > 0 ? (d.value / max) * height : 0;
        return (
          <div
            key={i}
            className="rounded-t-sm transition-all duration-300"
            style={{
              width: barWidth,
              height: barHeight,
              backgroundColor: barColor,
              opacity: 0.3 + (d.value / max) * 0.7,
            }}
          />
        );
      })}
    </div>
  );
}

/**
 * SparkProgress - Inline progress indicator
 */
interface SparkProgressProps {
  value: number;
  max?: number;
  color?: string | SparklineColor;
  width?: number;
  height?: number;
  className?: string;
}

export function SparkProgress({
  value,
  max = 100,
  color = "aurora",
  width = 60,
  height = 4,
  className,
}: SparkProgressProps) {
  const isPreset = typeof color === "string" && color in colorMap;
  const barColor = isPreset ? colorMap[color as SparklineColor].stroke : color;
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));

  return (
    <div
      className={cn("rounded-full bg-white/10 overflow-hidden", className)}
      style={{ width, height }}
    >
      <div
        className="h-full rounded-full transition-all duration-500 ease-out"
        style={{
          width: `${percentage}%`,
          backgroundColor: barColor,
          boxShadow: `0 0 8px ${barColor}50`,
        }}
      />
    </div>
  );
}

export default Sparkline;
