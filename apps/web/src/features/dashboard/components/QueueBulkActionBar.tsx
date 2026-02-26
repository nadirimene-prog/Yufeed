"use client";

import { Button } from "@/components/ui/button";

type BulkAction = "assign" | "escalate" | "mark_in_progress";

interface QueueBulkActionBarProps {
  selectedCount: number;
  allSelectedOnPage: boolean;
  bulkAssignee: string;
  users: Array<{ user_id: string }>;
  canBulkAction: boolean;
  onToggleSelectAllOnPage: (checked: boolean) => void;
  onBulkAssigneeChange: (value: string) => void;
  onRunBulkAction: (action: BulkAction, label: string) => void;
  onClear: () => void;
}

export function QueueBulkActionBar({
  selectedCount,
  allSelectedOnPage,
  bulkAssignee,
  users,
  canBulkAction,
  onToggleSelectAllOnPage,
  onBulkAssigneeChange,
  onRunBulkAction,
  onClear,
}: QueueBulkActionBarProps) {
  if (selectedCount <= 0) return null;

  return (
    <div className="mb-2 sticky top-0 z-10 rounded-xl border border-border bg-slate-50/95 p-2 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-slate-50/85">
      <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
        <span className="rounded-md border border-border bg-white px-2 py-1 font-medium text-foreground">
          {selectedCount} selected
        </span>
        <label className="inline-flex items-center gap-1 rounded-md border border-border bg-white px-2 py-1">
          <input
            type="checkbox"
            aria-label="Select all items on this page"
            checked={allSelectedOnPage}
            onChange={(event) => onToggleSelectAllOnPage(event.target.checked)}
            className="rounded border-border focus:ring-primary text-primary"
          />
          Select all on page
        </label>
        <select
          value={bulkAssignee}
          onChange={(event) => onBulkAssigneeChange(event.target.value)}
          className="h-8 min-w-[150px] rounded-lg border border-border bg-white px-2 text-[11px] text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20"
          aria-label="Bulk assignment analyst"
        >
          <option value="">Assign to...</option>
          {users.map((user) => (
            <option key={user.user_id} value={user.user_id}>
              {user.user_id}
            </option>
          ))}
        </select>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onRunBulkAction("assign", "Bulk assign")}
          disabled={!canBulkAction || bulkAssignee.trim().length === 0}
        >
          Bulk assign
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onRunBulkAction("escalate", "Escalate")}
          disabled={!canBulkAction}
        >
          Escalate
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onRunBulkAction("mark_in_progress", "Mark In Progress")}
          disabled={!canBulkAction}
        >
          In Progress
        </Button>
        <Button variant="outline" size="sm" onClick={onClear}>
          Clear
        </Button>
      </div>
    </div>
  );
}

export default QueueBulkActionBar;
