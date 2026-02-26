"use client";

import { useEffect, useRef } from "react";
import apiClient from "@/lib/http";
import type {
  DashboardTelemetryEventName,
  DashboardTelemetryPayload,
} from "@/features/dashboard/telemetry";

interface DashboardTelemetryEnvelope {
  event: DashboardTelemetryEventName;
  payload: DashboardTelemetryPayload;
  at: string;
}

interface UseDashboardTelemetryBridgeOptions {
  enabled?: boolean;
  flushIntervalMs?: number;
  maxBatchSize?: number;
}

export function useDashboardTelemetryBridge({
  enabled = true,
  flushIntervalMs = 2000,
  maxBatchSize = 20,
}: UseDashboardTelemetryBridgeOptions = {}) {
  const queueRef = useRef<DashboardTelemetryEnvelope[]>([]);
  const flushTimerRef = useRef<number | null>(null);
  const flushingRef = useRef(false);

  useEffect(() => {
    if (!enabled) return;

    const clearFlushTimer = () => {
      if (flushTimerRef.current) {
        window.clearTimeout(flushTimerRef.current);
        flushTimerRef.current = null;
      }
    };

    const flushQueue = async () => {
      if (flushingRef.current) return;
      if (queueRef.current.length === 0) return;

      flushingRef.current = true;
      const batch = queueRef.current.splice(0, maxBatchSize);
      try {
        await apiClient.post("/api/dashboard/telemetry/events", {
          events: batch,
        });
      } catch {
        // Requeue at the front, but cap queue growth to avoid unbounded memory.
        queueRef.current = [...batch, ...queueRef.current].slice(0, 200);
      } finally {
        flushingRef.current = false;
        if (queueRef.current.length > 0) {
          clearFlushTimer();
          flushTimerRef.current = window.setTimeout(
            () => {
              void flushQueue();
            },
            Math.max(250, flushIntervalMs),
          );
        }
      }
    };

    const scheduleFlush = () => {
      if (queueRef.current.length >= maxBatchSize) {
        clearFlushTimer();
        void flushQueue();
        return;
      }
      if (flushTimerRef.current) return;
      flushTimerRef.current = window.setTimeout(
        () => {
          flushTimerRef.current = null;
          void flushQueue();
        },
        Math.max(250, flushIntervalMs),
      );
    };

    const onTelemetry = (event: WindowEventMap["dashboard:telemetry"]) => {
      queueRef.current.push(event.detail);
      if (queueRef.current.length > 200) {
        queueRef.current = queueRef.current.slice(-200);
      }
      scheduleFlush();
    };

    const onPageHide = () => {
      clearFlushTimer();
      if (queueRef.current.length === 0) return;
      void flushQueue();
    };

    window.addEventListener(
      "dashboard:telemetry",
      onTelemetry as EventListener,
    );
    window.addEventListener("pagehide", onPageHide);
    window.addEventListener("beforeunload", onPageHide);

    return () => {
      window.removeEventListener(
        "dashboard:telemetry",
        onTelemetry as EventListener,
      );
      window.removeEventListener("pagehide", onPageHide);
      window.removeEventListener("beforeunload", onPageHide);
      clearFlushTimer();
      if (queueRef.current.length > 0) {
        void flushQueue();
      }
    };
  }, [enabled, flushIntervalMs, maxBatchSize]);
}

export default useDashboardTelemetryBridge;
