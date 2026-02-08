"use client";

import { ChevronLeft, ChevronRight, Scale, Activity } from "lucide-react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { Tooltip } from "@/components/ui/tooltip";
import type { NavArea } from "@/components/nav-data";

interface NavRailProps {
  areas: NavArea[];
  activeAreaId: string;
  collapsed: boolean;
  onSelectArea: (areaId: string) => void;
  onToggleCollapse: () => void;
  showStatusOnly?: boolean;
}

export default function NavRail({
  areas,
  activeAreaId,
  collapsed,
  onSelectArea,
  onToggleCollapse,
  showStatusOnly = false,
}: NavRailProps) {
  const router = useRouter();

  return (
    <div className="relative flex h-full w-[72px] flex-col items-center border-r border-sidebar-border bg-sidebar/50">
      <div className="flex h-16 items-center justify-center border-b border-sidebar-border w-full">
        <Tooltip content="YuFeed" side="right">
          <button
            type="button"
            onClick={() => router.push("/dashboard")}
            className="group flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent shadow-lg transition-transform active:scale-95"
            aria-label="YuFeed Home"
          >
            <Scale className="h-5 w-5 text-white" />
          </button>
        </Tooltip>
      </div>

      <nav
        role="navigation"
        aria-label="Primary areas"
        className="flex w-full flex-1 flex-col items-center gap-2 py-4"
      >
        {areas.map((area) => {
          const isActive = area.id === activeAreaId;
          const Icon = area.icon;

          const button = (
            <button
              type="button"
              onClick={() => {
                onSelectArea(area.id);
                router.push(area.defaultHref);
              }}
              aria-current={isActive ? "page" : undefined}
              aria-label={area.label}
              className={cn(
                "flex h-11 w-11 items-center justify-center rounded-xl transition-all duration-200",
                isActive
                  ? "bg-sidebar-primary/10 text-sidebar-primary shadow-[0_0_12px_rgba(109,90,205,0.2)] ring-1 ring-sidebar-primary/20"
                  : "text-sidebar-foreground hover:text-sidebar-primary hover:bg-sidebar-accent/50",
              )}
            >
              <Icon
                className={cn("h-5 w-5", isActive && "text-sidebar-primary")}
              />
            </button>
          );

          return (
            <Tooltip key={area.id} content={area.label} side="right">
              {button}
            </Tooltip>
          );
        })}
      </nav>

      <div className="flex w-full flex-col items-center gap-2 py-3 border-t border-sidebar-border/50">
        {showStatusOnly && (
          <Tooltip content="System status: all operational" side="right">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-risk-low-soft text-risk-low animate-pulse-glow">
              <Activity className="h-5 w-5" />
            </div>
          </Tooltip>
        )}

        <Tooltip
          content={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          side="right"
        >
          <button
            onClick={onToggleCollapse}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className={cn(
              "flex h-10 w-10 items-center justify-center rounded-xl transition-colors",
              "text-sidebar-foreground hover:text-white hover:bg-sidebar-accent",
            )}
          >
            {collapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </button>
        </Tooltip>
      </div>
    </div>
  );
}
