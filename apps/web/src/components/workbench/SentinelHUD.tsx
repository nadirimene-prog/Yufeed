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
}

export function SentinelHUD({
  latencyMs = null,
  signalsPerSecond = null,
  complianceBadge = "SOC2 Verified",
}: SentinelHUDProps) {
  const [pulseScale, setPulseScale] = useState(1);
  const profile = React.useMemo(() => getAuthUserProfile(), []);

  // Artificial AI "Heartbeat" effect
  useEffect(() => {
    const interval = setInterval(() => {
      setPulseScale((s) => (s === 1 ? 1.4 : 1));
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex h-11 w-full items-center justify-between px-6 bg-void-950/20 backdrop-blur-md border border-white/5 rounded-2xl mb-4 group hover:bg-void-950/40 transition-colors duration-500">
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
              className="absolute h-3 w-3 rounded-full bg-cyan-400"
            />
            <div className="relative h-2 w-2 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.8)]" />
          </div>
          <div className="flex flex-col">
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-cyan-400/80">
              Sentinel AI
            </span>
            <span className="text-[9px] text-white/30 font-medium">
              Core Active •{" "}
              {latencyMs != null ? `Latency ${latencyMs}ms` : "Latency live"}
            </span>
          </div>
        </div>

        <div className="h-4 w-px bg-white/10" />

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-aurora-500/5 border border-aurora-500/10">
            <ShieldCheck size={10} className="text-aurora-400" />
            <span className="text-[10px] font-semibold text-aurora-400">
              {complianceBadge}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <Zap size={10} className="text-emerald-400" />
            <span className="text-[10px] font-medium text-white/40">
              {signalsPerSecond != null
                ? `${signalsPerSecond.toLocaleString()} signals/sec`
                : "Signals live"}
            </span>
          </div>
        </div>
      </div>

      {/* Center: Search / Context Bridge (Minimalist) */}
      <div className="hidden md:flex items-center bg-white/5 border border-white/5 rounded-lg px-3 py-1 gap-2 w-1/3 group/search hover:border-white/10 transition-all">
        <Search
          size={12}
          className="text-white/20 group-hover/search:text-white/40"
        />
        <span className="text-[11px] text-white/20 flex-1">
          Filter across context bridge...
        </span>
        <div className="flex items-center gap-1">
          <kbd className="px-1.5 py-0.5 rounded bg-white/5 border border-white/10 text-[9px] text-white/40 font-sans">
            ⌘
          </kbd>
          <kbd className="px-1.5 py-0.5 rounded bg-white/5 border border-white/10 text-[9px] text-white/40 font-sans">
            K
          </kbd>
        </div>
      </div>

      {/* Right Area: Alerts & Active User */}
      <div className="flex items-center gap-5">
        <div className="flex items-center gap-4 text-white/30">
          <button className="hover:text-white transition-colors">
            <Bell size={14} />
          </button>
          <button className="hover:text-white transition-colors">
            <Info size={14} />
          </button>
        </div>

        <div className="h-4 w-px bg-white/10" />

        <div className="flex items-center gap-2 pl-2 cursor-pointer group/user">
          <div className="h-6 w-6 rounded-full bg-gradient-to-tr from-aurora-500 to-cyan-500 p-[1px]">
            <div className="h-full w-full rounded-full bg-void-925 flex items-center justify-center text-[9px] font-bold text-white">
              {profile?.initials ?? "YU"}
            </div>
          </div>
          <span className="text-[11px] font-medium text-white/60 group-hover/user:text-white transition-colors">
            {profile?.displayName ?? "Workspace User"}
          </span>
          <ChevronDown
            size={12}
            className="text-white/20 group-hover/user:text-white"
          />
        </div>
      </div>
    </div>
  );
}

export default SentinelHUD;
