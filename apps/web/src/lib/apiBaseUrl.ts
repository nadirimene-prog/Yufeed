export function resolveApiBaseUrl() {
  const envUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Browser: use envUrl as-is (localhost works from the user's machine)
  if (typeof window !== "undefined") return envUrl.replace(/\/$/, "");

  // Server (Next.js SSR inside Docker): localhost points to the web container
  try {
    const u = new URL(envUrl);
    if (u.hostname === "localhost" || u.hostname === "127.0.0.1") {
      u.hostname = "api";
    }
    return u.toString().replace(/\/$/, "");
  } catch {
    return "http://api:8000";
  }
}
