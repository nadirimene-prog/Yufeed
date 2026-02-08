import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
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

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Handle authentication errors
    if (error.response?.status === 401) {
      clearAuthTokens();
      // Optionally redirect to login
      if (typeof window !== "undefined") {
        logger.warn("[API] Unauthorized - clearing tokens");
      }
    }

    // Log error details for debugging (only in development)
    if (process.env.NODE_ENV === "development") {
      console.error("[API Error]", {
        url: error.config?.url,
        method: error.config?.method,
        status: error.response?.status,
        message: error.message,
      });
    }

    return Promise.reject(error);
  },
);

export default apiClient;
