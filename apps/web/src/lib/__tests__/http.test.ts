import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

// Mock dependencies before importing the module under test
vi.mock("axios", () => {
  const interceptors = {
    request: { use: vi.fn(), eject: vi.fn() },
    response: { use: vi.fn(), eject: vi.fn() },
  };
  const instance = {
    interceptors,
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    defaults: { baseURL: "", headers: { common: {} } },
  };
  return {
    default: {
      create: vi.fn(() => instance),
    },
  };
});

vi.mock("../auth", () => ({
  getAuthToken: vi.fn(),
  clearAuthTokens: vi.fn(),
}));

vi.mock("@/lib/apiBaseUrl", () => ({
  resolveApiBaseUrl: vi.fn(() => "http://localhost:8000"),
}));

vi.mock("@/lib/logger", () => ({
  logger: {
    debug: vi.fn(),
    log: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}));

import axios from "axios";
import { getAuthToken, clearAuthTokens } from "../auth";
import { resolveApiBaseUrl } from "@/lib/apiBaseUrl";
import { logger } from "@/lib/logger";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyFn = (...args: any[]) => any;

describe("http (apiClient)", () => {
  let requestInterceptor: AnyFn;
  let responseErrorInterceptor: AnyFn;

  beforeEach(async () => {
    vi.resetModules();

    // Clear mock call history so tests are independent
    vi.mocked(clearAuthTokens).mockClear();
    vi.mocked(getAuthToken).mockClear();
    vi.mocked(logger.warn).mockClear();
    vi.mocked(logger.error).mockClear();

    // Re-import to trigger module initialisation
    await import("../http");

    const createMock = vi.mocked(axios.create);
    const instance = createMock.mock.results[0]?.value;

    // Capture the most recently registered interceptors
    const reqUse = instance.interceptors.request.use as ReturnType<
      typeof vi.fn
    >;
    const resUse = instance.interceptors.response.use as ReturnType<
      typeof vi.fn
    >;

    const reqCalls = reqUse.mock.calls;
    const resCalls = resUse.mock.calls;

    requestInterceptor = reqCalls[reqCalls.length - 1][0];
    // response.use(successFn, errorFn) -- we want the error handler
    responseErrorInterceptor = resCalls[resCalls.length - 1][1];
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ---- axios.create configuration ----

  describe("default configuration", () => {
    it("creates axios instance with resolved base URL", () => {
      expect(axios.create).toHaveBeenCalledWith(
        expect.objectContaining({
          baseURL: "http://localhost:8000",
        }),
      );
    });

    it("sets Content-Type header to application/json", () => {
      expect(axios.create).toHaveBeenCalledWith(
        expect.objectContaining({
          headers: expect.objectContaining({
            "Content-Type": "application/json",
          }),
        }),
      );
    });

    it("calls resolveApiBaseUrl to determine base URL", () => {
      expect(resolveApiBaseUrl).toHaveBeenCalled();
    });
  });

  // ---- request interceptor ----

  describe("request interceptor", () => {
    it("adds Authorization header when a token exists", () => {
      vi.mocked(getAuthToken).mockReturnValue("test-jwt-token");

      const setMock = vi.fn();
      const config = { headers: { set: setMock } };
      const result = requestInterceptor(config);

      expect(setMock).toHaveBeenCalledWith(
        "Authorization",
        "Bearer test-jwt-token",
      );
      expect(result).toBe(config);
    });

    it("does not add Authorization header when no token exists", () => {
      vi.mocked(getAuthToken).mockReturnValue(null);

      const setMock = vi.fn();
      const config = { headers: { set: setMock } };
      const result = requestInterceptor(config);

      expect(setMock).not.toHaveBeenCalled();
      expect(result).toBe(config);
    });
  });

  // ---- response interceptor (error handler) ----

  describe("response error interceptor", () => {
    it("clears auth tokens on 401 response", async () => {
      const error = {
        response: { status: 401 },
        config: { url: "/api/test", method: "get" },
        message: "Unauthorized",
      };

      await expect(responseErrorInterceptor(error)).rejects.toBe(error);
      expect(clearAuthTokens).toHaveBeenCalledTimes(1);
    });

    it("logs a warning on 401 response", async () => {
      const error = {
        response: { status: 401 },
        config: { url: "/api/test", method: "get" },
        message: "Unauthorized",
      };

      await expect(responseErrorInterceptor(error)).rejects.toBe(error);
      expect(logger.warn).toHaveBeenCalledWith(
        "[API] Unauthorized - clearing tokens",
      );
    });

    it("does not clear tokens for non-401 errors", async () => {
      const error = {
        response: { status: 500 },
        config: { url: "/api/test", method: "get" },
        message: "Internal Server Error",
      };

      await expect(responseErrorInterceptor(error)).rejects.toBe(error);
      expect(clearAuthTokens).not.toHaveBeenCalled();
    });

    it("rejects with the original error", async () => {
      const error = {
        response: { status: 403 },
        config: { url: "/api/test", method: "get" },
        message: "Forbidden",
      };

      await expect(responseErrorInterceptor(error)).rejects.toBe(error);
    });

    it("handles errors without a response object", async () => {
      const error = {
        message: "Network Error",
        config: { url: "/api/test", method: "get" },
      };

      await expect(responseErrorInterceptor(error)).rejects.toBe(error);
      expect(clearAuthTokens).not.toHaveBeenCalled();
    });
  });
});
