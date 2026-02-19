"use client";

import { AnimatePresence, motion } from "framer-motion";
import { type ReactNode, useId } from "react";
import { cn } from "@/lib/utils";

export interface WorkspaceTab {
  id: string;
  label: string;
  content: ReactNode;
}

interface WorkspaceTabsProps {
  tabs: WorkspaceTab[];
  activeTab: string;
  onTabChange: (tab: string) => void;
  className?: string;
}

export function WorkspaceTabs({
  tabs,
  activeTab,
  onTabChange,
  className,
}: WorkspaceTabsProps) {
  const tabsId = useId();
  const currentTab = tabs.find((tab) => tab.id === activeTab) ?? tabs[0];
  const currentPanelId = `workspace-tabpanel-${tabsId}-${currentTab.id}`;

  return (
    <div className={cn("flex min-h-0 flex-1 flex-col", className)}>
      <div
        className="mb-3 flex flex-wrap items-center gap-2"
        role="tablist"
        aria-label="Investigation workspace sections"
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            id={`workspace-tab-${tabsId}-${tab.id}`}
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls={`workspace-tabpanel-${tabsId}-${tab.id}`}
            onClick={() => onTabChange(tab.id)}
            className={cn(
              "rounded-lg px-3 py-1.5 text-xs font-semibold uppercase tracking-wide transition",
              activeTab === tab.id
                ? "bg-primary/20 text-primary"
                : "bg-white/5 text-white/60 hover:bg-white/10 hover:text-white",
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="min-h-0 flex-1 overflow-auto">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={currentTab.id}
            id={currentPanelId}
            role="tabpanel"
            aria-labelledby={`workspace-tab-${tabsId}-${currentTab.id}`}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.18 }}
            className="h-full"
          >
            {currentTab.content}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}

export default WorkspaceTabs;
