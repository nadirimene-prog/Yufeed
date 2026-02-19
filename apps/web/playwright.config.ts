import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E test configuration for YuFeed.
 *
 * Assumes:
 * - Backend running on http://127.0.0.1:8000
 * - Frontend running on http://localhost:3000
 *
 * Run: npx playwright test
 * Debug: npx playwright test --debug
 * UI: npx playwright test --ui
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: process.env.CI ? 'github' : 'html',
  timeout: 30_000,

  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  /* Start the frontend dev server if not already running */
  webServer: process.env.CI
    ? undefined
    : {
        command: 'NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 API_INTERNAL_URL=http://127.0.0.1:8000 npm run dev',
        url: 'http://localhost:3000',
        reuseExistingServer: true,
        timeout: 120_000,
      },
});
