import { describe, expect, it } from "vitest";
import { dashboardKeys } from "@/lib/queryKeys";
import {
  formatRangeLabel,
  resolveDashboardTimeRange,
  resolveDashboardView,
  severityBadgeClass,
} from "@/features/dashboard/utils";

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

  it("generates stable dashboard query keys", () => {
    expect(dashboardKeys.overview("operations", "7d")).toEqual([
      "dashboard",
      "overview",
      "operations",
      "7d",
    ]);
    expect(dashboardKeys.badges()).toEqual(["dashboard", "badges"]);
  });
});
