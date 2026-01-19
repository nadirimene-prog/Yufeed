"use client";

import React, { Component, ReactNode } from "react";
import { AlertTriangle, RefreshCcw } from "lucide-react";

interface ErrorBoundaryProps {
    children: ReactNode;
    fallback?: ReactNode;
    onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface ErrorBoundaryState {
    hasError: boolean;
    error: Error | null;
}

/**
 * Reusable Error Boundary Component
 *
 * Wraps sections of the application to catch errors and display fallback UI.
 * Can be used to isolate error handling for specific features/sections.
 *
 * Usage:
 * ```tsx
 * <ErrorBoundary fallback={<CustomErrorUI />}>
 *   <YourComponent />
 * </ErrorBoundary>
 * ```
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
    constructor(props: ErrorBoundaryProps) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error: Error): ErrorBoundaryState {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        // Log error details
        console.error("ErrorBoundary caught an error:", error, errorInfo);

        // Call custom error handler if provided
        if (this.props.onError) {
            this.props.onError(error, errorInfo);
        }

        // TODO: Send to error monitoring service
        // Example: Sentry.captureException(error, { contexts: { react: errorInfo } });
    }

    handleReset = () => {
        this.setState({ hasError: false, error: null });
    };

    render() {
        if (this.state.hasError) {
            // Use custom fallback if provided
            if (this.props.fallback) {
                return this.props.fallback;
            }

            // Default error UI
            return (
                <div className="flex min-h-[400px] items-center justify-center rounded-lg border border-red-200 bg-red-50 p-8 dark:border-red-800 dark:bg-red-900/10">
                    <div className="w-full max-w-md space-y-4 text-center">
                        <div className="flex justify-center">
                            <div className="rounded-full bg-red-100 p-2 dark:bg-red-900/20">
                                <AlertTriangle className="h-6 w-6 text-red-600 dark:text-red-400" />
                            </div>
                        </div>

                        <div className="space-y-1">
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                                Something went wrong
                            </h3>
                            <p className="text-sm text-gray-600 dark:text-gray-400">
                                This section encountered an error. Please try again.
                            </p>
                        </div>

                        {process.env.NODE_ENV === "development" && this.state.error && (
                            <div className="rounded border border-red-300 bg-red-100 p-3 text-left dark:border-red-700 dark:bg-red-900/20">
                                <p className="text-xs font-mono text-red-800 dark:text-red-300">
                                    {this.state.error.message}
                                </p>
                            </div>
                        )}

                        <button
                            onClick={this.handleReset}
                            className="inline-flex items-center justify-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:bg-blue-500 dark:hover:bg-blue-600"
                        >
                            <RefreshCcw className="mr-2 h-4 w-4" />
                            Try again
                        </button>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
