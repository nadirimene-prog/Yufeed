import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

describe("logger", () => {
  const originalEnv = process.env.NODE_ENV;

  beforeEach(() => {
    vi.spyOn(console, "debug").mockImplementation(() => {});
    vi.spyOn(console, "log").mockImplementation(() => {});
    vi.spyOn(console, "warn").mockImplementation(() => {});
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
    (process.env as Record<string, string>).NODE_ENV = originalEnv!;
  });

  it("logs in development mode", async () => {
    (process.env as Record<string, string>).NODE_ENV = "development";
    // Re-import to pick up new env
    vi.resetModules();
    const { logger } = await import("../logger");

    logger.debug("d");
    logger.log("l");
    logger.warn("w");
    logger.error("e");

    expect(console.debug).toHaveBeenCalledWith("d");
    expect(console.log).toHaveBeenCalledWith("l");
    expect(console.warn).toHaveBeenCalledWith("w");
    expect(console.error).toHaveBeenCalledWith("e");
  });

  it("suppresses debug/log/warn in production", async () => {
    (process.env as Record<string, string>).NODE_ENV = "production";
    vi.resetModules();
    const { logger } = await import("../logger");

    logger.debug("d");
    logger.log("l");
    logger.warn("w");

    expect(console.debug).not.toHaveBeenCalled();
    expect(console.log).not.toHaveBeenCalled();
    expect(console.warn).not.toHaveBeenCalled();
  });
});
