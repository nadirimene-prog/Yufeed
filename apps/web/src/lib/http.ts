import axios, { InternalAxiosRequestConfig } from "axios";
import { clearAuthTokens, getAuthToken } from "./auth";
import { resolveApiBaseUrl } from "@/lib/apiBaseUrl";
import { logger } from "@/lib/logger";

const apiClient = axios.create({
  baseURL: resolveApiBaseUrl(),
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getAuthToken();
  if (token) {
    config.headers.set("Authorization", `Bearer ${token}`);
  }
  return config;
});

function getDevErrorPayload(error: unknown) {
  if (axios.isAxiosError(error)) {
    const responseHeaders = error.response?.headers as
      | Record<string, string | undefined>
      | undefined;

    return {
      name: error.name,
      code: error.code ?? null,
      url: error.config?.url ?? null,
      method: error.config?.method ?? null,
      status: error.response?.status ?? null,
      statusText: error.response?.statusText ?? null,
      requestId:
        responseHeaders?.["x-request-id"] ??
        responseHeaders?.["X-Request-Id"] ??
        null,
      message: error.message ?? null,
      data: error.response?.data ?? null,
    };
  }

  if (error instanceof Error) {
    return {
      name: error.name,
      message: error.message,
    };
  }

  return { value: error ?? null };
}

apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    const axiosError = axios.isAxiosError(error) ? error : undefined;

    // Handle authentication errors
    if (axiosError?.response?.status === 401) {
      clearAuthTokens();
      // Optionally redirect to login
      if (typeof window !== "undefined") {
        logger.warn("[API] Unauthorized - clearing tokens");
      }
    }

    // Log error details for debugging (only in development)
    if (process.env.NODE_ENV === "development") {
      console.error("[API Error]", getDevErrorPayload(error));
    }

    return Promise.reject(error);
  },
);

export default apiClient;
