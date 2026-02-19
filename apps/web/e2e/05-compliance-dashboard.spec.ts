import { test, expect } from "@playwright/test";
import { loginViaAPI } from "./helpers/auth";

/**
 * E2E Scenario 5: Compliance Dashboard
 *
 * Verifies the compliance overview:
 * - Dashboard loads with metrics
 * - Obligations section visible
 * - Navigation to sub-pages works
 */

test.describe("Compliance Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await loginViaAPI(page);
  });

  test("should display compliance dashboard with metrics", async ({ page }) => {
    await page.goto("/compliance/dashboard");

    await expect(page).toHaveURL(/\/dashboard\?view=compliance/);

    // Wait for the unified dashboard to load
    await expect(
      page.getByRole("heading", { name: /command center/i }),
    ).toBeVisible({ timeout: 10_000 });

    // The page should not be the login page
    expect(page.url()).not.toContain("/login");
  });

  test("should display watchlists page", async ({ page }) => {
    await page.goto("/watchlists");

    await expect(page.getByRole("heading", { name: /watchlist/i })).toBeVisible(
      { timeout: 10_000 },
    );
  });

  test("should navigate between compliance pages", async ({ page }) => {
    await page.goto("/compliance/dashboard");
    await expect(page).toHaveURL(/\/dashboard\?view=compliance/);

    await expect(
      page.getByRole("heading", { name: /command center/i }),
    ).toBeVisible({ timeout: 10_000 });

    // Sidebar defaults to collapsed; expand it so text links are visible.
    const expandSidebar = page.getByRole("button", { name: /expand sidebar/i });
    if (await expandSidebar.isVisible()) {
      await expandSidebar.click();
    }

    // Navigate through sidebar to obligations
    const obligationsLink = page
      .locator('aside:visible a[href="/compliance/obligations"]')
      .first();
    await expect(obligationsLink).toBeVisible({ timeout: 10_000 });
    await obligationsLink.click();
    await expect(page).toHaveURL(/\/compliance\/obligations/, {
      timeout: 10_000,
    });
  });
});
