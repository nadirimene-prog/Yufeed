"use client";

import React from "react";
import { cn } from "@/lib/utils";
import {
    AlertTriangle,
    Shield,
    User,
    Calendar,
    Link as LinkIcon,
    ChevronRight,
} from "lucide-react";
import type { RiskEntry, RiskLevelType, MitigationStatus } from "@/types/compliance";

interface RiskEntryCardProps {
    risk: RiskEntry;
    onClick?: () => void;
    onLinkObligations?: () => void;
    className?: string;
    compact?: boolean;
}

const getRiskLevelColor = (level: RiskLevelType): string => {
    switch (level) {
        case "critical": return "bg-red-500/20 text-red-400 border-red-500/30";
        case "high": return "bg-orange-500/20 text-orange-400 border-orange-500/30";
        case "medium": return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30";
        case "low": return "bg-green-500/20 text-green-400 border-green-500/30";
    }
};

const getMitigationStatusColor = (status: MitigationStatus): string => {
    switch (status) {
        case "monitored": return "bg-blue-500/20 text-blue-400";
        case "implemented": return "bg-green-500/20 text-green-400";
        case "in_progress": return "bg-yellow-500/20 text-yellow-400";
        case "not_started": return "bg-gray-500/20 text-gray-400";
    }
};

const getMitigationStatusLabel = (status: MitigationStatus): string => {
    switch (status) {
        case "monitored": return "Monitored";
        case "implemented": return "Implemented";
        case "in_progress": return "In Progress";
        case "not_started": return "Not Started";
    }
};

export default function RiskEntryCard({
    risk,
    onClick,
    onLinkObligations,
    className,
    compact = false,
}: RiskEntryCardProps) {
    if (compact) {
        return (
            <div
                onClick={onClick}
                className={cn(
                    "flex items-center gap-3 p-3 rounded-lg bg-white/5 border border-white/10 transition-all",
                    onClick && "cursor-pointer hover:bg-white/10",
                    className
                )}
            >
                <div className={cn(
                    "flex items-center justify-center w-8 h-8 rounded-lg",
                    getRiskLevelColor(risk.inherent_risk_level)
                )}>
                    <AlertTriangle className="h-4 w-4" />
                </div>
                <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{risk.name}</p>
                    <p className="text-xs text-white/50">{risk.category_name}</p>
                </div>
                <span className={cn(
                    "text-xs px-2 py-0.5 rounded-full",
                    getRiskLevelColor(risk.inherent_risk_level)
                )}>
                    {risk.inherent_risk_level}
                </span>
                {onClick && <ChevronRight className="h-4 w-4 text-white/30" />}
            </div>
        );
    }

    return (
        <div
            className={cn(
                "p-4 rounded-xl bg-white/5 border border-white/10 transition-all hover:bg-white/[0.07]",
                className
            )}
        >
            {/* Header */}
            <div className="flex items-start justify-between gap-3 mb-3">
                <div className="flex items-center gap-3">
                    <div className={cn(
                        "flex items-center justify-center w-10 h-10 rounded-lg",
                        getRiskLevelColor(risk.inherent_risk_level)
                    )}>
                        <AlertTriangle className="h-5 w-5" />
                    </div>
                    <div>
                        <h3 className="font-medium text-white">{risk.name}</h3>
                        <p className="text-xs text-white/50">{risk.risk_id}</p>
                    </div>
                </div>
                <span className={cn(
                    "text-xs px-2 py-1 rounded-full font-medium",
                    getMitigationStatusColor(risk.mitigation_status)
                )}>
                    {getMitigationStatusLabel(risk.mitigation_status)}
                </span>
            </div>

            {/* Description */}
            {risk.description && (
                <p className="text-sm text-white/70 mb-4 line-clamp-2">
                    {risk.description}
                </p>
            )}

            {/* Risk Levels */}
            <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="p-2 rounded-lg bg-white/5">
                    <p className="text-xs text-white/50 mb-1">Inherent Risk</p>
                    <div className="flex items-center gap-2">
                        <span className={cn(
                            "text-xs px-2 py-0.5 rounded border",
                            getRiskLevelColor(risk.inherent_risk_level)
                        )}>
                            {risk.inherent_risk_level.toUpperCase()}
                        </span>
                    </div>
                </div>
                <div className="p-2 rounded-lg bg-white/5">
                    <p className="text-xs text-white/50 mb-1">Residual Risk</p>
                    <div className="flex items-center gap-2">
                        <span className={cn(
                            "text-xs px-2 py-0.5 rounded border",
                            getRiskLevelColor(risk.residual_risk_level)
                        )}>
                            {risk.residual_risk_level.toUpperCase()}
                        </span>
                    </div>
                </div>
            </div>

            {/* Metadata */}
            <div className="flex flex-wrap items-center gap-3 text-xs text-white/50">
                {risk.category_name && (
                    <div className="flex items-center gap-1">
                        <Shield className="h-3.5 w-3.5" />
                        <span>{risk.category_name}</span>
                    </div>
                )}
                {risk.control_owner && (
                    <div className="flex items-center gap-1">
                        <User className="h-3.5 w-3.5" />
                        <span>{risk.control_owner}</span>
                    </div>
                )}
                {risk.review_date && (
                    <div className="flex items-center gap-1">
                        <Calendar className="h-3.5 w-3.5" />
                        <span>{new Date(risk.review_date).toLocaleDateString()}</span>
                    </div>
                )}
                {risk.linked_obligations_count !== undefined && risk.linked_obligations_count > 0 && (
                    <div className="flex items-center gap-1">
                        <LinkIcon className="h-3.5 w-3.5" />
                        <span>{risk.linked_obligations_count} linked</span>
                    </div>
                )}
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 mt-4 pt-4 border-t border-white/10">
                {onClick && (
                    <button
                        onClick={onClick}
                        className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-white/70 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
                    >
                        View Details
                        <ChevronRight className="h-4 w-4" />
                    </button>
                )}
                {onLinkObligations && (
                    <button
                        onClick={onLinkObligations}
                        className="flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-[#6d5acd] rounded-lg bg-[#6d5acd]/10 hover:bg-[#6d5acd]/20 transition-colors"
                    >
                        <LinkIcon className="h-4 w-4" />
                        Link Obligations
                    </button>
                )}
            </div>
        </div>
    );
}
