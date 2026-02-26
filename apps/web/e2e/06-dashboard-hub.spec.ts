import { test, expect, type Page } from "@playwright/test";
import { loginViaAPI } from "./helpers/auth";

function fakeJwt(payload: Record<string, unknown>) {
  const header = Buffer.from(
    JSON.stringify({ alg: "none", typ: "JWT" }),
  ).toString("base64url");
  const body = Buffer.from(JSON.stringify(payload)).toString("base64url");
  return `${header}.${body}.sig`;
}

function buildMockQueueItems(count = 18) {
  return Array.from({ length: count }).map((_, index) => ({
    item_id: `item_${index + 1}`,
    record_id: `rec_${index + 1}`,
    kind: "alert",
    ref_id: `ALERT-${String(index + 1).padStart(3, "0")}`,
    type_label: index % 2 === 0 ? "Velocity Alert" : "Sanctions Alert",
    severity:
      index % 5 === 0
        ? "critical"
        : index % 3 === 0
          ? "high"
          : index % 2 === 0
            ? "medium"
            : "low",
    entity: `user_${1000 + index}`,
    typology: index % 2 === 0 ? "Structuring" : "Rapid velocity",
    jurisdiction: ["US", "FR", "GB", "AE"][index % 4],
    age_minutes: 12 + index * 7,
    sla_due_at: null,
    sla_status: index % 4 === 0 ? "breached" : index % 3 === 0 ? "warning" : "ok",
    owner: index % 4 === 0 ? null : `analyst_${(index % 3) + 1}`,
    next_action: "review",
    risk_score: 35 + (index % 7) * 9,
    status: "open",
    sar_required: index % 6 === 0,
    review_requirement:
      index % 4 === 0
        ? { required: true, reasons: ["dual_control"] }
        : { required: false, reasons: [] },
  }));
}

async function seedDashboardAuth(page: Page) {
  const token = fakeJwt({
    exp: Math.floor(Date.now() / 1000) + 60 * 60,
    user_id: "analyst_1",
    email: "analyst@example.com",
    role: "aml_analyst",
    tenant_id: "tenant_demo",
  });

  await page.goto("/");
  await page.evaluate(
    ({ accessToken }) => {
      localStorage.setItem("access_token", accessToken);
      localStorage.setItem("token_type", "bearer");
    },
    { accessToken: token },
  );
}

async function installDashboardMocks(page: Page) {
  const queueItems = buildMockQueueItems();
  const selectedItem = queueItems[0];

  await page.route("**/api/workspace/users**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        { user_id: "analyst_1", role: "analyst", is_active: true },
        { user_id: "analyst_2", role: "analyst", is_active: true },
        { user_id: "lead_1", role: "lead", is_active: true },
      ]),
    });
  });

  await page.route("**/api/dashboard/overview**", async (route) => {
    const url = new URL(route.request().url());
    const view = url.searchParams.get("view") ?? "operations";
    const timeRange = url.searchParams.get("time_range") ?? "7d";

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        view,
        time_range: timeRange,
        generated_at: "2026-02-26T08:00:00Z",
        kpis: {
          pending_alerts: 83,
          critical_alerts: 7,
          open_cases: 19,
          transactions_in_range: 14320,
          average_risk_score: 61,
        },
        badges: {
          alerts_pending: 83,
          cases_open: 19,
          critical_open: 7,
        },
        system_health: {
          status: "warning",
          stuck_alerts: 4,
          unprocessed_transactions: 217,
        },
        queues: {
          alerts: [],
          cases: [],
        },
        critical_bar: {
          p1_sla_breaches: 3,
          p2_sla_breaches: 6,
          sanctions_hits_unreviewed: 4,
          sar_due_24h: 2,
          high_risk_cases_unassigned: 5,
          ingestion_lag_minutes: 14,
        },
        queue_summary: {
          alerts_open: 83,
          cases_open: 19,
          approvals_pending: 3,
          reg_tasks_due: 4,
        },
        governance: {
          rule_drift_score: 14.2,
          alert_to_case_rate: 0.23,
          fp_proxy_rate: 0.18,
          audit_completeness_rate: 0.94,
          rule_drift_score_history: [9, 10, 11, 10, 12, 14, 14],
          alert_to_case_rate_history: [0.19, 0.2, 0.18, 0.21, 0.22, 0.24, 0.23],
          fp_proxy_rate_history: [0.28, 0.24, 0.22, 0.2, 0.19, 0.18, 0.18],
          audit_completeness_rate_history: [0.86, 0.88, 0.9, 0.91, 0.93, 0.94, 0.94],
        },
        throughput: {
          median_time_to_first_action_minutes: 31,
          median_case_resolution_hours: 19,
          median_time_to_first_action_delta_minutes: -6,
          median_case_resolution_delta_hours: -2,
          median_time_to_first_action_history: [44, 41, 39, 37, 35, 33, 31],
          median_case_resolution_history: [25, 24, 23, 22, 21, 20, 19],
        },
      }),
    });
  });

  await page.route("**/api/dashboard/work-queue**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        page: 1,
        page_size: 50,
        total: queueItems.length,
        items: queueItems,
      }),
    });
  });

  await page.route("**/api/dashboard/work-items/**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        work_item: selectedItem,
        context_timeline: [
          {
            at: "2026-02-26T07:15:00Z",
            label: "Alert generated",
            detail: "Velocity spike on linked account",
          },
          {
            at: "2026-02-26T07:22:00Z",
            label: "Screening completed",
            detail: "Sanctions check clear",
          },
        ],
        linked_entities: ["user_1000", "merchant_204"],
        linked_transactions: ["tx_1001", "tx_1002", "tx_1003"],
        ai_recommendation: {
          summary: "Escalate for analyst review due to repeated velocity pattern.",
          confidence: 0.86,
          rationale: [
            "Repeated rapid inbound transfers within 30 minutes",
            "Risk score above team threshold",
          ],
        },
        narrative:
          "Clustered transactions indicate potential structuring behavior pending source-of-funds validation.",
        evidence_checklist: [
          { id: "kba", label: "KYC reviewed", completed: true },
          { id: "tx", label: "Transaction sample checked", completed: true },
          { id: "sof", label: "Source of funds requested", completed: false },
        ],
        action_history: [
          {
            at: "2026-02-26T07:26:00Z",
            actor: "analyst_2",
            action: "mark_in_progress",
            notes: "Initial review started",
          },
        ],
        review_requirement: { required: false, reasons: [] },
        allowed_actions: ["assign", "escalate", "mark_in_progress", "create_case"],
      }),
    });
  });
}

function dashboardVisualMasks(page: Page) {
  return [
    page.locator('[aria-label$="trend"]'),
    page.getByText("AI Active").locator("xpath=.."),
  ];
}

test.describe("Dashboard Hub", () => {
  test.beforeEach(async ({ page }) => {
    await loginViaAPI(page);
  });

  test("redirects legacy monitoring entry to unified dashboard", async ({
    page,
  }) => {
    await page.goto("/monitoring");
    await expect(page).toHaveURL(/\/dashboard\?view=monitoring/);
  });

  test("redirects legacy compliance dashboard to unified dashboard", async ({
    page,
  }) => {
    await page.goto("/compliance/dashboard");
    await expect(page).toHaveURL(/\/dashboard\?view=compliance/);
  });

  test("supports deep-linked dashboard views", async ({ page }) => {
    await page.goto("/dashboard?view=operations&range=7d");
    await expect(
      page.getByRole("heading", { name: /command center/i }),
    ).toBeVisible({ timeout: 10_000 });

    await page.goto("/dashboard?view=monitoring&range=24h");
    await expect(
      page.getByRole("heading", { name: /command center/i }),
    ).toBeVisible({ timeout: 10_000 });
  });
});

test.describe("Dashboard Hub visual", () => {
  test.beforeEach(async ({ page }) => {
    await installDashboardMocks(page);
    await seedDashboardAuth(page);
  });

  test("desktop 1280 layout remains stable with insights open @visual", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/dashboard?view=operations&range=7d");

    await expect(
      page.getByRole("heading", { name: /AMLCO Command Center/i }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Insights", exact: true }),
    ).toBeVisible();

    await page.getByRole("button", { name: "Insights", exact: true }).click();
    await page.getByRole("button", { name: /Advanced filters/i }).click();
    await page
      .getByRole("feed", { name: /Unified work queue items/i })
      .getByRole("checkbox", { name: "Select ALERT-001" })
      .click();

    await expect(page.getByText("1 selected")).toBeVisible();
    await expect(page.getByRole("button", { name: "Hide Insights" })).toBeVisible();

    await expect(page.getByTestId("dashboard-hub-root")).toHaveScreenshot(
      "dashboard-hub-desktop-1280.png",
      {
        animations: "disabled",
        caret: "hide",
        mask: dashboardVisualMasks(page),
        maxDiffPixels: 80,
      },
    );
  });

  test("mobile 390 queue and governance panels remain stable @visual", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/dashboard?view=operations&range=7d");

    await expect(
      page.getByRole("heading", { name: /AMLCO Command Center/i }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Queue", exact: true }),
    ).toBeVisible();

    await expect(page.getByTestId("dashboard-hub-root")).toHaveScreenshot(
      "dashboard-hub-mobile-390-queue.png",
      {
        animations: "disabled",
        caret: "hide",
        mask: dashboardVisualMasks(page),
        maxDiffPixels: 80,
      },
    );

    await page.getByRole("button", { name: "Governance", exact: true }).click();
    await expect(page.getByRole("region", { name: /Governance metrics/i })).toBeVisible();

    await expect(page.getByTestId("dashboard-hub-root")).toHaveScreenshot(
      "dashboard-hub-mobile-390-governance.png",
      {
        animations: "disabled",
        caret: "hide",
        mask: dashboardVisualMasks(page),
        maxDiffPixels: 80,
      },
    );
  });
});
