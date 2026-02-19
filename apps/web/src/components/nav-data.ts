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
    description: "Daily overview and KPIs.",
  },
  {
    label: "Analyst Performance",
    href: "/dashboard/operations",
    description: "Team throughput and SLA performance.",
  },
  {
    label: "Findings Triage",
    href: "/findings",
    description: "Triage, acknowledge, escalate.",
  },
  { label: "Cases", href: "/cases", description: "Investigation workspace." },
  {
    label: "Transaction Alerts",
    href: "/transaction-alerts",
    description: "AML transaction alert queue.",
  },
  {
    label: "Entities",
    href: "/entities",
    description: "Unified entity intelligence profiles.",
  },
  {
    label: "Regulatory Alerts",
    href: "/regulatory-alerts",
    description: "Document and regulatory update alerts.",
  },
  {
    label: "SAR Filing",
    href: "/sar/prepare",
    description: "SAR preparation workflow.",
  },
];

/* ─── 2. COMPLIANCE ─────────────────────────────────────────────── */
const COMPLIANCE_ITEMS: NavItem[] = [
  {
    label: "Compliance Command",
    href: "/dashboard?view=compliance",
    description: "AMLCO triage and governance.",
  },
  {
    label: "Obligations",
    href: "/compliance/obligations",
    description: "Regulatory obligations.",
  },
  {
    label: "Policies",
    href: "/compliance/policies",
    description: "Policy library and mapping.",
  },
  {
    label: "Risk Map",
    href: "/compliance/risk-map",
    description: "Risk inventory.",
  },
  {
    label: "KYC / KYB",
    href: "/compliance",
    description: "Onboarding reviews.",
  },
  {
    label: "AML Scope",
    href: "/compliance/aml-scope",
    description: "Scope configuration.",
  },
  {
    label: "Monitoring Rules",
    href: "/transaction-monitoring/rules",
    description: "Rule management.",
  },
  {
    label: "Monitoring Dashboard",
    href: "/dashboard?view=monitoring",
    description: "Live metrics.",
  },
];

/* ─── 3. INTELLIGENCE ───────────────────────────────────────────── */
const INTELLIGENCE_ITEMS: NavItem[] = [
  {
    label: "Global Search",
    href: "/search",
    description: "Documents and entities.",
  },
  {
    label: "AI Officer",
    href: "/aml-officer",
    description: "AI compliance assistant.",
  },
  {
    label: "AI Investigations",
    href: "/aml-officer/investigations",
    description: "AI-powered alert analysis.",
  },
  {
    label: "SAR Management",
    href: "/aml-officer/sar",
    description: "Suspicious Activity Reports.",
  },
  {
    label: "Query Lab",
    href: "/query",
    description: "Natural-language research.",
  },
  {
    label: "Reports",
    href: "/compliance-report",
    description: "Compliance reporting.",
  },
  {
    label: "Network Analysis",
    href: "/network-analysis",
    description: "Graph investigations.",
  },
  { label: "Audit Trail", href: "/audit", description: "Activity log." },
];

/* ─── 4. SETTINGS ───────────────────────────────────────────────── */
const SETTINGS_ITEMS: NavItem[] = [
  {
    label: "Preferences",
    href: "/settings",
    description: "User and system preferences.",
  },
  {
    label: "Model Registry",
    href: "/model-registry",
    description: "Models and versioning.",
  },
  {
    label: "Watchlists",
    href: "/watchlists",
    description: "Watchlist management.",
  },
  {
    label: "Decisioning",
    href: "/decisioning",
    description: "Scoring configuration.",
  },
  {
    label: "Travel Rule",
    href: "/travel-rule",
    description: "Travel rule compliance.",
  },
  {
    label: "On-chain Risk",
    href: "/onchain-risk",
    description: "Crypto exposure analysis.",
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
