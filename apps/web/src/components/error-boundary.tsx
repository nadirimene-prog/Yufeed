"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button-horizon";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { AlertTriangle, RefreshCw, Bug, Home } from "lucide-react";
import Link from "next/link";

/**
 * Horizon Error Boundary
 * Graceful error handling with recovery options
 */

/* ─────────────────────────────────────────────────────────────────────────────
   Types
   ───────────────────────────────────────────────────────────────────────────── */

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
  onReset?: () => void;
  resetKeys?: string[];
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

/* ─────────────────────────────────────────────────────────────────────────────
   Error Boundary Class Component
   ───────────────────────────────────────────────────────────────────────────── */

export class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.setState({ errorInfo });
    this.props.onError?.(error, errorInfo);

    // Log to error reporting service
    console.error("Error caught by boundary:", error, errorInfo);
  }

  componentDidUpdate(prevProps: ErrorBoundaryProps) {
    const { hasError } = this.state;
    const { resetKeys } = this.props;

    if (
      hasError &&
      prevProps.resetKeys !== resetKeys &&
      resetKeys?.some((key, index) => prevProps.resetKeys?.[index] !== key)
    ) {
      this.reset();
    }
  }

  reset = () => {
    this.props.onReset?.();
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render() {
    const { hasError, error, errorInfo } = this.state;
    const { children, fallback } = this.props;

    if (hasError) {
      if (fallback) {
        return fallback;
      }

      return (
        <DefaultErrorFallback
          error={error}
          errorInfo={errorInfo}
          onReset={this.reset}
        />
      );
    }

    return children;
  }
}

/* ─────────────────────────────────────────────────────────────────────────────
   Default Error Fallback UI
   ───────────────────────────────────────────────────────────────────────────── */

interface DefaultErrorFallbackProps {
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
  onReset: () => void;
}

function DefaultErrorFallback({
  error,
  errorInfo,
  onReset,
}: DefaultErrorFallbackProps) {
  const [showDetails, setShowDetails] = React.useState(false);

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-background">
      <Card className="max-w-lg w-full" variant="elevated">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-risk-critical/10">
            <AlertTriangle className="h-8 w-8 text-risk-critical" />
          </div>
          <CardTitle className="text-xl">Something went wrong</CardTitle>
          <CardDescription>
            We apologize for the inconvenience. The error has been logged and
            our team has been notified.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Error Message */}
          <div className="rounded-lg bg-risk-critical/10 border border-risk-critical/20 p-4">
            <p className="text-sm font-medium text-risk-critical">
              {error?.name || "Error"}
            </p>
            <p className="mt-1 text-sm text-foreground-secondary">
              {error?.message || "An unexpected error occurred"}
            </p>
          </div>

          {/* Stack Trace Toggle */}
          {errorInfo && (
            <div>
              <button
                onClick={() => setShowDetails(!showDetails)}
                className="flex items-center gap-2 text-sm text-foreground-secondary hover:text-foreground transition-colors"
              >
                <Bug className="h-4 w-4" />
                {showDetails ? "Hide" : "Show"} technical details
              </button>

              {showDetails && (
                <pre className="mt-2 p-3 rounded-lg bg-background-overlay text-xs text-foreground-secondary overflow-auto max-h-48">
                  {errorInfo.componentStack}
                </pre>
              )}
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-3 pt-2">
            <Button
              variant="primary"
              onClick={onReset}
              className="flex-1"
              leftIcon={<RefreshCw className="h-4 w-4" />}
            >
              Try again
            </Button>
            <Link href="/dashboard" className="flex-1">
              <Button
                variant="secondary"
                className="w-full"
                leftIcon={<Home className="h-4 w-4" />}
              >
                Go to dashboard
              </Button>
            </Link>
          </div>

          {/* Support Link */}
          <p className="text-center text-xs text-foreground-tertiary">
            If this problem persists, please{" "}
            <a
              href="mailto:support@yufeed.com"
              className="text-primary hover:underline"
            >
              contact support
            </a>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Section Error Boundary (for partial UI failures)
   ───────────────────────────────────────────────────────────────────────────── */

interface SectionErrorBoundaryProps {
  children: React.ReactNode;
  title?: string;
  description?: string;
  onReset?: () => void;
  className?: string;
}

export function SectionErrorBoundary({
  children,
  title = "Failed to load section",
  description = "There was an error loading this section. You can try refreshing it.",
  onReset,
  className,
}: SectionErrorBoundaryProps) {
  return (
    <ErrorBoundary
      fallback={
        <SectionErrorFallback
          title={title}
          description={description}
          onReset={onReset}
          className={className}
        />
      }
    >
      {children}
    </ErrorBoundary>
  );
}

function SectionErrorFallback({
  title,
  description,
  onReset,
  className,
}: {
  title: string;
  description: string;
  onReset?: () => void;
  className?: string;
}) {
  return (
    <Card className={cn("border-risk-critical/20", className)}>
      <CardContent className="p-6">
        <div className="flex items-start gap-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-risk-critical/10 shrink-0">
            <AlertTriangle className="h-5 w-5 text-risk-critical" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-medium text-foreground">{title}</h3>
            <p className="mt-1 text-sm text-foreground-secondary">
              {description}
            </p>
            {onReset && (
              <Button
                variant="secondary"
                size="sm"
                onClick={onReset}
                className="mt-3"
                leftIcon={<RefreshCw className="h-4 w-4" />}
              >
                Retry
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Async Error Handler Hook
   ───────────────────────────────────────────────────────────────────────────── */

interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
}

export function useAsyncError<T>() {
  const [state, setState] = React.useState<AsyncState<T>>({
    data: null,
    loading: false,
    error: null,
  });

  const execute = React.useCallback(async (promise: Promise<T>) => {
    setState({ data: null, loading: true, error: null });
    try {
      const data = await promise;
      setState({ data, loading: false, error: null });
      return data;
    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error));
      setState({ data: null, loading: false, error: err });
      throw err;
    }
  }, []);

  const reset = React.useCallback(() => {
    setState({ data: null, loading: false, error: null });
  }, []);

  return { ...state, execute, reset };
}

/* ─────────────────────────────────────────────────────────────────────────────
   Global Error Handler
   ───────────────────────────────────────────────────────────────────────────── */

export function setupGlobalErrorHandlers() {
  // Handle unhandled promise rejections
  if (typeof window !== "undefined") {
    window.addEventListener("unhandledrejection", (event) => {
      console.error("Unhandled promise rejection:", event.reason);
      // Could send to error reporting service here
    });

    // Handle global errors
    window.addEventListener("error", (event) => {
      console.error("Global error:", event.error);
      // Could send to error reporting service here
    });
  }
}

/* ─────────────────────────────────────────────────────────────────────────────
   Exports
   ───────────────────────────────────────────────────────────────────────────── */

export default ErrorBoundary;
