"use client";

import Link from "next/link";
import { EmptyState } from "@/components/ui/empty-state";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button-horizon";

export default function EntitiesIndexPage() {
  return (
    <Card className="border-border shadow-sm bg-white">
      <CardContent className="pt-6">
        <EmptyState
          title="Entity Profile"
          description="Open an entity profile from a case, alert, or dashboard queue item."
          variant="no-results"
        >
          <Link href="/cases">
            <Button variant="outline">Browse Cases</Button>
          </Link>
        </EmptyState>
      </CardContent>
    </Card>
  );
}
