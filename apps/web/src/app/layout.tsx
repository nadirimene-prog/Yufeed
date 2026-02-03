import type { Metadata } from "next";
import "./globals.css";
import { cn } from "@/lib/utils";
import AppShell from "@/components/app-shell";

/**
 * ═══════════════════════════════════════════════════════════════════
 * YUFEED SENTINEL - Typography Configuration
 * ═══════════════════════════════════════════════════════════════════
 */

export const metadata: Metadata = {
    title: "YuFeed Sentinel | Compliance Command Center",
    description: "AI-powered EU legal monitoring & AML compliance platform. Real-time regulatory intelligence, transaction monitoring, and investigation workflows.",
    keywords: ["compliance", "AML", "regulatory", "EU law", "CELEX", "transaction monitoring"],
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en" suppressHydrationWarning>
            <body
                className={cn(
                    "flex h-screen overflow-hidden bg-background text-foreground font-sans antialiased"
                )}
            >
                {/* Ambient Canvas - Living Background */}
                <div className="ambient-canvas" aria-hidden="true" />

                <AppShell>{children}</AppShell>
            </body>
        </html>
    );
}
