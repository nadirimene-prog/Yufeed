"use client";

export default function LinkedRisksList({
  linkedRisks,
}: {
  linkedRisks: Array<{
    link_id: number;
    link_type: string;
    risk_id: string;
    name: string;
    inherent_risk_level: string;
    residual_risk_level: string;
  }>;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="text-sm font-semibold text-gray-900 dark:text-white">
        Linked Risks ({linkedRisks.length})
      </div>
      <div className="mt-3 space-y-2">
        {linkedRisks.map((risk) => (
          <div
            key={risk.link_id}
            className="flex items-center gap-3 rounded-lg border border-gray-100 bg-gray-50/60 p-3 dark:border-slate-800 dark:bg-slate-800/40"
          >
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-gray-900 dark:text-white truncate">{risk.name}</div>
              <div className="text-xs text-gray-500">{risk.risk_id}</div>
            </div>
            <div className="flex items-center gap-2">
              <span
                className={`rounded-full px-2 py-1 text-[10px] font-semibold ${
                  risk.inherent_risk_level === "critical"
                    ? "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300"
                    : risk.inherent_risk_level === "high"
                      ? "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300"
                      : risk.inherent_risk_level === "medium"
                        ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300"
                        : "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300"
                }`}
              >
                {risk.inherent_risk_level}
              </span>
              <span className="rounded-full bg-gray-100 px-2 py-1 text-[10px] text-gray-600 dark:bg-slate-800 dark:text-gray-400">
                {risk.link_type}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

