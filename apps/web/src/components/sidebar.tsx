"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { IconButton } from "@/components/ui/button-horizon";
import { Shield, ChevronLeft, ChevronRight } from "lucide-react";
import { NAV_AREAS, isRouteMatch } from "@/components/nav-data";

/**
 * Horizon Sidebar System
 * Collapsible, accessible navigation with canonical IA from nav-data
 */

/* ─────────────────────────────────────────────────────────────────────────────
   Sidebar Component
   ───────────────────────────────────────────────────────────────────────────── */

interface SidebarProps {
  className?: string;
}

export default function Sidebar({ className }: SidebarProps) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = React.useState(false);
  const [expandedAreas, setExpandedAreas] = React.useState<string[]>(() =>
    NAV_AREAS.map((area) => area.id),
  );

  const toggleExpanded = (areaId: string) => {
    setExpandedAreas((prev) =>
      prev.includes(areaId)
        ? prev.filter((id) => id !== areaId)
        : [...prev, areaId],
    );
  };

  const isPathActive = (href: string) => isRouteMatch(pathname, href);
  const isAreaActive = (routePrefixes: string[]) =>
    routePrefixes.some((prefix) => isRouteMatch(pathname, prefix));

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
        {collapsed ? (
          <ul className="space-y-1">
            {NAV_AREAS.map((area) => {
              const active = isAreaActive(area.routePrefixes);
              return (
                <li key={area.id}>
                  <Tooltip content={area.label} side="right">
                    <Link
                      href={area.defaultHref}
                      className={cn(
                        "flex items-center justify-center rounded-lg p-2 transition-colors",
                        active
                          ? "bg-primary/10 text-primary"
                          : "text-foreground-secondary hover:bg-bg-overlay hover:text-foreground",
                      )}
                    >
                      <area.icon className="h-5 w-5" />
                    </Link>
                  </Tooltip>
                </li>
              );
            })}
          </ul>
        ) : (
          <div className="space-y-2">
            {NAV_AREAS.map((area) => {
              const isExpanded = expandedAreas.includes(area.id);
              const areaActive = isAreaActive(area.routePrefixes);

              return (
                <section
                  key={area.id}
                  className="rounded-lg border border-transparent data-[active=true]:bg-primary/5 data-[active=true]:border-primary/20"
                  data-active={areaActive}
                >
                  <button
                    onClick={() => toggleExpanded(area.id)}
                    className={cn(
                      "w-full flex items-center gap-3 rounded-lg px-3 py-2 text-xs font-semibold uppercase tracking-wider transition-colors",
                      areaActive
                        ? "text-primary"
                        : "text-foreground-tertiary hover:text-foreground",
                    )}
                  >
                    <area.icon className="h-4 w-4 shrink-0" />
                    <span className="flex-1 text-left">{area.label}</span>
                    <motion.div
                      animate={{ rotate: isExpanded ? 90 : 0 }}
                      transition={{ duration: 0.15 }}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </motion.div>
                  </button>
                  <AnimatePresence initial={false}>
                    {isExpanded && (
                      <motion.ul
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2, ease: [0, 0, 0.2, 1] }}
                        className="overflow-hidden pb-2"
                      >
                        {area.items.map((item) => {
                          const itemActive = isPathActive(item.href);
                          return (
                            <li key={`${area.id}:${item.href}`}>
                              <Link
                                href={item.href}
                                className={cn(
                                  "mx-2 block rounded-md px-3 py-2 text-sm transition-colors",
                                  itemActive
                                    ? "bg-primary/10 text-primary font-medium"
                                    : "text-foreground-secondary hover:bg-bg-overlay hover:text-foreground",
                                )}
                              >
                                {item.label}
                              </Link>
                            </li>
                          );
                        })}
                      </motion.ul>
                    )}
                  </AnimatePresence>
                </section>
              );
            })}
          </div>
        )}
      </nav>

      <div className="border-t border-border-subtle p-3">
        {/* Collapse Toggle */}
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
