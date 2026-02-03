"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Scale, Search, List, Bell, Brain, FileText, Network, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

export default function Navbar() {
    const pathname = usePathname();

    const links = [
        { href: "/aml-officer", label: "AI Officer", icon: Brain, highlight: true },
        { href: "/decisioning", label: "Decisioning", icon: Zap },
        { href: "/search", label: "Search", icon: Search },
        { href: "/alerts", label: "Alerts", icon: Bell },
        { href: "/cases", label: "Cases", icon: FileText },
        { href: "/network", label: "Network", icon: Network },
        { href: "/watchlists", label: "Watchlists", icon: List },
    ];

    return (
        <nav className="sticky top-0 z-50 w-full border-b border-gray-200 bg-white/80 backdrop-blur-md dark:border-gray-800 dark:bg-gray-950/80">
            <div className="container mx-auto flex h-16 items-center px-4">
                <Link href="/" className="mr-8 flex items-center space-x-2">
                    <Scale className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                    <span className="hidden font-bold sm:inline-block text-gray-900 dark:text-gray-100">
                        YuFeed Risk OS
                    </span>
                </Link>
                <div className="flex items-center space-x-4">
                    {links.map((link) => {
                        const isActive = pathname.startsWith(link.href);
                        const Icon = link.icon;
                        const isHighlight = 'highlight' in link && link.highlight;
                        return (
                            <Link
                                key={link.href}
                                href={link.href}
                                className={cn(
                                    "flex items-center space-x-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                                    isHighlight && !isActive
                                        ? "bg-indigo-50 text-indigo-700 hover:bg-indigo-100 dark:bg-indigo-900/30 dark:text-indigo-400 dark:hover:bg-indigo-900/50"
                                        : "hover:bg-gray-100 dark:hover:bg-gray-800",
                                    isActive
                                        ? isHighlight
                                            ? "bg-indigo-100 text-indigo-900 dark:bg-indigo-900/50 dark:text-indigo-300"
                                            : "bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-50"
                                        : !isHighlight && "text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-50"
                                )}
                            >
                                <Icon className={cn("h-4 w-4", isHighlight && "text-indigo-600 dark:text-indigo-400")} />
                                <span>{link.label}</span>
                            </Link>
                        );
                    })}
                </div>
            </div>
        </nav>
    );
}
