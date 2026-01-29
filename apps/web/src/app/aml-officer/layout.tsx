"use client";

import { usePathname } from "next/navigation";
import { CopilotWidget } from "@/components/aml-officer/copilot-widget";
import { CopilotProvider } from "@/components/aml-officer/copilot-context";

export default function AMLOfficerLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    // We can add specific logic here if we need to hide the widget on certain sub-pages
    const pathname = usePathname();

    return (
        <CopilotProvider>
            <div className="relative min-h-screen">
                {/* Main Content */}
                <main>
                    {children}
                </main>

                {/* Persistent AI Layer */}
                <CopilotWidget />
            </div>
        </CopilotProvider>
    );
}
