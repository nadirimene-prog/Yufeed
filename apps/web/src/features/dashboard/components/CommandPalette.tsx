"use client";

import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
} from "@/components/ui/command";

export interface DashboardCommandAction {
  id: string;
  label: string;
  shortcut?: string;
  group?: string;
  disabled?: boolean;
  onSelect: () => void;
}

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  actions: DashboardCommandAction[];
}

function groupActions(actions: DashboardCommandAction[]) {
  const groups = new Map<string, DashboardCommandAction[]>();
  for (const action of actions) {
    const group = action.group ?? "General";
    const list = groups.get(group);
    if (list) {
      list.push(action);
    } else {
      groups.set(group, [action]);
    }
  }
  return [...groups.entries()];
}

export function CommandPalette({
  open,
  onOpenChange,
  actions,
}: CommandPaletteProps) {
  const grouped = groupActions(actions);

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput placeholder="Run a dashboard command…" />
      <CommandList>
        <CommandEmpty>No matching commands.</CommandEmpty>
        {grouped.map(([group, groupActions], index) => (
          <div key={group}>
            <CommandGroup heading={group}>
              {groupActions.map((action) => (
                <CommandItem
                  key={action.id}
                  value={`${group} ${action.label}`}
                  disabled={action.disabled}
                  onSelect={() => {
                    onOpenChange(false);
                    action.onSelect();
                  }}
                >
                  <span>{action.label}</span>
                  {action.shortcut ? (
                    <CommandShortcut>{action.shortcut}</CommandShortcut>
                  ) : null}
                </CommandItem>
              ))}
            </CommandGroup>
            {index < grouped.length - 1 ? <CommandSeparator /> : null}
          </div>
        ))}
      </CommandList>
    </CommandDialog>
  );
}

export default CommandPalette;
