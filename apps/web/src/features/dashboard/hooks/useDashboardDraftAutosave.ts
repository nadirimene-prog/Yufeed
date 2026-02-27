"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import trackDashboardEvent from "@/features/dashboard/telemetry";

export type DashboardDraftAutosaveStatus =
  | "idle"
  | "saved"
  | "saving"
  | "retrying"
  | "error";

interface DraftPayload {
  narrative: string;
  notes: string;
}

interface PersistedDraft extends DraftPayload {
  updated_at: string;
}

type SaveAttemptResult = "success" | "error" | "busy";

interface UseDashboardDraftAutosaveOptions {
  itemId: string | null;
  narrative: string;
  notes: string;
  enabled?: boolean;
  dirty?: boolean;
  debounceMs?: number;
  onSaveDraft: (
    payload: DraftPayload,
    options?: { silent?: boolean; source?: "manual" | "autosave" },
  ) => Promise<void>;
  onSaved?: () => void;
}

const DRAFT_STORAGE_PREFIX = "dashboard:draft:";

function storageKey(itemId: string) {
  return `${DRAFT_STORAGE_PREFIX}${itemId}`;
}

export function readDashboardLocalDraft(
  itemId: string | null | undefined,
): PersistedDraft | null {
  if (!itemId || typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(storageKey(itemId));
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<PersistedDraft>;
    if (
      typeof parsed.narrative !== "string" ||
      typeof parsed.notes !== "string" ||
      typeof parsed.updated_at !== "string"
    ) {
      return null;
    }
    return {
      narrative: parsed.narrative,
      notes: parsed.notes,
      updated_at: parsed.updated_at,
    };
  } catch {
    return null;
  }
}

function writeDashboardLocalDraft(itemId: string, payload: DraftPayload) {
  if (typeof window === "undefined") return;
  const persisted: PersistedDraft = {
    ...payload,
    updated_at: new Date().toISOString(),
  };
  window.localStorage.setItem(storageKey(itemId), JSON.stringify(persisted));
}

function fingerprint(payload: DraftPayload) {
  return JSON.stringify(payload);
}

export function useDashboardDraftAutosave({
  itemId,
  narrative,
  notes,
  enabled = true,
  dirty = false,
  debounceMs = 1000,
  onSaveDraft,
  onSaved,
}: UseDashboardDraftAutosaveOptions) {
  const [status, setStatus] = useState<DashboardDraftAutosaveStatus>("idle");
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null);
  const timerRef = useRef<number | null>(null);
  const retryTimerRef = useRef<number | null>(null);
  const inFlightRef = useRef(false);
  const currentItemIdRef = useRef<string | null>(itemId);
  const lastSavedFingerprintRef = useRef<string | null>(null);
  const latestPayloadRef = useRef<DraftPayload>({ narrative, notes });
  const skipNextWriteForItemRef = useRef<string | null>(itemId);
  const previousRenderRef = useRef<{
    itemId: string | null;
    payload: DraftPayload;
    dirty: boolean;
  } | null>(null);

  const payload = useMemo(() => ({ narrative, notes }), [narrative, notes]);

  latestPayloadRef.current = payload;

  const clearTimers = useCallback(() => {
    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    if (retryTimerRef.current) {
      window.clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    currentItemIdRef.current = itemId;
    setStatus("idle");
    setLastSavedAt(null);
    lastSavedFingerprintRef.current = null;
    skipNextWriteForItemRef.current = itemId;
    clearTimers();
  }, [itemId, clearTimers]);

  useEffect(() => {
    if (!itemId) return;
    if (skipNextWriteForItemRef.current === itemId) {
      skipNextWriteForItemRef.current = null;
      return;
    }
    writeDashboardLocalDraft(itemId, payload);
  }, [itemId, payload]);

  const runSave = useCallback(
    async (
      targetItemId: string,
      targetPayload: DraftPayload,
      options: { silent?: boolean; source?: "manual" | "autosave" } = {},
    ): Promise<SaveAttemptResult> => {
      const targetFingerprint = fingerprint(targetPayload);
      if (inFlightRef.current) return "busy";
      if (
        options.source !== "manual" &&
        lastSavedFingerprintRef.current === targetFingerprint
      ) {
        if (currentItemIdRef.current === targetItemId) {
          setStatus("saved");
        }
        return "success";
      }

      inFlightRef.current = true;
      if (currentItemIdRef.current === targetItemId) {
        setStatus("saving");
      }

      try {
        await onSaveDraft(targetPayload, options);
        lastSavedFingerprintRef.current = targetFingerprint;
        trackDashboardEvent("dashboard_autosave_result", {
          source: options.source ?? "manual",
          result: "success",
          has_narrative: targetPayload.narrative.trim().length > 0,
          has_notes: targetPayload.notes.trim().length > 0,
        });
        if (currentItemIdRef.current === targetItemId) {
          setStatus("saved");
          setLastSavedAt(new Date().toISOString());
          onSaved?.();
        }
        return "success";
      } catch {
        trackDashboardEvent("dashboard_autosave_result", {
          source: options.source ?? "manual",
          result: "error",
          has_narrative: targetPayload.narrative.trim().length > 0,
          has_notes: targetPayload.notes.trim().length > 0,
        });
        if (currentItemIdRef.current === targetItemId) {
          setStatus("error");
        }
        return "error";
      } finally {
        inFlightRef.current = false;
      }
    },
    [onSaveDraft, onSaved],
  );

  useEffect(() => {
    const previous = previousRenderRef.current;
    if (
      previous &&
      previous.itemId &&
      previous.itemId !== itemId &&
      previous.dirty
    ) {
      void runSave(previous.itemId, previous.payload, {
        silent: true,
        source: "autosave",
      });
    }
    previousRenderRef.current = { itemId, payload, dirty };
  }, [dirty, itemId, payload, runSave]);

  const saveNow = useCallback(
    async (options?: { silent?: boolean; source?: "manual" | "autosave" }) => {
      if (!enabled || !itemId) return false;
      clearTimers();
      const result = await runSave(itemId, latestPayloadRef.current, {
        silent: options?.silent,
        source: options?.source ?? "manual",
      });
      return result !== "error";
    },
    [clearTimers, enabled, itemId, runSave],
  );

  useEffect(() => {
    if (!enabled || !itemId || !dirty) {
      clearTimers();
      return;
    }

    const targetPayload = payload;
    const targetFingerprint = fingerprint(targetPayload);
    if (lastSavedFingerprintRef.current === targetFingerprint) {
      return;
    }

    clearTimers();
    timerRef.current = window.setTimeout(async () => {
      timerRef.current = null;
      const saveResult = await runSave(itemId, targetPayload, {
        silent: true,
        source: "autosave",
      });
      if (saveResult === "error" && currentItemIdRef.current === itemId) {
        trackDashboardEvent("dashboard_autosave_result", {
          source: "autosave",
          result: "retrying",
        });
        setStatus("retrying");
        retryTimerRef.current = window.setTimeout(
          async () => {
            retryTimerRef.current = null;
            await runSave(itemId, latestPayloadRef.current, {
              silent: true,
              source: "autosave",
            });
          },
          Math.max(1500, debounceMs),
        );
      }
    }, debounceMs);

    return clearTimers;
  }, [clearTimers, debounceMs, dirty, enabled, itemId, payload, runSave]);

  useEffect(
    () => () => {
      clearTimers();
    },
    [clearTimers],
  );

  return {
    status,
    lastSavedAt,
    saveNow,
  };
}

export default useDashboardDraftAutosave;
