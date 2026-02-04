"use client";

import { useEffect, useMemo, useRef, useState } from "react";

export type ApiHealthStatus = "checking" | "ok" | "down";

const DEFAULT_API_URL = "http://localhost:8000";

function resolveHealthUrl(): string | null {
  const base = (process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_URL).replace(/\/$/, "");
  if (!base) return null;
  return `${base}/healthz`;
}

export function useApiHealth(pollIntervalMs = 30000) {
  const [status, setStatus] = useState<ApiHealthStatus>("checking");
  const [lastError, setLastError] = useState<string | null>(null);
  const inFlightRef = useRef(false);
  const url = useMemo(() => resolveHealthUrl(), []);

  useEffect(() => {
    if (!url) {
      setStatus("down");
      setLastError("API base URL not configured");
      return;
    }

    let mounted = true;
    let intervalId: number | null = null;

    const check = async () => {
      if (inFlightRef.current) return;
      inFlightRef.current = true;
      try {
        const res = await fetch(url, { cache: "no-store" });
        if (!mounted) return;
        if (res.ok) {
          setStatus("ok");
          setLastError(null);
        } else {
          setStatus("down");
          setLastError(`API responded ${res.status}`);
        }
      } catch (err) {
        if (!mounted) return;
        setStatus("down");
        setLastError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        inFlightRef.current = false;
      }
    };

    check();
    intervalId = window.setInterval(check, pollIntervalMs);

    return () => {
      mounted = false;
      if (intervalId !== null) {
        window.clearInterval(intervalId);
      }
    };
  }, [url, pollIntervalMs]);

  return { status, lastError, url };
}
