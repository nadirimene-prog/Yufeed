"use client";

import { useRouter } from "next/navigation";
import { Activity } from "lucide-react";
import { cn } from "@/lib/utils";
import type { NavArea } from "@/components/nav-data";
import { isRouteMatch } from "@/components/nav-data";

interface NavContextPanelProps {
  area: NavArea;
  pathname: string;
}

export default function NavContextPanel({
  area,
  pathname,
}: NavContextPanelProps) {
  const router = useRouter();

  return (
    <div className="flex h-full w-[232px] flex-col px-4 py-4">
      <div className="mb-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-sidebar-foreground-muted">
          {area.label}
        </p>
        <div className="mt-2 h-px w-full bg-gradient-to-r from-sidebar-border to-transparent" />
      </div>

      <nav
        role="navigation"
        aria-label={`${area.label} navigation`}
        className="flex-1 space-y-1 overflow-y-auto pr-1"
      >
        {area.items.map((item) => {
          const isActive = isRouteMatch(pathname, item.href);
          const isWorkArea = area.id === "work";
          return (
            <button
              key={item.href}
              type="button"
              onClick={() => router.push(item.href)}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "group flex flex-col gap-1 rounded-lg px-3 py-2 text-sm transition-all duration-200",
                isActive
                  ? "bg-sidebar-accent text-sidebar-foreground shadow-sm"
                  : "text-sidebar-foreground-muted hover:text-sidebar-foreground hover:bg-sidebar-accent/50",
                isWorkArea && "border-l-2 border-transparent",
                isWorkArea &&
                  isActive &&
                  "border-l-sidebar-primary bg-sidebar-primary/5",
                isWorkArea && !isActive && "hover:border-sidebar-primary/30",
              )}
            >
              <span
                className={cn(
                  "font-medium",
                  isActive && "text-sidebar-primary",
                  isWorkArea && isActive && "text-sidebar-primary",
                )}
              >
                {item.label}
              </span>
              {item.description && (
                <span
                  className={cn(
                    "text-[10px] transition-colors",
                    isActive
                      ? "text-sidebar-foreground/70"
                      : "text-sidebar-foreground-muted/70",
                  )}
                >
                  {item.description}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="mt-4 border-t border-sidebar-border pt-4">
        <div className="flex items-center gap-3 rounded-lg bg-sidebar-accent/50 px-3 py-2 border border-sidebar-border/50">
          <div className="relative">
            <Activity className="h-4 w-4 text-risk-low" />
            <span className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-risk-low animate-pulse" />
          </div>
          <div className="min-w-0">
            <p className="text-[11px] font-medium text-sidebar-foreground">
              System Status
            </p>
            <p className="text-[10px] text-risk-low font-mono">
              All systems operational
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
