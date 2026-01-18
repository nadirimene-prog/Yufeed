"use client";

import { Line, LineChart, ResponsiveContainer } from "recharts";

interface SparklineProps {
    data: { value: number }[];
    color?: string;
    width?: number;
    height?: number;
    className?: string;
}

export function Sparkline({
    data,
    color = "currentColor",
    width = 100,
    height = 40,
    className,
}: SparklineProps) {
    if (!data || data.length === 0) return null;

    // Determine min/max for better scaling, though Sparklines usually auto-scale well enough
    // We stick to simple rendering for speed and visual clarity

    return (
        <div className={className} style={{ width, height }}>
            <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data}>
                    <Line
                        type="monotone"
                        dataKey="value"
                        stroke={color}
                        strokeWidth={2}
                        dot={false}
                        isAnimationActive={false} // Disable animation for instant load feel or keep subtle
                    />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}
