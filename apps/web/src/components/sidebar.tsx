"use client";

import { useMemo, useState } from "react";
import { usePathname } from "next/navigation";
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
        const workArea = getAreaById("work");
        const isWorkPath = workArea ? isPathInAreaItems(workArea, pathname) : false;

        if (manualAreaId === "work" && isWorkPath && workArea) {
            return workArea;
        }

        return autoArea;
    }, [pathname, manualAreaId]);

    const handleSelectArea = (areaId: string) => {
        if (areaId === "work") {
            setManualAreaId("work");
            return;
        }
        setManualAreaId(null);
    };

    const toggleCollapse = () => setCollapsed((prev) => !prev);

    return (
        <aside
            className={cn(
                "relative flex h-screen flex-col border-r transition-all duration-300 ease-out z-50",
                "bg-[#0a0a12]/95 backdrop-blur-xl border-white/[0.06]",
                collapsed ? "w-[72px]" : "w-[304px]"
            )}
        >
            {/* Ambient gradient background */}
            <div className="absolute inset-0 pointer-events-none overflow-hidden">
                <div
                    className="absolute -top-32 -left-32 w-64 h-64 rounded-full opacity-20 blur-3xl"
                    style={{ background: "radial-gradient(circle, #6d5acd 0%, transparent 70%)" }}
                />
                <div
                    className="absolute -bottom-32 -right-16 w-48 h-48 rounded-full opacity-10 blur-3xl"
                    style={{ background: "radial-gradient(circle, #00d4ff 0%, transparent 70%)" }}
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

                {!collapsed && (
                    <NavContextPanel
                        area={activeArea}
                        pathname={pathname}
                    />
                )}
            </div>
        </aside>
    );
}
