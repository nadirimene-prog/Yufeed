import type { LucideIcon } from "lucide-react";
import { LayoutDashboard, ShieldAlert, Search, Settings } from "lucide-react";

export type NavItem = {
  label: string;
  href: string;
  description?: string;
};

export type NavArea = {
  id: string;
  label: string;
  icon: LucideIcon;
  defaultHref: string;
  routePrefixes: string[];
  items: NavItem[];
  isManual?: boolean;
};

/* ─── 1. OPERATIONS ─────────────────────────────────────────────── */
const OPERATIONS_ITEMS: NavItem[] = [
  {
    label: "Command Center",
    href: "/dashboard",
    description: "Real-time overview of alerts, cases, and key risk metrics.",
  },
  {
    label: "Analyst Performance",
    href: "/dashboard/operations",
    description:
      "Track team throughput, SLA compliance, and workload distribution.",
  },
  {
    label: "Findings Triage",
    href: "/findings",
    description: "Review, prioritize, and escalate compliance findings.",
  },
  {
    label: "Cases",
    href: "/cases",
    description: "Manage investigations from intake through resolution.",
  },
  {
    label: "Transaction Alerts",
    href: "/transaction-alerts",
    description: "Monitor and triage AML transaction alerts by risk level.",
  },
  {
    label: "Entities",
    href: "/entities",
    description:
      "View consolidated profiles with risk context and activity history.",
  },
  {
    label: "Regulatory Alerts",
    href: "/regulatory-alerts",
    description:
      "Stay current on regulatory changes that affect your obligations.",
  },
  {
    label: "SAR Filing",
    href: "/sar/prepare",
    description: "Draft, review, and submit Suspicious Activity Reports.",
  },
];

/* ─── 2. COMPLIANCE ─────────────────────────────────────────────── */
const COMPLIANCE_ITEMS: NavItem[] = [
  {
    label: "Compliance Command",
    href: "/dashboard?view=compliance",
    description:
      "Central hub for AMLCO triage, governance actions, and oversight.",
  },
  {
    label: "Obligations",
    href: "/compliance/obligations",
    description:
      "Track regulatory obligations and their implementation status.",
  },
  {
    label: "Policies",
    href: "/compliance/policies",
    description: "Maintain and version your internal policy library.",
  },
  {
    label: "Risk Map",
    href: "/compliance/risk-map",
    description: "Visualize and assess your organization's risk landscape.",
  },
  {
    label: "KYC / KYB",
    href: "/compliance",
    description: "Review and approve customer onboarding applications.",
  },
  {
    label: "AML Scope",
    href: "/compliance/aml-scope",
    description:
      "Define which entities and activities fall under AML monitoring.",
  },
  {
    label: "Monitoring Rules",
    href: "/transaction-monitoring/rules",
    description: "Configure and manage transaction monitoring rule sets.",
  },
  {
    label: "Monitoring Dashboard",
    href: "/dashboard?view=monitoring",
    description: "Live view of monitoring rule performance and alert volumes.",
  },
];

/* ─── 3. INTELLIGENCE ───────────────────────────────────────────── */
const INTELLIGENCE_ITEMS: NavItem[] = [
  {
    label: "Global Search",
    href: "/search",
    description: "Search across regulations, entities, and internal documents.",
  },
  {
    label: "AI Officer",
    href: "/aml-officer",
    description: "AI-assisted compliance briefings and proactive risk alerts.",
  },
  {
    label: "AI Investigations",
    href: "/aml-officer/investigations",
    description:
      "Automated alert analysis with risk scoring and recommendations.",
  },
  {
    label: "SAR Management",
    href: "/aml-officer/sar",
    description: "Track SAR lifecycle from draft through submission.",
  },
  {
    label: "Query Lab",
    href: "/query",
    description:
      "Ask regulatory questions in plain language, backed by source citations.",
  },
  {
    label: "Reports",
    href: "/compliance-report",
    description: "Generate and export compliance reports for stakeholders.",
  },
  {
    label: "Network Analysis",
    href: "/network-analysis",
    description:
      "Explore entity relationships and transaction patterns visually.",
  },
  {
    label: "Audit Trail",
    href: "/audit",
    description: "Full history of actions, decisions, and system events.",
  },
];

/* ─── 4. SETTINGS ───────────────────────────────────────────────── */
const SETTINGS_ITEMS: NavItem[] = [
  {
    label: "Preferences",
    href: "/settings",
    description: "Manage your profile, notifications, and workspace settings.",
  },
  {
    label: "Model Registry",
    href: "/model-registry",
    description: "View and manage AI model versions and deployments.",
  },
  {
    label: "Watchlists",
    href: "/watchlists",
    description: "Set up automated monitoring feeds and alert subscriptions.",
  },
  {
    label: "Decisioning",
    href: "/decisioning",
    description: "Configure risk scoring thresholds and decision logic.",
  },
  {
    label: "Travel Rule",
    href: "/travel-rule",
    description:
      "Manage travel rule data exchange for virtual asset transfers.",
  },
  {
    label: "On-chain Risk",
    href: "/onchain-risk",
    description:
      "Assess wallet risk exposure using on-chain intelligence providers.",
  },
];

export const NAV_AREAS: NavArea[] = [
  {
    id: "operations",
    label: "Operations",
    icon: LayoutDashboard,
    defaultHref: "/dashboard",
    routePrefixes: [
      "/dashboard",
      "/findings",
      "/cases",
      "/entities",
      "/alerts",
      "/regulatory-alerts",
      "/transaction-alerts",
      "/sar",
    ],
    items: OPERATIONS_ITEMS,
  },
  {
    id: "compliance",
    label: "Compliance",
    icon: ShieldAlert,
    defaultHref: "/compliance/obligations",
    routePrefixes: ["/compliance", "/transaction-monitoring"],
    items: COMPLIANCE_ITEMS,
  },
  {
    id: "intelligence",
    label: "Intelligence",
    icon: Search,
    defaultHref: "/search",
    routePrefixes: [
      "/search",
      "/query",
      "/aml-officer",
      "/aml-officer/investigations",
      "/aml-officer/sar",
      "/compliance-report",
      "/network-analysis",
      "/audit",
    ],
    items: INTELLIGENCE_ITEMS,
  },
  {
    id: "settings",
    label: "Settings",
    icon: Settings,
    defaultHref: "/settings",
    routePrefixes: [
      "/settings",
      "/model-registry",
      "/watchlists",
      "/decisioning",
      "/travel-rule",
      "/onchain-risk",
    ],
    items: SETTINGS_ITEMS,
  },
];

const normalizePath = (pathname: string) => {
  if (!pathname) return "/";
  const basePath = pathname.split("?")[0] || "/";
  if (basePath !== "/" && basePath.endsWith("/")) {
    return basePath.slice(0, -1);
  }
  return basePath;
};

export const isRouteMatch = (pathname: string, prefix: string) => {
  const normalized = normalizePath(pathname);
  const normalizedPrefix = normalizePath(prefix);
  if (normalizedPrefix === "/") {
    return normalized === "/";
  }
  return (
    normalized === normalizedPrefix ||
    normalized.startsWith(`${normalizedPrefix}/`)
  );
};

export const getAutoAreaForPath = (pathname: string) => {
  const normalized = normalizePath(pathname);
  const autoAreas = NAV_AREAS.filter((area) => !area.isManual);
  for (const area of autoAreas) {
    if (area.routePrefixes.some((prefix) => isRouteMatch(normalized, prefix))) {
      return area;
    }
  }
  return NAV_AREAS.find((area) => area.id === "operations") || NAV_AREAS[0];
};

export const getAreaById = (areaId: string) =>
  NAV_AREAS.find((area) => area.id === areaId);

export const isPathInAreaItems = (area: NavArea, pathname: string) => {
  const normalized = normalizePath(pathname);
  return area.items.some((item) => isRouteMatch(normalized, item.href));
};
