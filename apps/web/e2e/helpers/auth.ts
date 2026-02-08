import { type Page } from '@playwright/test';

/**
 * Shared authentication helper for E2E tests.
 *
 * Logs in via the API and stores the JWT in localStorage,
 * matching how the real app handles auth.
 */

const API_BASE = process.env.E2E_API_URL ?? 'http://localhost:8000';

export interface TestUser {
  email: string;
  password: string;
}

/** Default test user — must exist in the test database. */
export const TEST_USER: TestUser = {
  email: process.env.E2E_USER_EMAIL ?? 'admin@yufeed.local',
  password: process.env.E2E_USER_PASSWORD ?? 'Admin123!',
};

/**
 * Authenticate a test user and inject the JWT into the browser.
 * After calling this, the page can navigate to any protected route.
 */
export async function loginViaAPI(page: Page, user: TestUser = TEST_USER): Promise<void> {
  // Call the login endpoint directly
  const response = await page.request.post(`${API_BASE}/api/auth/login`, {
    data: { email: user.email, password: user.password },
  });

  if (!response.ok()) {
    throw new Error(`Login failed (${response.status()}): ${await response.text()}`);
  }

  const body = await response.json();
  const accessToken: string = body.access_token;
  const refreshToken: string = body.refresh_token;

  // Inject tokens into localStorage (matching the app's auth.ts storage keys)
  await page.goto('/');
  await page.evaluate(
    ({ access, refresh }) => {
      localStorage.setItem('yufeed_auth_token', access);
      localStorage.setItem('yufeed_refresh_token', refresh);
    },
    { access: accessToken, refresh: refreshToken },
  );
}

/**
 * Login via the UI login form (for the login flow test itself).
 */
export async function loginViaUI(page: Page, user: TestUser = TEST_USER): Promise<void> {
  await page.goto('/login');
  await page.getByLabel(/email/i).fill(user.email);
  await page.getByLabel(/password/i).fill(user.password);
  await page.getByRole('button', { name: /log\s*in|sign\s*in/i }).click();
}
