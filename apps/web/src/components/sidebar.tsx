"use client";

import { useMemo, useState } from "react";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import NavRail from "@/components/nav-rail";
import NavContextPanel from "@/components/nav-context-panel";
import {
  NAV_AREAS,
  getAreaById,
  getAutoAreaForPath,
  isPathInAreaItems,
} from "@/components/nav-data";

export default function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [manualAreaId, setManualAreaId] = useState<string | null>(null);

  const activeArea = useMemo(() => {
    const autoArea = getAutoAreaForPath(pathname);

    // If user manually selected an area and is on a path within that area, use it
    if (manualAreaId) {
      const manualArea = getAreaById(manualAreaId);
      if (manualArea && isPathInAreaItems(manualArea, pathname)) {
        return manualArea;
      }
    }

    return autoArea;
  }, [pathname, manualAreaId]);

  const handleSelectArea = (areaId: string) => {
    // Set manual area selection to override auto-detection
    setManualAreaId(areaId);
  };

  const toggleCollapse = () => setCollapsed((prev) => !prev);

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? 72 : 304 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className={cn(
        "relative flex h-screen flex-col border-r z-50 overflow-hidden",
        "bg-sidebar border-sidebar-border backdrop-blur-xl",
      )}
    >
      {/* Ambient gradient background */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden opacity-30">
        <div
          className="absolute -top-32 -left-32 w-64 h-64 rounded-full blur-3xl mix-blend-screen"
          style={{
            background:
              "radial-gradient(circle, var(--color-aurora-500) 0%, transparent 70%)",
          }}
        />
        <div
          className="absolute -bottom-32 -right-16 w-48 h-48 rounded-full blur-3xl mix-blend-screen"
          style={{
            background:
              "radial-gradient(circle, var(--color-cyan-500) 0%, transparent 70%)",
          }}
        />
      </div>

      <div className="relative flex h-full">
        <NavRail
          areas={NAV_AREAS}
          activeAreaId={activeArea.id}
          collapsed={collapsed}
          onSelectArea={handleSelectArea}
          onToggleCollapse={toggleCollapse}
          showStatusOnly={collapsed}
        />

        <AnimatePresence mode="wait">
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              transition={{ duration: 0.2 }}
              className="flex-1 min-w-0" // prevent flex overflow
            >
              <NavContextPanel area={activeArea} pathname={pathname} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.aside>
  );
}
