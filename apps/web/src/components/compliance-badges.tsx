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
    aml: "bg-blue-100 text-blue-800  ",
    cft: "bg-red-100 text-red-800  ",
    sanctions: "bg-orange-100 text-orange-800  ",
    kyc: "bg-blue-100 text-blue-800  ",
    cdd: "bg-cyan-100 text-cyan-800  ",
    payments: "bg-green-100 text-green-800  ",
    crypto: "bg-indigo-100 text-indigo-800  ",
    gdpr: "bg-pink-100 text-pink-800  ",
    other: "bg-slate-100 text-slate-800  ",
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
