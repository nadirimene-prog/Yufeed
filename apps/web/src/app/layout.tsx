import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Space_Grotesk } from "next/font/google";
import "./globals.css";
import Header from "@/components/header";
import Sidebar from "@/components/sidebar";
import { cn } from "@/lib/utils";
import ToastProvider from "@/components/ToastProvider";
import { CommandMenu } from "@/components/command-menu";
import { WebSocketProvider } from "@/components/WebSocketProvider";

/**
 * ═══════════════════════════════════════════════════════════════════
 * YUFEED SENTINEL - Typography Configuration
 * ═══════════════════════════════════════════════════════════════════
 */

// Primary body font - clean, technical, excellent readability
const inter = Inter({
    subsets: ["latin"],
    variable: "--font-geist", // Using as primary sans
    display: "swap",
});

// Display font - geometric, strong presence for headlines
const spaceGrotesk = Space_Grotesk({
    subsets: ["latin"],
    variable: "--font-space-grotesk",
    display: "swap",
    weight: ["400", "500", "600", "700"],
});

// Monospace font - for data, numbers, code
const jetbrainsMono = JetBrains_Mono({
    subsets: ["latin"],
    variable: "--font-jetbrains",
    display: "swap",
});

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
                    inter.variable,
                    spaceGrotesk.variable,
                    jetbrainsMono.variable,
                    "flex h-screen overflow-hidden bg-background text-foreground font-sans antialiased"
                )}
            >
                {/* Ambient Canvas - Living Background */}
                <div className="ambient-canvas" aria-hidden="true" />

                <WebSocketProvider>
                    <CommandMenu />
                    <Sidebar />
                    <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden z-10">
                        <Header />
                        <main className="container mx-auto py-6 px-4 md:px-8 max-w-7xl">
                            {children}
                        </main>
                    </div>
                    <ToastProvider />
                </WebSocketProvider>
            </body>
        </html>
    );
}
