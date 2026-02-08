"use client";

import * as React from "react";
import {
  Settings,
  User,
  LayoutDashboard,
  Brain,
  Search,
  Bell,
  FileText,
  Network,
  List,
} from "lucide-react";

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
import { useRouter } from "next/navigation";

export function CommandMenu() {
  const [open, setOpen] = React.useState(false);
  const router = useRouter();

  React.useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };

    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  const runCommand = React.useCallback((command: () => unknown) => {
    setOpen(false);
    command();
  }, []);

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Type a command or search..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="Suggestions">
          <CommandItem
            onSelect={() => runCommand(() => router.push("/dashboard"))}
          >
            <LayoutDashboard className="mr-2 h-4 w-4" />
            <span>Dashboard</span>
          </CommandItem>
          <CommandItem
            onSelect={() => runCommand(() => router.push("/search"))}
          >
            <Search className="mr-2 h-4 w-4" />
            <span>Global Search</span>
            <CommandShortcut>⌘S</CommandShortcut>
          </CommandItem>
          <CommandItem
            onSelect={() => runCommand(() => router.push("/aml-officer"))}
          >
            <Brain className="mr-2 h-4 w-4" />
            <span>AI Officer</span>
          </CommandItem>
        </CommandGroup>
        <CommandSeparator />
        <CommandGroup heading="Modules">
          <CommandItem
            onSelect={() => runCommand(() => router.push("/alerts"))}
          >
            <Bell className="mr-2 h-4 w-4" />
            <span>Alerts</span>
          </CommandItem>
          <CommandItem onSelect={() => runCommand(() => router.push("/cases"))}>
            <FileText className="mr-2 h-4 w-4" />
            <span>Cases</span>
          </CommandItem>
          <CommandItem
            onSelect={() => runCommand(() => router.push("/network-analysis"))}
          >
            <Network className="mr-2 h-4 w-4" />
            <span>Network Analysis</span>
          </CommandItem>
          <CommandItem
            onSelect={() => runCommand(() => router.push("/watchlists"))}
          >
            <List className="mr-2 h-4 w-4" />
            <span>Watchlists</span>
          </CommandItem>
        </CommandGroup>
        <CommandSeparator />
        <CommandGroup heading="Settings">
          <CommandItem
            onSelect={() => runCommand(() => router.push("/settings"))}
          >
            <Settings className="mr-2 h-4 w-4" />
            <span>Settings</span>
            <CommandShortcut>⌘,</CommandShortcut>
          </CommandItem>
          <CommandItem
            onSelect={() => runCommand(() => router.push("/profile"))}
          >
            <User className="mr-2 h-4 w-4" />
            <span>Profile</span>
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
