"use client";

import { CopilotWidget } from "@/components/aml-officer/copilot-widget";
import { CopilotProvider } from "@/components/aml-officer/copilot-context";

export default function AMLOfficerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <CopilotProvider>
      <div className="relative min-h-screen">
        {/* Main Content */}
        <main>{children}</main>

        {/* Persistent AI Layer */}
        <CopilotWidget />
      </div>
    </CopilotProvider>
  );
}
