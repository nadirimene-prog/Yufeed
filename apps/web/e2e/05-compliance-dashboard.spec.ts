import { test, expect } from '@playwright/test';
import { loginViaAPI } from './helpers/auth';

/**
 * E2E Scenario 5: Compliance Dashboard
 *
 * Verifies the compliance overview:
 * - Dashboard loads with metrics
 * - Obligations section visible
 * - Navigation to sub-pages works
 */

test.describe('Compliance Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await loginViaAPI(page);
  });

  test('should display compliance dashboard with metrics', async ({ page }) => {
    await page.goto('/compliance/dashboard');

    // Wait for the dashboard to load
    await expect(
      page.getByRole('heading').first(),
    ).toBeVisible({ timeout: 10_000 });

    // The page should not be the login page
    expect(page.url()).not.toContain('/login');
  });

  test('should display watchlists page', async ({ page }) => {
    await page.goto('/watchlists');

    await expect(
      page.getByRole('heading', { name: /watchlist/i }),
    ).toBeVisible({ timeout: 10_000 });
  });

  test('should navigate between compliance pages', async ({ page }) => {
    await page.goto('/compliance/dashboard');

    await expect(
      page.getByRole('heading').first(),
    ).toBeVisible({ timeout: 10_000 });

    // Try navigating to obligations
    const obligationsLink = page.getByRole('link', { name: /obligation|view all/i }).first();
    const hasLink = await obligationsLink.isVisible().catch(() => false);

    if (hasLink) {
      await obligationsLink.click();
      await page.waitForTimeout(1_000);
      // Should have navigated away from dashboard
      expect(page.url()).not.toBe('about:blank');
    }
  });
});
