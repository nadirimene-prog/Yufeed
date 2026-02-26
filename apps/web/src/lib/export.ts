/**
 * Export utilities for CSV and PDF generation.
 *
 * Uses only browser-native APIs:
 * - CSV: Blob + URL.createObjectURL for download
 * - PDF: window.open + window.print for native save-as-PDF
 */

// ---------------------------------------------------------------------------
// Date formatting
// ---------------------------------------------------------------------------

/**
 * Format a date value into a consistent export-friendly string (YYYY-MM-DD HH:mm).
 * Returns an empty string for null/undefined/invalid inputs.
 */
export function formatDateForExport(
  date: string | Date | null | undefined,
): string {
  if (date == null) return "";

  const d = typeof date === "string" ? new Date(date) : date;

  if (isNaN(d.getTime())) return "";

  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// ---------------------------------------------------------------------------
// CSV helpers
// ---------------------------------------------------------------------------

/**
 * Escape a single CSV cell value.
 * Wraps in double-quotes when the value contains a comma, quote, or newline,
 * and escapes inner double-quotes by doubling them (RFC 4180).
 */
function escapeCSVCell(value: unknown): string {
  if (value == null) return "";

  const str = String(value);

  // Must quote if value contains comma, double-quote, or newline
  if (
    str.includes(",") ||
    str.includes('"') ||
    str.includes("\n") ||
    str.includes("\r")
  ) {
    return `"${str.replace(/"/g, '""')}"`;
  }

  return str;
}

/**
 * Convert a header array and a 2-D rows array into a CSV string.
 *
 * @example
 * tableDataToCSV(
 *   ['Name', 'Score'],
 *   [['Alice', 95], ['Bob', 88]]
 * );
 */
export function tableDataToCSV(
  headers: string[],
  rows: (string | number | boolean | null | undefined)[][],
): string {
  const lines: string[] = [];

  // Header row
  lines.push(headers.map(escapeCSVCell).join(","));

  // Data rows
  for (const row of rows) {
    lines.push(row.map(escapeCSVCell).join(","));
  }

  return lines.join("\r\n");
}

// ---------------------------------------------------------------------------
// Column config type
// ---------------------------------------------------------------------------

export interface ExportColumn<T = Record<string, unknown>> {
  /** Property key on each data object */
  key: keyof T & string;
  /** Human-readable header label */
  label: string;
}

// ---------------------------------------------------------------------------
// CSV export
// ---------------------------------------------------------------------------

/**
 * Export an array of objects to a CSV file and trigger a browser download.
 *
 * @param data      - Array of objects to export.
 * @param filename  - Download file name (`.csv` is appended if missing).
 * @param columns   - Optional column config. When omitted, columns are
 *                    auto-detected from the keys of the first object.
 */
export function exportToCSV<T extends Record<string, unknown>>(
  data: T[],
  filename: string,
  columns?: ExportColumn<T>[],
): void {
  if (data.length === 0) {
    throw new Error("No data to export");
  }

  // Resolve columns: explicit config or auto-detect from first row
  const cols: ExportColumn<T>[] =
    columns ??
    (Object.keys(data[0]) as (keyof T & string)[]).map((key) => ({
      key,
      label: String(key)
        .replace(/_/g, " ")
        .replace(/\b\w/g, (c) => c.toUpperCase()),
    }));

  const headers = cols.map((c) => c.label);
  const rows = data.map((item) =>
    cols.map((c) => {
      const val = item[c.key];
      // Flatten objects/arrays to JSON for readability
      if (val !== null && typeof val === "object") {
        return JSON.stringify(val);
      }
      return val as string | number | boolean | null | undefined;
    }),
  );

  const csv = tableDataToCSV(headers, rows);
  triggerDownload(
    csv,
    ensureExtension(filename, ".csv"),
    "text/csv;charset=utf-8;",
  );
}

// ---------------------------------------------------------------------------
// PDF export (browser print dialog)
// ---------------------------------------------------------------------------

/**
 * Open a styled HTML page in a new window and trigger the browser's native
 * print dialog, which allows saving as PDF.
 *
 * @param title    - Document title shown at the top and in the print header.
 * @param content  - HTML string to render inside the page body.
 * @param filename - Not used for download (print dialog handles naming),
 *                   but set as the window title for user reference.
 */
export function exportToPDF(
  title: string,
  content: string,
  filename: string,
): void {
  const printWindow = window.open("", "_blank");
  if (!printWindow) {
    throw new Error(
      "Pop-up blocked. Please allow pop-ups for this site to export PDF.",
    );
  }

  const html = buildPrintHTML(title, content, filename);

  printWindow.document.write(html);
  printWindow.document.close();

  // Wait for content to render before triggering print
  printWindow.addEventListener("load", () => {
    setTimeout(() => {
      printWindow.focus();
      printWindow.print();
      // Close the window after a short delay to allow print dialog to appear
      setTimeout(() => {
        printWindow.close();
      }, 1000);
    }, 250);
  });
}

// ---------------------------------------------------------------------------
// Convenience: export data array as a PDF table
// ---------------------------------------------------------------------------

/**
 * Build an HTML table from a data array and export it via the print dialog.
 *
 * @param data      - Array of objects to export.
 * @param title     - Document / report title.
 * @param filename  - Reference filename (used as window title).
 * @param columns   - Optional column config; auto-detected if omitted.
 */
export function exportDataToPDF<T extends Record<string, unknown>>(
  data: T[],
  title: string,
  filename: string,
  columns?: ExportColumn<T>[],
): void {
  if (data.length === 0) {
    throw new Error("No data to export");
  }

  const cols: ExportColumn<T>[] =
    columns ??
    (Object.keys(data[0]) as (keyof T & string)[]).map((key) => ({
      key,
      label: String(key)
        .replace(/_/g, " ")
        .replace(/\b\w/g, (c) => c.toUpperCase()),
    }));

  // Build table HTML
  const headerRow = cols.map((c) => `<th>${escapeHTML(c.label)}</th>`).join("");
  const bodyRows = data
    .map((item) => {
      const cells = cols
        .map((c) => {
          const val = item[c.key];
          const display =
            val == null
              ? ""
              : typeof val === "object"
                ? JSON.stringify(val)
                : String(val);
          return `<td>${escapeHTML(display)}</td>`;
        })
        .join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");

  const tableHTML = `
    <table>
      <thead><tr>${headerRow}</tr></thead>
      <tbody>${bodyRows}</tbody>
    </table>
    <p class="meta">Total records: ${data.length}</p>
  `;

  exportToPDF(title, tableHTML, filename);
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/** Trigger a file download via an invisible anchor element. */
function triggerDownload(
  content: string,
  filename: string,
  mimeType: string,
): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);

  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.style.display = "none";
  document.body.appendChild(anchor);
  anchor.click();

  // Clean up
  setTimeout(() => {
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  }, 100);
}

/** Ensure a filename ends with the given extension. */
function ensureExtension(filename: string, ext: string): string {
  return filename.endsWith(ext) ? filename : `${filename}${ext}`;
}

/** Minimal HTML entity escaping for safe embedding in print HTML. */
function escapeHTML(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Build a full HTML document optimised for printing / save-as-PDF. */
function buildPrintHTML(
  title: string,
  content: string,
  filename: string,
): string {
  const timestamp = new Date().toLocaleString();

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>${escapeHTML(filename)}</title>
  <style>
    /* ---- Reset & base ---- */
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                   "Helvetica Neue", Arial, sans-serif;
      font-size: 12px;
      line-height: 1.5;
      color: #1a1a2e;
      padding: 24px 32px;
    }

    /* ---- Header ---- */
    .report-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      border-bottom: 2px solid #0052ff;
      padding-bottom: 12px;
      margin-bottom: 20px;
    }
    .report-header h1 {
      font-size: 20px;
      font-weight: 700;
      color: #1a1a2e;
    }
    .report-header .brand {
      font-size: 11px;
      color: #0052ff;
      font-weight: 600;
    }
    .report-header .timestamp {
      font-size: 10px;
      color: #666;
      text-align: right;
    }

    /* ---- Tables ---- */
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 12px 0;
      font-size: 11px;
    }
    th, td {
      border: 1px solid #ddd;
      padding: 6px 10px;
      text-align: left;
      word-break: break-word;
    }
    th {
      background: #f0edfa;
      color: #1a1a2e;
      font-weight: 600;
      white-space: nowrap;
    }
    tr:nth-child(even) { background: #fafafe; }
    tr:hover { background: #f0edfa; }

    /* ---- Meta text ---- */
    .meta {
      font-size: 10px;
      color: #888;
      margin-top: 8px;
    }

    /* ---- Print-specific ---- */
    @media print {
      body { padding: 0; }
      .report-header { page-break-after: avoid; }
      table { page-break-inside: auto; }
      tr { page-break-inside: avoid; }
      thead { display: table-header-group; }
    }

    @page {
      size: A4 landscape;
      margin: 15mm;
    }
  </style>
</head>
<body>
  <div class="report-header">
    <div>
      <div class="brand">YUFEED</div>
      <h1>${escapeHTML(title)}</h1>
    </div>
    <div class="timestamp">
      Exported: ${escapeHTML(timestamp)}
    </div>
  </div>
  ${content}
</body>
</html>`;
}
