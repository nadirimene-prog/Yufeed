"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    Scale, Search, List, Bell, Brain, FileText, Network,
    Settings, LogOut, ChevronLeft, ChevronRight, LayoutDashboard, ShieldCheck
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useState } from "react";

export default function Sidebar() {
    const pathname = usePathname();
    const [collapsed, setCollapsed] = useState(false);

    const links = [
        { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
        { href: "/aml-officer", label: "AI Officer", icon: Brain, highlight: true },
        { href: "/compliance", label: "KYC/KYB", icon: ShieldCheck },
        { href: "/search", label: "Search", icon: Search },
        { href: "/alerts", label: "Alerts", icon: Bell },
        { href: "/cases", label: "Cases", icon: FileText },
        { href: "/audit", label: "Audit Trail", icon: List },
        { href: "/network-analysis", label: "Network", icon: Network },
        { href: "/transaction-monitoring/dashboard", label: "Monitoring", icon: ShieldCheck },
    ];

    const toggleCollapse = () => setCollapsed(!collapsed);

    return (
        <aside
            className={cn(
                "relative flex flex-col h-screen border-r transition-all duration-300 ease-in-out bg-sidebar/95 backdrop-blur supports-[backdrop-filter]:bg-sidebar/90 border-sidebar-border z-50",
                collapsed ? "w-16" : "w-64"
            )}
        >
            {/* Logo Section */}
            <div className="flex h-16 items-center border-b border-sidebar-border px-4">
                <Link href="/" className="flex items-center gap-2 group">
                    <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
                        <Scale className="h-5 w-5" />
                    </div>
                    {!collapsed && (
                        <span className="font-bold text-lg text-sidebar-foreground tracking-tight">
                            EU Monitor
                        </span>
                    )}
                </Link>
            </div>

            {/* Navigation Links */}
            <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-1">
                {links.map((link) => {
                    const isActive = pathname.startsWith(link.href);
                    const Icon = link.icon;
                    // We treat highlight differently in sidebar if needed, but for now stick to consistent active states

                    return (
                        <Link
                            key={link.href}
                            href={link.href}
                            title={collapsed ? link.label : undefined}
                            className={cn(
                                "flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md transition-colors",
                                isActive
                                    ? "bg-sidebar-accent text-sidebar-accent-foreground shadow-sm"
                                    : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground",
                                collapsed && "justify-center px-2"
                            )}
                        >
                            <Icon className={cn("h-5 w-5 shrink-0", isActive ? "text-sidebar-primary" : "")} />
                            {!collapsed && <span>{link.label}</span>}
                        </Link>
                    );
                })}
            </nav>

            {/* Bottom Actions */}
            <div className="border-t border-sidebar-border p-2 space-y-1">
                <button
                    onClick={toggleCollapse}
                    className="flex w-full items-center gap-3 px-3 py-2 text-sm font-medium text-sidebar-foreground/70 hover:bg-sidebar-accent/50 rounded-md transition-colors"
                >
                    {collapsed ? <ChevronRight className="h-5 w-5" /> : <ChevronLeft className="h-5 w-5" />}
                    {!collapsed && <span>Collapse</span>}
                </button>

                <div className="pt-2 mt-2 border-t border-sidebar-border/50">
                    <Link
                        href="/settings"
                        className={cn(
                            "flex items-center gap-3 px-3 py-2 text-sm font-medium text-sidebar-foreground/70 hover:bg-sidebar-accent/50 rounded-md transition-colors",
                            collapsed && "justify-center px-2"
                        )}
                    >
                        <Settings className="h-5 w-5" />
                        {!collapsed && <span>Settings</span>}
                    </Link>
                </div>
            </div>
        </aside>
    );
}
