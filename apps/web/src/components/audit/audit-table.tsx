"use client";

import { format } from "date-fns";
import { cn } from "@/lib/utils";

export interface AuditLog {
  audit_id: string;
  actor_id?: string | null;
  actor_email?: string | null;
  actor_role?: string | null;
  actor_type?: string | null;
  actor_ip?: string | null;
  user_agent?: string | null;
  action?: string | null;
  method?: string | null;
  path?: string | null;
  entity_type?: string | null;
  entity_id?: string | null;
  status_code?: number | null;
  request_id?: string | null;
  changes?: Record<string, unknown> | null;
  metadata?: Record<string, unknown> | null;
  created_at: string;
}

interface AuditTableProps {
  logs: AuditLog[];
  onSelect: (log: AuditLog) => void;
}

const actionColors: Record<string, string> = {
  post: "bg-blue-100 text-blue-800  ",
  patch: "bg-amber-100 text-amber-800  ",
  put: "bg-indigo-100 text-indigo-800  ",
  delete: "bg-red-100 text-red-800  ",
};

export default function AuditTable({ logs, onSelect }: AuditTableProps) {
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200  bg-white ">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50  text-slate-600 ">
            <tr>
              <th className="px-4 py-3 font-semibold">Time</th>
              <th className="px-4 py-3 font-semibold">Action</th>
              <th className="px-4 py-3 font-semibold">Entity</th>
              <th className="px-4 py-3 font-semibold">Actor</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Path</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 ">
            {logs.map((log) => (
              <tr
                key={log.audit_id}
                onClick={() => onSelect(log)}
                className="cursor-pointer hover:bg-slate-50 "
              >
                <td className="px-4 py-3 text-slate-600  whitespace-nowrap">
                  {format(new Date(log.created_at), "yyyy-MM-dd HH:mm:ss")}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={cn(
                      "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium uppercase",
                      actionColors[log.action || ""] ??
                        "bg-slate-100 text-slate-700  ",
                    )}
                  >
                    {log.action || log.method || "n/a"}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="text-slate-900  font-medium">
                    {log.entity_type || "unknown"}
                  </div>
                  <div className="text-xs text-slate-500 ">
                    {log.entity_id || "—"}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="text-slate-900 ">
                    {log.actor_email || log.actor_id || "anonymous"}
                  </div>
                  <div className="text-xs text-slate-500 ">
                    {log.actor_role || log.actor_type || "—"}
                  </div>
                </td>
                <td className="px-4 py-3 text-slate-700 ">
                  {log.status_code ?? "—"}
                </td>
                <td className="px-4 py-3 text-slate-500  max-w-[260px] truncate">
                  {log.path || "—"}
                </td>
              </tr>
            ))}
            {logs.length === 0 && (
              <tr>
                <td
                  className="px-4 py-6 text-center text-slate-500 "
                  colSpan={6}
                >
                  No audit entries found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
