import type { Metadata, Viewport } from "next";
import { Geist, JetBrains_Mono, Space_Grotesk } from "next/font/google";
import "./globals-new.css";
import AppShell from "@/components/app-shell-new";

/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * YUFEED HORIZON — Root Layout
 * Modern typography, optimized performance, accessibility-first
 * ═══════════════════════════════════════════════════════════════════════════════
 */

/* ─────────────────────────────────────────────────────────────────────────────
   Font Configuration
   ───────────────────────────────────────────────────────────────────────────── */

const geist = Geist({
  subsets: ["latin"],
  variable: "--font-geist",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  display: "swap",
});

/* ─────────────────────────────────────────────────────────────────────────────
   Metadata Configuration
   ───────────────────────────────────────────────────────────────────────────── */

export const metadata: Metadata = {
  title: {
    default: "YuFeed Sentinel | Compliance Command Center",
    template: "%s | YuFeed Sentinel",
  },
  description:
    "AI-powered EU legal monitoring and AML compliance platform. Real-time regulatory intelligence, transaction monitoring, and investigation workflows.",
  keywords: [
    "compliance",
    "AML",
    "regulatory",
    "EU law",
    "CELEX",
    "transaction monitoring",
    "KYC",
    "SAR",
  ],
  authors: [{ name: "YuFeed" }],
  creator: "YuFeed",
  metadataBase: new URL("https://yufeed.io"),
  openGraph: {
    type: "website",
    locale: "en_US",
    title: "YuFeed Sentinel | Compliance Command Center",
    description: "AI-powered EU legal monitoring and AML compliance platform.",
    siteName: "YuFeed Sentinel",
  },
  twitter: {
    card: "summary_large_image",
    title: "YuFeed Sentinel | Compliance Command Center",
    description: "AI-powered EU legal monitoring and AML compliance platform.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#0a0a0f" },
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
  ],
};

/* ─────────────────────────────────────────────────────────────────────────────
   Root Layout
   ───────────────────────────────────────────────────────────────────────────── */

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geist.variable} ${jetbrainsMono.variable} ${spaceGrotesk.variable}`}
      suppressHydrationWarning
    >
      <body className="min-h-screen bg-bg-base text-foreground antialiased">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
