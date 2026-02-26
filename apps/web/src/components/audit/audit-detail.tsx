"use client";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { AuditLog } from "./audit-table";

interface AuditDetailProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  log?: AuditLog | null;
}

function JsonBlock({ value }: { value: unknown }) {
  if (!value) {
    return <div className="text-sm text-slate-500 ">No data</div>;
  }
  return (
    <pre className="text-xs bg-slate-950 text-slate-100 rounded-md p-3 overflow-auto max-h-64">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

export default function AuditDetail({
  open,
  onOpenChange,
  log,
}: AuditDetailProps) {
  if (!log) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>Audit Entry {log.audit_id}</DialogTitle>
          <DialogDescription>
            {log.actor_email || log.actor_id || "anonymous"} · {log.created_at}
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div className="space-y-2">
            <div>
              <div className="text-xs uppercase text-slate-500">Entity</div>
              <div className="font-medium text-slate-900 ">
                {log.entity_type || "unknown"} · {log.entity_id || "—"}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase text-slate-500">Action</div>
              <div className="font-medium text-slate-900 ">
                {log.action || log.method || "n/a"}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase text-slate-500">Status</div>
              <div className="font-medium text-slate-900 ">
                {log.status_code ?? "—"}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase text-slate-500">Path</div>
              <div className="font-medium text-slate-900 ">
                {log.path || "—"}
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <div>
              <div className="text-xs uppercase text-slate-500">Actor</div>
              <div className="font-medium text-slate-900 ">
                {log.actor_email || log.actor_id || "anonymous"}
              </div>
              <div className="text-xs text-slate-500 ">
                {log.actor_role || log.actor_type || "—"}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase text-slate-500">IP / UA</div>
              <div className="font-medium text-slate-900 ">
                {log.actor_ip || "—"}
              </div>
              <div className="text-xs text-slate-500  line-clamp-2">
                {log.user_agent || "—"}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase text-slate-500">Request ID</div>
              <div className="font-medium text-slate-900 ">
                {log.request_id || "—"}
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <div className="text-xs uppercase text-slate-500 mb-2">Changes</div>
            <JsonBlock value={log.changes} />
          </div>
          <div>
            <div className="text-xs uppercase text-slate-500 mb-2">
              Metadata
            </div>
            <JsonBlock value={log.metadata} />
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
