"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Scale,
  Search,
  List,
  Bell,
  Brain,
  FileText,
  Network,
  Zap,
} from "lucide-react";
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
    <nav className="sticky top-0 z-50 w-full border-b border-slate-200 bg-white/80 backdrop-blur-md  ">
      <div className="container mx-auto flex h-16 items-center px-4">
        <Link href="/" className="mr-8 flex items-center space-x-2">
          <Scale className="h-6 w-6 text-blue-600 " />
          <span className="hidden font-bold sm:inline-block text-slate-900 ">
            YuFeed Risk OS
          </span>
        </Link>
        <div className="flex items-center space-x-4">
          {links.map((link) => {
            const isActive = pathname.startsWith(link.href);
            const Icon = link.icon;
            const isHighlight = "highlight" in link && link.highlight;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "flex items-center space-x-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isHighlight && !isActive
                    ? "bg-indigo-50 text-indigo-700 hover:bg-indigo-100   "
                    : "hover:bg-slate-100 ",
                  isActive
                    ? isHighlight
                      ? "bg-indigo-100 text-indigo-900  "
                      : "bg-slate-100 text-slate-900  "
                    : !isHighlight && "text-slate-600 hover:text-slate-900  ",
                )}
              >
                <Icon
                  className={cn("h-4 w-4", isHighlight && "text-indigo-600 ")}
                />
                <span>{link.label}</span>
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
