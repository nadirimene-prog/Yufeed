import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import Header from "@/components/header";
import Sidebar from "@/components/sidebar";
import { cn } from "@/lib/utils";
import ToastProvider from "@/components/ToastProvider";
import { CommandMenu } from "@/components/command-menu";

const inter = Inter({
    subsets: ["latin"],
    variable: "--font-sans",
});

const jetbrainsMono = JetBrains_Mono({
    subsets: ["latin"],
    variable: "--font-mono",
});

export const metadata: Metadata = {
    title: "EU Legal Monitor",
    description: "Monitor EU regulations, directives, and decisions.",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en" className="antialiased" suppressHydrationWarning>
            <body className={cn(
                inter.variable,
                jetbrainsMono.variable,
                "flex h-screen overflow-hidden bg-background text-foreground font-sans"
            )}>
                <CommandMenu />
                <Sidebar />
                <div className="relative flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
                    <Header />
                    <main className="container mx-auto py-6 px-4 md:px-8 max-w-7xl">
                        {children}
                    </main>
                </div>
                <ToastProvider />
            </body>
        </html>
    );
}
