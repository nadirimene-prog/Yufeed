"use client";

import { AnimatePresence, motion } from "framer-motion";
import { type ReactNode, useId } from "react";
import { cn } from "@/lib/utils";

export interface WorkspaceTab {
  id: string;
  label: string;
  content: ReactNode;
}

const PREFERRED_TAB_ORDER = [
  "overview",
  "actions",
  "timeline",
  "evidence",
  "ai",
  "comments",
] as const;

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
  const preferredIndex = (tabId: string) => {
    const index = PREFERRED_TAB_ORDER.findIndex((value) => value === tabId);
    return index === -1 ? Number.MAX_SAFE_INTEGER : index;
  };
  const orderedTabs = [...tabs].sort((a, b) => {
    return preferredIndex(a.id) - preferredIndex(b.id);
  });
  const currentTab =
    orderedTabs.find((tab) => tab.id === activeTab) ?? orderedTabs[0];
  const currentPanelId = `workspace-tabpanel-${tabsId}-${currentTab.id}`;

  return (
    <div className={cn("flex min-h-0 flex-1 flex-col", className)}>
      <div
        className="mb-3 flex flex-wrap items-center gap-2"
        role="tablist"
        aria-label="Investigation workspace sections"
      >
        {orderedTabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            id={`workspace-tab-${tabsId}-${tab.id}`}
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls={`workspace-tabpanel-${tabsId}-${tab.id}`}
            tabIndex={activeTab === tab.id ? 0 : -1}
            onClick={() => onTabChange(tab.id)}
            className={cn(
              "rounded-lg border px-3 py-1.5 text-xs font-semibold uppercase tracking-wide transition",
              activeTab === tab.id
                ? "border-primary/30 bg-primary/10 text-primary"
                : "border-border bg-slate-50 text-muted-foreground hover:bg-slate-100 hover:text-foreground",
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
