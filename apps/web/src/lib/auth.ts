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
    if (value) {
      return value;
    }
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
  for (const store of [window.localStorage, window.sessionStorage]) {
    store.removeItem(ACCESS_TOKEN_KEY);
    store.removeItem(REFRESH_TOKEN_KEY);
    store.removeItem(TOKEN_TYPE_KEY);
  }
}

export async function loginWithPassword(
  email: string,
  password: string,
  options?: { apiUrl?: string; storage?: "local" | "session" }
): Promise<AuthTokens> {
  const apiUrl =
    options?.apiUrl ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000";
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
