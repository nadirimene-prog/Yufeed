import axios from "axios";
import { clearAuthTokens, getAuthToken } from "./auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers.set('Authorization', `Bearer ${token}`);
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    if (status === 401) {
      clearAuthTokens();
      if (typeof window !== "undefined") {
        const path = window.location.pathname || "/";
        if (path !== "/") {
          window.location.assign("/");
        }
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;
