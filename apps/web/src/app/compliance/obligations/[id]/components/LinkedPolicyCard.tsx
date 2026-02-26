"use client";

import Link from "next/link";
import { obligationStatusStyle } from "@/app/compliance/obligations/[id]/components/utils";

export default function LinkedPolicyCard({
  policy,
}: {
  policy: { id: number; policy_id: string; name: string; status: string };
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm  ">
      <div className="text-sm font-semibold text-slate-900 ">Linked Policy</div>
      <Link
        href={`/compliance/policies/${policy.id}`}
        className="mt-3 flex items-center gap-3 rounded-lg border border-slate-100 bg-slate-50/60 p-3 hover:bg-slate-100   "
      >
        <div className="flex-1">
          <div className="text-sm font-medium text-slate-900 ">
            {policy.name}
          </div>
          <div className="text-xs text-slate-500">{policy.policy_id}</div>
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
