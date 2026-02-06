export function obligationStatusStyle(status?: string) {
  const value = (status || "draft").toLowerCase();
  if (value === "approved")
    return "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300";
  if (value === "in_review")
    return "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300";
  if (value === "rejected")
    return "bg-rose-50 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300";
  return "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300";
}

export function formatDate(value?: string | null) {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return parsed.toLocaleString();
}

