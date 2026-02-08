import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock the logger before importing the module under test
vi.mock("@/lib/logger", () => ({
  logger: {
    debug: vi.fn(),
    log: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}));

import { handleApiError, isApiError, retryApiCall } from "../api-error-handler";
import { logger } from "@/lib/logger";

describe("api-error-handler", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ---- handleApiError ----

  describe("handleApiError", () => {
    describe("HTTP status code messages", () => {
      it("returns correct message for 400 Bad Request", () => {
        const error = { response: { status: 400 }, message: "Bad Request" };
        const result = handleApiError(error, { logError: false });

        expect(result.message).toBe(
          "Invalid request. Please check your input and try again.",
        );
        expect(result.statusCode).toBe(400);
      });

      it("returns correct message for 401 Unauthorized", () => {
        const error = { response: { status: 401 }, message: "Unauthorized" };
        const result = handleApiError(error, { logError: false });

        expect(result.message).toBe(
          "Authentication required. Please log in and try again.",
        );
        expect(result.statusCode).toBe(401);
      });

      it("returns correct message for 403 Forbidden", () => {
        const error = { response: { status: 403 }, message: "Forbidden" };
        const result = handleApiError(error, { logError: false });

        expect(result.message).toBe(
          "You do not have permission to perform this action.",
        );
        expect(result.statusCode).toBe(403);
      });

      it("returns correct message for 404 Not Found", () => {
        const error = { response: { status: 404 }, message: "Not Found" };
        const result = handleApiError(error, { logError: false });

        expect(result.message).toBe("The requested resource was not found.");
        expect(result.statusCode).toBe(404);
      });

      it("returns correct message for 409 Conflict", () => {
        const error = { response: { status: 409 }, message: "Conflict" };
        const result = handleApiError(error, { logError: false });

        expect(result.message).toBe(
          "This action conflicts with existing data.",
        );
        expect(result.statusCode).toBe(409);
      });

      it("returns correct message for 422 Validation Error", () => {
        const error = {
          response: { status: 422, data: { details: "name is required" } },
          message: "Unprocessable Entity",
        };
        const result = handleApiError(error, { logError: false });

        expect(result.message).toBe(
          "Validation failed. Please check your input.",
        );
        expect(result.statusCode).toBe(422);
        expect(result.details).toBe("name is required");
      });

      it("returns correct message for 429 Too Many Requests", () => {
        const error = {
          response: { status: 429 },
          message: "Too Many Requests",
        };
        const result = handleApiError(error, { logError: false });

        expect(result.message).toBe(
          "Too many requests. Please try again later.",
        );
        expect(result.statusCode).toBe(429);
      });

      it("returns correct message for 500 Internal Server Error", () => {
        const error = {
          response: { status: 500 },
          message: "Internal Server Error",
        };
        const result = handleApiError(error, { logError: false });

        expect(result.message).toBe("Server error. Please try again later.");
        expect(result.statusCode).toBe(500);
      });

      it("returns correct message for 503 Service Unavailable", () => {
        const error = {
          response: { status: 503 },
          message: "Service Unavailable",
        };
        const result = handleApiError(error, { logError: false });

        expect(result.message).toBe(
          "Service temporarily unavailable. Please try again later.",
        );
        expect(result.statusCode).toBe(503);
      });

      it("returns generic message for unknown status codes", () => {
        const error = {
          response: { status: 418 },
          message: "I'm a teapot",
        };
        const result = handleApiError(error, { logError: false });

        expect(result.message).toBe("An error occurred. Please try again.");
        expect(result.statusCode).toBe(418);
      });
    });

    describe("error parsing", () => {
      it("extracts detail from axios response data", () => {
        const error = {
          response: {
            status: 400,
            data: { detail: "Email already exists" },
          },
          message: "Bad Request",
        };
        const result = handleApiError(error, {
          logError: false,
          customMessage: undefined,
        });

        // customMessage is not provided so getUserFriendlyMessage returns
        // the status-based message, overwriting the parsed message
        expect(result.statusCode).toBe(400);
      });

      it("uses customMessage when provided", () => {
        const error = {
          response: { status: 500 },
          message: "Server Error",
        };
        const result = handleApiError(error, {
          logError: false,
          customMessage: "Failed to save record",
        });

        expect(result.message).toBe("Failed to save record");
      });

      it("handles network errors (Failed to fetch)", () => {
        const error = new TypeError("Failed to fetch");
        const result = handleApiError(error, { logError: false });

        // TypeError 'Failed to fetch' is detected -> statusCode 0
        // getUserFriendlyMessage(0, undefined) returns the default message
        expect(result.statusCode).toBe(0);
        expect(result.message).toBe("An error occurred. Please try again.");
      });

      it("handles standard Error objects", () => {
        const error = new Error("Something broke");
        const result = handleApiError(error, { logError: false });

        // Standard Error with no statusCode returns default message
        expect(result.message).toBe("An error occurred. Please try again.");
        expect(result.statusCode).toBeUndefined();
      });

      it("handles unknown error types", () => {
        const result = handleApiError("string error", { logError: false });

        expect(result.message).toBe("An error occurred. Please try again.");
        expect(result.statusCode).toBeUndefined();
      });

      it("handles null error", () => {
        const result = handleApiError(null, { logError: false });

        expect(result.message).toBe("An error occurred. Please try again.");
      });

      it("includes a timestamp on every error", () => {
        const beforeTs = new Date().toISOString().slice(0, 10);
        const result = handleApiError(new Error("test"), { logError: false });

        expect(result.timestamp).toBeDefined();
        expect(result.timestamp.slice(0, 10)).toBe(beforeTs);
      });
    });

    describe("logging", () => {
      it("logs error when logError is true", () => {
        const error = { response: { status: 500 }, message: "Server Error" };
        handleApiError(error, { logError: true, context: "fetchUsers" });

        expect(logger.error).toHaveBeenCalledWith(
          "[API Error - fetchUsers]:",
          expect.objectContaining({
            statusCode: 500,
            originalError: error,
          }),
        );
      });

      it("does not log when logError is false", () => {
        const error = { response: { status: 500 }, message: "Server Error" };
        handleApiError(error, { logError: false });

        expect(logger.error).not.toHaveBeenCalled();
      });

      it("formats log label without context when context is omitted", () => {
        const error = { response: { status: 404 }, message: "Not Found" };
        handleApiError(error, { logError: true });

        expect(logger.error).toHaveBeenCalledWith(
          "[API Error]:",
          expect.any(Object),
        );
      });
    });

    describe("validation error details", () => {
      it("parses details field from response data", () => {
        const error = {
          response: {
            status: 422,
            data: {
              detail: "Validation failed",
              details: "Field 'email' is required",
            },
          },
          message: "Unprocessable Entity",
        };
        const result = handleApiError(error, { logError: false });

        expect(result.details).toBe("Field 'email' is required");
      });

      it("handles response with message field instead of detail", () => {
        const error = {
          response: {
            status: 400,
            data: { message: "Custom server message" },
          },
          message: "Bad Request",
        };
        // The parsed message will be "Custom server message" but
        // getUserFriendlyMessage overrides it based on statusCode
        const result = handleApiError(error, { logError: false });

        expect(result.statusCode).toBe(400);
      });
    });
  });

  // ---- isApiError ----

  describe("isApiError", () => {
    it("returns true for a valid ApiError object", () => {
      const apiError = {
        message: "Something failed",
        timestamp: "2026-01-01T00:00:00.000Z",
      };
      expect(isApiError(apiError)).toBe(true);
    });

    it("returns true for ApiError with optional fields", () => {
      const apiError = {
        message: "Not found",
        statusCode: 404,
        details: "Resource not found",
        timestamp: "2026-01-01T00:00:00.000Z",
      };
      expect(isApiError(apiError)).toBe(true);
    });

    it("returns false for null", () => {
      expect(isApiError(null)).toBe(false);
    });

    it("returns false for undefined", () => {
      expect(isApiError(undefined)).toBe(false);
    });

    it("returns false for a string", () => {
      expect(isApiError("error message")).toBe(false);
    });

    it("returns false for an object missing timestamp", () => {
      expect(isApiError({ message: "error" })).toBe(false);
    });

    it("returns false for an object missing message", () => {
      expect(isApiError({ timestamp: "2026-01-01" })).toBe(false);
    });
  });

  // ---- retryApiCall ----

  describe("retryApiCall", () => {
    it("returns the result on first successful call", async () => {
      const fn = vi.fn().mockResolvedValue("data");
      const result = await retryApiCall(fn, { maxRetries: 3, delayMs: 1 });

      expect(result).toBe("data");
      expect(fn).toHaveBeenCalledTimes(1);
    });

    it("retries on failure and succeeds on retry", async () => {
      const fn = vi
        .fn()
        .mockRejectedValueOnce({ response: { status: 500 }, message: "fail" })
        .mockResolvedValueOnce("recovered");

      const result = await retryApiCall(fn, { maxRetries: 3, delayMs: 1 });

      expect(result).toBe("recovered");
      expect(fn).toHaveBeenCalledTimes(2);
    });

    it("does not retry on 4xx errors (except 429)", async () => {
      const error = { response: { status: 400 }, message: "Bad Request" };
      const fn = vi.fn().mockRejectedValue(error);

      await expect(
        retryApiCall(fn, { maxRetries: 3, delayMs: 1 }),
      ).rejects.toBe(error);
      expect(fn).toHaveBeenCalledTimes(1);
    });

    it("retries on 429 (rate limit) errors", async () => {
      const rateLimitError = {
        response: { status: 429 },
        message: "Too Many Requests",
      };
      const fn = vi
        .fn()
        .mockRejectedValueOnce(rateLimitError)
        .mockResolvedValueOnce("ok");

      const result = await retryApiCall(fn, { maxRetries: 3, delayMs: 1 });

      expect(result).toBe("ok");
      expect(fn).toHaveBeenCalledTimes(2);
    });

    it("throws after exhausting all retries", async () => {
      const error = { response: { status: 500 }, message: "Server Error" };
      const fn = vi.fn().mockRejectedValue(error);

      await expect(
        retryApiCall(fn, { maxRetries: 2, delayMs: 1 }),
      ).rejects.toBe(error);
      // 1 initial + 2 retries = 3 calls
      expect(fn).toHaveBeenCalledTimes(3);
    });

    it("calls onRetry callback with attempt number", async () => {
      const error = { response: { status: 500 }, message: "Server Error" };
      const fn = vi
        .fn()
        .mockRejectedValueOnce(error)
        .mockRejectedValueOnce(error)
        .mockResolvedValueOnce("ok");

      const onRetry = vi.fn();
      await retryApiCall(fn, { maxRetries: 3, delayMs: 1, onRetry });

      expect(onRetry).toHaveBeenCalledTimes(2);
      expect(onRetry).toHaveBeenCalledWith(1, error);
      expect(onRetry).toHaveBeenCalledWith(2, error);
    });

    it("uses default values when no options provided", async () => {
      const fn = vi.fn().mockResolvedValue("data");
      const result = await retryApiCall(fn);

      expect(result).toBe("data");
      expect(fn).toHaveBeenCalledTimes(1);
    });
  });
});
