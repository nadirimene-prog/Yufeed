import Link from "next/link";
import { type ReactNode } from "react";

const TABS = [
  { key: "overview", label: "Overview" },
  { key: "alerts", label: "Alerts" },
  { key: "cases", label: "Cases" },
  { key: "transactions", label: "Transactions" },
  { key: "network", label: "Network" },
  { key: "risk", label: "Risk History" },
  { key: "timeline", label: "Timeline" },
  { key: "documents", label: "Documents" },
] as const;

export default async function EntityLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ type: string; id: string }>;
}) {
  const resolvedParams = await params;
  const base = `/entities/${resolvedParams.type}/${resolvedParams.id}`;

  return (
    <div className="space-y-4">
      <nav
        className="flex flex-wrap items-center gap-2 rounded-xl border border-border-subtle bg-bg-overlay p-2"
        aria-label="Entity profile tabs"
      >
        {TABS.map((tab) => (
          <Link
            key={tab.key}
            href={`${base}?tab=${tab.key}`}
            className="rounded-lg px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-foreground-secondary transition hover:bg-bg-floating hover:text-foreground"
          >
            {tab.label}
          </Link>
        ))}
      </nav>
      {children}
    </div>
  );
}
