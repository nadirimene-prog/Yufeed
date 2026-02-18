"use client";

import Link from "next/link";
import { obligationStatusStyle } from "@/app/compliance/obligations/[id]/components/utils";

export default function LinkedPolicyCard({
  policy,
}: {
  policy: { id: number; policy_id: string; name: string; status: string };
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="text-sm font-semibold text-gray-900 dark:text-white">
        Linked Policy
      </div>
      <Link
        href={`/compliance/policies/${policy.id}`}
        className="mt-3 flex items-center gap-3 rounded-lg border border-gray-100 bg-gray-50/60 p-3 hover:bg-gray-100 dark:border-slate-800 dark:bg-slate-800/40 dark:hover:bg-slate-800"
      >
        <div className="flex-1">
          <div className="text-sm font-medium text-gray-900 dark:text-white">
            {policy.name}
          </div>
          <div className="text-xs text-gray-500">{policy.policy_id}</div>
        </div>
        <span
          className={
            "rounded-full px-2 py-1 text-[10px] font-semibold " +
            obligationStatusStyle(policy.status)
          }
        >
          {policy.status}
        </span>
      </Link>
    </div>
  );
}
