"use client";

import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import Header from "@/components/header";
import Sidebar from "@/components/sidebar";
import ToastProvider from "@/components/ToastProvider";
import { CommandMenu } from "@/components/command-menu";
import { WebSocketProvider } from "@/components/WebSocketProvider";

const CHROMELESS_ROUTES = new Set(["/", "/forgot-password", "/request-access"]);

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isChromeless = CHROMELESS_ROUTES.has(pathname);

  return (
    <WebSocketProvider enabled={!isChromeless}>
      {!isChromeless && <CommandMenu />}
      {!isChromeless && <Sidebar />}

      <div
        className={cn(
          "relative z-10 flex flex-1 flex-col overflow-y-auto overflow-x-hidden",
          isChromeless && "w-full"
        )}
      >
        {!isChromeless && <Header />}
        <main
          className={cn(
            isChromeless
              ? "mx-auto w-full max-w-6xl px-6 py-10 md:px-10"
              : "container mx-auto py-6 px-4 md:px-8 max-w-7xl"
          )}
        >
          {children}
        </main>
      </div>

      {!isChromeless && <ToastProvider />}
    </WebSocketProvider>
  );
}
