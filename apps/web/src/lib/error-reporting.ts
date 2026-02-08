/**
 * Error reporting utility.
 *
 * When NEXT_PUBLIC_SENTRY_DSN is set, errors are forwarded to Sentry.
 * Otherwise errors are silently ignored in production (already logged by logger.ts in dev).
 *
 * To enable Sentry:
 * 1. npm install @sentry/nextjs
 * 2. Set NEXT_PUBLIC_SENTRY_DSN in .env
 * 3. Uncomment the Sentry.init block below
 */

let sentryModule: { captureException: (error: unknown) => void } | null = null;

if (typeof window !== "undefined" && process.env.NEXT_PUBLIC_SENTRY_DSN) {
  import("@sentry/nextjs")
    .then((Sentry) => {
      Sentry.init({
        dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
        environment: process.env.NODE_ENV,
        tracesSampleRate: process.env.NODE_ENV === "production" ? 0.1 : 1.0,
      });
      sentryModule = Sentry;
    })
    .catch(() => {
      // @sentry/nextjs not installed - that's fine
    });
}

export function captureException(error: unknown): void {
  if (sentryModule) {
    sentryModule.captureException(error);
  }
}
