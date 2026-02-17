"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Download, FileSpreadsheet, FileText, ChevronDown } from "lucide-react";
import toast from "react-hot-toast";
import { cn } from "@/lib/utils";
import { Button, type ButtonProps } from "@/components/ui/button";
import { exportToCSV, exportDataToPDF, type ExportColumn } from "@/lib/export";
import { logger } from "@/lib/logger";

/**
 * ================================================================
 * EXPORT BUTTON - Dropdown with CSV and PDF export options
 * ================================================================
 *
 * Usage:
 *   <ExportButton
 *     data={alerts}
 *     filename="alerts-report"
 *     pdfTitle="Transaction Alerts Report"
 *     columns={[
 *       { key: 'id', label: 'Alert ID' },
 *       { key: 'severity', label: 'Severity' },
 *     ]}
 *   />
 */

export interface ExportButtonProps {
  /** Array of objects to export */
  data: Record<string, unknown>[];
  /** Base filename (without extension) */
  filename: string;
  /** Title shown at the top of the PDF report. Defaults to filename. */
  pdfTitle?: string;
  /** Optional column definitions. Auto-detected from data keys if omitted. */
  columns?: ExportColumn[];
  /** Button visual variant - matches the project's Button component */
  variant?: ButtonProps["variant"];
  /** Button size */
  size?: ButtonProps["size"];
  /** Extra classes on the wrapper */
  className?: string;
  /** Whether the data is currently loading */
  loading?: boolean;
  /** Disable the button */
  disabled?: boolean;
}

export function ExportButton({
  data,
  filename,
  pdfTitle,
  columns,
  variant = "outline",
  size = "md",
  className,
  loading = false,
  disabled = false,
}: ExportButtonProps) {
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!open) return;

    function handleClickOutside(e: MouseEvent) {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  // Close on Escape key
  useEffect(() => {
    if (!open) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open]);

  const handleCSV = useCallback(() => {
    setOpen(false);
    try {
      exportToCSV(data, filename, columns);
      toast.success("CSV exported successfully");
    } catch (err) {
      logger.error("CSV export failed:", err);
      toast.error(err instanceof Error ? err.message : "Failed to export CSV");
    }
  }, [data, filename, columns]);

  const handlePDF = useCallback(() => {
    setOpen(false);
    try {
      exportDataToPDF(data, pdfTitle ?? filename, filename, columns);
      toast.success("PDF export opened in print dialog");
    } catch (err) {
      logger.error("PDF export failed:", err);
      toast.error(err instanceof Error ? err.message : "Failed to export PDF");
    }
  }, [data, filename, pdfTitle, columns]);

  const isDisabled = disabled || loading || data.length === 0;

  return (
    <div ref={wrapperRef} className={cn("relative inline-block", className)}>
      <Button
        variant={variant}
        size={size}
        disabled={isDisabled}
        loading={loading}
        onClick={() => setOpen((prev) => !prev)}
        leftIcon={<Download className="h-4 w-4" />}
        rightIcon={
          <ChevronDown
            className={cn("h-3 w-3 transition-transform", open && "rotate-180")}
          />
        }
        aria-haspopup="true"
        aria-expanded={open}
      >
        Export
      </Button>

      {open && (
        <div
          className={cn(
            "absolute right-0 z-50 mt-1 w-48 origin-top-right",
            "rounded-lg border border-gray-200 dark:border-gray-700",
            "bg-white dark:bg-gray-800 shadow-lg",
            "animate-in fade-in-0 zoom-in-95",
          )}
          role="menu"
        >
          <button
            onClick={handleCSV}
            className={cn(
              "flex w-full items-center gap-3 px-4 py-2.5 text-sm",
              "text-gray-700 dark:text-gray-200",
              "hover:bg-gray-100 dark:hover:bg-gray-700",
              "rounded-t-lg transition-colors",
            )}
            role="menuitem"
          >
            <FileSpreadsheet className="h-4 w-4 text-green-600" />
            Export as CSV
          </button>
          <button
            onClick={handlePDF}
            className={cn(
              "flex w-full items-center gap-3 px-4 py-2.5 text-sm",
              "text-gray-700 dark:text-gray-200",
              "hover:bg-gray-100 dark:hover:bg-gray-700",
              "rounded-b-lg transition-colors",
            )}
            role="menuitem"
          >
            <FileText className="h-4 w-4 text-red-600" />
            Export as PDF
          </button>
        </div>
      )}
    </div>
  );
}

export default ExportButton;
