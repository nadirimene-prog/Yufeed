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
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <div className="text-sm font-semibold text-slate-900">
        Linked Risks ({linkedRisks.length})
      </div>
      <div className="mt-3 space-y-2">
        {linkedRisks.map((risk) => (
          <div
            key={risk.link_id}
            className="flex items-center gap-3 rounded-lg border border-slate-100 bg-slate-50/60 p-3"
          >
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-slate-900 truncate">
                {risk.name}
              </div>
              <div className="text-xs text-slate-500">{risk.risk_id}</div>
            </div>
            <div className="flex items-center gap-2">
              <span
                className={`rounded-full px-2 py-1 text-[10px] font-semibold ${
                  risk.inherent_risk_level === "critical"
                    ? "bg-rose-100 text-rose-700"
                    : risk.inherent_risk_level === "high"
                      ? "bg-orange-100 text-orange-700"
                      : risk.inherent_risk_level === "medium"
                        ? "bg-amber-100 text-amber-700"
                        : "bg-green-100 text-green-700"
                }`}
              >
                {risk.inherent_risk_level}
              </span>
              <span className="rounded-full bg-slate-100 px-2 py-1 text-[10px] text-slate-600">
                {risk.link_type}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
