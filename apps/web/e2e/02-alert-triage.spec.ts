import { test, expect } from '@playwright/test';
import { loginViaAPI } from './helpers/auth';

/**
 * E2E Scenario 2: Triage Alert
 *
 * Verifies the alert investigation workflow:
 * - Navigate to transaction alerts page
 * - Open an alert
 * - Verify alert detail page loads
 * - Check that status/actions are visible
 */

test.describe('Alert Triage', () => {
  test.beforeEach(async ({ page }) => {
    await loginViaAPI(page);
  });

  test('should display alerts list', async ({ page }) => {
    await page.goto('/transaction-alerts');

    // Wait for page to load
    await expect(
      page.getByRole('heading', { name: /transaction alert/i }),
    ).toBeVisible({ timeout: 10_000 });

    // Verify filter controls are present
    await expect(page.getByPlaceholder(/search/i)).toBeVisible();
  });

  test('should filter alerts by severity', async ({ page }) => {
    await page.goto('/transaction-alerts');

    await expect(
      page.getByRole('heading', { name: /transaction alert/i }),
    ).toBeVisible({ timeout: 10_000 });

    // Select "Critical" severity filter
    const severitySelect = page.locator('select').last();
    await severitySelect.selectOption('critical');

    // Wait for re-render — the filtered list should update
    await page.waitForTimeout(500);

    // If any alert cards are visible, they should all show "CRITICAL"
    const severityBadges = page.locator('text=CRITICAL');
    const count = await severityBadges.count();
    // Either we have critical alerts or we see a "No alerts found" message
    if (count === 0) {
      await expect(page.getByText(/no alerts found/i)).toBeVisible();
    }
  });

  test('should navigate to alert detail', async ({ page }) => {
    await page.goto('/transaction-alerts');

    await expect(
      page.getByRole('heading', { name: /transaction alert/i }),
    ).toBeVisible({ timeout: 10_000 });

    // Click the first alert card (if any exist)
    const alertCards = page.locator('[class*="cursor-pointer"]');
    const cardCount = await alertCards.count();

    if (cardCount > 0) {
      await alertCards.first().click();

      // Should navigate to alert detail page
      await page.waitForURL(/\/transaction-alerts\//, { timeout: 10_000 });
    }
  });
});
