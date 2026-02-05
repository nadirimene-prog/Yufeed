"use client";

import { motion, AnimatePresence } from "framer-motion";
import { ChevronRight, LogOut, Moon, Settings, Sparkles, Sun, User } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { NotificationBell } from "./NotificationBell";
import { SearchInput } from "./ui/input";
import { Tooltip } from "./ui/tooltip";
import { springs, transitions } from "@/lib/motion";
import { clearAuthTokens } from "@/lib/auth";

/**
 * ═══════════════════════════════════════════════════════════════════
 * HEADER - Sentinel Design System
 * Glass-styled command bar with premium interactions
 * ═══════════════════════════════════════════════════════════════════
 */

export default function Header() {
    const pathname = usePathname();
    const router = useRouter();
    const [searchFocused, setSearchFocused] = useState(false);
    const [isDark, setIsDark] = useState(() =>
        typeof document !== "undefined" && document.documentElement.classList.contains("dark")
    );
    const [menuOpen, setMenuOpen] = useState(false);
    const menuRef = useRef<HTMLDivElement>(null);

    // Simple breadcrumb logic: split path and capitalize
    const segments = pathname.split("/").filter(Boolean);
    const breadcrumbs = segments.map((segment, index) => ({
        label: segment.charAt(0).toUpperCase() + segment.slice(1).replace(/-/g, " "),
        href: "/" + segments.slice(0, index + 1).join("/"),
    }));

    const toggleTheme = () => {
        document.documentElement.classList.toggle("dark");
        setIsDark((prev) => !prev);
    };

    useEffect(() => {
        const handleClick = (event: MouseEvent) => {
            if (!menuRef.current) return;
            if (!menuRef.current.contains(event.target as Node)) {
                setMenuOpen(false);
            }
        };

        const handleKey = (event: KeyboardEvent) => {
            if (event.key === "Escape") {
                setMenuOpen(false);
            }
        };

        document.addEventListener("mousedown", handleClick);
        document.addEventListener("keydown", handleKey);

        return () => {
            document.removeEventListener("mousedown", handleClick);
            document.removeEventListener("keydown", handleKey);
        };
    }, []);

    return (
        <header className="sticky top-0 z-40 w-full">
            {/* Glass background */}
            <div
                className={cn(
                    "absolute inset-0 border-b transition-all duration-300",
                    "bg-[#0a0a12]/80 backdrop-blur-xl border-white/[0.06]"
                )}
            />

            {/* Subtle top highlight */}
            <div
                className="absolute inset-x-0 top-0 h-px"
                style={{
                    background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.05), transparent)",
                }}
            />

            <div className="relative flex h-16 items-center px-4 md:px-6 gap-4">
                {/* Left: Breadcrumbs */}
                <nav
                    className="flex items-center gap-1.5 text-sm min-w-0 flex-shrink-0"
                    aria-label="Breadcrumb"
                >
                    <Link
                        href="/dashboard"
                        className="hidden md:flex items-center gap-1.5 text-white/40 hover:text-white/70 transition-colors"
                    >
                        <svg
                            className="h-4 w-4"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            strokeWidth={1.5}
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25"
                            />
                        </svg>
                    </Link>

                    {breadcrumbs.length > 0 && (
                        <ChevronRight className="h-3.5 w-3.5 text-white/20 hidden md:block" />
                    )}

                    <div className="flex items-center gap-1">
                        {breadcrumbs.map((crumb, index) => (
                            <motion.span
                                key={`${crumb.href}-${index}`}
                                initial={{ opacity: 0, x: -5 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ ...transitions.fast, delay: index * 0.05 }}
                                className="flex items-center gap-1"
                            >
                                {index > 0 && (
                                    <ChevronRight className="h-3.5 w-3.5 text-white/20" />
                                )}
                                {index === breadcrumbs.length - 1 ? (
                                    <span className="font-medium text-white truncate max-w-[200px]">
                                        {crumb.label}
                                    </span>
                                ) : (
                                    <Link
                                        href={crumb.href}
                                        className="text-white/50 hover:text-white/80 transition-colors truncate max-w-[100px]"
                                    >
                                        {crumb.label}
                                    </Link>
                                )}
                            </motion.span>
                        ))}
                    </div>
                </nav>

                {/* Center: Global Search */}
                <div className="flex-1 flex justify-center max-w-xl mx-auto">
                    <motion.div
                        className="relative w-full"
                        animate={{
                            scale: searchFocused ? 1.02 : 1,
                        }}
                        transition={springs.snappy}
                    >
                        <SearchInput
                            placeholder="Search entities, documents, alerts..."
                            shortcut="⌘K"
                            onFocus={() => setSearchFocused(true)}
                            onBlur={() => setSearchFocused(false)}
                            aria-label="Global search"
                            className={cn(
                                "w-full transition-all duration-200",
                                searchFocused && "shadow-[0_0_30px_rgba(109,90,205,0.2)]"
                            )}
                        />

                        {/* Search focus glow */}
                        <AnimatePresence>
                            {searchFocused && (
                                <motion.div
                                    className="absolute inset-0 -z-10 rounded-lg"
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }}
                                    style={{
                                        background: "radial-gradient(ellipse at center, rgba(109, 90, 205, 0.15) 0%, transparent 70%)",
                                    }}
                                />
                            )}
                        </AnimatePresence>
                    </motion.div>
                </div>

                {/* Right: Actions */}
                <div className="flex items-center gap-2">
                    {/* AI Assistant Quick Access */}
                    <Tooltip content="AI Officer" side="bottom">
                        <motion.button
                            type="button"
                            onClick={() => router.push("/aml-officer")}
                            className={cn(
                                "relative flex items-center justify-center h-9 w-9 rounded-lg",
                                "bg-gradient-to-br from-[#6d5acd]/20 to-[#00d4ff]/10",
                                "border border-[#6d5acd]/30",
                                "text-[#00d4ff] hover:text-white",
                                "transition-colors"
                            )}
                            aria-label="Open AI Officer"
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                        >
                            <Sparkles className="h-4 w-4" />
                            {/* Pulsing indicator */}
                            <motion.span
                                className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-[#06d6a0]"
                                animate={{
                                    scale: [1, 1.3, 1],
                                    opacity: [1, 0.5, 1],
                                }}
                                transition={{
                                    duration: 2,
                                    repeat: Infinity,
                                    ease: "easeInOut",
                                }}
                            />
                        </motion.button>
                    </Tooltip>

                    {/* Notifications */}
                    <NotificationBell />

                    {/* Theme Toggle */}
                    <Tooltip content={isDark ? "Light mode" : "Dark mode"} side="bottom">
                        <motion.button
                            onClick={toggleTheme}
                            aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
                            className={cn(
                                "flex items-center justify-center h-9 w-9 rounded-lg",
                                "text-white/50 hover:text-white hover:bg-white/[0.05]",
                                "transition-colors"
                            )}
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                        >
                            <AnimatePresence mode="wait">
                                {isDark ? (
                                    <motion.div
                                        key="moon"
                                        initial={{ rotate: -90, opacity: 0 }}
                                        animate={{ rotate: 0, opacity: 1 }}
                                        exit={{ rotate: 90, opacity: 0 }}
                                        transition={springs.snappy}
                                    >
                                        <Moon className="h-4 w-4" />
                                    </motion.div>
                                ) : (
                                    <motion.div
                                        key="sun"
                                        initial={{ rotate: 90, opacity: 0 }}
                                        animate={{ rotate: 0, opacity: 1 }}
                                        exit={{ rotate: -90, opacity: 0 }}
                                        transition={springs.snappy}
                                    >
                                        <Sun className="h-4 w-4" />
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </motion.button>
                    </Tooltip>

                    {/* Separator */}
                    <div className="h-6 w-px bg-white/[0.08] mx-1" />

                    {/* User Menu */}
                    <div className="relative" ref={menuRef}>
                        <motion.button
                            onClick={() => setMenuOpen((open) => !open)}
                            className={cn(
                                "flex items-center gap-2.5 rounded-lg pl-1.5 pr-3 py-1.5",
                                "hover:bg-white/[0.05] transition-colors"
                            )}
                            aria-label="Open user menu"
                            aria-haspopup="menu"
                            aria-expanded={menuOpen}
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                        >
                            {/* Avatar with gradient ring */}
                            <div className="relative">
                                <div
                                    className="absolute inset-0 rounded-full"
                                    style={{
                                        background: "linear-gradient(135deg, #6d5acd 0%, #00d4ff 100%)",
                                        padding: "2px",
                                    }}
                                />
                                <div className="relative h-8 w-8 rounded-full bg-[#0a0a12] flex items-center justify-center">
                                    <span className="text-xs font-bold text-white">AU</span>
                                </div>
                                {/* Online indicator */}
                                <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-[#06d6a0] border-2 border-[#0a0a12]" />
                            </div>

                            {/* User info */}
                            <div className="hidden md:block text-left">
                                <p className="text-sm font-medium text-white leading-none">
                                    Admin User
                                </p>
                                <p className="text-[11px] text-white/40 mt-0.5">
                                    admin@yufeed.eu
                                </p>
                            </div>

                            {/* Dropdown indicator */}
                            <ChevronRight className="h-3.5 w-3.5 text-white/30 rotate-90 hidden md:block" />
                        </motion.button>

                        <AnimatePresence>
                            {menuOpen && (
                                <motion.div
                                    initial={{ opacity: 0, y: 8 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: 8 }}
                                    transition={transitions.fast}
                                    className={cn(
                                        "absolute right-0 mt-2 w-56 overflow-hidden rounded-xl",
                                        "border border-white/[0.08] bg-[#0a0a12]/95 backdrop-blur-xl",
                                        "shadow-[0_20px_60px_rgba(0,0,0,0.35)]"
                                    )}
                                    role="menu"
                                >
                                    <div className="px-3 py-2 text-[11px] uppercase tracking-[0.2em] text-white/30">
                                        Workspace
                                    </div>
                                    <div className="px-3 pb-2 text-xs text-white/70">
                                        admin@yufeed.eu
                                    </div>
                                    <div className="h-px bg-white/[0.06]" />
                                    <div className="p-2 space-y-1">
                                        <Link
                                            href="/profile"
                                            className="flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm text-white/70 hover:text-white hover:bg-white/[0.06]"
                                            onClick={() => setMenuOpen(false)}
                                            role="menuitem"
                                        >
                                            <User className="h-4 w-4" />
                                            Profile
                                        </Link>
                                        <Link
                                            href="/settings"
                                            className="flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm text-white/70 hover:text-white hover:bg-white/[0.06]"
                                            onClick={() => setMenuOpen(false)}
                                            role="menuitem"
                                        >
                                            <Settings className="h-4 w-4" />
                                            Settings
                                        </Link>
                                    </div>
                                    <div className="h-px bg-white/[0.06]" />
                                    <button
                                        onClick={() => {
                                            clearAuthTokens();
                                            setMenuOpen(false);
                                            router.push("/");
                                        }}
                                        className="flex w-full items-center gap-2 px-4 py-2.5 text-sm text-[#ff8aa8] hover:bg-[#ff3366]/10"
                                        role="menuitem"
                                    >
                                        <LogOut className="h-4 w-4" />
                                        Sign out
                                    </button>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>
            </div>
        </header>
    );
}
