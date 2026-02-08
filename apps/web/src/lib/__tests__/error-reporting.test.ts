import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock @sentry/nextjs so Vite does not try to resolve the missing package
vi.mock("@sentry/nextjs", () => ({
  init: vi.fn(),
  captureException: vi.fn(),
}));

describe("error-reporting", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("exports captureException as a function", async () => {
    // Ensure Sentry dynamic import is not triggered (no DSN set)
    delete (process.env as Record<string, string | undefined>)
      .NEXT_PUBLIC_SENTRY_DSN;

    const mod = await import("../error-reporting");

    expect(typeof mod.captureException).toBe("function");
  });

  it("captureException does not throw when Sentry is not loaded", async () => {
    // No NEXT_PUBLIC_SENTRY_DSN means sentryModule stays null
    delete (process.env as Record<string, string | undefined>)
      .NEXT_PUBLIC_SENTRY_DSN;

    const { captureException } = await import("../error-reporting");

    // Should silently succeed (no-op) without throwing
    expect(() => captureException(new Error("test error"))).not.toThrow();
  });

  it("captureException accepts non-Error values without throwing", async () => {
    delete (process.env as Record<string, string | undefined>)
      .NEXT_PUBLIC_SENTRY_DSN;

    const { captureException } = await import("../error-reporting");

    expect(() => captureException("string error")).not.toThrow();
    expect(() => captureException(null)).not.toThrow();
    expect(() => captureException(undefined)).not.toThrow();
    expect(() => captureException(42)).not.toThrow();
    expect(() => captureException({ custom: "object" })).not.toThrow();
  });

  it("captureException returns void", async () => {
    delete (process.env as Record<string, string | undefined>)
      .NEXT_PUBLIC_SENTRY_DSN;

    const { captureException } = await import("../error-reporting");

    const result = captureException(new Error("test"));
    expect(result).toBeUndefined();
  });
});
