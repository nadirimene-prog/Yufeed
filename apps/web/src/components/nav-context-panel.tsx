"use client";

import Link from "next/link";
import { Activity } from "lucide-react";
import { cn } from "@/lib/utils";
import type { NavArea } from "@/components/nav-data";
import { isRouteMatch } from "@/components/nav-data";

interface NavContextPanelProps {
    area: NavArea;
    pathname: string;
}

export default function NavContextPanel({ area, pathname }: NavContextPanelProps) {
    return (
        <div className="flex h-full w-[232px] flex-col px-4 py-4">
            <div className="mb-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-white/40">
                    {area.label}
                </p>
                <div className="mt-2 h-px w-full bg-gradient-to-r from-white/10 to-transparent" />
            </div>

            <nav
                role="navigation"
                aria-label={`${area.label} navigation`}
                className="flex-1 space-y-2 overflow-y-auto pr-1"
            >
                {area.items.map((item) => {
                    const isActive = isRouteMatch(pathname, item.href);
                    const isWorkArea = area.id === "work";
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            aria-current={isActive ? "page" : undefined}
                            className={cn(
                                "group flex flex-col gap-1 rounded-lg px-3 py-2 text-sm transition-all",
                                isActive
                                    ? "bg-white/[0.10] text-white shadow-[0_0_12px_rgba(0,212,255,0.12)]"
                                    : "text-white/60 hover:text-white/90 hover:bg-white/[0.05]",
                                isWorkArea && "border-l-2 border-transparent",
                                isWorkArea && isActive && "border-[#6d5acd]",
                                isWorkArea && !isActive && "hover:border-white/20"
                            )}
                        >
                            <span
                                className={cn(
                                    "font-medium",
                                    isWorkArea && "text-white"
                                )}
                            >
                                {item.label}
                            </span>
                            {item.description && (
                                <span className="text-[11px] text-white/40">
                                    {item.description}
                                </span>
                            )}
                        </Link>
                    );
                })}
            </nav>

            <div className="mt-4 border-t border-white/[0.06] pt-4">
                <div className="flex items-center gap-3 rounded-lg bg-white/[0.04] px-3 py-2">
                    <div className="relative">
                        <Activity className="h-4 w-4 text-[#06d6a0]" />
                        <span className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-[#06d6a0]" />
                    </div>
                    <div className="min-w-0">
                        <p className="text-[11px] font-medium text-white/70">System Status</p>
                        <p className="text-[10px] text-[#06d6a0] font-mono">All systems operational</p>
                    </div>
                </div>
            </div>
        </div>
    );
}
