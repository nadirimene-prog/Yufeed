/**
 * Resolves the API base URL based on the environment (Browser vs SSR)
 * and whether it's running inside Docker or directly on the host.
 */
export function resolveApiBaseUrl(): string {
  // Browser context: Use relative paths to rely on Next.js rewrites
  if (typeof window !== "undefined") {
    return "";
  }

  // SSR context: Prefer API_INTERNAL_URL (docker service name)
  const internalUrl = process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || "http://api:8000";
  return internalUrl.replace(/\/$/, "");
}

// Alias for backwards compatibility
export const getApiBaseUrl = resolveApiBaseUrl;
