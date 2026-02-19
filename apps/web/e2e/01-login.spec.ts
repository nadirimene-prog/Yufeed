import { test, expect } from '@playwright/test';
import { loginViaUI } from './helpers/auth';

/**
 * E2E Scenario 1: Login → Dashboard visible
 *
 * Verifies the full authentication flow:
 * - Navigate to login page
 * - Enter credentials
 * - Submit form
 * - Dashboard loads with key elements visible
 */

test.describe('Login Flow', () => {
  test('should login and show dashboard', async ({ page }) => {
    await loginViaUI(page);

    // Wait for navigation to dashboard (or any post-login page)
    await page.waitForURL(/\/dashboard/, { timeout: 20_000 });

    // Verify the user is authenticated — the page should show navigation
    // and not redirect back to login
    const currentURL = page.url();
    expect(currentURL).not.toContain('/login');

    // Check for common dashboard elements
    await expect(
      page.getByRole('heading', { name: /command center/i }),
    ).toBeVisible({ timeout: 10_000 });
  });

  test('should reject invalid credentials', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/email/i).fill('invalid@test.com');
    await page.getByLabel(/password/i).fill('WrongPassword1');
    await page.getByRole('button', { name: /log\s*in|sign\s*in/i }).click();

    // Should stay on login page or show an error
    await expect(
      page.getByText(/incorrect|invalid|failed/i),
    ).toBeVisible({ timeout: 10_000 });
  });

  test('should redirect unauthenticated users to login', async ({ page }) => {
    // Clear any stored tokens
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });

    // Try to access a protected route
    await page.goto('/compliance/dashboard');

    // Should redirect to sign-in route
    await page.waitForURL(/\/$/, { timeout: 20_000 });
    await expect(
      page.getByRole('heading', { name: /sign in to your workspace/i }),
    ).toBeVisible({ timeout: 10_000 });
  });
});
