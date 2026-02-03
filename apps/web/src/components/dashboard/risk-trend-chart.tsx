"use client";

import { useMemo } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend } from "recharts";

interface RiskTrendData {
    date: string;
    critical: number;
    high: number;
    medium: number;
    low: number;
    total: number;
}

interface RiskTrendChartProps {
    data?: RiskTrendData[];
    timeRange?: '7d' | '30d' | '90d';
    className?: string;
}

// Generate mock data for demonstration
const generateMockData = (days: number): RiskTrendData[] => {
    const data: RiskTrendData[] = [];
    const today = new Date();

    for (let i = days - 1; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);

        // Generate realistic-looking trend data
        const critical = Math.floor(Math.random() * 5) + 2;
        const high = Math.floor(Math.random() * 15) + 10;
        const medium = Math.floor(Math.random() * 25) + 20;
        const low = Math.floor(Math.random() * 30) + 40;

        data.push({
            date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
            critical,
            high,
            medium,
            low,
            total: critical + high + medium + low,
        });
    }

    return data;
};

type TooltipEntry = {
    name?: string;
    value?: number;
    color?: string;
};

type RiskTrendTooltipProps = {
    active?: boolean;
    payload?: TooltipEntry[];
    label?: string;
};

function RiskTrendTooltip({ active, payload, label }: RiskTrendTooltipProps) {
    if (active && payload && payload.length) {
        return (
            <div className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg shadow-lg p-3">
                <p className="text-sm font-semibold text-gray-900 dark:text-white mb-2">{label}</p>
                <div className="space-y-1">
                    {payload.map((entry, index) => (
                        <div key={index} className="flex items-center justify-between gap-4 text-xs">
                            <div className="flex items-center gap-2">
                                <div
                                    className="w-3 h-3 rounded-full"
                                    style={{ backgroundColor: entry.color }}
                                />
                                <span className="text-gray-600 dark:text-gray-400 capitalize">{entry.name}</span>
                            </div>
                            <span className="font-medium text-gray-900 dark:text-white">{entry.value}</span>
                        </div>
                    ))}
                </div>
            </div>
        );
    }
    return null;
}

export function RiskTrendChart({ data, timeRange = '30d', className }: RiskTrendChartProps) {
    const chartData = useMemo(() => {
        if (data && data.length > 0) return data;

        const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90;
        return generateMockData(days);
    }, [data, timeRange]);

    return (
        <div className={className}>
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                    data={chartData}
                    margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                >
                    <defs>
                        <linearGradient id="colorCritical" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="var(--color-risk-critical)" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="var(--color-risk-critical)" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="colorHigh" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="var(--color-risk-high)" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="var(--color-risk-high)" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="colorMedium" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="var(--color-risk-medium)" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="var(--color-risk-medium)" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="colorLow" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="var(--color-risk-low)" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="var(--color-risk-low)" stopOpacity={0} />
                        </linearGradient>
                    </defs>

                    <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="#e5e7eb"
                        className="dark:stroke-slate-700"
                    />

                    <XAxis
                        dataKey="date"
                        stroke="#6b7280"
                        className="dark:stroke-slate-400"
                        style={{ fontSize: '12px' }}
                        tickLine={false}
                    />

                    <YAxis
                        stroke="#6b7280"
                        className="dark:stroke-slate-400"
                        style={{ fontSize: '12px' }}
                        tickLine={false}
                    />

                    <Tooltip content={<RiskTrendTooltip />} />

                    <Legend
                        wrapperStyle={{ fontSize: '13px' }}
                        iconType="circle"
                    />

                    <Area
                        type="monotone"
                        dataKey="critical"
                        stackId="1"
                        stroke="var(--color-risk-critical)"
                        fill="url(#colorCritical)"
                        strokeWidth={2}
                        name="Critical"
                    />

                    <Area
                        type="monotone"
                        dataKey="high"
                        stackId="1"
                        stroke="var(--color-risk-high)"
                        fill="url(#colorHigh)"
                        strokeWidth={2}
                        name="High"
                    />

                    <Area
                        type="monotone"
                        dataKey="medium"
                        stackId="1"
                        stroke="var(--color-risk-medium)"
                        fill="url(#colorMedium)"
                        strokeWidth={2}
                        name="Medium"
                    />

                    <Area
                        type="monotone"
                        dataKey="low"
                        stackId="1"
                        stroke="var(--color-risk-low)"
                        fill="url(#colorLow)"
                        strokeWidth={2}
                        name="Low"
                    />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}
