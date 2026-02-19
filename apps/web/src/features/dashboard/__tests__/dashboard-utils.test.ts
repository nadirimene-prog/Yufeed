import { describe, expect, it } from "vitest";
import { dashboardKeys } from "@/lib/queryKeys";
import {
  formatAgeMinutes,
  formatRangeLabel,
  rankQueueItems,
  resolveDashboardTimeRange,
  resolveDashboardView,
  severityBadgeClass,
  slaBadgeClass,
} from "@/features/dashboard/utils";
import {
  DashboardWorkQueueItem,
  WorkspaceMessage,
} from "@/features/dashboard/types";

describe("dashboard utils", () => {
  it("resolves dashboard view with safe defaults", () => {
    expect(resolveDashboardView("operations")).toBe("operations");
    expect(resolveDashboardView("compliance")).toBe("compliance");
    expect(resolveDashboardView("monitoring")).toBe("monitoring");
    expect(resolveDashboardView("unknown")).toBe("operations");
    expect(resolveDashboardView(undefined)).toBe("operations");
  });

  it("resolves time range with safe defaults", () => {
    expect(resolveDashboardTimeRange("24h")).toBe("24h");
    expect(resolveDashboardTimeRange("7d")).toBe("7d");
    expect(resolveDashboardTimeRange("30d")).toBe("30d");
    expect(resolveDashboardTimeRange("bad")).toBe("7d");
  });

  it("formats labels for selected time ranges", () => {
    expect(formatRangeLabel("24h")).toBe("Last 24 hours");
    expect(formatRangeLabel("7d")).toBe("Last 7 days");
    expect(formatRangeLabel("30d")).toBe("Last 30 days");
  });

  it("maps severity to expected badge classes", () => {
    expect(severityBadgeClass("critical")).toContain("text-risk-critical");
    expect(severityBadgeClass("high")).toContain("text-risk-high");
    expect(severityBadgeClass("medium")).toContain("text-risk-medium");
    expect(severityBadgeClass("low")).toContain("text-risk-low");
  });

  it("maps SLA status to expected badge classes", () => {
    expect(slaBadgeClass("breached")).toContain("text-risk-critical");
    expect(slaBadgeClass("warning")).toContain("text-risk-high");
    expect(slaBadgeClass("ok")).toContain("text-risk-clear");
    expect(slaBadgeClass("none")).toContain("text-risk-low");
  });

  it("formats queue age labels", () => {
    expect(formatAgeMinutes(45)).toBe("45m");
    expect(formatAgeMinutes(180)).toBe("3h");
    expect(formatAgeMinutes(2880)).toBe("2d");
  });

  it("preserves server-ranked queue order", () => {
    const base: Omit<
      DashboardWorkQueueItem,
      "item_id" | "severity" | "sla_status"
    > = {
      record_id: "1",
      kind: "alert",
      ref_id: "A-1",
      type_label: "Alert",
      entity: "u-1",
      typology: "sanctions",
      jurisdiction: "US",
      age_minutes: 60,
      sla_due_at: null,
      owner: null,
      next_action: "Review",
      risk_score: 10,
      status: "pending",
      sar_required: false,
      review_requirement: { required: false, reasons: [] },
    };
    const items: DashboardWorkQueueItem[] = [
      {
        ...base,
        item_id: "low-ok",
        severity: "low",
        sla_status: "ok",
        risk_score: 10,
        age_minutes: 120,
      },
      {
        ...base,
        item_id: "high-warning",
        severity: "high",
        sla_status: "warning",
        risk_score: 80,
      },
      {
        ...base,
        item_id: "critical-breached",
        severity: "critical",
        sla_status: "breached",
        risk_score: 90,
      },
    ];

    const ranked = rankQueueItems(items);
    expect(ranked.map((item) => item.item_id)).toEqual([
      "low-ok",
      "high-warning",
      "critical-breached",
    ]);
  });

  it("generates stable dashboard query keys", () => {
    expect(dashboardKeys.overview("operations", "7d")).toEqual([
      "dashboard",
      "overview",
      "operations",
      "7d",
    ]);
    expect(dashboardKeys.badges()).toEqual(["dashboard", "badges"]);
    expect(
      dashboardKeys.workQueue({
        page: 1,
        queue: "all",
      }),
    ).toEqual(["dashboard", "work-queue", { page: 1, queue: "all" }]);
    expect(dashboardKeys.workItem("alert", "123")).toEqual([
      "dashboard",
      "work-item",
      "alert",
      "123",
    ]);
  });

  it("encodes URL-persisted queue filters in query keys", () => {
    expect(
      dashboardKeys.workQueue({
        page: 3,
        pageSize: 25,
        queue: "alerts",
        severity: "critical",
        sla: "breached",
        search: "entity_123",
        jurisdiction: "US",
        savedView: "team_queue",
      }),
    ).toEqual([
      "dashboard",
      "work-queue",
      {
        page: 3,
        pageSize: 25,
        queue: "alerts",
        severity: "critical",
        sla: "breached",
        search: "entity_123",
        jurisdiction: "US",
        savedView: "team_queue",
      },
    ]);
  });

  it("supports typed workspace messages", () => {
    const successMessage: WorkspaceMessage = {
      text: "Draft saved",
      type: "success",
    };
    const errorMessage: WorkspaceMessage = {
      text: "Action failed",
      type: "error",
    };

    expect(successMessage.type).toBe("success");
    expect(errorMessage.type).toBe("error");
  });
});
