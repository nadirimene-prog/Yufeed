export function obligationStatusStyle(status?: string) {
  const value = (status ?? "draft").toLowerCase();
  if (value === "approved") return "bg-emerald-50 text-emerald-700";
  if (value === "in_review") return "bg-blue-50 text-blue-700";
  if (value === "rejected") return "bg-rose-50 text-rose-700";
  return "bg-amber-50 text-amber-700";
}

export function formatDate(value?: string | null) {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return parsed.toLocaleString();
}
