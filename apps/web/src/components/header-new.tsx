"use client";

import * as React from "react";
import Link from "next/link";

import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { Button, IconButton } from "@/components/ui/button-horizon";

import {
  Search,
  Bell,
  Command,
  User,
  LogOut,
  ChevronDown,
  Menu,
  Sparkles,
} from "lucide-react";

/**
 * Horizon Header System
 * Modern, accessible header with global search and user actions
 */

/* ─────────────────────────────────────────────────────────────────────────────
   Breadcrumb Component
   ───────────────────────────────────────────────────────────────────────────── */

interface BreadcrumbItem {
  label: string;
  href?: string;
}

function Breadcrumbs({ items }: { items: BreadcrumbItem[] }) {
  return (
    <nav aria-label="Breadcrumb" className="hidden md:flex">
      <ol className="flex items-center gap-2 text-sm">
        {items.map((item, index) => {
          const isLast = index === items.length - 1;
          return (
            <li key={item.label} className="flex items-center gap-2">
              {index > 0 && <span className="text-foreground-tertiary">/</span>}
              {item.href && !isLast ? (
                <Link
                  href={item.href}
                  className="text-foreground-secondary hover:text-foreground transition-colors"
                >
                  {item.label}
                </Link>
              ) : (
                <span
                  className={cn(
                    isLast
                      ? "text-foreground font-medium"
                      : "text-foreground-secondary",
                  )}
                >
                  {item.label}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Global Search Component
   ───────────────────────────────────────────────────────────────────────────── */

function GlobalSearch() {
  const [isOpen, setIsOpen] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setIsOpen(true);
      }
      if (e.key === "Escape") {
        setIsOpen(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  React.useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  return (
    <>
      {/* Search Trigger */}
      <button
        onClick={() => setIsOpen(true)}
        className={cn(
          "hidden md:flex items-center gap-2 rounded-lg border border-border-subtle bg-bg-elevated px-3 py-2 text-sm text-foreground-tertiary transition-colors hover:border-border-default hover:text-foreground-secondary",
          "w-64 lg:w-80",
        )}
      >
        <Search className="h-4 w-4" />
        <span className="flex-1 text-left">Search...</span>
        <kbd className="rounded bg-bg-overlay px-1.5 py-0.5 text-xs font-mono text-foreground-tertiary">
          ⌘K
        </kbd>
      </button>

      {/* Search Modal */}
      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="fixed inset-0 z-50 bg-black/50"
              onClick={() => setIsOpen(false)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: -10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -10 }}
              transition={{ duration: 0.15, ease: [0, 0, 0.2, 1] }}
              className="fixed left-1/2 top-24 z-50 w-full max-w-2xl -translate-x-1/2"
            >
              <div className="overflow-hidden rounded-xl border border-border-default bg-bg-overlay shadow-2xl">
                {/* Search Input */}
                <div className="flex items-center gap-3 border-b border-border-subtle px-4 py-3">
                  <Search className="h-5 w-5 text-foreground-tertiary" />
                  <input
                    ref={inputRef}
                    type="text"
                    placeholder="Search documents, cases, alerts..."
                    className="flex-1 bg-transparent text-foreground placeholder:text-foreground-tertiary focus:outline-none"
                  />
                  <kbd
                    className="rounded bg-bg-floating px-2 py-1 text-xs font-mono text-foreground-tertiary cursor-pointer hover:text-foreground"
                    onClick={() => setIsOpen(false)}
                  >
                    ESC
                  </kbd>
                </div>

                {/* Search Results */}
                <div className="max-h-[60vh] overflow-y-auto p-2">
                  <div className="px-3 py-2 text-xs font-medium text-foreground-tertiary uppercase tracking-wider">
                    Recent Searches
                  </div>
                  <ul className="space-y-1">
                    {[
                      "AML Regulation 2024/1234",
                      "Case #45231",
                      "SAR Q4 Report",
                      "GDPR Compliance Check",
                    ].map((item) => (
                      <li key={item}>
                        <button className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm text-foreground-secondary hover:bg-bg-elevated hover:text-foreground">
                          <Search className="h-4 w-4" />
                          {item}
                        </button>
                      </li>
                    ))}
                  </ul>

                  <div className="mt-4 px-3 py-2 text-xs font-medium text-foreground-tertiary uppercase tracking-wider">
                    Quick Actions
                  </div>
                  <ul className="space-y-1">
                    {[
                      { label: "Create New Case", shortcut: "⌘N" },
                      { label: "Submit SAR", shortcut: "⌘⇧S" },
                      { label: "View Dashboard", shortcut: "⌘D" },
                    ].map((item) => (
                      <li key={item.label}>
                        <button className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm text-foreground-secondary hover:bg-bg-elevated hover:text-foreground">
                          <span>{item.label}</span>
                          <kbd className="rounded bg-bg-floating px-1.5 py-0.5 text-xs font-mono text-foreground-tertiary">
                            {item.shortcut}
                          </kbd>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Footer */}
                <div className="border-t border-border-subtle px-4 py-2 text-xs text-foreground-tertiary flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span>
                      <kbd className="rounded bg-bg-floating px-1">↑</kbd>{" "}
                      <kbd className="rounded bg-bg-floating px-1">↓</kbd> to
                      navigate
                    </span>
                    <span>
                      <kbd className="rounded bg-bg-floating px-1.5">↵</kbd> to
                      select
                    </span>
                  </div>
                  <span>AI-powered search</span>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   User Menu Component
   ───────────────────────────────────────────────────────────────────────────── */

function UserMenu() {
  const [isOpen, setIsOpen] = React.useState(false);
  const menuRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 rounded-lg p-1.5 hover:bg-bg-overlay transition-colors"
      >
        <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
          <User className="h-4 w-4 text-primary" />
        </div>
        <div className="hidden lg:block text-left">
          <div className="text-sm font-medium text-foreground">John Doe</div>
          <div className="text-xs text-foreground-tertiary">
            Compliance Officer
          </div>
        </div>
        <ChevronDown
          className={cn(
            "h-4 w-4 text-foreground-tertiary transition-transform",
            isOpen && "rotate-180",
          )}
        />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.95 }}
            transition={{ duration: 0.15, ease: [0, 0, 0.2, 1] }}
            className="absolute right-0 top-full mt-2 w-56 rounded-xl border border-border-default bg-bg-overlay shadow-xl overflow-hidden z-50"
          >
            <div className="px-4 py-3 border-b border-border-subtle">
              <div className="font-medium text-foreground">John Doe</div>
              <div className="text-sm text-foreground-secondary">
                john@yufeed.com
              </div>
            </div>
            <ul className="py-1">
              <li>
                <Link
                  href="/profile"
                  className="flex items-center gap-3 px-4 py-2 text-sm text-foreground-secondary hover:bg-bg-elevated hover:text-foreground"
                >
                  <User className="h-4 w-4" />
                  Profile
                </Link>
              </li>
              <li>
                <Link
                  href="/settings"
                  className="flex items-center gap-3 px-4 py-2 text-sm text-foreground-secondary hover:bg-bg-elevated hover:text-foreground"
                >
                  <Command className="h-4 w-4" />
                  Settings
                </Link>
              </li>
            </ul>
            <div className="border-t border-border-subtle py-1">
              <button className="flex w-full items-center gap-3 px-4 py-2 text-sm text-critical-400 hover:bg-critical-500/10">
                <LogOut className="h-4 w-4" />
                Sign out
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Main Header Component
   ───────────────────────────────────────────────────────────────────────────── */

interface HeaderProps {
  className?: string;
  onMenuClick?: () => void;
  breadcrumbs?: BreadcrumbItem[];
}

export default function Header({
  className,
  onMenuClick,
  breadcrumbs = [{ label: "Dashboard", href: "/dashboard" }],
}: HeaderProps) {
  return (
    <header
      className={cn(
        "sticky top-0 z-30 h-14 border-b border-border-subtle bg-bg-base/80 backdrop-blur-xl",
        className,
      )}
    >
      <div className="flex h-full items-center justify-between gap-4 px-4 lg:px-6">
        {/* Left Section */}
        <div className="flex items-center gap-4">
          {/* Mobile Menu Button */}
          <IconButton
            variant="ghost"
            size="md"
            icon={<Menu className="h-5 w-5" />}
            label="Open menu"
            onClick={onMenuClick}
            className="lg:hidden"
          />

          {/* Breadcrumbs */}
          <Breadcrumbs items={breadcrumbs} />
        </div>

        {/* Center - Search */}
        <div className="flex-1 max-w-xl hidden md:block">
          <GlobalSearch />
        </div>

        {/* Right Section */}
        <div className="flex items-center gap-2">
          {/* AI Assistant Button */}
          <Button
            variant="secondary"
            size="sm"
            leftIcon={<Sparkles className="h-4 w-4 text-primary" />}
            className="hidden sm:flex"
          >
            AI Assistant
          </Button>

          {/* Notifications */}
          <div className="relative">
            <IconButton
              variant="ghost"
              size="md"
              icon={<Bell className="h-5 w-5" />}
              label="Notifications"
            />
            <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-critical-500 ring-2 ring-bg-base" />
          </div>

          {/* User Menu */}
          <UserMenu />
        </div>
      </div>
    </header>
  );
}
