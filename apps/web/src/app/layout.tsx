import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono, Calistoga } from "next/font/google";
import "./globals.css";
import AppShell from "@/components/app-shell";
import ReactQueryProvider from "@/components/ReactQueryProvider";

/**
 * YUFEED — Root Layout
 * Minimalist Modern design system
 * Fonts: Inter (body), Calistoga (display), JetBrains Mono (mono)
 */

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
  display: "swap",
});

const calistoga = Calistoga({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-calistoga",
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
  themeColor: "#fafafa",
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
      className={`${inter.variable} ${jetbrainsMono.variable} ${calistoga.variable}`}
      suppressHydrationWarning
    >
      <body className="min-h-screen bg-background text-foreground antialiased">
        <ReactQueryProvider>
          <AppShell>{children}</AppShell>
        </ReactQueryProvider>
      </body>
    </html>
  );
}
