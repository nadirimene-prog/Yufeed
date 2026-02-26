"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface ShortcutHelpDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const SHORTCUT_SECTIONS: Array<{
  title: string;
  items: Array<{ keys: string; description: string }>;
}> = [
  {
    title: "Navigation",
    items: [
      { keys: "j / k", description: "Move to next/previous queue item" },
      { keys: "g then q", description: "Focus queue search" },
      { keys: "g then d", description: "Focus workspace panel" },
      { keys: "i", description: "Toggle insights rail" },
    ],
  },
  {
    title: "Actions",
    items: [
      { keys: "a", description: "Focus assignee field in Actions tab" },
      { keys: "e", description: "Run Escalate action (if available)" },
      { keys: "n", description: "Run first available '+ Next' action" },
      { keys: "x", description: "Toggle selection for current queue item" },
    ],
  },
  {
    title: "Help",
    items: [
      { keys: "?", description: "Open shortcut help" },
      { keys: "Ctrl/Cmd + K", description: "Open command palette" },
    ],
  },
];

export function ShortcutHelpDialog({
  open,
  onOpenChange,
}: ShortcutHelpDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg" aria-label="Keyboard shortcuts">
        <DialogHeader>
          <DialogTitle>Keyboard Shortcuts</DialogTitle>
          <DialogDescription>
            Power-user shortcuts for queue triage and workspace actions.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {SHORTCUT_SECTIONS.map((section) => (
            <section key={section.title}>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {section.title}
              </h3>
              <div className="space-y-1.5">
                {section.items.map((item) => (
                  <div
                    key={`${section.title}-${item.keys}`}
                    className="flex items-center justify-between gap-3 rounded-lg border border-border bg-slate-50 px-3 py-2"
                  >
                    <span className="text-xs text-foreground">
                      {item.description}
                    </span>
                    <kbd className="shrink-0 rounded border border-border bg-white px-2 py-0.5 font-mono text-[11px] text-foreground">
                      {item.keys}
                    </kbd>
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default ShortcutHelpDialog;
