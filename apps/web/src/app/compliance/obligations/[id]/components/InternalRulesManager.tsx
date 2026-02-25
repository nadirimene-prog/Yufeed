"use client";

import type { Policy, PolicySection } from "@/types/compliance";
import type { InternalRule } from "@/app/compliance/obligations/[id]/components/types";
import { obligationStatusStyle } from "@/app/compliance/obligations/[id]/components/utils";

type SetStateAction<T> = T | ((prev: T) => T);
type StateSetter<T> = (value: SetStateAction<T>) => void;

export default function InternalRulesManager({
  internalRules,
  rulesLoading,
  rulesActionLoading,
  mappingForm,
  setMappingForm,
  onAddMapping,
  ruleForm,
  setRuleForm,
  policies,
  policiesLoading,
  sections,
  sectionsLoading,
  onCreateInternalRule,
}: {
  internalRules: InternalRule[];
  rulesLoading: boolean;
  rulesActionLoading: string | null;
  mappingForm: Record<number, { target: string; mappingType: string }>;
  setMappingForm: StateSetter<
    Record<number, { target: string; mappingType: string }>
  >;
  onAddMapping: (ruleId: number) => void;
  ruleForm: {
    name: string;
    description: string;
    control_owner: string;
    status: string;
    policy_id: string;
    policy_section_id: string;
  };
  setRuleForm: (next: {
    name: string;
    description: string;
    control_owner: string;
    status: string;
    policy_id: string;
    policy_section_id: string;
  }) => void;
  policies: Policy[];
  policiesLoading: boolean;
  sections: PolicySection[];
  sectionsLoading: boolean;
  onCreateInternalRule: () => void;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <div className="text-sm font-semibold text-slate-900">
        Internal rules & mappings
      </div>
      <p className="mt-1 text-xs text-slate-500">
        Define the internal controls required by this obligation and map them to
        monitoring rules.
      </p>

      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,320px)]">
        <div className="space-y-3">
          {rulesLoading ? (
            <div className="text-sm text-slate-500">
              Loading internal rules...
            </div>
          ) : internalRules.length ? (
            internalRules.map((rule) => (
              <div
                key={rule.id}
                className="rounded-lg border border-slate-100 bg-slate-50/60 p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-sm font-semibold text-slate-900">
                      {rule.name}
                    </div>
                    <div className="mt-1 text-xs text-slate-500">
                      {rule.internal_rule_id} •{""}
                      {rule.control_owner ?? "Owner TBD"}
                    </div>
                  </div>
                  <span
                    className={
                      "rounded-full px-2 py-1 text-[10px] font-semibold" +
                      obligationStatusStyle(rule.status ?? undefined)
                    }
                  >
                    {(rule.status ?? "draft").replace("_", "")}
                  </span>
                </div>

                {rule.description && (
                  <div className="mt-2 text-xs text-slate-600">
                    {rule.description}
                  </div>
                )}

                {rule.policy_section && (
                  <div className="mt-2 text-[11px] text-slate-500">
                    Policy section: {rule.policy_section.section_ref ?? "—"}
                    {""}
                    {rule.policy_section.title
                      ? `• ${rule.policy_section.title}`
                      : ""}
                  </div>
                )}

                <div className="mt-4 border-t border-slate-100 pt-3">
                  <div className="text-[11px] font-semibold text-slate-500">
                    Mapped monitoring rules
                  </div>
                  <div className="mt-2 space-y-2">
                    {rule.mappings?.length ? (
                      rule.mappings.map((mapping) => (
                        <div
                          key={mapping.id}
                          className="rounded-md border border-slate-100 bg-white px-3 py-2 text-xs"
                        >
                          <div className="flex items-center justify-between">
                            <div className="text-xs font-semibold text-slate-800">
                              {mapping.monitoring_rule?.name ??
                                "Monitoring rule"}
                            </div>
                            <div className="text-[10px] text-slate-500">
                              {mapping.monitoring_rule?.rule_id ??
                                mapping.monitoring_rule_id ??
                                "—"}
                            </div>
                          </div>
                          <div className="mt-1 text-[11px] text-slate-500">
                            {mapping.mapping_type ?? "transaction_monitoring"} •
                            {""}
                            {mapping.monitoring_rule?.severity ?? "severity ?"}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-xs text-slate-500">
                        No monitoring rules linked yet.
                      </div>
                    )}
                  </div>

                  <div className="mt-3 flex flex-col gap-2 text-xs text-slate-600">
                    <input
                      value={mappingForm[rule.id]?.target || ""}
                      onChange={(event) =>
                        setMappingForm((prev) => ({
                          ...prev,
                          [rule.id]: {
                            ...(prev[rule.id] || {
                              mappingType: "transaction_monitoring",
                            }),
                            target: event.target.value,
                          },
                        }))
                      }
                      placeholder="Monitoring rule ID or rule_id"
                      className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700"
                    />
                    <div className="flex gap-2">
                      <select
                        value={
                          mappingForm[rule.id]?.mappingType ||
                          "transaction_monitoring"
                        }
                        onChange={(event) =>
                          setMappingForm((prev) => ({
                            ...prev,
                            [rule.id]: {
                              ...(prev[rule.id] || { target: "" }),
                              mappingType: event.target.value,
                            },
                          }))
                        }
                        className="flex-1 rounded-md border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700"
                      >
                        <option value="transaction_monitoring">
                          Transaction monitoring
                        </option>
                        <option value="sanctions">Sanctions</option>
                        <option value="fraud">Fraud</option>
                      </select>
                      <button
                        onClick={() => onAddMapping(rule.id)}
                        disabled={rulesActionLoading === `map-${rule.id}`}
                        className="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600 hover:border-slate-300 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {rulesActionLoading === `map-${rule.id}`
                          ? "Saving..."
                          : "Add mapping"}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="text-sm text-slate-500">
              No internal rules linked yet.
            </div>
          )}
        </div>

        <div className="rounded-lg border border-slate-100 bg-slate-50/60 p-4 text-xs text-slate-600">
          <div className="text-xs font-semibold text-slate-700">
            Create internal rule
          </div>
          <div className="mt-3 space-y-2">
            <input
              value={ruleForm.name}
              onChange={(event) =>
                setRuleForm({ ...ruleForm, name: event.target.value })
              }
              placeholder="Rule name"
              className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700"
            />
            <input
              value={ruleForm.control_owner}
              onChange={(event) =>
                setRuleForm({ ...ruleForm, control_owner: event.target.value })
              }
              placeholder="Control owner"
              className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700"
            />
            <textarea
              value={ruleForm.description}
              onChange={(event) =>
                setRuleForm({ ...ruleForm, description: event.target.value })
              }
              placeholder="Rule description"
              rows={3}
              className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700"
            />
            <select
              value={ruleForm.status}
              onChange={(event) =>
                setRuleForm({ ...ruleForm, status: event.target.value })
              }
              className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700"
            >
              <option value="draft">Draft</option>
              <option value="in_review">In review</option>
              <option value="approved">Approved</option>
            </select>
            <select
              value={ruleForm.policy_id}
              onChange={(event) =>
                setRuleForm({
                  ...ruleForm,
                  policy_id: event.target.value,
                  policy_section_id: "",
                })
              }
              className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700"
            >
              <option value="">Policy (optional)</option>
              {policiesLoading ? (
                <option>Loading policies...</option>
              ) : (
                policies.map((policy) => (
                  <option key={policy.id} value={policy.id}>
                    {policy.policy_id} • {policy.name}
                  </option>
                ))
              )}
            </select>
            <select
              value={ruleForm.policy_section_id}
              onChange={(event) =>
                setRuleForm({
                  ...ruleForm,
                  policy_section_id: event.target.value,
                })
              }
              disabled={!ruleForm.policy_id}
              className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700 disabled:opacity-60"
            >
              <option value="">Policy section (optional)</option>
              {sectionsLoading ? (
                <option>Loading sections...</option>
              ) : (
                sections.map((section) => (
                  <option key={section.id} value={section.id}>
                    {section.section_ref ?? "Section"}
                    {""}
                    {section.title ? `• ${section.title}` : ""}
                  </option>
                ))
              )}
            </select>
            <button
              onClick={onCreateInternalRule}
              disabled={rulesActionLoading === "create"}
              className="w-full rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-semibold text-slate-600 hover:border-slate-300 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {rulesActionLoading === "create"
                ? "Saving..."
                : "Add internal rule"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
