"use client";

import * as React from "react";
import { cva } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";

/**
 * Horizon Tabs System
 * Accessible, animated tabs with multiple variants
 */

/* ─────────────────────────────────────────────────────────────────────────────
   Tabs Context
   ───────────────────────────────────────────────────────────────────────────── */

interface TabsContextValue {
  selectedTab: string;
  setSelectedTab: (id: string) => void;
  variant: TabsProps["variant"];
  size: TabsProps["size"];
  fullWidth: boolean;
}

const TabsContext = React.createContext<TabsContextValue | null>(null);

function useTabs() {
  const context = React.useContext(TabsContext);
  if (!context) {
    throw new Error("Tab components must be used within a Tabs");
  }
  return context;
}

/* ─────────────────────────────────────────────────────────────────────────────
   Tabs Component
   ───────────────────────────────────────────────────────────────────────────── */

const tabsListVariants = cva("flex items-center", {
  variants: {
    variant: {
      default: "border-b border-border-subtle",
      pills: "gap-1 rounded-lg bg-muted p-1",
      underline: "border-b border-border-subtle",
      cards: "gap-2",
    },
  },
  defaultVariants: {
    variant: "default",
  },
});

export interface TabsProps {
  children: React.ReactNode;
  defaultTab?: string;
  selectedTab?: string;
  onChange?: (tabId: string) => void;
  variant?: "default" | "pills" | "underline" | "cards";
  size?: "sm" | "md" | "lg";
  fullWidth?: boolean;
  className?: string;
}

export function Tabs({
  children,
  defaultTab,
  selectedTab: controlledTab,
  onChange,
  variant = "default",
  size = "md",
  fullWidth = false,
  className,
}: TabsProps) {
  const [internalTab, setInternalTab] = React.useState(defaultTab ?? "");
  const selectedTab = controlledTab ?? internalTab;

  const setSelectedTab = React.useCallback(
    (id: string) => {
      if (controlledTab === undefined) {
        setInternalTab(id);
      }
      onChange?.(id);
    },
    [controlledTab, onChange],
  );

  // Set first tab as default if no default provided
  React.useEffect(() => {
    if (!selectedTab && !defaultTab) {
      const firstTab = React.Children.toArray(children).find(
        (child): child is React.ReactElement<TabProps> =>
          React.isValidElement(child) && child.type === Tab,
      );
      if (firstTab) {
        setSelectedTab(firstTab.props.id);
      }
    }
  }, [children, defaultTab, selectedTab, setSelectedTab]);

  return (
    <TabsContext.Provider
      value={{ selectedTab, setSelectedTab, variant, size, fullWidth }}
    >
      <div className={cn("w-full", className)}>{children}</div>
    </TabsContext.Provider>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Tab List Component
   ───────────────────────────────────────────────────────────────────────────── */

export interface TabListProps {
  children: React.ReactNode;
  className?: string;
}

export function TabList({ children, className }: TabListProps) {
  const { variant, fullWidth } = useTabs();

  return (
    <div
      className={cn(
        tabsListVariants({ variant }),
        fullWidth && "w-full",
        className,
      )}
      role="tablist"
    >
      {children}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Tab Component
   ───────────────────────────────────────────────────────────────────────────── */

const tabVariants = cva(
  "relative inline-flex items-center justify-center gap-2 font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "border-b-2 border-transparent text-foreground-secondary hover:text-foreground data-[state=active]:text-primary data-[state=active]:border-primary",
        pills:
          "rounded-md text-foreground-secondary hover:bg-secondary hover:text-foreground data-[state=active]:bg-primary data-[state=active]:text-primary-foreground",
        underline:
          "border-b-2 border-transparent text-foreground-secondary hover:text-foreground data-[state=active]:text-foreground data-[state=active]:border-primary",
        cards:
          "rounded-lg border border-border-subtle bg-background-elevated px-4 py-3 text-foreground-secondary hover:border-border-default hover:text-foreground data-[state=active]:border-primary data-[state=active]:bg-primary/5 data-[state=active]:text-primary",
      },
      size: {
        sm: "text-xs py-2 px-3",
        md: "text-sm py-2.5 px-4",
        lg: "text-base py-3 px-5",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "md",
    },
  },
);

export interface TabProps {
  id: string;
  children: React.ReactNode;
  disabled?: boolean;
  icon?: React.ReactNode;
  badge?: React.ReactNode;
  className?: string;
}

export function Tab({
  id,
  children,
  disabled,
  icon,
  badge,
  className,
}: TabProps) {
  const { selectedTab, setSelectedTab, variant, size, fullWidth } = useTabs();
  const isSelected = selectedTab === id;
  const ref = React.useRef<HTMLButtonElement>(null);

  const handleClick = () => {
    if (!disabled) {
      setSelectedTab(id);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    const tabList = ref.current?.parentElement;
    if (!tabList) return;

    const tabs = Array.from(tabList.querySelectorAll('[role="tab"]'));
    const currentIndex = tabs.indexOf(ref.current!);

    switch (event.key) {
      case "ArrowLeft":
      case "ArrowUp":
        event.preventDefault();
        const prevIndex = currentIndex > 0 ? currentIndex - 1 : tabs.length - 1;
        (tabs[prevIndex] as HTMLElement).focus();
        (tabs[prevIndex] as HTMLElement).click();
        break;
      case "ArrowRight":
      case "ArrowDown":
        event.preventDefault();
        const nextIndex = currentIndex < tabs.length - 1 ? currentIndex + 1 : 0;
        (tabs[nextIndex] as HTMLElement).focus();
        (tabs[nextIndex] as HTMLElement).click();
        break;
      case "Home":
        event.preventDefault();
        (tabs[0] as HTMLElement).focus();
        (tabs[0] as HTMLElement).click();
        break;
      case "End":
        event.preventDefault();
        (tabs[tabs.length - 1] as HTMLElement).focus();
        (tabs[tabs.length - 1] as HTMLElement).click();
        break;
    }
  };

  return (
    <button
      ref={ref}
      role="tab"
      aria-selected={isSelected}
      aria-disabled={disabled}
      tabIndex={isSelected ? 0 : -1}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={cn(
        tabVariants({ variant, size }),
        fullWidth && "flex-1",
        className,
      )}
      data-state={isSelected ? "active" : "inactive"}
      disabled={disabled}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      <span className="truncate">{children}</span>
      {badge && <span className="shrink-0 ml-1">{badge}</span>}

      {/* Animated indicator for default/underline variants */}
      {(variant === "default" || variant === "underline") && isSelected && (
        <motion.div
          layoutId="activeTabIndicator"
          className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary"
          transition={{ type: "spring", stiffness: 500, damping: 30 }}
        />
      )}
    </button>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Tab Panels Container
   ───────────────────────────────────────────────────────────────────────────── */

export interface TabPanelsProps {
  children: React.ReactNode;
  className?: string;
}

export function TabPanels({ children, className }: TabPanelsProps) {
  return <div className={cn("mt-4", className)}>{children}</div>;
}

/* ─────────────────────────────────────────────────────────────────────────────
   Tab Panel Component
   ───────────────────────────────────────────────────────────────────────────── */

export interface TabPanelProps {
  id: string;
  children: React.ReactNode;
  className?: string;
}

export function TabPanel({ id, children, className }: TabPanelProps) {
  const { selectedTab } = useTabs();
  const isSelected = selectedTab === id;

  if (!isSelected) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.2 }}
      role="tabpanel"
      aria-labelledby={id}
      className={className}
    >
      {children}
    </motion.div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Segmented Control (Alternative to tabs)
   ───────────────────────────────────────────────────────────────────────────── */

export interface SegmentedControlProps {
  options: { value: string; label: string; disabled?: boolean }[];
  value: string;
  onChange: (value: string) => void;
  size?: "sm" | "md";
  className?: string;
}

export function SegmentedControl({
  options,
  value,
  onChange,
  size = "md",
  className,
}: SegmentedControlProps) {
  // className is reserved for future styling
  void className;
  return (
    <div
      className={cn(
        "inline-flex rounded-lg bg-muted p-1",
        size === "sm" && "p-0.5",
        className,
      )}
      role="radiogroup"
    >
      {options.map((option) => (
        <button
          key={option.value}
          role="radio"
          aria-checked={value === option.value}
          disabled={option.disabled}
          onClick={() => onChange(option.value)}
          className={cn(
            "relative px-3 py-1.5 text-sm font-medium rounded-md transition-all",
            size === "sm" && "px-2 py-1 text-xs",
            value === option.value
              ? "bg-primary text-white shadow-sm"
              : "text-foreground-secondary hover:text-foreground",
            option.disabled && "opacity-50 cursor-not-allowed",
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Exports
   ───────────────────────────────────────────────────────────────────────────── */

export default Tabs;
