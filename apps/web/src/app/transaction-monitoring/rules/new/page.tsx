"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, Code2, Eye, Save, WandSparkles } from "lucide-react";
import { Button } from "@/components/ui/button-horizon";
import { cn } from "@/lib/utils";
import {
  RuleConditionBuilder,
  buildRuleConditionsPayload,
  createDefaultRuleGroup,
  type RuleConditionGroupNode,
} from "@/components/rules/RuleConditionBuilder";
import { useCreateRule } from "@/hooks/queries/useRulesData";

const SEVERITY_OPTIONS = ["low", "medium", "high", "critical"] as const;
const DEFAULT_ACTION_OPTIONS = [
  "flag_for_review",
  "accept",
  "decline",
  "escalate",
] as const;

export default function RuleBuilderPage() {
  const router = useRouter();
  const createRule = useCreateRule();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("velocity");
  const [severity, setSeverity] =
    useState<(typeof SEVERITY_OPTIONS)[number]>("medium");
  const [enabled, setEnabled] = useState(true);
  const [thresholds, setThresholds] = useState("{}");
  const [conditionsGroup, setConditionsGroup] =
    useState<RuleConditionGroupNode>(createDefaultRuleGroup);

  const [defaultAction, setDefaultAction] =
    useState<(typeof DEFAULT_ACTION_OPTIONS)[number]>("flag_for_review");
  const [variantAPercent, setVariantAPercent] = useState(100);

  const [activeTab, setActiveTab] = useState<"builder" | "preview">("builder");
  const [error, setError] = useState<string | null>(null);

  const conditionsPayload = useMemo(
    () => buildRuleConditionsPayload(conditionsGroup),
    [conditionsGroup],
  );

  const previewPayload = useMemo(
    () => ({
      name,
      description,
      category,
      severity,
      enabled,
      conditions: conditionsPayload,
      thresholds,
      workflow: {
        default_action: defaultAction,
        variant_a_percent: variantAPercent,
        variant_b_percent: Math.max(0, 100 - variantAPercent),
      },
    }),
    [
      category,
      conditionsPayload,
      defaultAction,
      description,
      enabled,
      name,
      severity,
      thresholds,
      variantAPercent,
    ],
  );

  const handleSave = async () => {
    setError(null);

    if (name.trim().length < 3) {
      setError("Rule name must be at least 3 characters.");
      return;
    }

    if (conditionsPayload.conditions.length === 0) {
      setError("Add at least one condition to save the rule.");
      return;
    }

    let thresholdsPayload: Record<string, unknown> | undefined;
    try {
      thresholdsPayload = thresholds.trim()
        ? (JSON.parse(thresholds) as Record<string, unknown>)
        : undefined;
    } catch {
      setError("Thresholds must be valid JSON.");
      return;
    }

    if (variantAPercent < 0 || variantAPercent > 100) {
      setError("A/B split must be between 0 and 100.");
      return;
    }

    try {
      await createRule.mutateAsync({
        name: name.trim(),
        description: description.trim() || undefined,
        category: category.trim() || undefined,
        severity,
        enabled,
        conditions: conditionsPayload as unknown as Record<string, unknown>,
        thresholds: {
          ...(thresholdsPayload ?? {}),
          workflow: {
            default_action: defaultAction,
            variant_a_percent: variantAPercent,
            variant_b_percent: Math.max(0, 100 - variantAPercent),
          },
        },
      });
      router.push("/transaction-monitoring/rules");
    } catch (saveError) {
      const message =
        saveError instanceof Error
          ? saveError.message
          : "Failed to create rule";
      setError(message);
    }
  };

  return (
    <div className="flex h-[calc(100vh-7rem)] flex-col gap-4 overflow-hidden">
      <header className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-display font-semibold text-foreground">
            Visual Workflow Builder
          </h1>
          <p className="text-sm text-foreground-secondary">
            Build transaction decision logic with reusable conditions and
            rollout settings.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="glass"
            onClick={() => router.push("/transaction-monitoring/rules")}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            loading={createRule.isPending}
            leftIcon={<Save className="h-4 w-4" />}
          >
            Save Rule
          </Button>
        </div>
      </header>

      {error ? (
        <div className="rounded-xl border border-risk-critical/40 bg-risk-critical-soft px-4 py-3 text-sm text-risk-critical">
          {error}
        </div>
      ) : null}

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[320px_1fr]">
        <aside className="min-h-0 space-y-4 overflow-auto rounded-2xl border border-border-default bg-bg-elevated p-4">
          <div className="space-y-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-foreground-secondary">
              Rule Metadata
            </h2>

            <label className="space-y-1 text-xs text-foreground-secondary">
              <span>Name</span>
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Unusual High Value Transfer"
                className="h-10 w-full rounded-lg border border-border-default bg-bg-overlay px-3 text-sm"
              />
            </label>

            <label className="space-y-1 text-xs text-foreground-secondary">
              <span>Severity</span>
              <select
                value={severity}
                onChange={(event) =>
                  setSeverity(
                    event.target.value as (typeof SEVERITY_OPTIONS)[number],
                  )
                }
                className="h-10 w-full rounded-lg border border-border-default bg-bg-overlay px-3 text-sm"
              >
                {SEVERITY_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-1 text-xs text-foreground-secondary">
              <span>Category</span>
              <input
                value={category}
                onChange={(event) => setCategory(event.target.value)}
                placeholder="velocity"
                className="h-10 w-full rounded-lg border border-border-default bg-bg-overlay px-3 text-sm"
              />
            </label>

            <label className="space-y-1 text-xs text-foreground-secondary">
              <span>Description</span>
              <textarea
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                rows={4}
                className="w-full rounded-lg border border-border-default bg-bg-overlay px-3 py-2 text-sm"
              />
            </label>

            <label className="inline-flex items-center gap-2 text-sm text-foreground-secondary">
              <input
                type="checkbox"
                checked={enabled}
                onChange={(event) => setEnabled(event.target.checked)}
              />
              Enabled on publish
            </label>
          </div>

          <div className="space-y-3 rounded-xl border border-border-subtle bg-bg-overlay p-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-foreground-secondary">
              Decision Workflow
            </h3>
            <label className="space-y-1 text-xs text-foreground-secondary">
              <span>Default action</span>
              <select
                value={defaultAction}
                onChange={(event) =>
                  setDefaultAction(
                    event.target
                      .value as (typeof DEFAULT_ACTION_OPTIONS)[number],
                  )
                }
                className="h-9 w-full rounded-lg border border-border-default bg-bg-base px-2 text-sm"
              >
                {DEFAULT_ACTION_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option.replaceAll("_", " ")}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-1 text-xs text-foreground-secondary">
              <span>A/B traffic split (Variant A)</span>
              <input
                type="number"
                min={0}
                max={100}
                value={variantAPercent}
                onChange={(event) =>
                  setVariantAPercent(Number(event.target.value || 0))
                }
                className="h-9 w-full rounded-lg border border-border-default bg-bg-base px-2 text-sm"
              />
            </label>
            <p className="text-[11px] text-foreground-tertiary">
              Variant B receives {Math.max(0, 100 - variantAPercent)}% of
              traffic. Keep at 0% until experiments are approved.
            </p>
          </div>

          <div className="space-y-1 text-xs text-foreground-secondary">
            <label htmlFor="thresholds-json">Thresholds JSON</label>
            <textarea
              id="thresholds-json"
              value={thresholds}
              onChange={(event) => setThresholds(event.target.value)}
              rows={5}
              className="w-full rounded-lg border border-border-default bg-bg-overlay px-3 py-2 font-mono text-xs"
            />
          </div>

          <div className="rounded-xl border border-primary/30 bg-primary/10 p-3 text-xs text-primary">
            <p className="mb-1 font-semibold">Workflow note</p>
            <p>
              Version history and rollback remain available through the rule
              approval flow in the rules index.
            </p>
          </div>
        </aside>

        <section className="flex min-h-0 flex-col overflow-hidden rounded-2xl border border-border-default bg-bg-elevated">
          <div className="flex items-center gap-1 border-b border-border-subtle p-2">
            <button
              type="button"
              onClick={() => setActiveTab("builder")}
              className={cn(
                "inline-flex items-center gap-1 rounded-lg px-3 py-2 text-xs font-semibold uppercase tracking-wide",
                activeTab === "builder"
                  ? "bg-primary/20 text-primary"
                  : "text-foreground-secondary hover:bg-bg-overlay",
              )}
            >
              <WandSparkles className="h-3.5 w-3.5" />
              Builder
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("preview")}
              className={cn(
                "inline-flex items-center gap-1 rounded-lg px-3 py-2 text-xs font-semibold uppercase tracking-wide",
                activeTab === "preview"
                  ? "bg-primary/20 text-primary"
                  : "text-foreground-secondary hover:bg-bg-overlay",
              )}
            >
              <Code2 className="h-3.5 w-3.5" />
              JSON Preview
            </button>
          </div>

          <div className="min-h-0 flex-1 overflow-auto p-4">
            {activeTab === "builder" ? (
              <RuleConditionBuilder
                group={conditionsGroup}
                onChange={setConditionsGroup}
              />
            ) : (
              <div className="h-full rounded-xl border border-border-subtle bg-black/40 p-4">
                <p className="mb-2 inline-flex items-center gap-1 text-xs uppercase tracking-wide text-foreground-tertiary">
                  <Eye className="h-3.5 w-3.5" />
                  Payload Preview
                </p>
                <pre className="overflow-auto font-mono text-xs text-cyan-200">
                  {JSON.stringify(previewPayload, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </section>
      </div>

      <footer className="rounded-xl border border-border-subtle bg-bg-elevated px-4 py-3 text-xs text-foreground-tertiary">
        <p className="inline-flex items-center gap-1.5">
          <AlertTriangle className="h-3.5 w-3.5 text-risk-high" />
          Rules are tenant-scoped and submitted through the approval workflow
          for production changes.
        </p>
      </footer>
    </div>
  );
}
