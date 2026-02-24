"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface SectionBadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  label: string;
  pulsing?: boolean;
}

export const SectionBadge = React.forwardRef<HTMLDivElement, SectionBadgeProps>(
  ({ label, pulsing = true, className, ...props }, ref) => {
    return (
      <div ref={ref} className={cn("section-label", className)} {...props}>
        <span
          className={cn("section-label-dot", pulsing && "animate-status-pulse")}
        />
        <span className="section-label-text">{label}</span>
      </div>
    );
  },
);
SectionBadge.displayName = "SectionBadge";
