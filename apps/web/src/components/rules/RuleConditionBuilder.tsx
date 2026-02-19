"use client";

import { useMemo } from "react";
import RuleConditionGroup, {
  type RuleConditionGroupNode,
  type RuleTreeNode,
} from "@/components/rules/RuleConditionGroup";
import type {
  RuleConditionNode,
  RuleOperator,
} from "@/components/rules/RuleConditionRow";

export interface RuleConditionPayload {
  field: string;
  operator: RuleOperator;
  value: string | number | Array<string | number>;
}

export interface RuleConditionsPayload {
  logic: "AND" | "OR";
  conditions: RuleConditionPayload[];
}

export const DEFAULT_RULE_FIELDS = [
  "amount",
  "currency",
  "country_code",
  "transaction_type",
  "user_id",
  "counterparty_id",
  "status",
  "risk_score",
];

export function createDefaultRuleCondition(): RuleConditionNode {
  return {
    id: crypto.randomUUID(),
    type: "condition",
    field: "amount",
    operator: "greater_than",
    value: "1000",
  };
}

export function createDefaultRuleGroup(): RuleConditionGroupNode {
  return {
    id: crypto.randomUUID(),
    type: "group",
    logic: "AND",
    children: [createDefaultRuleCondition()],
  };
}

function collectConditionNodes(node: RuleTreeNode): RuleConditionNode[] {
  if (node.type === "condition") return [node];
  return node.children.flatMap((child) => collectConditionNodes(child));
}

function parsePrimitiveValue(value: string): string | number {
  const trimmed = value.trim();
  if (trimmed.length === 0) return "";

  const numeric = Number(trimmed);
  if (!Number.isNaN(numeric) && Number.isFinite(numeric)) {
    return numeric;
  }

  return trimmed;
}

function parseConditionValue(condition: RuleConditionNode) {
  if (condition.operator === "in" || condition.operator === "not_in") {
    return condition.value
      .split(",")
      .map((item) => parsePrimitiveValue(item))
      .filter((item) => `${item}`.trim().length > 0);
  }

  return parsePrimitiveValue(condition.value);
}

export function buildRuleConditionsPayload(
  group: RuleConditionGroupNode,
): RuleConditionsPayload {
  const conditions = collectConditionNodes(group).map((condition) => ({
    field: condition.field,
    operator: condition.operator,
    value: parseConditionValue(condition),
  }));

  return {
    logic: group.logic,
    conditions,
  };
}

interface RuleConditionBuilderProps {
  group: RuleConditionGroupNode;
  onChange: (next: RuleConditionGroupNode) => void;
  fields?: string[];
  className?: string;
}

export function RuleConditionBuilder({
  group,
  onChange,
  fields = DEFAULT_RULE_FIELDS,
  className,
}: RuleConditionBuilderProps) {
  const dedupedFields = useMemo(
    () => Array.from(new Set(fields.filter(Boolean))),
    [fields],
  );

  return (
    <div className={className}>
      <RuleConditionGroup
        group={group}
        isRoot
        availableFields={dedupedFields}
        onChange={onChange}
      />
    </div>
  );
}

export default RuleConditionBuilder;
export type { RuleConditionGroupNode } from "@/components/rules/RuleConditionGroup";
