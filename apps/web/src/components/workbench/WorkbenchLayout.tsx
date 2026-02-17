"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity,
  BrainCircuit,
  ChevronLeft,
  ChevronRight,
  Maximize2,
  Search,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { SentinelHUD } from "./SentinelHUD";

interface WorkbenchLayoutProps {
  discoveryRail?: React.ReactNode;
  workspace?: React.ReactNode;
  intelligencePanel?: React.ReactNode;
  title?: string;
  activeId?: string; // ID for shared element transitions
}

export function WorkbenchLayout({
  discoveryRail,
  workspace,
  intelligencePanel,
  title = "Sentinel Workbench",
  activeId,
}: WorkbenchLayoutProps) {
  const [isDiscoveryExpanded, setIsDiscoveryExpanded] = useState(true);
  const [isIntelligenceExpanded, setIsIntelligenceExpanded] = useState(true);
  const [isFlowing, setIsFlowing] = useState(false);
  const [isDesktop, setIsDesktop] = useState(false);

  useEffect(() => {
    const media = window.matchMedia("(min-width: 1280px)");
    const apply = () => setIsDesktop(media.matches);

    apply();
    if (media.addEventListener) {
      media.addEventListener("change", apply);
      return () => media.removeEventListener("change", apply);
    }
    media.addListener(apply);
    return () => media.removeListener(apply);
  }, []);

  // Trigger wayfinding particles when activeId changes
  useEffect(() => {
    if (activeId) {
      // Use requestAnimationFrame to avoid synchronous setState during render warning
      const rafId = requestAnimationFrame(() => {
        setIsFlowing(true);
      });
      const timer = setTimeout(() => setIsFlowing(false), 2000);
      return () => {
        cancelAnimationFrame(rafId);
        clearTimeout(timer);
      };
    }
  }, [activeId]);

  return (
    <div className="flex flex-col min-h-[calc(100vh-theme(spacing.24))] w-full gap-2 p-2 md:p-4">
      {/* Global HUD */}
      <SentinelHUD />

      <div
        className={cn(
          "flex flex-1 w-full gap-4",
          isDesktop ? "flex-row overflow-hidden" : "flex-col overflow-visible",
        )}
      >
        {/* Discovery Rail (Left) */}
        <AnimatePresence initial={false}>
          <motion.aside
            layout
            initial={false}
            animate={{
              width: isDesktop ? (isDiscoveryExpanded ? 320 : 64) : "100%",
              height: isDesktop ? "auto" : isDiscoveryExpanded ? 260 : 56,
              opacity: 1,
            }}
            className={cn(
              "order-2 xl:order-1 relative flex flex-col overflow-hidden rounded-2xl border border-white/10 bg-void-925/40 backdrop-blur-xl transition-colors duration-300 hover:border-white/20",
              !isDiscoveryExpanded && "items-center",
            )}
          >
            <div className="flex h-12 items-center justify-between px-4 shrink-0">
              {isDiscoveryExpanded && (
                <span className="text-xs font-semibold uppercase tracking-widest text-white/60">
                  Discovery Rail
                </span>
              )}
              <button
                onClick={() => setIsDiscoveryExpanded(!isDiscoveryExpanded)}
                className="rounded-lg p-1.5 text-white/40 hover:bg-white/5 hover:text-white"
              >
                {isDiscoveryExpanded ? (
                  <ChevronLeft size={16} />
                ) : (
                  <Activity size={16} />
                )}
              </button>
            </div>

            <div
              className={cn(
                "flex-1 overflow-y-auto px-4 py-2",
                !isDiscoveryExpanded && "hidden",
              )}
            >
              {discoveryRail || (
                <div className="flex flex-col gap-4">
                  <div className="relative">
                    <Search
                      className="absolute left-3 top-1/2 -translate-y-1/2 text-white/20"
                      size={14}
                    />
                    <input
                      type="text"
                      placeholder="Search signals..."
                      className="w-full rounded-xl border border-white/5 bg-white/5 py-2 pl-9 pr-4 text-xs text-white placeholder:text-white/20 focus:border-aurora-500 focus:outline-none"
                    />
                  </div>
                  {/* Placeholder content for visualization */}
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div
                      key={i}
                      className="animate-pulse rounded-xl bg-white/5 p-4 h-24"
                    />
                  ))}
                </div>
              )}
            </div>
          </motion.aside>
        </AnimatePresence>

        {/* Flow Particles Overlay */}
        <AnimatePresence>
          {isFlowing && (
            <div className="absolute inset-0 pointer-events-none z-50 overflow-hidden">
              {[...Array(6)].map((_, i) => (
                <motion.div
                  key={i}
                  initial={{
                    x: isDiscoveryExpanded ? 160 : 32,
                    y: 200 + i * 40,
                    opacity: 0,
                    scale: 0,
                  }}
                  animate={{
                    x: [null, 600, 1000],
                    y: [null, 150 + i * 20, 100],
                    opacity: [0, 0.8, 0],
                    scale: [0, 1, 0.5],
                  }}
                  transition={{
                    duration: 1.5,
                    delay: i * 0.1,
                    ease: "circOut",
                  }}
                  className="absolute"
                >
                  <div className="h-1.5 w-1.5 rounded-full bg-cyan-400 shadow-[0_0_12px_rgba(34,211,238,0.8)]" />
                </motion.div>
              ))}
            </div>
          )}
        </AnimatePresence>

        {/* Main Workspace (Center) */}
        <main
          className={cn(
            "order-1 xl:order-2 relative flex flex-1 flex-col rounded-2xl border border-white/10 bg-void-925/20 backdrop-blur-md shadow-2xl",
            isDesktop ? "overflow-hidden" : "overflow-visible min-h-[420px]",
          )}
        >
          <header className="flex h-12 items-center justify-between border-b border-white/5 px-6 shrink-0">
            <div className="flex items-center gap-3">
              <h2 className="text-sm font-semibold text-white/90">{title}</h2>
              <motion.div
                animate={
                  isFlowing ? { scale: [1, 1.5, 1], rotate: [0, 180, 360] } : {}
                }
                className="h-1.5 w-1.5 rounded-full bg-cyan-500 shadow-[0_0_8px_rgba(0,212,255,0.6)]"
              />
            </div>
            <div className="flex items-center gap-2">
              <button className="rounded-lg p-1.5 text-white/40 hover:bg-white/5 hover:text-white">
                <Maximize2 size={14} />
              </button>
            </div>
          </header>

          <div className="flex-1 overflow-y-auto p-6">
            {workspace || (
              <div className="flex h-full items-center justify-center space-y-4">
                <div className="text-center">
                  <BrainCircuit
                    size={48}
                    className="mx-auto mb-4 text-white/10"
                  />
                  <p className="text-sm text-white/40">
                    Select a signal from the discovery rail to begin
                    investigation.
                  </p>
                </div>
              </div>
            )}
          </div>
        </main>

        {/* Intelligence Panel (Right) */}
        <AnimatePresence initial={false}>
          <motion.aside
            layout
            initial={false}
            animate={{
              width: isDesktop ? (isIntelligenceExpanded ? 380 : 64) : "100%",
              height: isDesktop ? "auto" : isIntelligenceExpanded ? 300 : 56,
              opacity: 1,
            }}
            className={cn(
              "order-3 relative flex flex-col overflow-hidden rounded-2xl border border-white/10 bg-void-925/40 backdrop-blur-xl transition-colors duration-300 hover:border-white/20",
              !isIntelligenceExpanded && "items-center",
            )}
          >
            <div className="flex h-12 items-center justify-between px-4">
              <button
                onClick={() =>
                  setIsIntelligenceExpanded(!isIntelligenceExpanded)
                }
                className="rounded-lg p-1.5 text-white/40 hover:bg-white/5 hover:text-white"
              >
                {isIntelligenceExpanded ? (
                  <ChevronRight size={16} />
                ) : (
                  <BrainCircuit size={16} />
                )}
              </button>
              {isIntelligenceExpanded && (
                <span className="text-xs font-semibold uppercase tracking-widest text-white/60">
                  Intelligence
                </span>
              )}
            </div>

            <div
              className={cn(
                "flex-1 overflow-y-auto px-6 py-4",
                !isIntelligenceExpanded && "hidden",
              )}
            >
              {intelligencePanel || (
                <div className="space-y-6">
                  <div className="rounded-xl border border-aurora-500/20 bg-aurora-500/5 p-4 shadow-[0_0_20px_rgba(109,90,205,0.1)]">
                    <div className="mb-2 flex items-center gap-2">
                      <BrainCircuit size={16} className="text-aurora-400" />
                      <span className="text-xs font-semibold text-aurora-400">
                        AI Officer Insights
                      </span>
                    </div>
                    <p className="text-xs text-white/60 leading-relaxed">
                      Analyzing existing signal patterns and cross-referencing
                      with recent EU AML regulations...
                    </p>
                  </div>

                  <div className="space-y-3">
                    <h4 className="text-[10px] font-bold uppercase tracking-widest text-white/40">
                      Contextual Entities
                    </h4>
                    {[1, 2].map((i) => (
                      <div
                        key={i}
                        className="rounded-xl bg-white/5 border border-white/5 p-3 h-16"
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.aside>
        </AnimatePresence>
      </div>
    </div>
  );
}

export default WorkbenchLayout;
