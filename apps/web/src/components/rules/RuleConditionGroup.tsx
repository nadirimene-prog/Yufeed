"use client";

import { Braces, GitBranch, Plus } from "lucide-react";
import { Button } from "@/components/ui/button-horizon";
import { cn } from "@/lib/utils";
import RuleConditionRow, {
  type RuleConditionNode,
  type RuleOperator,
} from "@/components/rules/RuleConditionRow";

export interface RuleConditionGroupNode {
  id: string;
  type: "group";
  logic: "AND" | "OR";
  children: RuleTreeNode[];
}

export type RuleTreeNode = RuleConditionNode | RuleConditionGroupNode;

function createCondition(): RuleConditionNode {
  return {
    id: crypto.randomUUID(),
    type: "condition",
    field: "amount",
    operator: "greater_than",
    value: "1000",
  };
}

function createGroup(): RuleConditionGroupNode {
  return {
    id: crypto.randomUUID(),
    type: "group",
    logic: "AND",
    children: [createCondition()],
  };
}

interface RuleConditionGroupProps {
  group: RuleConditionGroupNode;
  availableFields: string[];
  onChange: (next: RuleConditionGroupNode) => void;
  onRemove?: () => void;
  isRoot?: boolean;
  depth?: number;
}

function updateChild(
  children: RuleTreeNode[],
  childId: string,
  updater: (node: RuleTreeNode) => RuleTreeNode,
) {
  return children.map((child) =>
    child.id === childId ? updater(child) : child,
  );
}

export function RuleConditionGroup({
  group,
  availableFields,
  onChange,
  onRemove,
  isRoot = false,
  depth = 0,
}: RuleConditionGroupProps) {
  const canRemoveChild = group.children.length > 1;

  return (
    <section
      className={cn(
        "rounded-xl border border-border bg-background-elevated p-3",
        depth > 0 && "bg-background-overlay",
      )}
    >
      <header className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="inline-flex items-center gap-2 rounded-lg bg-primary/10 px-2 py-1 text-xs font-semibold uppercase tracking-wide text-primary">
          <GitBranch className="h-3.5 w-3.5" />
          Logic Group
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <label className="inline-flex items-center gap-1 text-xs text-foreground-secondary">
            Logic
            <select
              value={group.logic}
              onChange={(event) =>
                onChange({
                  ...group,
                  logic: event.target.value as "AND" | "OR",
                })
              }
              className="h-8 rounded-md border border-border bg-background px-2 text-xs text-foreground"
            >
              <option value="AND">AND</option>
              <option value="OR">OR</option>
            </select>
          </label>

          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() =>
              onChange({
                ...group,
                children: [...group.children, createCondition()],
              })
            }
          >
            <Plus className="h-3.5 w-3.5" />
            Condition
          </Button>
          <Button
            type="button"
            size="sm"
            variant="secondary"
            onClick={() =>
              onChange({
                ...group,
                children: [...group.children, createGroup()],
              })
            }
          >
            <Braces className="h-3.5 w-3.5" />
            Group
          </Button>
          {!isRoot && onRemove ? (
            <Button type="button" size="sm" variant="ghost" onClick={onRemove}>
              Remove
            </Button>
          ) : null}
        </div>
      </header>

      <div className="space-y-3">
        {group.children.map((child) => {
          if (child.type === "condition") {
            return (
              <RuleConditionRow
                key={child.id}
                condition={child}
                availableFields={availableFields}
                removable={canRemoveChild}
                onChange={(patch) => {
                  onChange({
                    ...group,
                    children: updateChild(group.children, child.id, (node) => ({
                      ...(node as RuleConditionNode),
                      ...patch,
                      operator:
                        (patch.operator as RuleOperator | undefined) ??
                        (node as RuleConditionNode).operator,
                    })),
                  });
                }}
                onRemove={() => {
                  if (!canRemoveChild) return;
                  onChange({
                    ...group,
                    children: group.children.filter(
                      (node) => node.id !== child.id,
                    ),
                  });
                }}
              />
            );
          }

          return (
            <RuleConditionGroup
              key={child.id}
              group={child}
              availableFields={availableFields}
              depth={depth + 1}
              onChange={(nextChild) => {
                onChange({
                  ...group,
                  children: updateChild(
                    group.children,
                    child.id,
                    () => nextChild,
                  ),
                });
              }}
              onRemove={() => {
                if (!canRemoveChild) return;
                onChange({
                  ...group,
                  children: group.children.filter(
                    (node) => node.id !== child.id,
                  ),
                });
              }}
            />
          );
        })}
      </div>
    </section>
  );
}

export default RuleConditionGroup;
