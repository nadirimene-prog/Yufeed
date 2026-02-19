"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, FileText, Search, User, Workflow } from "lucide-react";
import apiClient from "@/lib/http";
import { NAV_AREAS } from "@/components/nav-data";
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

interface OmniscientSearchResult {
  id: string;
  type: "entity" | "alert" | "case" | "rule" | string;
  title: string;
  subtitle?: string | null;
  href: string;
}

const OPEN_COMMAND_EVENT = "open-command-palette";

function typeIcon(type: OmniscientSearchResult["type"]) {
  if (type === "entity") return User;
  if (type === "alert") return AlertTriangle;
  if (type === "case") return FileText;
  if (type === "rule") return Workflow;
  return Search;
}

function flattenPageShortcuts() {
  return NAV_AREAS.flatMap((area) =>
    area.items.map((item) => ({
      id: `page:${item.href}`,
      title: item.label,
      subtitle: item.description ?? area.label,
      href: item.href,
      type: "page" as const,
    })),
  );
}

export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = React.useState(false);
  const [query, setQuery] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [results, setResults] = React.useState<OmniscientSearchResult[]>([]);
  const pageShortcuts = React.useMemo(() => flattenPageShortcuts(), []);

  React.useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((current) => !current);
        return;
      }

      if (event.key === "Escape") {
        setOpen(false);
      }
    };

    const onOpenRequest = () => setOpen(true);

    document.addEventListener("keydown", onKeyDown);
    window.addEventListener(OPEN_COMMAND_EVENT, onOpenRequest);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      window.removeEventListener(OPEN_COMMAND_EVENT, onOpenRequest);
    };
  }, []);

  React.useEffect(() => {
    if (!open) {
      setQuery("");
      setResults([]);
    }
  }, [open]);

  React.useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setResults([]);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);

    const timeoutId = window.setTimeout(async () => {
      try {
        const response = await apiClient.get<{
          results: OmniscientSearchResult[];
        }>("/api/search/omniscient", {
          params: {
            q: trimmed,
            scope: "all",
            limit: 30,
          },
        });
        if (!cancelled) {
          setResults(response.data.results ?? []);
        }
      } catch {
        if (!cancelled) {
          setResults([]);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }, 180);

    return () => {
      cancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [query]);

  const filteredPages = React.useMemo(() => {
    const search = query.trim().toLowerCase();
    if (search.length === 0) return pageShortcuts.slice(0, 8);
    return pageShortcuts
      .filter(
        (item) =>
          item.title.toLowerCase().includes(search) ||
          (item.subtitle ?? "").toLowerCase().includes(search),
      )
      .slice(0, 8);
  }, [pageShortcuts, query]);

  const grouped = React.useMemo(() => {
    const byType: Record<string, OmniscientSearchResult[]> = {};
    for (const result of results) {
      if (!byType[result.type]) byType[result.type] = [];
      byType[result.type].push(result);
    }
    return byType;
  }, [results]);

  const runNavigation = React.useCallback(
    (href: string) => {
      setOpen(false);
      router.push(href);
    },
    [router],
  );

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput
        value={query}
        onValueChange={setQuery}
        placeholder="Search entities, alerts, cases, rules, or pages..."
      />
      <CommandList>
        <CommandEmpty>
          {loading ? "Searching..." : "No results found."}
        </CommandEmpty>

        {query.trim().length < 2 ? (
          <>
            <CommandGroup heading="Quick Navigation">
              {filteredPages.map((item) => (
                <CommandItem
                  key={item.id}
                  onSelect={() => runNavigation(item.href)}
                >
                  <Search className="mr-2 h-4 w-4" />
                  <span>{item.title}</span>
                  {item.subtitle ? (
                    <span className="ml-2 truncate text-xs text-muted-foreground">
                      {item.subtitle}
                    </span>
                  ) : null}
                </CommandItem>
              ))}
            </CommandGroup>
            <CommandSeparator />
            <CommandGroup heading="Hints">
              <CommandItem disabled>
                <span>Type at least 2 characters for omniscient search</span>
                <CommandShortcut>⌘K</CommandShortcut>
              </CommandItem>
            </CommandGroup>
          </>
        ) : (
          <>
            {Object.entries(grouped).map(([type, items]) => (
              <CommandGroup
                key={type}
                heading={type.charAt(0).toUpperCase() + type.slice(1)}
              >
                {items.map((item) => {
                  const Icon = typeIcon(item.type);
                  return (
                    <CommandItem
                      key={`${item.type}:${item.id}`}
                      onSelect={() => runNavigation(item.href)}
                    >
                      <Icon className="mr-2 h-4 w-4" />
                      <span>{item.title}</span>
                      {item.subtitle ? (
                        <span className="ml-2 truncate text-xs text-muted-foreground">
                          {item.subtitle}
                        </span>
                      ) : null}
                    </CommandItem>
                  );
                })}
              </CommandGroup>
            ))}

            {filteredPages.length > 0 ? (
              <>
                <CommandSeparator />
                <CommandGroup heading="Pages">
                  {filteredPages.map((item) => (
                    <CommandItem
                      key={item.id}
                      onSelect={() => runNavigation(item.href)}
                    >
                      <Search className="mr-2 h-4 w-4" />
                      <span>{item.title}</span>
                    </CommandItem>
                  ))}
                </CommandGroup>
              </>
            ) : null}
          </>
        )}
      </CommandList>
    </CommandDialog>
  );
}

export default CommandPalette;
