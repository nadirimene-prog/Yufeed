"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  ShieldCheck,
  Zap,
  Search,
  Bell,
  Info,
  ChevronDown,
} from "lucide-react";
import { getAuthUserProfile } from "@/lib/auth";

interface SentinelHUDProps {
  latencyMs?: number | null;
  signalsPerSecond?: number | null;
  complianceBadge?: string;
  animateStatus?: boolean;
}

export function SentinelHUD({
  latencyMs = null,
  signalsPerSecond = null,
  complianceBadge = "SOC2 Verified",
  animateStatus = false,
}: SentinelHUDProps) {
  const [pulseScale, setPulseScale] = useState(1);
  const profile = React.useMemo(() => getAuthUserProfile(), []);

  useEffect(() => {
    if (!animateStatus) return;
    const interval = setInterval(() => {
      setPulseScale((s) => (s === 1 ? 1.4 : 1));
    }, 2000);
    return () => clearInterval(interval);
  }, [animateStatus]);

  return (
    <div className="flex h-11 w-full items-center justify-between px-6 bg-white border border-[#E2E8F0] rounded-2xl mb-4 group hover:bg-slate-50 transition-colors duration-500 shadow-sm">
      {/* Left Area: AI Heartbeat & Status */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center">
            <motion.div
              animate={{
                scale: pulseScale,
                opacity: pulseScale === 1 ? 0.3 : 0,
              }}
              transition={{ duration: 1 }}
              className="absolute h-3 w-3 rounded-full bg-[#4D7CFF]"
            />
            <div className="relative h-2 w-2 rounded-full bg-[#4D7CFF] shadow-sm" />
          </div>
          <div className="flex flex-col">
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#0052FF]">
              Yufeed AI
            </span>
            <span className="text-[9px] text-slate-400 font-medium">
              Core Active •{" "}
              {latencyMs != null ? `Latency ${latencyMs}ms` : "Latency live"}
            </span>
          </div>
        </div>

        <div className="h-4 w-px bg-slate-200" />

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-[#0052FF]/5 border border-[#0052FF]/10">
            <ShieldCheck size={10} className="text-[#0052FF]" />
            <span className="text-[10px] font-semibold text-[#0052FF]">
              {complianceBadge}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <Zap size={10} className="text-emerald-500" />
            <span className="text-[10px] font-medium text-slate-500">
              {signalsPerSecond != null
                ? `${signalsPerSecond.toLocaleString()} signals/sec`
                : "Signals live"}
            </span>
          </div>
        </div>
      </div>

      {/* Center: Search / Context Bridge (Minimalist) */}
      <div className="hidden md:flex items-center bg-slate-100 border border-[#E2E8F0] rounded-lg px-3 py-1 gap-2 w-1/3 group/search hover:border-slate-300 transition-all">
        <Search
          size={12}
          className="text-slate-400 group-hover/search:text-slate-500"
        />
        <span className="text-[11px] text-slate-400 flex-1">
          Filter across context bridge...
        </span>
        <div className="flex items-center gap-1">
          <kbd className="px-1.5 py-0.5 rounded bg-white border border-[#E2E8F0] text-[9px] text-slate-400 font-sans">
            ⌘
          </kbd>
          <kbd className="px-1.5 py-0.5 rounded bg-white border border-[#E2E8F0] text-[9px] text-slate-400 font-sans">
            K
          </kbd>
        </div>
      </div>

      {/* Right Area: Alerts & Active User */}
      <div className="flex items-center gap-5">
        <div className="flex items-center gap-4 text-slate-400">
          <button className="hover:text-slate-700 transition-colors">
            <Bell size={14} />
          </button>
          <button className="hover:text-slate-700 transition-colors">
            <Info size={14} />
          </button>
        </div>

        <div className="h-4 w-px bg-slate-200" />

        <div className="flex items-center gap-2 pl-2 cursor-pointer group/user">
          <div className="h-6 w-6 rounded-full bg-gradient-to-tr from-[#0052FF] to-[#4D7CFF] p-[1px]">
            <div className="h-full w-full rounded-full bg-white flex items-center justify-center text-[9px] font-bold text-[#0052FF]">
              {profile?.initials ?? "YU"}
            </div>
          </div>
          <span className="text-[11px] font-medium text-slate-600 group-hover/user:text-slate-900 transition-colors">
            {profile?.displayName ?? "Workspace User"}
          </span>
          <ChevronDown
            size={12}
            className="text-slate-400 group-hover/user:text-slate-700"
          />
        </div>
      </div>
    </div>
  );
}

export default SentinelHUD;
