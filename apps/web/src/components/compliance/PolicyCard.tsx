"use client";

import React from "react";
import { cn } from "@/lib/utils";
import {
    FileText,
    User,
    Calendar,
    ExternalLink,
    Link as LinkIcon,
    ChevronRight,
    Check,
    Clock,
    FileEdit,
} from "lucide-react";
import type { Policy, PolicyStatus } from "@/types/compliance";

interface PolicyCardProps {
    policy: Policy;
    onClick?: () => void;
    onViewExternal?: () => void;
    className?: string;
    compact?: boolean;
}

const getStatusColor = (status: PolicyStatus): string => {
    switch (status) {
        case "active": return "bg-green-500/20 text-green-400 border-green-500/30";
        case "approved": return "bg-blue-500/20 text-blue-400 border-blue-500/30";
        case "in_review": return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30";
        case "draft": return "bg-gray-500/20 text-gray-400 border-gray-500/30";
        case "retired": return "bg-red-500/20 text-red-400 border-red-500/30";
    }
};

const getStatusIcon = (status: PolicyStatus) => {
    switch (status) {
        case "active": return <Check className="h-3.5 w-3.5" />;
        case "approved": return <Check className="h-3.5 w-3.5" />;
        case "in_review": return <Clock className="h-3.5 w-3.5" />;
        case "draft": return <FileEdit className="h-3.5 w-3.5" />;
        case "retired": return <FileText className="h-3.5 w-3.5" />;
    }
};

export default function PolicyCard({
    policy,
    onClick,
    onViewExternal,
    className,
    compact = false,
}: PolicyCardProps) {
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
                <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-[#6d5acd]/20">
                    <FileText className="h-4 w-4 text-[#6d5acd]" />
                </div>
                <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{policy.name}</p>
                    <p className="text-xs text-white/50">{policy.policy_id}</p>
                </div>
                <span className={cn(
                    "text-xs px-2 py-0.5 rounded-full border flex items-center gap-1",
                    getStatusColor(policy.status)
                )}>
                    {getStatusIcon(policy.status)}
                    {policy.status}
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
                    <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-[#6d5acd]/20">
                        <FileText className="h-5 w-5 text-[#6d5acd]" />
                    </div>
                    <div>
                        <h3 className="font-medium text-white">{policy.name}</h3>
                        <p className="text-xs text-white/50">{policy.policy_id}</p>
                    </div>
                </div>
                <span className={cn(
                    "text-xs px-2 py-1 rounded-full border flex items-center gap-1 font-medium",
                    getStatusColor(policy.status)
                )}>
                    {getStatusIcon(policy.status)}
                    {policy.status}
                </span>
            </div>

            {/* Version and Language */}
            <div className="flex items-center gap-4 mb-4 text-xs text-white/60">
                {policy.version && (
                    <span className="bg-white/10 px-2 py-0.5 rounded">
                        v{policy.version}
                    </span>
                )}
                <span className="uppercase">{policy.language}</span>
            </div>

            {/* Metadata */}
            <div className="grid grid-cols-2 gap-3 mb-4">
                {policy.owner && (
                    <div className="flex items-center gap-2 text-sm text-white/70">
                        <User className="h-4 w-4 text-white/40" />
                        <span className="truncate">{policy.owner}</span>
                    </div>
                )}
                {policy.effective_date && (
                    <div className="flex items-center gap-2 text-sm text-white/70">
                        <Calendar className="h-4 w-4 text-white/40" />
                        <span>{new Date(policy.effective_date).toLocaleDateString()}</span>
                    </div>
                )}
            </div>

            {/* Stats */}
            <div className="flex items-center gap-4 text-xs text-white/50 mb-4">
                {policy.sections_count !== undefined && (
                    <div className="flex items-center gap-1">
                        <FileText className="h-3.5 w-3.5" />
                        <span>{policy.sections_count} sections</span>
                    </div>
                )}
                {policy.linked_obligations_count !== undefined && policy.linked_obligations_count > 0 && (
                    <div className="flex items-center gap-1">
                        <LinkIcon className="h-3.5 w-3.5" />
                        <span>{policy.linked_obligations_count} obligations</span>
                    </div>
                )}
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 pt-4 border-t border-white/10">
                {onClick && (
                    <button
                        onClick={onClick}
                        className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-white/70 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
                    >
                        View Details
                        <ChevronRight className="h-4 w-4" />
                    </button>
                )}
                {policy.source_url && (
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            if (onViewExternal) {
                                onViewExternal();
                            } else {
                                window.open(policy.source_url, "_blank");
                            }
                        }}
                        className="flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-[#00d4ff] rounded-lg bg-[#00d4ff]/10 hover:bg-[#00d4ff]/20 transition-colors"
                    >
                        <ExternalLink className="h-4 w-4" />
                        External
                    </button>
                )}
            </div>
        </div>
    );
}
