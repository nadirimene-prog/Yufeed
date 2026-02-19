"use client";

import Link from "next/link";
import { EmptyState } from "@/components/ui/empty-state";
import { GlassCard, GlassCardContent } from "@/components/ui/glass-card";
import { Button } from "@/components/ui/button-horizon";

export default function EntitiesIndexPage() {
  return (
    <GlassCard>
      <GlassCardContent>
        <EmptyState
          title="Entity Profile"
          description="Open an entity profile from a case, alert, or dashboard queue item."
          variant="no-results"
        >
          <Link href="/cases">
            <Button variant="glass">Browse Cases</Button>
          </Link>
        </EmptyState>
      </GlassCardContent>
    </GlassCard>
  );
}
