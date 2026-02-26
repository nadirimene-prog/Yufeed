"use client";

import { useEffect, useRef } from "react";
import trackDashboardEvent from "@/features/dashboard/telemetry";

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
      if (!enabled) return;

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
        onOpenCommandPalette();
        clearPrefix();
        return;
      }

      if (isTargetBlocked || (hasOpenDialog() && !isTargetBlocked)) {
        clearPrefix();
        return;
      }

      if (key === "?" && !hasModifierKey(event)) {
        event.preventDefault();
        trackDashboardEvent("dashboard_shortcut_used", { shortcut: "?" });
        onOpenShortcutHelp();
        clearPrefix();
        return;
      }

      if (pendingPrefixRef.current === "g" && !hasModifierKey(event)) {
        if (lowerKey === "q") {
          event.preventDefault();
          trackDashboardEvent("dashboard_shortcut_used", { shortcut: "g q" });
          onFocusQueueSearch?.();
          clearPrefix();
          return;
        }
        if (lowerKey === "d") {
          event.preventDefault();
          trackDashboardEvent("dashboard_shortcut_used", { shortcut: "g d" });
          onFocusWorkspacePanel?.();
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
        onToggleInsights?.();
        return;
      }

      if (lowerKey === "a") {
        event.preventDefault();
        trackDashboardEvent("dashboard_shortcut_used", { shortcut: "a" });
        onFocusAssign?.();
        return;
      }

      if (lowerKey === "e") {
        event.preventDefault();
        trackDashboardEvent("dashboard_shortcut_used", { shortcut: "e" });
        onEscalate?.();
        return;
      }

      if (lowerKey === "n") {
        event.preventDefault();
        trackDashboardEvent("dashboard_shortcut_used", { shortcut: "n" });
        onActionNext?.();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      clearPrefix();
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
}

export default useDashboardShortcuts;
