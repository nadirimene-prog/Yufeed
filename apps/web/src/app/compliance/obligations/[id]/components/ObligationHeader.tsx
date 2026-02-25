"use client";

import Link from "next/link";
import { obligationStatusStyle } from "@/app/compliance/obligations/[id]/components/utils";

export default function ObligationHeader({
  obligationId,
  title,
  celex,
  jurisdiction,
  sourceSystem,
  status,
}: {
  obligationId: string;
  title: string;
  celex?: string | null;
  jurisdiction?: string | null;
  sourceSystem?: string | null;
  status: string;
}) {
  return (
    <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
      <div>
        <div className="text-xs text-slate-500">Obligation {obligationId}</div>
        <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
        <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-500">
          <span>{celex ?? "—"}</span>
          <span>•</span>
          <span>{jurisdiction ?? "EU"}</span>
          <span>•</span>
          <span>{sourceSystem ?? "source"}</span>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <span
          className={
            "rounded-full px-3 py-1 text-xs font-semibold" +
            obligationStatusStyle(status)
          }
        >
          {status.replace("_", "")}
        </span>
        <Link
          href="/compliance/obligations"
          className="rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-medium text-slate-600 hover:border-slate-300"
        >
          Back
        </Link>
      </div>
    </div>
  );
}
