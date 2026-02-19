"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button-horizon";
import {
  ChevronDown,
  ChevronUp,
  ChevronsUpDown,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Search,
  Download,
} from "lucide-react";

/**
 * Horizon Data Table
 * Professional data table with sorting, filtering, and pagination
 */

/* ─────────────────────────────────────────────────────────────────────────────
   Types
   ───────────────────────────────────────────────────────────────────────────── */

export type SortDirection = "asc" | "desc" | null;

export interface Column<T> {
  key: string;
  header: React.ReactNode;
  accessor: (row: T) => React.ReactNode;
  sortable?: boolean;
  width?: string;
  align?: "left" | "center" | "right";
  className?: string;
}

export interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  keyExtractor: (row: T) => string;

  // Loading state
  loading?: boolean;
  skeletonRows?: number;

  // Sorting
  sortable?: boolean;
  defaultSort?: { key: string; direction: SortDirection };
  onSort?: (key: string, direction: SortDirection) => void;

  // Pagination
  pagination?: boolean;
  pageSize?: number;
  pageSizeOptions?: number[];

  // Search/Filter
  searchable?: boolean;
  searchPlaceholder?: string;
  onSearch?: (query: string) => void;

  // Selection
  selectable?: boolean;
  selectedKeys?: string[];
  onSelectionChange?: (keys: string[]) => void;

  // Actions
  onRowClick?: (row: T) => void;
  rowClassName?: (row: T) => string;

  // Empty state
  emptyTitle?: string;
  emptyDescription?: string;
  emptyAction?: React.ReactNode;

  // Export
  exportable?: boolean;
  onExport?: () => void;

  // Styling
  className?: string;
  striped?: boolean;
  bordered?: boolean;
  compact?: boolean;
  captionText?: string;
}

/* ─────────────────────────────────────────────────────────────────────────────
   Table Header Cell Component
   ───────────────────────────────────────────────────────────────────────────── */

interface TableHeaderCellProps<T> {
  column: Column<T>;
  sortDirection: SortDirection;
  onSort: () => void;
  compact?: boolean;
}

function TableHeaderCell<T>({
  column,
  sortDirection,
  onSort,
  compact,
}: TableHeaderCellProps<T>) {
  const alignClass = {
    left: "text-left",
    center: "text-center",
    right: "text-right",
  }[column.align ?? "left"];

  const content = (
    <div className={cn("flex items-center gap-1", alignClass)}>
      <span className="font-semibold">{column.header}</span>
      {column.sortable && (
        <span className="inline-flex">
          {sortDirection === "asc" ? (
            <ChevronUp className="h-4 w-4 text-primary" />
          ) : sortDirection === "desc" ? (
            <ChevronDown className="h-4 w-4 text-primary" />
          ) : (
            <ChevronsUpDown className="h-4 w-4 text-foreground-tertiary" />
          )}
        </span>
      )}
    </div>
  );

  if (column.sortable) {
    return (
      <th
        className={cn(
          "px-4 py-3 text-xs uppercase tracking-wider text-foreground-secondary cursor-pointer hover:text-foreground transition-colors select-none",
          compact && "px-3 py-2",
          alignClass,
          column.className,
        )}
        style={{ width: column.width }}
        onClick={onSort}
        role="columnheader"
        scope="col"
        aria-sort={
          sortDirection === "asc"
            ? "ascending"
            : sortDirection === "desc"
              ? "descending"
              : "none"
        }
      >
        {content}
      </th>
    );
  }

  return (
    <th
      className={cn(
        "px-4 py-3 text-xs uppercase tracking-wider text-foreground-secondary",
        compact && "px-3 py-2",
        alignClass,
        column.className,
      )}
      style={{ width: column.width }}
      role="columnheader"
      scope="col"
    >
      {content}
    </th>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Table Skeleton Component
   ───────────────────────────────────────────────────────────────────────────── */

function TableSkeleton({
  columns,
  rows,
  compact,
}: {
  columns: number;
  rows: number;
  compact?: boolean;
}) {
  return (
    <>
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <tr
          key={rowIndex}
          className={cn(
            "animate-pulse",
            rowIndex % 2 === 1 && "bg-bg-elevated/50",
          )}
        >
          {Array.from({ length: columns }).map((_, colIndex) => (
            <td
              key={colIndex}
              className={cn("px-4 py-4", compact && "px-3 py-3")}
            >
              <div
                className={cn(
                  "h-4 bg-bg-floating rounded",
                  colIndex === 0 && "w-3/4",
                  colIndex === columns - 1 && "w-1/2",
                )}
              />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Empty State Component
   ───────────────────────────────────────────────────────────────────────────── */

function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <tr>
      <td colSpan={100} className="px-4 py-16 text-center">
        <div className="mx-auto max-w-sm">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-bg-floating">
            <Search className="h-6 w-6 text-foreground-tertiary" />
          </div>
          <h3 className="text-lg font-medium text-foreground">{title}</h3>
          <p className="mt-1 text-sm text-foreground-secondary">
            {description}
          </p>
          {action && <div className="mt-4">{action}</div>}
        </div>
      </td>
    </tr>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Pagination Component
   ───────────────────────────────────────────────────────────────────────────── */

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  pageSize: number;
  totalItems: number;
  pageSizeOptions: number[];
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
}

function Pagination({
  currentPage,
  totalPages,
  pageSize,
  totalItems,
  pageSizeOptions,
  onPageChange,
  onPageSizeChange,
}: PaginationProps) {
  const startItem = (currentPage - 1) * pageSize + 1;
  const endItem = Math.min(currentPage * pageSize, totalItems);

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-4 px-4 py-3 border-t border-border-subtle">
      {/* Page size selector */}
      <div className="flex items-center gap-2 text-sm text-foreground-secondary">
        <span>Show</span>
        <select
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
          className="rounded border border-border-default bg-bg-elevated px-2 py-1 text-sm focus:border-primary focus:outline-none"
        >
          {pageSizeOptions.map((size) => (
            <option key={size} value={size}>
              {size}
            </option>
          ))}
        </select>
        <span>entries</span>
      </div>

      {/* Pagination info */}
      <p className="text-sm text-foreground-secondary">
        Showing <span className="font-medium text-foreground">{startItem}</span>{" "}
        to <span className="font-medium text-foreground">{endItem}</span> of{" "}
        <span className="font-medium text-foreground">{totalItems}</span>{" "}
        results
      </p>

      {/* Navigation buttons */}
      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => onPageChange(1)}
          disabled={currentPage === 1}
          aria-label="First page"
        >
          <ChevronsLeft className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          aria-label="Previous page"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>

        {/* Page numbers */}
        <div className="flex items-center gap-1 px-2">
          {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
            let pageNum: number;
            if (totalPages <= 5) {
              pageNum = i + 1;
            } else if (currentPage <= 3) {
              pageNum = i + 1;
            } else if (currentPage >= totalPages - 2) {
              pageNum = totalPages - 4 + i;
            } else {
              pageNum = currentPage - 2 + i;
            }

            return (
              <button
                key={pageNum}
                onClick={() => onPageChange(pageNum)}
                className={cn(
                  "h-8 w-8 rounded-md text-sm font-medium transition-colors",
                  currentPage === pageNum
                    ? "bg-primary text-white"
                    : "text-foreground-secondary hover:bg-bg-floating hover:text-foreground",
                )}
                aria-current={currentPage === pageNum ? "page" : undefined}
              >
                {pageNum}
              </button>
            );
          })}
        </div>

        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          aria-label="Next page"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => onPageChange(totalPages)}
          disabled={currentPage === totalPages}
          aria-label="Last page"
        >
          <ChevronsRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Main Data Table Component
   ───────────────────────────────────────────────────────────────────────────── */

export function DataTable<T>({
  data,
  columns,
  keyExtractor,
  loading = false,
  skeletonRows = 5,
  sortable = false,
  defaultSort,
  onSort,
  pagination = false,
  pageSize: initialPageSize = 10,
  pageSizeOptions = [10, 25, 50, 100],
  searchable = false,
  searchPlaceholder = "Search...",
  onSearch,
  selectable = false,
  selectedKeys,
  onSelectionChange,
  onRowClick,
  rowClassName,
  emptyTitle = "No results found",
  emptyDescription = "Try adjusting your search or filters.",
  emptyAction,
  exportable = false,
  onExport,
  className,
  striped = true,
  // bordered is reserved for future table border styling
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  bordered = true,
  compact = false,
  captionText = "Data table",
}: DataTableProps<T>) {
  // Sorting state
  const [sortState, setSortState] = React.useState<{
    key: string;
    direction: SortDirection;
  }>({
    key: defaultSort?.key ?? "",
    direction: defaultSort?.direction ?? null,
  });

  // Search state
  const [searchQuery, setSearchQuery] = React.useState("");

  // Pagination state
  const [currentPage, setCurrentPage] = React.useState(1);
  const [pageSize, setPageSize] = React.useState(initialPageSize);

  // Selection state
  const [localSelectedKeys, setLocalSelectedKeys] = React.useState<string[]>(
    selectedKeys ?? [],
  );

  React.useEffect(() => {
    if (selectedKeys) {
      setLocalSelectedKeys([...selectedKeys]);
    }
  }, [selectedKeys]);

  // Handle sorting
  const handleSort = (columnKey: string) => {
    if (!sortable) return;

    let newDirection: SortDirection;
    if (sortState.key === columnKey) {
      newDirection =
        sortState.direction === "asc"
          ? "desc"
          : sortState.direction === "desc"
            ? null
            : "asc";
    } else {
      newDirection = "asc";
    }

    const newSortState = { key: columnKey, direction: newDirection };
    setSortState(newSortState);
    setCurrentPage(1);
    onSort?.(columnKey, newDirection);
  };

  // Handle search
  const handleSearch = (value: string) => {
    setSearchQuery(value);
    setCurrentPage(1);
    onSearch?.(value);
  };

  // Handle selection
  const handleSelectAll = (checked: boolean) => {
    const newKeys = checked ? data.map(keyExtractor) : [];
    setLocalSelectedKeys(newKeys);
    onSelectionChange?.(newKeys);
  };

  const handleSelectRow = (key: string, checked: boolean) => {
    const newKeys = checked
      ? [...localSelectedKeys, key]
      : localSelectedKeys.filter((k) => k !== key);
    setLocalSelectedKeys(newKeys);
    onSelectionChange?.(newKeys);
  };

  // Pagination calculations
  const totalPages = Math.ceil(data.length / pageSize);
  const paginatedData = pagination
    ? data.slice((currentPage - 1) * pageSize, currentPage * pageSize)
    : data;

  const allSelected =
    data.length > 0 && localSelectedKeys.length === data.length;
  const someSelected =
    localSelectedKeys.length > 0 && localSelectedKeys.length < data.length;

  return (
    <div
      className={cn(
        "bg-bg-elevated rounded-xl border border-border-subtle overflow-hidden",
        className,
      )}
    >
      {/* Toolbar */}
      {(searchable || exportable || selectable) && (
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 px-4 py-3 border-b border-border-subtle">
          <div className="flex items-center gap-3">
            {selectable && (
              <span className="text-sm text-foreground-secondary">
                {localSelectedKeys.length} selected
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 w-full sm:w-auto">
            {searchable && (
              <div className="relative flex-1 sm:flex-none">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-foreground-tertiary" />
                <input
                  type="text"
                  placeholder={searchPlaceholder}
                  value={searchQuery}
                  onChange={(e) => handleSearch(e.target.value)}
                  className="w-full sm:w-64 pl-9 pr-4 py-2 rounded-lg border border-border-default bg-bg-base text-sm placeholder:text-foreground-tertiary focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>
            )}
            {exportable && onExport && (
              <Button
                variant="secondary"
                size="sm"
                onClick={onExport}
                leftIcon={<Download className="h-4 w-4" />}
              >
                Export
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <caption className="sr-only">{captionText}</caption>
          <thead className="bg-bg-overlay">
            <tr>
              {selectable && (
                <th className="px-4 py-3 w-10">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    ref={(input) => {
                      if (input) {
                        input.indeterminate = someSelected;
                      }
                    }}
                    onChange={(e) => handleSelectAll(e.target.checked)}
                    className="h-4 w-4 rounded border-border-strong text-primary focus:ring-primary/20"
                    aria-label="Select all rows"
                  />
                </th>
              )}
              {columns.map((column) => (
                <TableHeaderCell
                  key={column.key}
                  column={column}
                  sortDirection={
                    sortState.key === column.key ? sortState.direction : null
                  }
                  onSort={() => handleSort(column.key)}
                  compact={compact}
                />
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border-subtle">
            {loading ? (
              <TableSkeleton
                columns={columns.length + (selectable ? 1 : 0)}
                rows={skeletonRows}
                compact={compact}
              />
            ) : paginatedData.length === 0 ? (
              <EmptyState
                title={emptyTitle}
                description={emptyDescription}
                action={emptyAction}
              />
            ) : (
              paginatedData.map((row, index) => {
                const key = keyExtractor(row);
                const isSelected = localSelectedKeys.includes(key);

                return (
                  <tr
                    key={key}
                    onClick={() => onRowClick?.(row)}
                    onKeyDown={
                      onRowClick
                        ? (event) => {
                            if (event.key === "Enter" || event.key === " ") {
                              event.preventDefault();
                              onRowClick(row);
                            }
                          }
                        : undefined
                    }
                    tabIndex={onRowClick ? 0 : undefined}
                    role={onRowClick ? "button" : undefined}
                    className={cn(
                      "transition-colors",
                      striped && index % 2 === 1 && "bg-bg-overlay/50",
                      isSelected && "bg-primary/5",
                      onRowClick && "cursor-pointer hover:bg-bg-floating",
                      rowClassName?.(row),
                    )}
                  >
                    {selectable && (
                      <td className="px-4 py-4">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={(e) =>
                            handleSelectRow(key, e.target.checked)
                          }
                          onClick={(e) => e.stopPropagation()}
                          className="h-4 w-4 rounded border-border-strong text-primary focus:ring-primary/20"
                          aria-label={`Select row ${key}`}
                        />
                      </td>
                    )}
                    {columns.map((column) => (
                      <td
                        key={column.key}
                        className={cn(
                          "px-4 py-4 text-sm",
                          compact && "px-3 py-3",
                          column.align === "center" && "text-center",
                          column.align === "right" && "text-right",
                        )}
                      >
                        {column.accessor(row)}
                      </td>
                    ))}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pagination && !loading && data.length > 0 && (
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          pageSize={pageSize}
          totalItems={data.length}
          pageSizeOptions={pageSizeOptions}
          onPageChange={setCurrentPage}
          onPageSizeChange={(size) => {
            setPageSize(size);
            setCurrentPage(1);
          }}
        />
      )}
    </div>
  );
}

export default DataTable;
