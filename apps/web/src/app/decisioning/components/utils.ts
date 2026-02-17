import type { DecisionListItem } from "@/app/decisioning/components/types";

export function downloadFile(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function decisionsToCsv(items: DecisionListItem[]) {
  const headers = [
    "decision_id",
    "event_id",
    "decision",
    "created_at",
    "event_type",
    "entity_type",
    "entity_id",
    "source",
    "reason_codes",
    "rule_version",
    "model_version",
  ];

  const rows = items.map((item) => [
    item.decision_id,
    item.event_id ?? "",
    item.decision,
    item.created_at,
    item.event_type ?? "",
    item.entity_type ?? "",
    item.entity_id ?? "",
    item.source ?? "",
    (item.reason_codes ?? []).join("|"),
    item.rule_version ?? "",
    item.model_version ?? "",
  ]);

  return [headers, ...rows]
    .map((row) =>
      row
        .map((value) => `"${String(value ?? "").replace(/"/g, '""')}"`)
        .join(","),
    )
    .join("\n");
}
