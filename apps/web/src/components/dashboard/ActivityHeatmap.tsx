"use client";

import React from "react";
import { motion } from "framer-motion";
import { Globe, Info } from "lucide-react";
import { cn } from "@/lib/utils";

interface RegionData {
  id: string;
  name: string;
  intensity: number; // 0 to 1
  findings: number;
}

const regions: RegionData[] = [
  { id: "eu", name: "European Union", intensity: 0.8, findings: 124 },
  { id: "fr", name: "France (AMF)", intensity: 0.9, findings: 89 },
  { id: "us", name: "United States (FINCEN)", intensity: 0.4, findings: 32 },
  { id: "uk", name: "United Kingdom (FCA)", intensity: 0.6, findings: 56 },
  { id: "sg", name: "Singapore (MAS)", intensity: 0.3, findings: 12 },
];

export function ActivityHeatmap() {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Globe size={14} className="text-cyan-400" />
          <h3 className="text-xs font-bold uppercase tracking-widest text-white/80">
            Regional Pulse
          </h3>
        </div>
        <div className="flex items-center gap-1.5 rounded-full bg-white/5 px-2 py-0.5 border border-white/5">
          <span className="relative flex h-1.5 w-1.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
          </span>
          <span className="text-[9px] font-mono text-white/40">LIVE</span>
        </div>
      </div>

      <div className="relative aspect-[16/9] w-full rounded-xl bg-void-950/40 border border-white/5 overflow-hidden group">
        {/* Simple Abstract SVG Map */}
        <svg viewBox="0 0 400 200" className="h-full w-full">
          <defs>
            <filter id="glow">
              <feGaussianBlur stdDeviation="2.5" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Abstract landmasses as simple paths */}
          <path
            d="M 50 100 Q 80 50 120 80 T 180 60 T 250 100 T 320 70 T 380 120"
            fill="none"
            stroke="white"
            strokeWidth="0.5"
            strokeOpacity="0.1"
            strokeDasharray="2 4"
          />

          {/* Region Hotspots */}
          {regions.map((region, i) => {
            const x = 80 + i * 60;
            const y = 60 + Math.sin(i) * 30;
            return (
              <g key={region.id} className="cursor-pointer group/spot">
                <motion.circle
                  initial={{ r: 0 }}
                  animate={{ r: 4 + region.intensity * 8 }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    repeatType: "reverse",
                    delay: i * 0.2,
                  }}
                  cx={x}
                  cy={y}
                  fill={
                    region.intensity > 0.7
                      ? "var(--color-risk-critical)"
                      : "var(--color-aurora-500)"
                  }
                  fillOpacity={0.2 * region.intensity}
                  filter="url(#glow)"
                />
                <circle
                  cx={x}
                  cy={y}
                  r="2"
                  fill={
                    region.intensity > 0.7
                      ? "var(--color-risk-critical)"
                      : "var(--color-aurora-500)"
                  }
                />
              </g>
            );
          })}
        </svg>

        {/* Legend Overlay */}
        <div className="absolute bottom-3 left-3 flex flex-col gap-1.5">
          {regions.slice(0, 3).map((region) => (
            <div key={region.id} className="flex items-center gap-2">
              <div
                className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  region.intensity > 0.7
                    ? "bg-risk-critical shadow-[0_0_6px_rgba(255,51,102,0.4)]"
                    : "bg-aurora-500 shadow-[0_0_6px_rgba(109,90,205,0.4)]",
                )}
              />
              <span className="text-[10px] text-white/50 font-medium">
                {region.name}
              </span>
              <span className="text-[9px] font-mono text-cyan-400">
                +{region.findings}
              </span>
            </div>
          ))}
        </div>

        {/* Hover Interaction Overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-void-950/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-4">
          <div className="flex items-center gap-2 text-[10px] text-white/60">
            <Info size={12} />
            <span>Click region for detailed cross-border analysis</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ActivityHeatmap;
