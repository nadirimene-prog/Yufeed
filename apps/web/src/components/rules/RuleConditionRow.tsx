"use client";

import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button-horizon";
import { cn } from "@/lib/utils";

export type RuleOperator =
  | "equals"
  | "not_equals"
  | "greater_than"
  | "less_than"
  | "greater_than_or_equal"
  | "less_than_or_equal"
  | "contains"
  | "in"
  | "not_in"
  | "starts_with"
  | "ends_with";

export interface RuleConditionNode {
  id: string;
  type: "condition";
  field: string;
  operator: RuleOperator;
  value: string;
}

interface RuleConditionRowProps {
  condition: RuleConditionNode;
  availableFields: string[];
  onChange: (patch: Partial<RuleConditionNode>) => void;
  onRemove: () => void;
  removable?: boolean;
  className?: string;
}

const OPERATOR_OPTIONS: Array<{ value: RuleOperator; label: string }> = [
  { value: "greater_than", label: "greater than" },
  { value: "greater_than_or_equal", label: "greater or equal" },
  { value: "less_than", label: "less than" },
  { value: "less_than_or_equal", label: "less or equal" },
  { value: "equals", label: "equals" },
  { value: "not_equals", label: "not equals" },
  { value: "contains", label: "contains" },
  { value: "starts_with", label: "starts with" },
  { value: "ends_with", label: "ends with" },
  { value: "in", label: "in list" },
  { value: "not_in", label: "not in list" },
];

export function RuleConditionRow({
  condition,
  availableFields,
  onChange,
  onRemove,
  removable = true,
  className,
}: RuleConditionRowProps) {
  return (
    <div
      className={cn(
        "grid grid-cols-1 gap-2 rounded-xl border border-border-subtle bg-background-overlay p-3 md:grid-cols-[1fr_1fr_1fr_auto]",
        className,
      )}
    >
      <label className="space-y-1 text-xs text-foreground-secondary">
        <span>Field</span>
        <select
          value={condition.field}
          onChange={(event) => onChange({ field: event.target.value })}
          className="h-9 w-full rounded-lg border border-border bg-background px-2 text-sm text-foreground"
        >
          {availableFields.map((field) => (
            <option key={field} value={field}>
              {field}
            </option>
          ))}
        </select>
      </label>

      <label className="space-y-1 text-xs text-foreground-secondary">
        <span>Operator</span>
        <select
          value={condition.operator}
          onChange={(event) =>
            onChange({ operator: event.target.value as RuleOperator })
          }
          className="h-9 w-full rounded-lg border border-border bg-background px-2 text-sm text-foreground"
        >
          {OPERATOR_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>

      <label className="space-y-1 text-xs text-foreground-secondary">
        <span>Value</span>
        <input
          value={condition.value}
          onChange={(event) => onChange({ value: event.target.value })}
          placeholder={
            condition.operator === "in" || condition.operator === "not_in"
              ? "comma,separated,values"
              : "value"
          }
          className="h-9 w-full rounded-lg border border-border bg-background px-2 text-sm text-foreground placeholder:text-foreground-tertiary"
        />
      </label>

      <div className="flex items-end">
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          disabled={!removable}
          onClick={onRemove}
          aria-label="Remove condition"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

export default RuleConditionRow;
