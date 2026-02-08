"use client";

import { Suspense } from "react";
import AuditTrail from "@/components/audit/audit-trail";

export default function AuditPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        <Suspense
          fallback={
            <div className="animate-pulse text-white/50 text-center py-8">
              Loading audit trail...
            </div>
          }
        >
          <AuditTrail />
        </Suspense>
      </div>
    </div>
  );
}
