"use client";

import { Badge } from "lucide-react";

interface RiskBadgeProps {
    level: string;
    className?: string;
}

export function RiskBadge({ level, className = "" }: RiskBadgeProps) {
    const colors = {
        high: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
        medium: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
        low: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
        unknown: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400",
    };

    const color = colors[level as keyof typeof colors] || colors.unknown;

    return (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${color} ${className}`}>
            {level.toUpperCase()}
        </span>
    );
}

interface ComplianceDomainBadgeProps {
    domain: string;
    className?: string;
}

export function ComplianceDomainBadge({ domain, className = "" }: ComplianceDomainBadgeProps) {
    const colors = {
        aml: "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400",
        cft: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
        sanctions: "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400",
        kyc: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
        cdd: "bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-400",
        payments: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
        crypto: "bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-400",
        gdpr: "bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-400",
        other: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400",
    };

    const color = colors[domain as keyof typeof colors] || colors.other;

    return (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${color} ${className}`}>
            {domain.toUpperCase()}
        </span>
    );
}
