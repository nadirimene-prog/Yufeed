"use client";

import { useEffect, useEffectEvent, useMemo, useState } from "react";
import { BookmarkPlus, Save, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import type {
  DashboardLayoutPreferences,
  DashboardSavedViewCreateRequest,
  DashboardSavedViewRecord,
  DashboardSavedViewRole,
  DashboardSavedViewScope,
  DashboardWorkQueueParams,
} from "@/features/dashboard/types";

interface DashboardSavedViewsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  views: DashboardSavedViewRecord[];
  loading?: boolean;
  currentRole?: string | null;
  currentFilters: DashboardWorkQueueParams;
  currentLayoutPrefs: DashboardLayoutPreferences;
  activeViewId: string | null;
  defaultSavedViewId: string | null;
  onApplyView: (view: DashboardSavedViewRecord) => void;
  onCreateView: (
    payload: DashboardSavedViewCreateRequest,
    options?: { setAsUserDefault?: boolean },
  ) => Promise<void>;
  onUpdateView: (
    viewId: string,
    payload: Partial<DashboardSavedViewCreateRequest>,
    options?: { setAsUserDefault?: boolean },
  ) => Promise<void>;
  onDeleteView: (viewId: string) => Promise<void>;
  onSetUserDefaultView: (viewId: string | null) => Promise<void>;
  pending?: boolean;
}

const ROLE_OPTIONS: Array<{ value: DashboardSavedViewRole; label: string }> = [
  { value: "analyst", label: "Analyst" },
  { value: "reviewer", label: "Reviewer" },
  { value: "manager", label: "Manager" },
  { value: "qa_audit", label: "QA / Audit" },
];

function isSupportedRole(
  value: string | null | undefined,
): value is DashboardSavedViewRole {
  return ROLE_OPTIONS.some((option) => option.value === value);
}

export function DashboardSavedViewsDialog({
  open,
  onOpenChange,
  views,
  loading = false,
  currentRole = null,
  currentFilters,
  currentLayoutPrefs,
  activeViewId,
  defaultSavedViewId,
  onApplyView,
  onCreateView,
  onUpdateView,
  onDeleteView,
  onSetUserDefaultView,
  pending = false,
}: DashboardSavedViewsDialogProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [scope, setScope] = useState<DashboardSavedViewScope>("private");
  const [setRoleDefault, setSetRoleDefault] = useState(false);
  const [role, setRole] = useState<DashboardSavedViewRole | "">("");
  const [setAsUserDefault, setSetAsUserDefault] = useState(false);

  const selectedView = useMemo(
    () => views.find((view) => view.id === selectedId) ?? null,
    [selectedId, views],
  );

  const syncSelectedId = useEffectEvent(() => {
    setSelectedId((current) => {
      if (current && views.some((view) => view.id === current)) {
        return current;
      }
      if (activeViewId && views.some((view) => view.id === activeViewId)) {
        return activeViewId;
      }
      return views[0]?.id ?? null;
    });
  });

  const syncFormState = useEffectEvent(() => {
    if (!selectedView) {
      setName("");
      setScope("private");
      setSetRoleDefault(false);
      setRole(isSupportedRole(currentRole) ? currentRole : "");
      setSetAsUserDefault(false);
      return;
    }
    setName(selectedView.name);
    setScope(selectedView.scope);
    setSetRoleDefault(
      Boolean(selectedView.is_default_for_role && selectedView.role),
    );
    setRole(
      selectedView.role ?? (isSupportedRole(currentRole) ? currentRole : ""),
    );
    setSetAsUserDefault(defaultSavedViewId === selectedView.id);
  });

  useEffect(() => {
    if (!open) return;
    syncSelectedId();
  }, [open, views, activeViewId]);

  useEffect(() => {
    if (!open) return;
    syncFormState();
  }, [open, selectedView, defaultSavedViewId, currentRole]);

  const savePayloadBase = (): DashboardSavedViewCreateRequest => ({
    name: name.trim() || "Saved view",
    scope,
    filters: currentFilters,
    layout_prefs: currentLayoutPrefs,
    is_default_for_role: setRoleDefault && Boolean(role),
    role: setRoleDefault && role ? role : null,
  });

  const handleCreate = async () => {
    await onCreateView(savePayloadBase(), { setAsUserDefault });
  };

  const handleUpdate = async () => {
    if (!selectedView) return;
    await onUpdateView(selectedView.id, savePayloadBase(), {
      setAsUserDefault,
    });
  };

  const handleDelete = async () => {
    if (!selectedView) return;
    await onDeleteView(selectedView.id);
    if (defaultSavedViewId === selectedView.id) {
      await onSetUserDefaultView(null);
    }
  };

  const handleApply = async () => {
    if (!selectedView) return;
    onApplyView(selectedView);
    if (setAsUserDefault && defaultSavedViewId !== selectedView.id) {
      await onSetUserDefaultView(selectedView.id);
    }
    if (!setAsUserDefault && defaultSavedViewId === selectedView.id) {
      await onSetUserDefaultView(null);
    }
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle>Saved Dashboard Views</DialogTitle>
          <DialogDescription>
            Save and share queue filters plus layout preferences for faster
            triage.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 lg:grid-cols-[260px_minmax(0,1fr)]">
          <div className="rounded-xl border border-border bg-slate-50 p-2">
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Available Views
              </h3>
              <span className="text-[11px] text-muted-foreground">
                {views.length}
              </span>
            </div>
            <div className="max-h-72 space-y-1 overflow-auto pr-1">
              {loading ? (
                <div className="rounded-lg border border-border bg-white px-2 py-2 text-xs text-muted-foreground">
                  Loading saved views…
                </div>
              ) : views.length === 0 ? (
                <div className="rounded-lg border border-border bg-white px-2 py-2 text-xs text-muted-foreground">
                  No saved views yet.
                </div>
              ) : (
                views.map((view) => {
                  const selected = view.id === selectedId;
                  const active = view.id === activeViewId;
                  return (
                    <button
                      key={view.id}
                      type="button"
                      onClick={() => setSelectedId(view.id)}
                      className={cn(
                        "w-full rounded-lg border px-2 py-2 text-left transition",
                        selected
                          ? "border-primary/40 bg-primary/5"
                          : "border-border bg-white hover:border-border/70",
                      )}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="truncate text-xs font-medium text-foreground">
                            {view.name}
                          </p>
                          <p className="mt-0.5 text-[11px] text-muted-foreground">
                            {view.scope === "team" ? "Team" : "Private"}
                            {view.role ? ` • ${view.role}` : ""}
                          </p>
                        </div>
                        <div className="flex flex-col items-end gap-1">
                          {active ? (
                            <span className="rounded-full bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold text-primary">
                              Active
                            </span>
                          ) : null}
                          {defaultSavedViewId === view.id ? (
                            <span className="rounded-full bg-slate-200 px-1.5 py-0.5 text-[10px] text-slate-700">
                              My default
                            </span>
                          ) : null}
                        </div>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </div>

          <div className="space-y-4">
            <section className="rounded-xl border border-border bg-white p-3">
              <h3 className="mb-2 text-sm font-semibold text-foreground">
                Save / Update View
              </h3>
              <div className="grid gap-3 md:grid-cols-2">
                <label className="flex flex-col gap-1 text-xs text-muted-foreground">
                  Name
                  <input
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    placeholder="e.g. Analyst P1 Queue"
                    className="h-9 rounded-lg border border-border bg-white px-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
                  />
                </label>

                <label className="flex flex-col gap-1 text-xs text-muted-foreground">
                  Scope
                  <select
                    value={scope}
                    onChange={(event) =>
                      setScope(event.target.value as DashboardSavedViewScope)
                    }
                    className="h-9 rounded-lg border border-border bg-white px-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
                  >
                    <option value="private">Private</option>
                    <option value="team">Team</option>
                  </select>
                </label>
              </div>

              <div className="mt-3 grid gap-2 md:grid-cols-2">
                <label className="inline-flex items-center gap-2 text-xs text-foreground">
                  <input
                    type="checkbox"
                    checked={setAsUserDefault}
                    onChange={(event) =>
                      setSetAsUserDefault(event.target.checked)
                    }
                    className="rounded border-border text-primary focus:ring-primary"
                  />
                  Set as my default view
                </label>
                <label className="inline-flex items-center gap-2 text-xs text-foreground">
                  <input
                    type="checkbox"
                    checked={setRoleDefault}
                    onChange={(event) =>
                      setSetRoleDefault(event.target.checked)
                    }
                    className="rounded border-border text-primary focus:ring-primary"
                  />
                  Set as role default
                </label>
              </div>

              {setRoleDefault ? (
                <div className="mt-2">
                  <label className="flex flex-col gap-1 text-xs text-muted-foreground">
                    Role
                    <select
                      value={role}
                      onChange={(event) =>
                        setRole(
                          event.target.value as DashboardSavedViewRole | "",
                        )
                      }
                      className="h-9 rounded-lg border border-border bg-white px-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
                    >
                      <option value="">Select role</option>
                      {ROLE_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              ) : null}

              <div className="mt-3 rounded-lg border border-border bg-slate-50 p-2 text-[11px] text-muted-foreground">
                Saves current queue filters and layout prefs:{" "}
                {currentLayoutPrefs.queueDensity ?? "comfortable"} density,{" "}
                insights {currentLayoutPrefs.insightsOpen ? "open" : "closed"},
                default tab{" "}
                {currentLayoutPrefs.defaultWorkspaceTab ?? "overview"}.
              </div>
            </section>

            <section className="rounded-xl border border-border bg-white p-3">
              <h3 className="mb-2 text-sm font-semibold text-foreground">
                Selected View Actions
              </h3>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={handleApply}
                  disabled={!selectedView || pending}
                >
                  Apply selected
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={handleCreate}
                  disabled={pending || name.trim().length === 0}
                >
                  <BookmarkPlus className="mr-1.5 h-3.5 w-3.5" />
                  Save as new
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={handleUpdate}
                  disabled={
                    !selectedView || pending || name.trim().length === 0
                  }
                >
                  <Save className="mr-1.5 h-3.5 w-3.5" />
                  Overwrite selected
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={handleDelete}
                  disabled={!selectedView || pending}
                >
                  <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                  Delete selected
                </Button>
              </div>
            </section>
          </div>
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default DashboardSavedViewsDialog;
