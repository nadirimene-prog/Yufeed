import type { LucideIcon } from "lucide-react";
import {
  Activity,
  Scale,
  Search,
  ShieldAlert,
  Settings,
  Sparkles,
} from "lucide-react";

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

const WORK_ITEMS: NavItem[] = [
  {
    label: "Command Center",
    href: "/dashboard",
    description: "Global status and daily entry point.",
  },
  {
    label: "Obligations Review",
    href: "/compliance/obligations",
    description: "Review queue and approvals.",
  },
  {
    label: "Policy Mapping",
    href: "/compliance/policies",
    description: "Map internal policies to obligations.",
  },
  {
    label: "Risk Escalations",
    href: "/compliance/risk-map",
    description: "High priority risks and remediation.",
  },
  {
    label: "KYC/KYB",
    href: "/compliance",
    description: "Case triage and approvals.",
  },
];

const COMPLIANCE_ITEMS: NavItem[] = [
  {
    label: "Overview",
    href: "/compliance/dashboard",
    description: "KPIs and backlog summary.",
  },
  {
    label: "KYC/KYB",
    href: "/compliance",
    description: "Case workflow and reviews.",
  },
  {
    label: "Obligations",
    href: "/compliance/obligations",
    description: "Regulatory obligation list.",
  },
  {
    label: "Policies",
    href: "/compliance/policies",
    description: "Policy library and mapping.",
  },
  {
    label: "Risk Map",
    href: "/compliance/risk-map",
    description: "Risk inventory and remediation.",
  },
  {
    label: "AML Scope",
    href: "/compliance/aml-scope",
    description: "Scope configuration.",
  },
];

const INVESTIGATION_ITEMS: NavItem[] = [
  {
    label: "Alerts",
    href: "/alerts",
    description: "All alerts queue.",
  },
  {
    label: "Cases",
    href: "/cases",
    description: "Investigations workspace.",
  },
  {
    label: "Transaction Alerts",
    href: "/transaction-alerts",
    description: "AML alert queue.",
  },
  {
    label: "SAR Filing",
    href: "/sar/prepare",
    description: "SAR workflow.",
  },
  {
    label: "Network Analysis",
    href: "/network-analysis",
    description: "Graph investigations.",
  },
  {
    label: "Audit Trail",
    href: "/audit",
    description: "Activity log.",
  },
];

const INTELLIGENCE_ITEMS: NavItem[] = [
  {
    label: "Global Search",
    href: "/search",
    description: "Documents and entities.",
  },
  {
    label: "AI Officer",
    href: "/aml-officer",
    description: "AI assistant.",
  },
  {
    label: "Query",
    href: "/query",
    description: "Natural language research.",
  },
  {
    label: "Compliance Reports",
    href: "/compliance-report",
    description: "Reporting views.",
  },
];

const MONITORING_ITEMS: NavItem[] = [
  {
    label: "Monitoring Dashboard",
    href: "/transaction-monitoring/dashboard",
    description: "Live metrics and queues.",
  },
  {
    label: "Monitoring Rules",
    href: "/transaction-monitoring/rules",
    description: "Rule management.",
  },
  {
    label: "Decisioning",
    href: "/decisioning",
    description: "Scoring and decisions.",
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

const ADMIN_ITEMS: NavItem[] = [
  {
    label: "Settings",
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
];

export const NAV_AREAS: NavArea[] = [
  {
    id: "work",
    label: "Work",
    icon: Sparkles,
    defaultHref: "/compliance/obligations",
    routePrefixes: ["/compliance", "/dashboard"],
    items: WORK_ITEMS,
    isManual: true,
  },
  {
    id: "compliance",
    label: "Compliance",
    icon: Scale,
    defaultHref: "/compliance/dashboard",
    routePrefixes: ["/compliance"],
    items: COMPLIANCE_ITEMS,
  },
  {
    id: "investigations",
    label: "Investigations",
    icon: ShieldAlert,
    defaultHref: "/alerts",
    routePrefixes: [
      "/alerts",
      "/cases",
      "/transaction-alerts",
      "/sar",
      "/audit",
      "/network-analysis",
    ],
    items: INVESTIGATION_ITEMS,
  },
  {
    id: "intelligence",
    label: "Intelligence",
    icon: Search,
    defaultHref: "/search",
    routePrefixes: ["/search", "/query", "/aml-officer", "/compliance-report"],
    items: INTELLIGENCE_ITEMS,
  },
  {
    id: "monitoring",
    label: "Monitoring",
    icon: Activity,
    defaultHref: "/transaction-monitoring/dashboard",
    routePrefixes: [
      "/transaction-monitoring",
      "/decisioning",
      "/travel-rule",
      "/onchain-risk",
      "/monitoring",
    ],
    items: MONITORING_ITEMS,
  },
  {
    id: "admin",
    label: "Admin",
    icon: Settings,
    defaultHref: "/settings",
    routePrefixes: ["/settings", "/model-registry", "/watchlists"],
    items: ADMIN_ITEMS,
  },
];

const normalizePath = (pathname: string) => {
  if (!pathname) return "/";
  if (pathname !== "/" && pathname.endsWith("/")) {
    return pathname.slice(0, -1);
  }
  return pathname;
};

export const isRouteMatch = (pathname: string, prefix: string) => {
  const normalized = normalizePath(pathname);
  if (prefix === "/") {
    return normalized === "/";
  }
  return normalized === prefix || normalized.startsWith(`${prefix}/`);
};

export const getAutoAreaForPath = (pathname: string) => {
  const normalized = normalizePath(pathname);
  const autoAreas = NAV_AREAS.filter((area) => !area.isManual);
  for (const area of autoAreas) {
    if (area.routePrefixes.some((prefix) => isRouteMatch(normalized, prefix))) {
      return area;
    }
  }
  return NAV_AREAS.find((area) => area.id === "compliance") || NAV_AREAS[0];
};

export const getAreaById = (areaId: string) =>
  NAV_AREAS.find((area) => area.id === areaId);

export const isPathInAreaItems = (area: NavArea, pathname: string) => {
  const normalized = normalizePath(pathname);
  return area.items.some((item) => isRouteMatch(normalized, item.href));
};
