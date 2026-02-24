"use client";

import { Suspense } from "react";
import AuditTrail from "@/components/audit/audit-trail";

export default function AuditPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        <Suspense
          fallback={
            <div className="animate-pulse text-muted-foreground text-center py-8">
              Compiling audit lineage and security records...
            </div>
          }
        >
          <AuditTrail />
        </Suspense>
      </div>
    </div>
  );
}
