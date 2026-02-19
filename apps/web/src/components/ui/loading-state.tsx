"use client";

import * as React from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface LoadingStateProps extends React.HTMLAttributes<HTMLDivElement> {
  message?: string;
  type?: "fullscreen" | "inline" | "spinner";
}

export const LoadingState = React.forwardRef<HTMLDivElement, LoadingStateProps>(
  ({ message = "Loading...", type = "inline", className, ...props }, ref) => {
    if (type === "fullscreen") {
      return (
        <div
          ref={ref}
          role="status"
          aria-live="polite"
          className={cn(
            "flex min-h-screen items-center justify-center bg-bg-base text-foreground",
            className,
          )}
          {...props}
        >
          <div className="text-center">
            <Loader2
              className="mx-auto mb-4 h-12 w-12 animate-spin text-primary"
              aria-hidden="true"
            />
            <p className="text-lg text-foreground-secondary">{message}</p>
          </div>
        </div>
      );
    }

    if (type === "spinner") {
      return (
        <div
          ref={ref}
          role="status"
          aria-live="polite"
          className={cn("flex items-center justify-center", className)}
          {...props}
        >
          <Loader2
            className="h-6 w-6 animate-spin text-primary"
            aria-hidden="true"
          />
          <span className="sr-only">{message}</span>
        </div>
      );
    }

    return (
      <div
        ref={ref}
        role="status"
        aria-live="polite"
        className={cn("flex items-center gap-2", className)}
        {...props}
      >
        <Loader2
          className="h-5 w-5 animate-spin text-primary"
          aria-hidden="true"
        />
        <span className="text-foreground-secondary">{message}</span>
      </div>
    );
  },
);

LoadingState.displayName = "LoadingState";

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3" role="status" aria-live="polite">
      {Array.from({ length: rows }).map((_, index) => (
        <div
          key={index}
          className="h-12 w-full overflow-hidden rounded-lg bg-bg-overlay"
        >
          <div className="h-full w-full animate-shimmer" />
        </div>
      ))}
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div
      className="space-y-4 rounded-lg border border-border-subtle bg-bg-elevated p-6"
      role="status"
      aria-live="polite"
    >
      <div className="h-6 w-3/4 overflow-hidden rounded bg-bg-overlay">
        <div className="h-full w-full animate-shimmer" />
      </div>
      <div className="h-4 w-1/2 overflow-hidden rounded bg-bg-overlay">
        <div className="h-full w-full animate-shimmer" />
      </div>
      <div className="h-4 w-5/6 overflow-hidden rounded bg-bg-overlay">
        <div className="h-full w-full animate-shimmer" />
      </div>
    </div>
  );
}
