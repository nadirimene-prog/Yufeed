"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { type FormEvent, useState } from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button-horizon";
import apiClient from "@/lib/http";

interface CreateCaseModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  entityId?: string;
  onCreated?: (caseId: string) => void;
}

export function CreateCaseModal({
  open,
  onOpenChange,
  entityId,
  onCreated,
}: CreateCaseModalProps) {
  const [caseType, setCaseType] = useState("transaction_monitoring");
  const [severity, setSeverity] = useState("medium");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      const response = await apiClient.post("/api/cases/", {
        case_type: caseType,
        severity,
        description,
        subject_type: "user",
        subject_id: entityId,
      });
      const createdCase = response.data;
      onCreated?.(createdCase.case_id ?? String(createdCase.id));
      onOpenChange(false);
      setDescription("");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/60" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[min(560px,92vw)] -translate-x-1/2 -translate-y-1/2 rounded-xl border border-border-subtle bg-bg-elevated p-5 shadow-xl">
          <div className="mb-4 flex items-center justify-between">
            <Dialog.Title className="text-lg font-semibold text-foreground">
              Create Case
            </Dialog.Title>
            <Dialog.Close asChild>
              <button
                type="button"
                className="rounded-md p-1 text-foreground-secondary hover:bg-bg-overlay"
                aria-label="Close"
              >
                <X className="h-4 w-4" />
              </button>
            </Dialog.Close>
          </div>

          <form className="space-y-3" onSubmit={handleSubmit}>
            <div className="space-y-1">
              <label className="text-xs text-foreground-secondary">
                Case Type
              </label>
              <input
                value={caseType}
                onChange={(event) => setCaseType(event.target.value)}
                className="h-10 w-full rounded-lg border border-border-default bg-bg-overlay px-3 text-sm"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs text-foreground-secondary">
                Severity
              </label>
              <select
                value={severity}
                onChange={(event) => setSeverity(event.target.value)}
                className="h-10 w-full rounded-lg border border-border-default bg-bg-overlay px-3 text-sm"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs text-foreground-secondary">
                Description
              </label>
              <textarea
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                rows={4}
                className="w-full rounded-lg border border-border-default bg-bg-overlay px-3 py-2 text-sm"
              />
            </div>

            <div className="flex justify-end gap-2 pt-1">
              <Button
                type="button"
                variant="glass"
                onClick={() => onOpenChange(false)}
              >
                Cancel
              </Button>
              <Button type="submit" loading={submitting}>
                Create Case
              </Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export default CreateCaseModal;
