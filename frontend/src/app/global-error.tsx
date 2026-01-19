"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCcw } from "lucide-react";

interface GlobalErrorProps {
    error: Error & { digest?: string };
    reset: () => void;
}

/**
 * Global Error Boundary for root layout errors
 *
 * This catches errors that occur in the root layout itself.
 * Must be a separate file from error.tsx as per Next.js requirements.
 * Only activated in production. In development, the error overlay is shown instead.
 */
export default function GlobalError({ error, reset }: GlobalErrorProps) {
    useEffect(() => {
        // Log critical error
        console.error("Critical application error:", error);

        // TODO: Send to monitoring service
        // Example: Sentry.captureException(error);
    }, [error]);

    return (
        <html lang="en">
            <body>
                <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
                    <div className="w-full max-w-md space-y-6 text-center">
                        {/* Error Icon */}
                        <div className="flex justify-center">
                            <div className="rounded-full bg-red-100 p-3">
                                <AlertTriangle className="h-8 w-8 text-red-600" />
                            </div>
                        </div>

                        {/* Error Message */}
                        <div className="space-y-2">
                            <h1 className="text-2xl font-bold text-gray-900">
                                Application Error
                            </h1>
                            <p className="text-gray-600">
                                A critical error occurred. Please refresh the page or contact support if this continues.
                            </p>
                        </div>

                        {/* Error Details (Development Only) */}
                        {process.env.NODE_ENV === "development" && (
                            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-left">
                                <h3 className="mb-2 text-sm font-semibold text-red-800">
                                    Error Details (Development Only)
                                </h3>
                                <div className="space-y-1 text-xs text-red-700">
                                    <p className="font-semibold">{error.name}</p>
                                    <p className="break-all font-mono">{error.message}</p>
                                    {error.digest && (
                                        <p className="mt-2 font-mono text-red-600">
                                            Digest: {error.digest}
                                        </p>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* Action Button */}
                        <button
                            onClick={reset}
                            className="inline-flex items-center justify-center rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                        >
                            <RefreshCcw className="mr-2 h-4 w-4" />
                            Reload Application
                        </button>

                        {/* Support Information */}
                        <div className="text-xs text-gray-500">
                            <p>
                                If this problem persists, please contact{" "}
                                <a
                                    href="mailto:support@yufeed.com"
                                    className="underline hover:text-gray-700"
                                >
                                    support
                                </a>
                            </p>
                        </div>
                    </div>
                </div>
            </body>
        </html>
    );
}
