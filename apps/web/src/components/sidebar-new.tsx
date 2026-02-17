"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { IconButton } from "@/components/ui/button-horizon";
import { CountBadge } from "@/components/ui/badge-horizon";
import {
  LayoutDashboard,
  FileText,
  Shield,
  Gavel,
  Search,
  Settings,
  ChevronLeft,
  ChevronRight,
  Bell,
  HelpCircle,
  type LucideIcon,
} from "lucide-react";

/**
 * Horizon Sidebar System
 * Collapsible, accessible navigation with modern aesthetics
 */

/* ─────────────────────────────────────────────────────────────────────────────
   Navigation Items Configuration
   ───────────────────────────────────────────────────────────────────────────── */

interface NavItem {
  id: string;
  label: string;
  href: string;
  icon: LucideIcon;
  badge?: number;
  badgeVariant?: "default" | "critical";
  children?: NavItem[];
}

const mainNavItems: NavItem[] = [
  {
    id: "dashboard",
    label: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
  },
  {
    id: "compliance",
    label: "Compliance",
    href: "/compliance",
    icon: Shield,
    badge: 3,
    badgeVariant: "critical",
    children: [
      {
        id: "obligations",
        label: "Obligations",
        href: "/compliance/obligations",
        icon: FileText,
      },
      {
        id: "policies",
        label: "Policies",
        href: "/compliance/policies",
        icon: FileText,
      },
      {
        id: "deadlines",
        label: "Deadlines",
        href: "/compliance/deadlines",
        icon: FileText,
      },
    ],
  },
  {
    id: "aml",
    label: "AML Officer",
    href: "/aml-officer",
    icon: Gavel,
    children: [
      {
        id: "investigations",
        label: "Investigations",
        href: "/aml-officer/investigations",
        icon: FileText,
      },
      { id: "alerts", label: "Alerts", href: "/aml-officer", icon: FileText },
      { id: "sar", label: "SAR", href: "/aml-officer/sar", icon: FileText },
    ],
  },
  {
    id: "cases",
    label: "Cases",
    href: "/cases",
    icon: FileText,
    badge: 12,
  },
  {
    id: "search",
    label: "Search",
    href: "/search",
    icon: Search,
  },
];

const bottomNavItems: NavItem[] = [
  {
    id: "notifications",
    label: "Notifications",
    href: "#",
    icon: Bell,
    badge: 5,
  },
  { id: "help", label: "Help & Support", href: "#", icon: HelpCircle },
  { id: "settings", label: "Settings", href: "/settings", icon: Settings },
];

/* ─────────────────────────────────────────────────────────────────────────────
   Sidebar Component
   ───────────────────────────────────────────────────────────────────────────── */

interface SidebarProps {
  className?: string;
}

export default function Sidebar({ className }: SidebarProps) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = React.useState(false);
  const [expandedItems, setExpandedItems] = React.useState<string[]>([
    "compliance",
  ]);

  const toggleExpanded = (itemId: string) => {
    setExpandedItems((prev) =>
      prev.includes(itemId)
        ? prev.filter((id) => id !== itemId)
        : [...prev, itemId],
    );
  };

  const isActive = (href: string) => {
    if (href === "/") return pathname === href;
    return pathname === href || pathname.startsWith(`${href}/`);
  };

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? 72 : 256 }}
      transition={{ type: "spring", stiffness: 400, damping: 30 }}
      className={cn(
        "fixed left-0 top-0 z-40 flex h-screen flex-col border-r border-border-subtle bg-bg-elevated",
        className,
      )}
    >
      {/* Logo Section */}
      <div className="flex h-14 items-center gap-3 border-b border-border-subtle px-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-white shrink-0">
          <Shield className="h-4 w-4" />
        </div>
        <AnimatePresence mode="popLayout">
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              transition={{ duration: 0.15 }}
              className="flex flex-col"
            >
              <span className="font-display font-semibold text-sm text-foreground">
                YuFeed
              </span>
              <span className="text-[10px] text-foreground-tertiary uppercase tracking-wider">
                Sentinel
              </span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-3">
        <ul className="space-y-1">
          {mainNavItems.map((item) => {
            const active = isActive(item.href);
            const hasChildren = item.children && item.children.length > 0;
            const isExpanded = expandedItems.includes(item.id);

            return (
              <li key={item.id}>
                {hasChildren && !collapsed ? (
                  <>
                    <button
                      onClick={() => toggleExpanded(item.id)}
                      className={cn(
                        "w-full flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                        active
                          ? "bg-primary/10 text-primary"
                          : "text-foreground-secondary hover:bg-bg-overlay hover:text-foreground",
                      )}
                    >
                      <item.icon className="h-4 w-4 shrink-0" />
                      <span className="flex-1 text-left">{item.label}</span>
                      {item.badge && (
                        <CountBadge
                          count={item.badge}
                          variant={item.badgeVariant}
                        />
                      )}
                      <motion.div
                        animate={{ rotate: isExpanded ? 90 : 0 }}
                        transition={{ duration: 0.15 }}
                      >
                        <ChevronRight className="h-4 w-4 text-foreground-tertiary" />
                      </motion.div>
                    </button>
                    <AnimatePresence>
                      {isExpanded && (
                        <motion.ul
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.2, ease: [0, 0, 0.2, 1] }}
                          className="overflow-hidden"
                        >
                          {item.children?.map((child) => {
                            const childActive = isActive(child.href);
                            return (
                              <li key={child.id}>
                                <Link
                                  href={child.href}
                                  className={cn(
                                    "flex items-center gap-3 rounded-lg py-2 pl-10 pr-3 text-sm transition-colors",
                                    childActive
                                      ? "text-primary font-medium"
                                      : "text-foreground-tertiary hover:text-foreground",
                                  )}
                                >
                                  {child.label}
                                </Link>
                              </li>
                            );
                          })}
                        </motion.ul>
                      )}
                    </AnimatePresence>
                  </>
                ) : collapsed ? (
                  <Tooltip content={item.label} side="right">
                    <Link
                      href={item.href}
                      className={cn(
                        "flex items-center justify-center rounded-lg p-2 transition-colors",
                        active
                          ? "bg-primary/10 text-primary"
                          : "text-foreground-secondary hover:bg-bg-overlay hover:text-foreground",
                      )}
                    >
                      <item.icon className="h-5 w-5" />
                      {item.badge && item.badge > 0 && (
                        <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-critical-500" />
                      )}
                    </Link>
                  </Tooltip>
                ) : (
                  <Link
                    href={item.href}
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                      active
                        ? "bg-primary/10 text-primary"
                        : "text-foreground-secondary hover:bg-bg-overlay hover:text-foreground",
                    )}
                  >
                    <item.icon className="h-4 w-4 shrink-0" />
                    <span className="flex-1">{item.label}</span>
                    {item.badge && (
                      <CountBadge
                        count={item.badge}
                        variant={item.badgeVariant}
                      />
                    )}
                  </Link>
                )}
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Bottom Navigation */}
      <div className="border-t border-border-subtle p-3">
        <ul className="space-y-1">
          {bottomNavItems.map((item) => {
            const active = isActive(item.href);
            return collapsed ? (
              <li key={item.id}>
                <Tooltip content={item.label} side="right">
                  <Link
                    href={item.href}
                    className={cn(
                      "flex items-center justify-center rounded-lg p-2 transition-colors",
                      active
                        ? "bg-primary/10 text-primary"
                        : "text-foreground-secondary hover:bg-bg-overlay hover:text-foreground",
                    )}
                  >
                    <item.icon className="h-5 w-5" />
                    {item.badge && item.badge > 0 && (
                      <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-critical-500" />
                    )}
                  </Link>
                </Tooltip>
              </li>
            ) : (
              <li key={item.id}>
                <Link
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-primary/10 text-primary"
                      : "text-foreground-secondary hover:bg-bg-overlay hover:text-foreground",
                  )}
                >
                  <item.icon className="h-4 w-4 shrink-0" />
                  <span className="flex-1">{item.label}</span>
                  {item.badge && <CountBadge count={item.badge} />}
                </Link>
              </li>
            );
          })}
        </ul>

        {/* Collapse Toggle */}
        <div className="mt-3 pt-3 border-t border-border-subtle">
          <IconButton
            variant="ghost"
            size="md"
            icon={
              collapsed ? (
                <ChevronRight className="h-4 w-4" />
              ) : (
                <ChevronLeft className="h-4 w-4" />
              )
            }
            label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            onClick={() => setCollapsed(!collapsed)}
            className={cn("w-full", collapsed && "justify-center")}
          />
        </div>
      </div>
    </motion.aside>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Tooltip Component (Simple implementation)
   ───────────────────────────────────────────────────────────────────────────── */

interface TooltipProps {
  children: React.ReactNode;
  content: string;
  side?: "top" | "bottom" | "left" | "right";
}

function Tooltip({ children, content, side = "top" }: TooltipProps) {
  const [isVisible, setIsVisible] = React.useState(false);

  const positionClasses = {
    top: "bottom-full left-1/2 -translate-x-1/2 mb-2",
    bottom: "top-full left-1/2 -translate-x-1/2 mt-2",
    left: "right-full top-1/2 -translate-y-1/2 mr-2",
    right: "left-full top-1/2 -translate-y-1/2 ml-2",
  }[side];

  return (
    <div
      className="relative flex"
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
      onFocus={() => setIsVisible(true)}
      onBlur={() => setIsVisible(false)}
    >
      {children}
      <AnimatePresence>
        {isVisible && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.1 }}
            className={cn(
              "absolute z-50 px-2 py-1 rounded-md bg-bg-floating text-foreground text-xs font-medium whitespace-nowrap shadow-lg border border-border-subtle pointer-events-none",
              positionClasses,
            )}
          >
            {content}
            <div
              className={cn(
                "absolute w-2 h-2 bg-bg-floating border-border-subtle rotate-45",
                side === "top" &&
                  "bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2 border-b border-r",
                side === "bottom" &&
                  "top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 border-t border-l",
                side === "left" &&
                  "right-0 top-1/2 -translate-y-1/2 translate-x-1/2 border-t border-r",
                side === "right" &&
                  "left-0 top-1/2 -translate-y-1/2 -translate-x-1/2 border-b border-l",
              )}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
