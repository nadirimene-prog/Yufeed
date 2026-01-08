"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Scale, Search, List, Bell, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

export default function Navbar() {
    const pathname = usePathname();

    const links = [
        { href: "/search", label: "Search", icon: Search },
        { href: "/query", label: "Ask AI", icon: Sparkles },
        { href: "/watchlists", label: "Watchlists", icon: List },
        { href: "/alerts", label: "Alerts", icon: Bell },
    ];

    return (
        <nav className="sticky top-0 z-50 w-full border-b border-gray-200 bg-white/80 backdrop-blur-md dark:border-gray-800 dark:bg-gray-950/80">
            <div className="container mx-auto flex h-16 items-center px-4">
                <Link href="/" className="mr-8 flex items-center space-x-2">
                    <Scale className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                    <span className="hidden font-bold sm:inline-block text-gray-900 dark:text-gray-100">
                        EU Monitor
                    </span>
                </Link>
                <div className="flex items-center space-x-4">
                    {links.map((link) => {
                        const isActive = pathname.startsWith(link.href);
                        const Icon = link.icon;
                        return (
                            <Link
                                key={link.href}
                                href={link.href}
                                className={cn(
                                    "flex items-center space-x-2 rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-gray-100 dark:hover:bg-gray-800",
                                    isActive
                                        ? "bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-50"
                                        : "text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-50"
                                )}
                            >
                                <Icon className="h-4 w-4" />
                                <span>{link.label}</span>
                            </Link>
                        );
                    })}
                </div>
            </div>
        </nav>
    );
}
