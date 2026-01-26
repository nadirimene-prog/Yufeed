"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Bell, Search, User, ChevronRight, Command, Moon, Sun, Sparkles } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { NotificationBell } from "./NotificationBell";
import { SearchInput } from "./ui/input";
import { Tooltip } from "./ui/tooltip";
import { springs, transitions } from "@/lib/motion";

/**
 * ═══════════════════════════════════════════════════════════════════
 * HEADER - Sentinel Design System
 * Glass-styled command bar with premium interactions
 * ═══════════════════════════════════════════════════════════════════
 */

export default function Header() {
    const pathname = usePathname();
    const [searchFocused, setSearchFocused] = useState(false);
    const [isDark, setIsDark] = useState(true);

    // Simple breadcrumb logic: split path and capitalize
    const breadcrumbs = pathname
        .split("/")
        .filter(Boolean)
        .map((segment) => ({
            label: segment.charAt(0).toUpperCase() + segment.slice(1).replace(/-/g, " "),
            href: "/" + pathname.split("/").slice(1, pathname.split("/").indexOf(segment) + 2).join("/"),
        }));

    // Sync with document class on mount
    useEffect(() => {
        setIsDark(document.documentElement.classList.contains("dark"));
    }, []);

    const toggleTheme = () => {
        document.documentElement.classList.toggle("dark");
        setIsDark(!isDark);
    };

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
                <nav className="flex items-center gap-1.5 text-sm min-w-0 flex-shrink-0">
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
                        <Link href="/aml-officer">
                            <motion.button
                                className={cn(
                                    "relative flex items-center justify-center h-9 w-9 rounded-lg",
                                    "bg-gradient-to-br from-[#6d5acd]/20 to-[#00d4ff]/10",
                                    "border border-[#6d5acd]/30",
                                    "text-[#00d4ff] hover:text-white",
                                    "transition-colors"
                                )}
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
                        </Link>
                    </Tooltip>

                    {/* Notifications */}
                    <NotificationBell />

                    {/* Theme Toggle */}
                    <Tooltip content={isDark ? "Light mode" : "Dark mode"} side="bottom">
                        <motion.button
                            onClick={toggleTheme}
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
                    <motion.button
                        className={cn(
                            "flex items-center gap-2.5 rounded-lg pl-1.5 pr-3 py-1.5",
                            "hover:bg-white/[0.05] transition-colors"
                        )}
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
                </div>
            </div>
        </header>
    );
}
