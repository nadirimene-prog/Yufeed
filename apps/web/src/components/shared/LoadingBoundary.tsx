/**
 * LoadingBoundary Component
 *
 * A reusable boundary component that handles loading, error, and empty states.
 * Simplifies common data fetching patterns by providing consistent UI states.
 *
 * Features:
 * - Loading spinner with optional message
 * - Error display with retry capability
 * - Empty state with customizable message and CTA
 * - Skeleton loading option
 * - Accessible with proper ARIA attributes
 *
 * Usage:
 * ```tsx
 * <LoadingBoundary loading={isLoading} error={error} isEmpty={data?.length === 0}>
 *   <DataTable data={data} />
 * </LoadingBoundary>
 *
 * <LoadingBoundary
 *   loading={isLoading}
 *   error={error}
 *   isEmpty={!data}
 *   emptyMessage="No alerts found"
 *   emptyAction={{ label: "Create Alert", onClick: () => navigate('/alerts/new') }}
 * >
 *   <AlertsList alerts={data} />
 * </LoadingBoundary>
 * ```
 */

import { ReactNode } from "react";
import { AlertCircle, Loader2, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface LoadingBoundaryProps {
  loading: boolean;
  error?: Error | string | null;
  isEmpty?: boolean;
  children: ReactNode;

  // Loading state customization
  loadingMessage?: string;
  loadingVariant?: "spinner" | "skeleton";
  skeletonComponent?: ReactNode;

  // Error state customization
  errorTitle?: string;
  onRetry?: () => void;

  // Empty state customization
  emptyMessage?: string;
  emptyDescription?: string;
  emptyIcon?: ReactNode;
  emptyAction?: {
    label: string;
    onClick: () => void;
  };

  // Styling
  className?: string;
  minHeight?: string;
}

export function LoadingBoundary({
  loading,
  error,
  isEmpty,
  children,
  loadingMessage = "Loading...",
  loadingVariant = "spinner",
  skeletonComponent,
  errorTitle = "Error loading data",
  onRetry,
  emptyMessage = "No data available",
  emptyDescription,
  emptyIcon,
  emptyAction,
  className,
  minHeight = "400px",
}: LoadingBoundaryProps) {
  // Loading state
  if (loading) {
    if (loadingVariant === "skeleton" && skeletonComponent) {
      return <div className={cn(className)}>{skeletonComponent}</div>;
    }

    return (
      <div
        className={cn("flex flex-col items-center justify-center", className)}
        style={{ minHeight }}
        role="status"
        aria-live="polite"
        aria-busy="true"
      >
        <Loader2
          className="h-12 w-12 animate-spin text-blue-600 dark:text-blue-400"
          aria-hidden="true"
        />
        {loadingMessage && (
          <p className="mt-4 text-sm text-gray-600 dark:text-gray-400">
            {loadingMessage}
          </p>
        )}
        <span className="sr-only">{loadingMessage}</span>
      </div>
    );
  }

  // Error state
  if (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);

    return (
      <div
        className={cn(
          "flex flex-col items-center justify-center rounded-lg border-2 border-red-200 bg-red-50 p-8 dark:border-red-900 dark:bg-red-950",
          className,
        )}
        style={{ minHeight }}
        role="alert"
        aria-live="assertive"
      >
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-100 dark:bg-red-900">
          <AlertCircle
            className="h-6 w-6 text-red-600 dark:text-red-400"
            aria-hidden="true"
          />
        </div>
        <h3 className="mt-4 text-lg font-semibold text-red-900 dark:text-red-100">
          {errorTitle}
        </h3>
        <p className="mt-2 max-w-md text-center text-sm text-red-700 dark:text-red-300">
          {errorMessage}
        </p>
        {onRetry && (
          <Button
            onClick={onRetry}
            variant="outline"
            className="mt-4 border-red-300 text-red-700 hover:bg-red-100 dark:border-red-700 dark:text-red-300 dark:hover:bg-red-900"
          >
            Try Again
          </Button>
        )}
      </div>
    );
  }

  // Empty state
  if (isEmpty) {
    return (
      <div
        className={cn(
          "flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-200 bg-gray-50 p-8 dark:border-gray-800 dark:bg-gray-950",
          className,
        )}
        style={{ minHeight }}
        role="status"
        aria-live="polite"
      >
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-900">
          {emptyIcon || (
            <Search className="h-6 w-6 text-gray-400" aria-hidden="true" />
          )}
        </div>
        <h3 className="mt-4 text-lg font-semibold text-gray-900 dark:text-gray-100">
          {emptyMessage}
        </h3>
        {emptyDescription && (
          <p className="mt-2 max-w-md text-center text-sm text-gray-600 dark:text-gray-400">
            {emptyDescription}
          </p>
        )}
        {emptyAction && (
          <Button onClick={emptyAction.onClick} className="mt-4">
            {emptyAction.label}
          </Button>
        )}
      </div>
    );
  }

  // Success state - render children
  return <div className={cn(className)}>{children}</div>;
}

/**
 * Skeleton variants for common loading patterns
 */
export function TableSkeleton({
  rows = 5,
  cols = 4,
}: {
  rows?: number;
  cols?: number;
}) {
  return (
    <div className="space-y-3" role="status" aria-label="Loading table">
      {/* Header skeleton */}
      <div className="flex gap-4">
        {Array.from({ length: cols }).map((_, i) => (
          <div
            key={i}
            className="h-4 flex-1 animate-pulse rounded bg-gray-200 dark:bg-gray-800"
          />
        ))}
      </div>
      {/* Row skeletons */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="flex gap-4">
          {Array.from({ length: cols }).map((_, colIndex) => (
            <div
              key={colIndex}
              className="h-8 flex-1 animate-pulse rounded bg-gray-100 dark:bg-gray-900"
              style={{
                animationDelay: `${(rowIndex * cols + colIndex) * 50}ms`,
              }}
            />
          ))}
        </div>
      ))}
      <span className="sr-only">Loading table data</span>
    </div>
  );
}

export function CardSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div
      className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3"
      role="status"
      aria-label="Loading cards"
    >
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="rounded-lg border p-6 dark:border-gray-800">
          <div className="h-6 w-3/4 animate-pulse rounded bg-gray-200 dark:bg-gray-800" />
          <div className="mt-4 space-y-2">
            <div className="h-4 animate-pulse rounded bg-gray-100 dark:bg-gray-900" />
            <div className="h-4 w-5/6 animate-pulse rounded bg-gray-100 dark:bg-gray-900" />
          </div>
        </div>
      ))}
      <span className="sr-only">Loading cards</span>
    </div>
  );
}

/**
 * Export default and utilities
 */
export default LoadingBoundary;
