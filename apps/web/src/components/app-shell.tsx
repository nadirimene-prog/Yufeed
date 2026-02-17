"use client";

import * as React from "react";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import Sidebar from "./sidebar";
import Header from "./header";

/**
 * Horizon App Shell
 * Main application layout with sidebar, header, and content area
 */

/* ─────────────────────────────────────────────────────────────────────────────
   Skip Link for Accessibility
   ───────────────────────────────────────────────────────────────────────────── */

function SkipLink() {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[100] focus:rounded-lg focus:bg-primary focus:px-4 focus:py-2 focus:text-white"
    >
      Skip to main content
    </a>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Page Transition Wrapper
   ───────────────────────────────────────────────────────────────────────────── */

function PageTransition({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      transition={{
        duration: 0.2,
        ease: [0, 0, 0.2, 1],
      }}
    >
      {children}
    </motion.div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Breadcrumb Builder from Pathname
   ───────────────────────────────────────────────────────────────────────────── */

function useBreadcrumbs(pathname: string) {
  return React.useMemo(() => {
    const segments = pathname.split("/").filter(Boolean);
    const breadcrumbs = [{ label: "Home", href: "/dashboard" }];

    let currentPath = "";
    segments.forEach((segment) => {
      currentPath += `/${segment}`;
      breadcrumbs.push({
        label: segment
          .split("-")
          .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
          .join(" "),
        href: currentPath,
      });
    });

    return breadcrumbs;
  }, [pathname]);
}

/* ─────────────────────────────────────────────────────────────────────────────
   Main App Shell Component
   ───────────────────────────────────────────────────────────────────────────── */

interface AppShellProps {
  children: React.ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const breadcrumbs = useBreadcrumbs(pathname);
  const [mobileSidebarOpen, setMobileSidebarOpen] = React.useState(false);

  // Chromeless routes (no sidebar/header)
  const isChromeless = ["/", "/forgot-password", "/request-access"].includes(
    pathname,
  );

  if (isChromeless) {
    return (
      <div className="min-h-screen bg-bg-base">
        <PageTransition>{children}</PageTransition>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg-base">
      <SkipLink />

      {/* Sidebar - Desktop */}
      <div className="hidden lg:block">
        <Sidebar />
      </div>

      {/* Sidebar - Mobile */}
      <AnimatePresence>
        {mobileSidebarOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 z-40 bg-black/50 lg:hidden"
              onClick={() => setMobileSidebarOpen(false)}
            />
            <motion.div
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="fixed left-0 top-0 z-50 h-screen w-64 lg:hidden"
            >
              <Sidebar />
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Main Content Area */}
      <div className="lg:ml-64">
        {/* Header */}
        <Header
          onMenuClick={() => setMobileSidebarOpen(true)}
          breadcrumbs={breadcrumbs}
        />

        {/* Main Content */}
        <main
          id="main-content"
          className="min-h-[calc(100vh-3.5rem)] p-4 lg:p-6"
          tabIndex={-1}
        >
          <div className="mx-auto max-w-7xl">
            <PageTransition key={pathname}>{children}</PageTransition>
          </div>
        </main>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Layout Components for Content Organization
   ───────────────────────────────────────────────────────────────────────────── */

interface PageHeaderProps {
  title: string;
  description?: string;
  children?: React.ReactNode;
}

export function PageHeader({ title, description, children }: PageHeaderProps) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h1 className="text-2xl font-display font-semibold text-foreground">
          {title}
        </h1>
        {description && (
          <p className="mt-1 text-foreground-secondary">{description}</p>
        )}
      </div>
      {children && <div className="flex items-center gap-2">{children}</div>}
    </div>
  );
}

interface PageGridProps {
  children: React.ReactNode;
  columns?: 1 | 2 | 3 | 4;
  gap?: "sm" | "md" | "lg";
}

export function PageGrid({ children, columns = 3, gap = "md" }: PageGridProps) {
  const gapClasses = {
    sm: "gap-4",
    md: "gap-6",
    lg: "gap-8",
  }[gap];

  const columnClasses = {
    1: "grid-cols-1",
    2: "grid-cols-1 md:grid-cols-2",
    3: "grid-cols-1 md:grid-cols-2 lg:grid-cols-3",
    4: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4",
  }[columns];

  return (
    <div className={cn("grid", columnClasses, gapClasses)}>{children}</div>
  );
}

interface PageSectionProps {
  title?: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
}

export function PageSection({
  title,
  description,
  children,
  className,
}: PageSectionProps) {
  return (
    <section className={cn("space-y-4", className)}>
      {(title || description) && (
        <div>
          {title && (
            <h2 className="text-lg font-display font-semibold text-foreground">
              {title}
            </h2>
          )}
          {description && (
            <p className="text-sm text-foreground-secondary">{description}</p>
          )}
        </div>
      )}
      {children}
    </section>
  );
}
