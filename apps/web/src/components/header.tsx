"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { Button, IconButton } from "@/components/ui/button-horizon";
import { clearAuthTokens, getAuthUserProfile } from "@/lib/auth";

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
  return (
    <>
      {/* Search Trigger */}
      <button
        onClick={() => window.dispatchEvent(new Event("open-command-palette"))}
        className={cn(
          "hidden md:flex items-center gap-2 rounded-lg border border-[#E2E8F0] bg-white px-3 py-2 text-sm text-foreground-tertiary transition-colors hover:border-[#CBD5E1] hover:text-foreground-secondary",
          "w-64 lg:w-80",
        )}
      >
        <Search className="h-4 w-4" />
        <span className="flex-1 text-left">Search...</span>
        <kbd className="rounded bg-slate-100 px-1.5 py-0.5 text-xs font-mono text-foreground-tertiary">
          ⌘K
        </kbd>
      </button>
    </>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   User Menu Component
   ───────────────────────────────────────────────────────────────────────────── */

function UserMenu() {
  const [isOpen, setIsOpen] = React.useState(false);
  const menuRef = React.useRef<HTMLDivElement>(null);
  const router = useRouter();
  const profile = React.useMemo(() => getAuthUserProfile(), []);

  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const displayName = profile?.displayName ?? "Workspace User";
  const email = profile?.email ?? "unknown@yufeed.local";
  const roleLabel = profile?.role
    ? profile.role
        .replaceAll("_", " ")
        .replace(/\b\w/g, (token) => token.toUpperCase())
    : "Analyst";
  const initials = profile?.initials ?? "YU";

  const handleSignOut = () => {
    clearAuthTokens();
    router.replace("/");
  };

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 rounded-lg p-1.5 hover:bg-slate-100 transition-colors"
      >
        <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-xs font-semibold text-primary">
          {initials}
        </div>
        <div className="hidden lg:block text-left">
          <div className="text-sm font-medium text-foreground">
            {displayName}
          </div>
          <div className="text-xs text-foreground-tertiary">{roleLabel}</div>
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
            className="absolute right-0 top-full mt-2 w-56 rounded-xl border border-[#E2E8F0] bg-white shadow-xl overflow-hidden z-50"
          >
            <div className="px-4 py-3 border-b border-border-subtle">
              <div className="font-medium text-foreground">{displayName}</div>
              <div className="text-sm text-foreground-secondary">{email}</div>
            </div>
            <ul className="py-1">
              <li>
                <Link
                  href="/profile"
                  className="flex items-center gap-3 px-4 py-2 text-sm text-foreground-secondary hover:bg-slate-50 hover:text-foreground"
                >
                  <User className="h-4 w-4" />
                  Profile
                </Link>
              </li>
              <li>
                <Link
                  href="/settings"
                  className="flex items-center gap-3 px-4 py-2 text-sm text-foreground-secondary hover:bg-slate-50 hover:text-foreground"
                >
                  <Command className="h-4 w-4" />
                  Settings
                </Link>
              </li>
            </ul>
            <div className="border-t border-border-subtle py-1">
              <button
                className="flex w-full items-center gap-3 px-4 py-2 text-sm text-[#DC2626] hover:bg-red-50"
                onClick={handleSignOut}
              >
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
        "sticky top-0 z-30 h-14 border-b border-[#E2E8F0] bg-white/80 backdrop-blur-xl",
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
            <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-[#DC2626] ring-2 ring-white" />
          </div>

          {/* User Menu */}
          <UserMenu />
        </div>
      </div>
    </header>
  );
}
