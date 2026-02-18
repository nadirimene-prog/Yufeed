import { test, expect } from "@playwright/test";
import { loginViaAPI } from "./helpers/auth";

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
