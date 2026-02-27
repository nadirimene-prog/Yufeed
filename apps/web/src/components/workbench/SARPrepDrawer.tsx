"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { type FormEvent, useEffect, useState } from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button-horizon";
import apiClient from "@/lib/http";
import SARLifecycleTracker, {
  type SARLifecycleData,
} from "@/components/workbench/SARLifecycleTracker";

interface SARPrepDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  caseId?: string;
  entityId?: string;
  onPrepared?: (sarId?: string) => void;
}

export function SARPrepDrawer({
  open,
  onOpenChange,
  caseId,
  entityId,
  onPrepared,
}: SARPrepDrawerProps) {
  const [narrative, setNarrative] = useState("");
  const [regulatoryBasis, setRegulatoryBasis] = useState(
    "Suspicious activity threshold exceeded",
  );
  const [jurisdiction, setJurisdiction] = useState("US");
  const [submitting, setSubmitting] = useState(false);
  const [lifecycle, setLifecycle] = useState<SARLifecycleData | null>(null);

  useEffect(() => {
    if (!open || !caseId) return;
    let cancelled = false;

    apiClient
      .get(`/api/cases/${encodeURIComponent(caseId)}`)
      .then((response) => {
        if (cancelled) return;
        const evidence = response.data?.evidence;
        if (evidence && typeof evidence === "object") {
          setLifecycle((evidence.sar_lifecycle as SARLifecycleData) ?? null);
        } else {
          setLifecycle(null);
        }
      })
      .catch(() => {
        if (!cancelled) setLifecycle(null);
      });

    return () => {
      cancelled = true;
    };
  }, [open, caseId]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      const response = await apiClient.post("/api/aml-officer/sar/prepare", {
        case_id: caseId,
        case_data: {
          subject_id: entityId,
          narrative,
          regulatory_basis: regulatoryBasis,
          jurisdiction,
        },
      });
      if (response.data?.sar_lifecycle) {
        setLifecycle(response.data.sar_lifecycle as SARLifecycleData);
      }
      onPrepared?.(response.data?.sar_id);
      onOpenChange(false);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/60" />
        <Dialog.Content className="fixed right-0 top-0 z-50 h-screen w-[min(680px,92vw)] border-l border-border-subtle bg-background-elevated p-5 shadow-xl">
          <div className="mb-4 flex items-center justify-between">
            <Dialog.Title className="text-lg font-semibold text-foreground">
              Prepare SAR Filing
            </Dialog.Title>
            <Dialog.Close asChild>
              <button
                type="button"
                className="rounded-md p-1 text-foreground-secondary hover:bg-background-overlay"
                aria-label="Close"
              >
                <X className="h-4 w-4" />
              </button>
            </Dialog.Close>
          </div>

          <form
            className="flex h-[calc(100%-3rem)] flex-col gap-3"
            onSubmit={handleSubmit}
          >
            {lifecycle ? <SARLifecycleTracker lifecycle={lifecycle} /> : null}

            <div className="space-y-1">
              <label className="text-xs text-foreground-secondary">
                Regulatory Basis
              </label>
              <input
                value={regulatoryBasis}
                onChange={(event) => setRegulatoryBasis(event.target.value)}
                className="h-10 w-full rounded-lg border border-border bg-background-overlay px-3 text-sm"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs text-foreground-secondary">
                Jurisdiction
              </label>
              <input
                value={jurisdiction}
                onChange={(event) =>
                  setJurisdiction(event.target.value.toUpperCase())
                }
                className="h-10 w-full rounded-lg border border-border bg-background-overlay px-3 text-sm"
              />
            </div>

            <div className="min-h-0 flex-1 space-y-1">
              <label className="text-xs text-foreground-secondary">
                Narrative
              </label>
              <textarea
                value={narrative}
                onChange={(event) => setNarrative(event.target.value)}
                className="h-full min-h-[220px] w-full rounded-lg border border-border bg-background-overlay px-3 py-2 text-sm"
              />
            </div>

            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
              >
                Cancel
              </Button>
              <Button type="submit" loading={submitting}>
                Save draft
              </Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export default SARPrepDrawer;
