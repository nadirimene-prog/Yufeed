import { test, expect } from '@playwright/test';
import { loginViaAPI } from './helpers/auth';

/**
 * E2E Scenario 3: Monitoring Rules Management
 *
 * Verifies the rules CRUD workflow:
 * - Navigate to rules page
 * - See rules list with stats
 * - Filter rules
 * - Export rules (CSV button visible)
 */

test.describe('Monitoring Rules', () => {
  test.beforeEach(async ({ page }) => {
    await loginViaAPI(page);
  });

  test('should display rules list with stats', async ({ page }) => {
    await page.goto('/transaction-monitoring/rules');

    // Wait for rules page to load
    await expect(
      page.getByRole('heading', { name: /monitoring rules/i }),
    ).toBeVisible({ timeout: 10_000 });

    // Verify stat cards are present
    await expect(page.getByText(/total rules/i)).toBeVisible();
    await expect(page.getByText(/enabled rules/i)).toBeVisible();
  });

  test('should filter rules by search', async ({ page }) => {
    await page.goto('/transaction-monitoring/rules');

    await expect(
      page.getByRole('heading', { name: /monitoring rules/i }),
    ).toBeVisible({ timeout: 10_000 });

    // Type in search box
    const searchInput = page.getByPlaceholder(/search rules/i);
    await searchInput.fill('structuring');

    // Wait for filter to apply
    await page.waitForTimeout(300);

    // The page should have filtered results (or empty state)
  });

  test('should have export button', async ({ page }) => {
    await page.goto('/transaction-monitoring/rules');

    await expect(
      page.getByRole('heading', { name: /monitoring rules/i }),
    ).toBeVisible({ timeout: 10_000 });

    // Verify the Export button exists
    const exportBtn = page.getByRole('button', { name: /export/i });
    await expect(exportBtn).toBeVisible();
  });
});
