// Stub for @sentry/nextjs used by Vitest when the real package is not installed.
// Individual test files can override this with vi.mock("@sentry/nextjs", ...).
export function init() {}
export function captureException() {}
