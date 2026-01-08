import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/navbar";
import { cn } from "@/lib/utils";

const inter = Inter({ subsets: ["latin"] });

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
        <html lang="en" className="antialiased">
            <body className={cn(inter.className, "min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100")}>
                <Navbar />
                <main className="container mx-auto py-6 px-4">
                    {children}
                </main>
            </body>
        </html>
    );
}
