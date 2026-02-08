// Type stub for optional @sentry/nextjs dependency.
// The actual package is loaded dynamically in error-reporting.ts only when NEXT_PUBLIC_SENTRY_DSN is set.
declare module "@sentry/nextjs" {
  export function init(options: {
    dsn?: string;
    environment?: string;
    tracesSampleRate?: number;
  }): void;
  export function captureException(error: unknown): void;
}
