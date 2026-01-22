"use client";

import { Bell, HelpCircle, Search, User, ChevronRight } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

export default function Header() {
    const pathname = usePathname();
    // Simple breadcrumb logic: split path and capitalize
    const breadcrumbs = pathname
        .split("/")
        .filter(Boolean)
        .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1));

    return (
        <header className="sticky top-0 z-40 w-full border-b border-sidebar-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="flex h-16 items-center px-4 md:px-8 gap-4">
                {/* Left: Breadcrumbs */}
                <div className="flex items-center gap-2 text-sm text-muted-foreground min-w-0">
                    <Link href="/dashboard" className="hover:text-foreground transition-colors hidden md:block">
                        Home
                    </Link>
                    {breadcrumbs.length > 0 && <ChevronRight className="h-4 w-4 hidden md:block" />}

                    <div className="flex items-center gap-1 font-medium text-foreground truncate">
                        {breadcrumbs.length > 0 ? (
                            breadcrumbs.map((crumb, index) => (
                                <span key={crumb} className="flex items-center gap-1">
                                    {index > 0 && <ChevronRight className="h-4 w-4" />}
                                    {crumb}
                                </span>
                            ))
                        ) : (
                            <span>Dashboard</span>
                        )}
                    </div>
                </div>

                {/* Center: Global Search (Compact) */}
                <div className="flex-1 flex justify-center max-w-xl mx-auto">
                    <div className="relative w-full">
                        <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                        <input
                            type="text"
                            placeholder="Search documents, entities, or alerts..."
                            className="h-9 w-full rounded-md border border-input bg-muted/50 pl-9 pr-4 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                        />
                    </div>
                </div>

                {/* Right: Actions */}
                <div className="flex items-center gap-4">
                    <button className="relative rounded-full p-2 hover:bg-muted transition-colors text-muted-foreground hover:text-foreground">
                        <Bell className="h-5 w-5" />
                        <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-red-600 border border-background" />
                    </button>

                    <button
                        onClick={() => document.documentElement.classList.toggle('dark')}
                        className="rounded-full p-2 hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
                        title="Toggle Dark Mode"
                    >
                        {/* Simple Sun/Moon icon toggle approach for now - pure CSS/SVG would be ideal but JS toggle is fine for MVP */}
                        <div className="dark:hidden">
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="5" /><path d="M12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4" /></svg>
                        </div>
                        <div className="hidden dark:block">
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" /></svg>
                        </div>
                    </button>

                    <div className="h-6 w-px bg-border mx-1" />

                    <button className="flex items-center gap-2 rounded-full pl-2 pr-4 py-1 hover:bg-muted transition-colors">
                        <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                            <User className="h-4 w-4" />
                        </div>
                        <div className="hidden md:block text-left">
                            <p className="text-sm font-medium leading-none">Admin User</p>
                            <p className="text-xs text-muted-foreground">admin@yufeed.eu</p>
                        </div>
                    </button>
                </div>
            </div>
        </header>
    );
}
