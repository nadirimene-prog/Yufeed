"use client";

export const dynamic = "force-dynamic";

import { Suspense } from "react";
import DashboardHub from "@/features/dashboard/DashboardHub";
import DashboardLoading from "./loading";

export default function DashboardPage() {
  return (
    <Suspense fallback={<DashboardLoading />}>
      <DashboardHub />
    </Suspense>
  );
}
