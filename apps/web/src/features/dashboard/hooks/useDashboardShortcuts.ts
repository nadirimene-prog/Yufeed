"use client";

import { useEffect, useRef } from "react";
import trackDashboardEvent from "@/features/dashboard/telemetry";

export interface DashboardShortcutHelpSection {
  title: string;
  items: Array<{ keys: string; description: string }>;
}

export const DASHBOARD_SHORTCUT_HELP_SECTIONS: DashboardShortcutHelpSection[] =
  [
    {
      title: "Navigation",
      items: [
        { keys: "j / k", description: "Move to next/previous queue item" },
        { keys: "g then q", description: "Focus queue search" },
        { keys: "g then d", description: "Focus workspace panel" },
        { keys: "i", description: "Toggle insights rail" },
      ],
    },
    {
      title: "Actions",
      items: [
        { keys: "a", description: "Focus assignee field in Actions tab" },
        { keys: "e", description: "Run Escalate action (if available)" },
        { keys: "n", description: "Run first available '+ Next' action" },
        { keys: "x", description: "Toggle selection for current queue item" },
      ],
    },
    {
      title: "Help",
      items: [
        { keys: "?", description: "Open shortcut help" },
        { keys: "Ctrl/Cmd + K", description: "Open command palette" },
      ],
    },
  ];

interface DashboardShortcutHandlers {
  enabled?: boolean;
  onOpenShortcutHelp: () => void;
  onOpenCommandPalette: () => void;
  onFocusQueueSearch?: () => void;
  onFocusWorkspacePanel?: () => void;
  onToggleInsights?: () => void;
  onFocusAssign?: () => void;
  onEscalate?: () => void;
  onActionNext?: () => void;
}

function hasModifierKey(event: KeyboardEvent) {
  return event.metaKey || event.ctrlKey || event.altKey;
}

function hasOpenDialog() {
  if (typeof document === "undefined") return false;
  return document.querySelector("[role='dialog']") !== null;
}

export function isDashboardShortcutTargetBlocked(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) {
    return false;
  }

  if (target.closest("[role='dialog']")) {
    return true;
  }

  if (target.isContentEditable) {
    return true;
  }

  const tagName = target.tagName.toLowerCase();
  if (tagName === "input" || tagName === "textarea" || tagName === "select") {
    return true;
  }

  const role = target.getAttribute("role");
  if (role === "textbox" || role === "combobox") {
    return true;
  }

  return false;
}

export function useDashboardShortcuts({
  enabled = true,
  onOpenShortcutHelp,
  onOpenCommandPalette,
  onFocusQueueSearch,
  onFocusWorkspacePanel,
  onToggleInsights,
  onFocusAssign,
  onEscalate,
  onActionNext,
}: DashboardShortcutHandlers) {
  const pendingPrefixRef = useRef<"g" | null>(null);
  const prefixTimeoutRef = useRef<number | null>(null);
  const handlersRef = useRef({
    enabled,
    onOpenShortcutHelp,
    onOpenCommandPalette,
    onFocusQueueSearch,
    onFocusWorkspacePanel,
    onToggleInsights,
    onFocusAssign,
    onEscalate,
    onActionNext,
  });

  useEffect(() => {
    handlersRef.current = {
      enabled,
      onOpenShortcutHelp,
      onOpenCommandPalette,
      onFocusQueueSearch,
      onFocusWorkspacePanel,
      onToggleInsights,
      onFocusAssign,
      onEscalate,
      onActionNext,
    };
  }, [
    enabled,
    onActionNext,
    onEscalate,
    onFocusAssign,
    onFocusQueueSearch,
    onFocusWorkspacePanel,
    onOpenCommandPalette,
    onOpenShortcutHelp,
    onToggleInsights,
  ]);

  useEffect(() => {
    if (!enabled) return;

    const clearPrefix = () => {
      pendingPrefixRef.current = null;
      if (prefixTimeoutRef.current) {
        window.clearTimeout(prefixTimeoutRef.current);
        prefixTimeoutRef.current = null;
      }
    };

    const setPrefix = (prefix: "g") => {
      clearPrefix();
      pendingPrefixRef.current = prefix;
      prefixTimeoutRef.current = window.setTimeout(() => {
        pendingPrefixRef.current = null;
        prefixTimeoutRef.current = null;
      }, 1000);
    };

    const onKeyDown = (event: KeyboardEvent) => {
      const handlers = handlersRef.current;
      if (!handlers.enabled) return;

      const key = event.key;
      const lowerKey = key.toLowerCase();
      const isTargetBlocked = isDashboardShortcutTargetBlocked(event.target);

      if (
        (event.metaKey || event.ctrlKey) &&
        lowerKey === "k" &&
        !event.altKey &&
        !event.shiftKey
      ) {
        event.preventDefault();
        trackDashboardEvent("dashboard_shortcut_used", {
          shortcut: "mod+k",
        });
        handlers.onOpenCommandPalette();
        clearPrefix();
        return;
      }

      if (isTargetBlocked || hasOpenDialog()) {
        clearPrefix();
        return;
      }

      if (key === "?" && !hasModifierKey(event)) {
        event.preventDefault();
        trackDashboardEvent("dashboard_shortcut_used", { shortcut: "?" });
        handlers.onOpenShortcutHelp();
        clearPrefix();
        return;
      }

      if (pendingPrefixRef.current === "g" && !hasModifierKey(event)) {
        if (lowerKey === "q") {
          event.preventDefault();
          trackDashboardEvent("dashboard_shortcut_used", { shortcut: "g q" });
          handlers.onFocusQueueSearch?.();
          clearPrefix();
          return;
        }
        if (lowerKey === "d") {
          event.preventDefault();
          trackDashboardEvent("dashboard_shortcut_used", { shortcut: "g d" });
          handlers.onFocusWorkspacePanel?.();
          clearPrefix();
          return;
        }
        clearPrefix();
      }

      if (hasModifierKey(event) || event.shiftKey) {
        return;
      }

      if (lowerKey === "g") {
        event.preventDefault();
        trackDashboardEvent("dashboard_shortcut_used", { shortcut: "g" });
        setPrefix("g");
        return;
      }

      if (lowerKey === "i") {
        event.preventDefault();
        trackDashboardEvent("dashboard_shortcut_used", { shortcut: "i" });
        handlers.onToggleInsights?.();
        return;
      }

      if (lowerKey === "a") {
        event.preventDefault();
        trackDashboardEvent("dashboard_shortcut_used", { shortcut: "a" });
        handlers.onFocusAssign?.();
        return;
      }

      if (lowerKey === "e") {
        event.preventDefault();
        trackDashboardEvent("dashboard_shortcut_used", { shortcut: "e" });
        handlers.onEscalate?.();
        return;
      }

      if (lowerKey === "n") {
        event.preventDefault();
        trackDashboardEvent("dashboard_shortcut_used", { shortcut: "n" });
        handlers.onActionNext?.();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      clearPrefix();
    };
  }, [enabled]);
}

export default useDashboardShortcuts;
