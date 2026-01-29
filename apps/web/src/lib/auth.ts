import { getApiBaseUrl } from "@/lib/apiBaseUrl";
const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";
const TOKEN_TYPE_KEY = "token_type";

const TOKEN_KEYS = [
  ACCESS_TOKEN_KEY,
  "auth_token",
  "token",
  "jwt",
  "yufeed_token",
];

export interface AuthTokens {
  access_token: string;
  refresh_token?: string;
  token_type?: string;
}

interface JwtPayload {
  exp?: number;
  iat?: number;
  sub?: string;
  user_id?: string;
  email?: string;
  role?: string;
  [key: string]: unknown;
}

function decodeJwtPayload(token: string): JwtPayload | null {
  const parts = token.split(".");
  if (parts.length < 2) return null;
  const payload = parts[1].replace(/-/g, "+").replace(/_/g, "/");
  try {
    const decoded =
      typeof window !== "undefined" && typeof atob === "function"
        ? atob(payload)
        : Buffer.from(payload, "base64").toString("utf-8");
    return JSON.parse(decoded) as JwtPayload;
  } catch {
    return null;
  }
}

function isJwtTokenValid(token: string): boolean {
  const payload = decodeJwtPayload(token);
  if (!payload) return false;
  const exp = payload.exp;
  if (typeof exp !== "number") {
    return true;
  }
  const now = Math.floor(Date.now() / 1000);
  return exp > now;
}

export function getAuthToken(): string | null {
  if (typeof window === "undefined") {
    return (
      process.env.NEXT_PUBLIC_API_TOKEN ||
      process.env.NEXT_PUBLIC_AUTH_TOKEN ||
      null
    );
  }

  for (const key of TOKEN_KEYS) {
    const value =
      window.localStorage.getItem(key) ||
      window.sessionStorage.getItem(key);
    if (!value) continue;
    if (isJwtTokenValid(value)) {
      return value;
    }
    window.localStorage.removeItem(key);
    window.sessionStorage.removeItem(key);
  }

  return null;
}

export function setAuthTokens(
  tokens: AuthTokens,
  storage: "local" | "session" = "local"
) {
  if (typeof window === "undefined") {
    return;
  }
  const target =
    storage === "session" ? window.sessionStorage : window.localStorage;
  target.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  if (tokens.refresh_token) {
    target.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
  }
  if (tokens.token_type) {
    target.setItem(TOKEN_TYPE_KEY, tokens.token_type);
  }
}

export function clearAuthTokens() {
  if (typeof window === "undefined") {
    return;
  }
  const allKeys = [...TOKEN_KEYS, REFRESH_TOKEN_KEY, TOKEN_TYPE_KEY];
  for (const store of [window.localStorage, window.sessionStorage]) {
    for (const key of allKeys) {
      store.removeItem(key);
    }
  }
}

export async function loginWithPassword(
  email: string,
  password: string,
  options?: { apiUrl?: string; storage?: "local" | "session" }
): Promise<AuthTokens> {
  clearAuthTokens();
  const apiUrl =
    options?.apiUrl ||
    getApiBaseUrl();
  const response = await fetch(`${apiUrl}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Login failed");
  }
  const tokens = (await response.json()) as AuthTokens;
  setAuthTokens(tokens, options?.storage ?? "local");
  return tokens;
}

export function withAuthHeaders(headers: HeadersInit = {}) {
  const normalized = new Headers(headers);
  const token = getAuthToken();
  if (token && !normalized.has("Authorization")) {
    normalized.set("Authorization", `Bearer ${token}`);
  }
  return normalized;
}

export function fetchWithAuth(input: RequestInfo | URL, init: RequestInit = {}) {
  return fetch(input, {
    ...init,
    headers: withAuthHeaders(init.headers ?? {}),
  });
}