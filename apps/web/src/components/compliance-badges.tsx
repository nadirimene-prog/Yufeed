"use client";

/**
 * Compliance Badges
 *
 * This file provides compliance-specific badge components.
 * RiskBadge is re-exported from ui/risk-badge for consistency.
 */

// Re-export RiskBadge from the consolidated UI component
export {
  RiskBadge,
  RiskScoreBadge,
  type RiskLevel,
  type BadgeSize,
} from "@/components/ui/risk-badge";

interface ComplianceDomainBadgeProps {
  domain: string;
  className?: string;
}

/**
 * Badge for displaying compliance domains (AML, KYC, GDPR, etc.)
 */
export function ComplianceDomainBadge({
  domain,
  className = "",
}: ComplianceDomainBadgeProps) {
  const colors = {
    aml: "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400",
    cft: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
    sanctions:
      "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400",
    kyc: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
    cdd: "bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-400",
    payments:
      "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
    crypto:
      "bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-400",
    gdpr: "bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-400",
    other: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400",
  };

  const color =
    colors[domain.toLowerCase() as keyof typeof colors] || colors.other;

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${color} ${className}`}
    >
      {domain.toUpperCase()}
    </span>
  );
}
