"use client";

import React from "react";
import { cn } from "@/lib/utils";
import type { RiskHeatMapCell, LikelihoodLevel, ImpactLevel } from "@/types/compliance";

interface RiskHeatMapProps {
    cells: RiskHeatMapCell[];
    onCellClick?: (cell: RiskHeatMapCell) => void;
    className?: string;
}

const likelihoodLabels: { value: LikelihoodLevel; label: string }[] = [
    { value: "almost_certain", label: "Almost Certain" },
    { value: "likely", label: "Likely" },
    { value: "possible", label: "Possible" },
    { value: "unlikely", label: "Unlikely" },
    { value: "rare", label: "Rare" },
];

const impactLabels: { value: ImpactLevel; label: string }[] = [
    { value: "insignificant", label: "Insignificant" },
    { value: "minor", label: "Minor" },
    { value: "moderate", label: "Moderate" },
    { value: "major", label: "Major" },
    { value: "catastrophic", label: "Catastrophic" },
];

// Risk level matrix based on likelihood x impact
const getRiskLevel = (likelihood: LikelihoodLevel, impact: ImpactLevel): "low" | "medium" | "high" | "critical" => {
    const likelihoodIdx = likelihoodLabels.findIndex((l) => l.value === likelihood);
    const impactIdx = impactLabels.findIndex((i) => i.value === impact);

    // Higher indices = higher risk (almost_certain=0 is highest, rare=4 is lowest)
    // We invert likelihood since it's ordered from high to low
    const likelihoodScore = 4 - likelihoodIdx; // 4 (almost_certain) to 0 (rare)
    const impactScore = impactIdx; // 0 (insignificant) to 4 (catastrophic)

    const riskScore = likelihoodScore + impactScore;

    if (riskScore >= 7) return "critical";
    if (riskScore >= 5) return "high";
    if (riskScore >= 3) return "medium";
    return "low";
};

const getCellColor = (level: "low" | "medium" | "high" | "critical", count: number): string => {
    if (count === 0) {
        switch (level) {
            case "critical": return "bg-red-900/20 hover:bg-red-900/30";
            case "high": return "bg-orange-900/20 hover:bg-orange-900/30";
            case "medium": return "bg-yellow-900/20 hover:bg-yellow-900/30";
            case "low": return "bg-green-900/20 hover:bg-green-900/30";
        }
    }
    switch (level) {
        case "critical": return "bg-red-500/40 hover:bg-red-500/50 ring-2 ring-red-500/30";
        case "high": return "bg-orange-500/40 hover:bg-orange-500/50 ring-2 ring-orange-500/30";
        case "medium": return "bg-yellow-500/40 hover:bg-yellow-500/50 ring-2 ring-yellow-500/30";
        case "low": return "bg-green-500/40 hover:bg-green-500/50 ring-2 ring-green-500/30";
    }
};

export default function RiskHeatMap({ cells, onCellClick, className }: RiskHeatMapProps) {
    const getCellData = (likelihood: LikelihoodLevel, impact: ImpactLevel): RiskHeatMapCell | null => {
        return cells.find((c) => c.likelihood === likelihood && c.impact === impact) || null;
    };

    return (
        <div className={cn("", className)}>
            {/* Header row - Impact labels */}
            <div className="grid grid-cols-6 gap-1 mb-1">
                <div className="text-xs text-white/40 text-center"></div>
                {impactLabels.map((impact) => (
                    <div
                        key={impact.value}
                        className="text-xs text-white/60 text-center font-medium py-2"
                    >
                        {impact.label}
                    </div>
                ))}
            </div>

            {/* Risk matrix grid */}
            <div className="space-y-1">
                {likelihoodLabels.map((likelihood) => (
                    <div key={likelihood.value} className="grid grid-cols-6 gap-1">
                        {/* Row label */}
                        <div className="flex items-center justify-end pr-2">
                            <span className="text-xs text-white/60 font-medium truncate">
                                {likelihood.label}
                            </span>
                        </div>

                        {/* Cells */}
                        {impactLabels.map((impact) => {
                            const cell = getCellData(likelihood.value, impact.value);
                            const riskLevel = getRiskLevel(likelihood.value, impact.value);
                            const count = cell?.count || 0;

                            return (
                                <button
                                    key={`${likelihood.value}-${impact.value}`}
                                    onClick={() => cell && onCellClick?.(cell)}
                                    disabled={count === 0}
                                    className={cn(
                                        "aspect-square rounded-lg flex items-center justify-center transition-all cursor-pointer",
                                        getCellColor(riskLevel, count),
                                        count === 0 && "cursor-default opacity-50"
                                    )}
                                >
                                    {count > 0 && (
                                        <span className="text-sm font-bold text-white">
                                            {count}
                                        </span>
                                    )}
                                </button>
                            );
                        })}
                    </div>
                ))}
            </div>

            {/* Legend */}
            <div className="mt-4 flex items-center justify-center gap-4">
                <div className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded bg-green-500/40" />
                    <span className="text-xs text-white/60">Low</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded bg-yellow-500/40" />
                    <span className="text-xs text-white/60">Medium</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded bg-orange-500/40" />
                    <span className="text-xs text-white/60">High</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded bg-red-500/40" />
                    <span className="text-xs text-white/60">Critical</span>
                </div>
            </div>

            {/* Axis labels */}
            <div className="mt-4 flex justify-between text-xs text-white/40">
                <span>Likelihood (vertical)</span>
                <span>Impact (horizontal)</span>
            </div>
        </div>
    );
}
