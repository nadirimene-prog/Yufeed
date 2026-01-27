import axios from "axios";
import { clearAuthTokens, getAuthToken } from "./auth";
import { resolveApiBaseUrl } from "@/lib/apiBaseUrl";

const API_URL = resolveApiBaseUrl();

/**
 * Resolve API base URL correctly for:
 * - Browser (localhost)
 * - Next.js SSR inside Docker (api service)
 */
export function resolveApiBaseUrl(): string {
  const publicUrl = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

  // Browser
  if (typeof window !== "undefined") {
    return publicUrl;
  }

  // Server / SSR (Docker)
  return (process.env.API_INTERNAL_URL || "http://api:8000").replace(/\/$/, "");
}

const apiClient = axios.create({
  baseURL: resolveApiBaseUrl(),
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers = config.headers || {};
    (config.headers as any).Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      clearAuthTokens();
    }
    return Promise.reject(error);
  }
);

export default apiClient;