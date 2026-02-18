"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * ═══════════════════════════════════════════════════════════════════
 * TABLE - Sentinel Design System
 * Glass-styled data tables with premium effects
 * ═══════════════════════════════════════════════════════════════════
 */

const Table = React.forwardRef<
  HTMLTableElement,
  React.HTMLAttributes<HTMLTableElement>
>(({ className, ...props }, ref) => (
  <div className="relative w-full overflow-auto">
    <table
      ref={ref}
      className={cn("w-full caption-bottom text-sm", className)}
      {...props}
    />
  </div>
));
Table.displayName = "Table";

const TableHeader = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <thead
    ref={ref}
    className={cn(
      "[&_tr]:border-b [&_tr]:border-white/[0.06]",
      "bg-white/[0.02]",
      className,
    )}
    {...props}
  />
));
TableHeader.displayName = "TableHeader";

const TableBody = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <tbody
    ref={ref}
    className={cn("[&_tr:last-child]:border-0", className)}
    {...props}
  />
));
TableBody.displayName = "TableBody";

const TableFooter = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <tfoot
    ref={ref}
    className={cn(
      "border-t border-white/[0.06] bg-white/[0.02] font-medium [&>tr]:last:border-b-0",
      className,
    )}
    {...props}
  />
));
TableFooter.displayName = "TableFooter";

const TableRow = React.forwardRef<
  HTMLTableRowElement,
  React.HTMLAttributes<HTMLTableRowElement>
>(({ className, ...props }, ref) => (
  <tr
    ref={ref}
    className={cn(
      "border-b border-white/[0.04] transition-colors",
      "hover:bg-white/[0.03]",
      "data-[state=selected]:bg-[#6d5acd]/10",
      className,
    )}
    {...props}
  />
));
TableRow.displayName = "TableRow";

const TableHead = React.forwardRef<
  HTMLTableCellElement,
  React.ThHTMLAttributes<HTMLTableCellElement>
>(({ className, ...props }, ref) => (
  <th
    ref={ref}
    className={cn(
      "h-11 px-4 text-left align-middle",
      "text-xs font-semibold uppercase tracking-wider text-white/40",
      "[&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]",
      className,
    )}
    {...props}
  />
));
TableHead.displayName = "TableHead";

const TableCell = React.forwardRef<
  HTMLTableCellElement,
  React.TdHTMLAttributes<HTMLTableCellElement>
>(({ className, ...props }, ref) => (
  <td
    ref={ref}
    className={cn(
      "px-4 py-3 align-middle text-white/80",
      "[&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]",
      className,
    )}
    {...props}
  />
));
TableCell.displayName = "TableCell";

const TableCaption = React.forwardRef<
  HTMLTableCaptionElement,
  React.HTMLAttributes<HTMLTableCaptionElement>
>(({ className, ...props }, ref) => (
  <caption
    ref={ref}
    className={cn("mt-4 text-sm text-white/40", className)}
    {...props}
  />
));
TableCaption.displayName = "TableCaption";

/**
 * Glass Table Container - Wraps table in glass styling
 */
interface GlassTableContainerProps
  extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

const GlassTableContainer = React.forwardRef<
  HTMLDivElement,
  GlassTableContainerProps
>(({ className, children, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "rounded-xl overflow-hidden",
      "border border-white/[0.06]",
      "bg-white/[0.02] backdrop-blur-sm",
      className,
    )}
    {...props}
  >
    {children}
  </div>
));
GlassTableContainer.displayName = "GlassTableContainer";

/**
 * Table Toolbar - For filters, search, and actions
 */
interface TableToolbarProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

const TableToolbar = React.forwardRef<HTMLDivElement, TableToolbarProps>(
  ({ className, children, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "flex items-center justify-between gap-4 p-4",
        "border-b border-white/[0.06]",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  ),
);
TableToolbar.displayName = "TableToolbar";

/**
 * Table Pagination - Footer with pagination controls
 */
interface TablePaginationProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

const TablePagination = React.forwardRef<HTMLDivElement, TablePaginationProps>(
  ({ className, children, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "flex items-center justify-between gap-4 px-4 py-3",
        "border-t border-white/[0.06]",
        "text-sm text-white/50",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  ),
);
TablePagination.displayName = "TablePagination";

export {
  Table,
  TableHeader,
  TableBody,
  TableFooter,
  TableHead,
  TableRow,
  TableCell,
  TableCaption,
  GlassTableContainer,
  TableToolbar,
  TablePagination,
};
