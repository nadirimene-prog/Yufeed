"use client";

import { Search } from "lucide-react";
import { cn } from "@/lib/utils";

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onSearch: () => void;
  className?: string;
}

export default function SearchBar({
  value,
  onChange,
  onSearch,
  className,
}: SearchBarProps) {
  return (
    <div className={cn("relative w-full max-w-3xl mx-auto", className)}>
      <div className="relative">
        <Search className="absolute left-4 top-1/2 h-6 w-6 -translate-y-1/2 text-slate-400 " />
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && onSearch()}
          placeholder="Search by CELEX, title, or keywords..."
          className="h-14 w-full rounded-full border border-slate-200 bg-white pl-12 pr-4 text-lg shadow-sm transition-all focus:border-blue-500 focus:outline-none focus:ring-4 focus:ring-blue-500/10     placeholder:text-slate-400 "
        />
        <button
          onClick={onSearch}
          className="absolute right-2 top-2 h-10 rounded-full bg-blue-600 px-6 text-sm font-semibold text-white transition-colors hover:bg-blue-700  "
        >
          Search
        </button>
      </div>
    </div>
  );
}
