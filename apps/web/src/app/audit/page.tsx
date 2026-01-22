"use client";

import AuditTrail from "@/components/audit/audit-trail";

export default function AuditPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        <AuditTrail />
      </div>
    </div>
  );
}
