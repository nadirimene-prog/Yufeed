/**
 * Resolves the API base URL based on the environment (Browser vs SSR)
 * and whether it's running inside Docker or directly on the host.
 */
export function resolveApiBaseUrl(): string {
  // Browser context: Prefer public API URL if provided, otherwise use relative paths
  if (typeof window !== "undefined") {
    const publicUrl = process.env.NEXT_PUBLIC_API_URL;
    if (publicUrl) {
      return publicUrl.replace(/\/$/, "");
    }
    return "";
  }

  // SSR context: Prefer API_INTERNAL_URL (docker service name)
  const internalUrl =
    process.env.API_INTERNAL_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://api:8000";
  return internalUrl.replace(/\/$/, "");
}

// Alias for backwards compatibility
export const getApiBaseUrl = resolveApiBaseUrl;
