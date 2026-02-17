"use client";

import * as React from "react";
import {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  VisibilityState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Search,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  GlassTableContainer,
  TableToolbar,
  TablePagination,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { transitions } from "@/lib/motion";

/**
 * ═══════════════════════════════════════════════════════════════════
 * DATA TABLE - Sentinel Design System
 * Premium data table with glass effects and animations
 * ═══════════════════════════════════════════════════════════════════
 */

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  /** Loading state */
  loading?: boolean;
  /** Search placeholder */
  searchPlaceholder?: string;
  /** Searchable column key */
  searchColumn?: string;
  /** Show pagination */
  showPagination?: boolean;
  /** Page sizes */
  pageSizes?: number[];
  /** Empty state message */
  emptyMessage?: string;
  /** Additional toolbar content */
  toolbarContent?: React.ReactNode;
  /** On row click handler */
  onRowClick?: (row: TData) => void;
  /** Custom className */
  className?: string;
}

export function DataTable<TData, TValue>({
  columns,
  data,
  loading = false,
  searchPlaceholder = "Search...",
  searchColumn,
  showPagination = true,
  pageSizes = [10, 20, 50, 100],
  emptyMessage = "No results found.",
  toolbarContent,
  onRowClick,
  className,
}: DataTableProps<TData, TValue>) {
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>(
    [],
  );
  const [columnVisibility, setColumnVisibility] =
    React.useState<VisibilityState>({});
  const [rowSelection, setRowSelection] = React.useState({});
  const [globalFilter, setGlobalFilter] = React.useState("");

  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data,
    columns,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    onGlobalFilterChange: setGlobalFilter,
    state: {
      sorting,
      columnFilters,
      columnVisibility,
      rowSelection,
      globalFilter,
    },
  });

  const pageIndex = table.getState().pagination.pageIndex;
  const pageSize = table.getState().pagination.pageSize;
  const totalRows = table.getFilteredRowModel().rows.length;
  const pageCount = table.getPageCount();

  return (
    <GlassTableContainer className={className}>
      {/* Toolbar */}
      {(searchColumn || toolbarContent) && (
        <TableToolbar>
          <div className="flex items-center gap-3 flex-1">
            {searchColumn && (
              <div className="relative max-w-sm">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/30" />
                <Input
                  placeholder={searchPlaceholder}
                  value={
                    (table
                      .getColumn(searchColumn)
                      ?.getFilterValue() as string) ?? ""
                  }
                  onChange={(event) =>
                    table
                      .getColumn(searchColumn)
                      ?.setFilterValue(event.target.value)
                  }
                  className="pl-10 w-[250px]"
                />
              </div>
            )}
          </div>
          {toolbarContent && (
            <div className="flex items-center gap-2">{toolbarContent}</div>
          )}
        </TableToolbar>
      )}

      {/* Table */}
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableHead
                  key={header.id}
                  className={cn(
                    header.column.getCanSort() &&
                      "cursor-pointer select-none hover:text-white/60",
                  )}
                  onClick={header.column.getToggleSortingHandler()}
                >
                  <div className="flex items-center gap-2">
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )}
                    {header.column.getIsSorted() && (
                      <ChevronDown
                        className={cn(
                          "h-4 w-4 transition-transform",
                          header.column.getIsSorted() === "asc" && "rotate-180",
                        )}
                      />
                    )}
                  </div>
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>

        <TableBody>
          {loading ? (
            // Loading skeleton
            Array.from({ length: 5 }).map((_, i) => (
              <TableRow key={i}>
                {columns.map((_, j) => (
                  <TableCell key={j}>
                    <Skeleton className="h-5 w-full" />
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : table.getRowModel().rows?.length ? (
            <AnimatePresence mode="popLayout">
              {table.getRowModel().rows.map((row, index) => (
                <motion.tr
                  key={row.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ ...transitions.fast, delay: index * 0.02 }}
                  className={cn(
                    "border-b border-white/[0.04] transition-colors",
                    "hover:bg-white/[0.03]",
                    "data-[state=selected]:bg-[#6d5acd]/10",
                    onRowClick && "cursor-pointer",
                  )}
                  onClick={() => onRowClick?.(row.original)}
                  data-state={row.getIsSelected() && "selected"}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext(),
                      )}
                    </TableCell>
                  ))}
                </motion.tr>
              ))}
            </AnimatePresence>
          ) : (
            <TableRow>
              <TableCell colSpan={columns.length} className="h-32 text-center">
                <div className="flex flex-col items-center justify-center gap-2 text-white/40">
                  <svg
                    className="h-8 w-8"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={1.5}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
                    />
                  </svg>
                  <span className="text-sm">{emptyMessage}</span>
                </div>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      {/* Pagination */}
      {showPagination && (
        <TablePagination>
          <div className="flex items-center gap-2">
            <span className="text-xs">Rows per page:</span>
            <select
              value={pageSize}
              onChange={(e) => table.setPageSize(Number(e.target.value))}
              className="h-8 rounded-lg border border-white/10 bg-white/5 px-2 text-xs text-white focus:outline-none focus:ring-1 focus:ring-[#6d5acd]"
            >
              {pageSizes.map((size) => (
                <option key={size} value={size} className="bg-[#0a0a12]">
                  {size}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs">
              {pageIndex * pageSize + 1}-
              {Math.min((pageIndex + 1) * pageSize, totalRows)} of {totalRows}
            </span>

            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => table.setPageIndex(0)}
                disabled={!table.getCanPreviousPage()}
              >
                <ChevronsLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>

              <span className="px-2 text-xs font-medium">
                {pageIndex + 1} / {pageCount || 1}
              </span>

              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => table.nextPage()}
                disabled={!table.getCanNextPage()}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => table.setPageIndex(pageCount - 1)}
                disabled={!table.getCanNextPage()}
              >
                <ChevronsRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </TablePagination>
      )}
    </GlassTableContainer>
  );
}

/**
 * Column Header Helper - Sortable header with icon
 */
interface DataTableColumnHeaderProps<TData, TValue>
  extends React.HTMLAttributes<HTMLDivElement> {
  column: import("@tanstack/react-table").Column<TData, TValue>;
  title: string;
}

export function DataTableColumnHeader<TData, TValue>({
  column,
  title,
  className,
}: DataTableColumnHeaderProps<TData, TValue>) {
  if (!column.getCanSort()) {
    return <div className={cn(className)}>{title}</div>;
  }

  return (
    <div
      className={cn(
        "flex items-center gap-2 cursor-pointer select-none",
        className,
      )}
      onClick={column.getToggleSortingHandler()}
    >
      <span>{title}</span>
      <ChevronDown
        className={cn(
          "h-4 w-4 transition-transform text-white/30",
          column.getIsSorted() === "desc" && "rotate-0",
          column.getIsSorted() === "asc" && "rotate-180",
          !column.getIsSorted() && "opacity-0 group-hover:opacity-50",
        )}
      />
    </div>
  );
}

export default DataTable;
