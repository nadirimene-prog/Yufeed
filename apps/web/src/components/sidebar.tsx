"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
    Scale, Search, List, Bell, Brain, FileText, Network,
    Settings, LogOut, ChevronLeft, ChevronRight, LayoutDashboard, ShieldCheck, Zap,
    Route, Link2, Cpu, Sparkles, Activity
} from "lucide-react";
import { cn } from "@/lib/utils";
import { clearAuthTokens } from "@/lib/auth";
import { useState } from "react";
import { sidebarItem, staggerContainer, springs, transitions } from "@/lib/motion";

/**
 * ═══════════════════════════════════════════════════════════════════
 * SIDEBAR - Sentinel Design System
 * Command Center Navigation with glass effects and aurora accents
 * ═══════════════════════════════════════════════════════════════════
 */

interface NavSection {
    title: string;
    items: NavItem[];
}

interface NavItem {
    href: string;
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    highlight?: boolean;
    badge?: string | number;
}

const navSections: NavSection[] = [
    {
        title: "Command",
        items: [
            { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
            { href: "/aml-officer", label: "AI Officer", icon: Brain, highlight: true },
        ],
    },
    {
        title: "Compliance",
        items: [
            { href: "/compliance", label: "KYC/KYB", icon: ShieldCheck },
            { href: "/compliance/obligations", label: "Obligations", icon: Scale },
            { href: "/compliance/aml-scope", label: "AML Scope", icon: Activity },
            { href: "/compliance/policies", label: "Policies", icon: FileText },
            { href: "/decisioning", label: "Decisioning", icon: Zap },
        ],
    },
    {
        title: "Intelligence",
        items: [
            { href: "/search", label: "Search", icon: Search },
            { href: "/alerts", label: "Alerts", icon: Bell },
            { href: "/cases", label: "Cases", icon: FileText },
            { href: "/audit", label: "Audit Trail", icon: List },
        ],
    },
    {
        title: "Analysis",
        items: [
            { href: "/network-analysis", label: "Network", icon: Network },
            { href: "/transaction-monitoring/dashboard", label: "Monitoring", icon: ShieldCheck },
            { href: "/travel-rule", label: "Travel Rule", icon: Route },
            { href: "/onchain-risk", label: "On-chain Risk", icon: Link2 },
            { href: "/model-registry", label: "Model Registry", icon: Cpu },
        ],
    },
];

export default function Sidebar() {
    const pathname = usePathname();
    const router = useRouter();
    const [collapsed, setCollapsed] = useState(false);

    const toggleCollapse = () => setCollapsed(!collapsed);

    return (
        <aside
            className={cn(
                "relative flex flex-col h-screen border-r transition-all duration-300 ease-out z-50",
                "bg-[#0a0a12]/95 backdrop-blur-xl",
                "border-white/[0.06]",
                collapsed ? "w-[72px]" : "w-[260px]"
            )}
        >
            {/* Ambient gradient background */}
            <div className="absolute inset-0 pointer-events-none overflow-hidden">
                <div
                    className="absolute -top-32 -left-32 w-64 h-64 rounded-full opacity-20 blur-3xl"
                    style={{ background: "radial-gradient(circle, #6d5acd 0%, transparent 70%)" }}
                />
                <div
                    className="absolute -bottom-32 -right-16 w-48 h-48 rounded-full opacity-10 blur-3xl"
                    style={{ background: "radial-gradient(circle, #00d4ff 0%, transparent 70%)" }}
                />
            </div>

            {/* Subtle edge gradient */}
            <div
                className="absolute right-0 top-0 bottom-0 w-px"
                style={{
                    background: "linear-gradient(180deg, transparent 0%, rgba(109, 90, 205, 0.3) 50%, transparent 100%)"
                }}
            />

            {/* Logo Section */}
            <div className="relative flex h-16 items-center border-b border-white/[0.06] px-4">
                <Link href="/" className="flex items-center gap-3 group">
                    {/* Animated logo container */}
                    <motion.div
                        className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-[#6d5acd] to-[#00d4ff] shadow-lg"
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        transition={springs.snappy}
                    >
                        {/* Glow ring */}
                        <motion.div
                            className="absolute inset-0 rounded-xl"
                            animate={{
                                boxShadow: [
                                    "0 0 20px rgba(109, 90, 205, 0.4)",
                                    "0 0 30px rgba(109, 90, 205, 0.6)",
                                    "0 0 20px rgba(109, 90, 205, 0.4)",
                                ],
                            }}
                            transition={{
                                duration: 2,
                                repeat: Infinity,
                                ease: "easeInOut",
                            }}
                        />
                        <Scale className="h-5 w-5 text-white relative z-10" />
                    </motion.div>

                    <AnimatePresence mode="wait">
                        {!collapsed && (
                            <motion.div
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -10 }}
                                transition={transitions.fast}
                                className="flex flex-col"
                            >
                                <span className="font-bold text-base text-white tracking-tight font-display">
                                    YuFeed
                                </span>
                                <span className="text-[10px] font-medium uppercase tracking-[0.2em] text-[#00d4ff]/80">
                                    Sentinel
                                </span>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </Link>
            </div>

            {/* Navigation */}
            <nav className="flex-1 overflow-y-auto py-4 px-3 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
                <motion.div
                    variants={staggerContainer}
                    initial="initial"
                    animate="animate"
                    className="space-y-6"
                >
                    {navSections.map((section) => (
                        <div key={section.title}>
                            {/* Section Title */}
                            <AnimatePresence mode="wait">
                                {!collapsed && (
                                    <motion.div
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        exit={{ opacity: 0 }}
                                        className="flex items-center gap-2 px-3 mb-2"
                                    >
                                        <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-white/30">
                                            {section.title}
                                        </span>
                                        <div className="flex-1 h-px bg-gradient-to-r from-white/10 to-transparent" />
                                    </motion.div>
                                )}
                            </AnimatePresence>

                            {/* Section Items */}
                            <div className="space-y-1">
                                {section.items.map((item) => (
                                    <NavLink
                                        key={item.href}
                                        item={item}
                                        isActive={pathname.startsWith(item.href)}
                                        collapsed={collapsed}
                                    />
                                ))}
                            </div>
                        </div>
                    ))}
                </motion.div>
            </nav>

            {/* System Status */}
            <div className="px-3 py-3 border-t border-white/[0.06]">
                <AnimatePresence mode="wait">
                    {!collapsed ? (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-white/[0.03]"
                        >
                            <div className="relative">
                                <Activity className="h-4 w-4 text-[#06d6a0]" />
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
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-[11px] font-medium text-white/70">System Status</p>
                                <p className="text-[10px] text-[#06d6a0] font-mono">All systems operational</p>
                            </div>
                            {/* Mini activity bars */}
                            <div className="flex items-end gap-0.5 h-4">
                                {[0.4, 0.7, 0.5, 0.9, 0.6].map((height, i) => (
                                    <motion.div
                                        key={i}
                                        className="w-1 rounded-full bg-[#06d6a0]/50"
                                        animate={{
                                            height: [`${height * 100}%`, `${height * 60}%`, `${height * 100}%`],
                                        }}
                                        transition={{
                                            duration: 1.5,
                                            repeat: Infinity,
                                            delay: i * 0.1,
                                            ease: "easeInOut",
                                        }}
                                    />
                                ))}
                            </div>
                        </motion.div>
                    ) : (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="flex justify-center"
                        >
                            <div className="relative">
                                <Activity className="h-5 w-5 text-[#06d6a0]" />
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
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* Bottom Actions */}
            <div className="border-t border-white/[0.06] p-3 space-y-1">
                {/* Collapse Toggle */}
                <motion.button
                    onClick={toggleCollapse}
                    className={cn(
                        "flex w-full items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-colors",
                        "text-white/50 hover:text-white/80 hover:bg-white/[0.05]",
                        collapsed && "justify-center"
                    )}
                    whileHover={{ x: collapsed ? 0 : 2 }}
                    whileTap={{ scale: 0.98 }}
                >
                    <motion.div
                        animate={{ rotate: collapsed ? 180 : 0 }}
                        transition={springs.snappy}
                    >
                        <ChevronLeft className="h-4 w-4" />
                    </motion.div>
                    <AnimatePresence mode="wait">
                        {!collapsed && (
                            <motion.span
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                            >
                                Collapse
                            </motion.span>
                        )}
                    </AnimatePresence>
                </motion.button>

                {/* Divider */}
                <div className="my-2 h-px bg-white/[0.06]" />

                {/* Settings */}
                <Link
                    href="/settings"
                    className={cn(
                        "flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-all",
                        "text-white/50 hover:text-white/80 hover:bg-white/[0.05]",
                        collapsed && "justify-center"
                    )}
                >
                    <Settings className="h-4 w-4" />
                    {!collapsed && <span>Settings</span>}
                </Link>

                {/* Logout */}
                <motion.button
                    onClick={() => {
                        clearAuthTokens();
                        router.push("/login");
                    }}
                    className={cn(
                        "flex w-full items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-all",
                        "text-white/50 hover:text-[#ff3366] hover:bg-[#ff3366]/10",
                        collapsed && "justify-center"
                    )}
                    whileHover={{ x: collapsed ? 0 : 2 }}
                    whileTap={{ scale: 0.98 }}
                >
                    <LogOut className="h-4 w-4" />
                    {!collapsed && <span>Logout</span>}
                </motion.button>
            </div>
        </aside>
    );
}

/**
 * Individual Navigation Link Component
 */
interface NavLinkProps {
    item: NavItem;
    isActive: boolean;
    collapsed: boolean;
}

function NavLink({ item, isActive, collapsed }: NavLinkProps) {
    const Icon = item.icon;

    return (
        <Link
            href={item.href}
            title={collapsed ? item.label : undefined}
        >
            <motion.div
                className={cn(
                    "relative flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-all",
                    isActive
                        ? "text-white bg-white/[0.08]"
                        : "text-white/50 hover:text-white/80 hover:bg-white/[0.04]",
                    collapsed && "justify-center px-2"
                )}
                whileHover={{ x: collapsed ? 0 : 4 }}
                whileTap={{ scale: 0.98 }}
                transition={springs.snappy}
            >
                {/* Active indicator - gradient left border */}
                {isActive && (
                    <motion.div
                        className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-8 rounded-full"
                        style={{
                            background: "linear-gradient(180deg, #6d5acd 0%, #00d4ff 100%)",
                        }}
                        layoutId="activeIndicator"
                        transition={springs.snappy}
                    />
                )}

                {/* Icon with glow for highlighted items */}
                <div className="relative">
                    <Icon
                        className={cn(
                            "h-[18px] w-[18px] shrink-0",
                            isActive && "text-[#00d4ff]",
                            item.highlight && !isActive && "text-[#6d5acd]"
                        )}
                    />
                    {/* AI sparkle indicator */}
                    {item.highlight && (
                        <motion.div
                            className="absolute -top-1 -right-1"
                            animate={{
                                opacity: [0.5, 1, 0.5],
                                scale: [0.8, 1, 0.8],
                            }}
                            transition={{
                                duration: 2,
                                repeat: Infinity,
                                ease: "easeInOut",
                            }}
                        >
                            <Sparkles className="h-2.5 w-2.5 text-[#00d4ff]" />
                        </motion.div>
                    )}
                </div>

                {/* Label */}
                <AnimatePresence mode="wait">
                    {!collapsed && (
                        <motion.span
                            initial={{ opacity: 0, x: -5 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -5 }}
                            transition={transitions.fast}
                            className="truncate"
                        >
                            {item.label}
                        </motion.span>
                    )}
                </AnimatePresence>

                {/* Badge */}
                {item.badge && !collapsed && (
                    <motion.span
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        className="ml-auto px-1.5 py-0.5 text-[10px] font-bold rounded-full bg-[#ff3366]/20 text-[#ff3366]"
                    >
                        {item.badge}
                    </motion.span>
                )}

                {/* Hover glow for active items */}
                {isActive && (
                    <motion.div
                        className="absolute inset-0 rounded-lg pointer-events-none"
                        style={{
                            background: "linear-gradient(90deg, rgba(109, 90, 205, 0.1) 0%, transparent 100%)",
                        }}
                    />
                )}
            </motion.div>
        </Link>
    );
}
