"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCcw, Home } from "lucide-react";
import Link from "next/link";
import { captureException } from "@/lib/error-reporting";

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

/**
 * Global Error Boundary for the application
 *
 * Catches runtime errors in client components and provides:
 * - User-friendly error message
 * - Error details in development mode
 * - Recovery options (retry, go home)
 * - Error reporting to monitoring service
 */
export default function Error({ error, reset }: ErrorProps) {
  useEffect(() => {
    // Log error to console in development
    if (process.env.NODE_ENV === "development") {
      console.error("Error boundary caught:", error);
      console.error("Stack trace:", error.stack);
    }

    captureException(error);
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 ">
      <div className="w-full max-w-md space-y-6 text-center">
        {/* Error Icon */}
        <div className="flex justify-center">
          <div className="rounded-full bg-red-100 p-3 ">
            <AlertTriangle className="h-8 w-8 text-red-600 " />
          </div>
        </div>

        {/* Error Message */}
        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-slate-900 ">
            Something went wrong
          </h1>
          <p className="text-slate-600 ">
            We encountered an unexpected error. Please try again or return to
            the home page.
          </p>
        </div>

        {/* Error Details (Development Only) */}
        {process.env.NODE_ENV === "development" && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-left  ">
            <h3 className="mb-2 text-sm font-semibold text-red-800 ">
              Error Details (Development Only)
            </h3>
            <div className="space-y-1 text-xs text-red-700 ">
              <p className="font-semibold">{error.name}</p>
              <p className="break-all font-mono">{error.message}</p>
              {error.digest && (
                <p className="mt-2 font-mono text-red-600 ">
                  Digest: {error.digest}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
          <button
            onClick={reset}
            className="inline-flex items-center justify-center rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2  "
          >
            <RefreshCcw className="mr-2 h-4 w-4" />
            Try again
          </button>
          <Link
            href="/"
            className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-500 focus:ring-offset-2    "
          >
            <Home className="mr-2 h-4 w-4" />
            Go to home
          </Link>
        </div>

        {/* Support Information */}
        <div className="text-xs text-slate-500 ">
          <p>
            If this problem persists, please contact{" "}
            <a
              href="mailto:support@yufeed.com"
              className="underline hover:text-slate-700 "
            >
              support
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
