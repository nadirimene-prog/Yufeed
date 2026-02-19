import { type Page } from '@playwright/test';

/**
 * Shared authentication helper for E2E tests.
 *
 * Logs in via the API and stores the JWT in localStorage,
 * matching how the real app handles auth.
 */

const API_BASE = process.env.E2E_API_URL ?? 'http://127.0.0.1:8000';
const POST_LOGIN_URL = '/dashboard?view=operations&range=7d';
const TOKEN_CACHE = new Map<
  string,
  {
    accessToken: string;
    refreshToken?: string;
    tokenType?: string;
    expiresAt?: number;
  }
>();

export interface TestUser {
  email: string;
  password: string;
  tenantId?: string;
}

/** Default test user — must exist in the test database. */
export const TEST_USER: TestUser = {
  email: process.env.E2E_USER_EMAIL ?? 'admin@yufeed.eu',
  password: process.env.E2E_USER_PASSWORD ?? 'YufeedDev123',
  tenantId: process.env.E2E_USER_TENANT_ID ?? process.env.E2E_TENANT_ID,
};

async function login(
  page: Page,
  payload: { email: string; password: string; tenant_id?: string },
) {
  const response = await page.request.post(`${API_BASE}/api/auth/login`, {
    data: payload,
  });
  const body = await response.json().catch(async () => response.text());
  return { response, body };
}

function decodeJwtExpiryMs(token: string): number | undefined {
  const parts = token.split('.');
  if (parts.length < 2) return undefined;
  const payload = parts[1]?.replace(/-/g, '+').replace(/_/g, '/');
  if (!payload) return undefined;
  try {
    const decoded = JSON.parse(Buffer.from(payload, 'base64').toString('utf-8')) as {
      exp?: number;
    };
    if (typeof decoded.exp !== 'number') return undefined;
    return decoded.exp * 1000;
  } catch {
    return undefined;
  }
}

async function loginWithRetry(
  page: Page,
  payload: { email: string; password: string; tenant_id?: string },
  attempts = 6,
) {
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    const result = await login(page, payload);
    if (result.response.ok()) return result;
    if (result.response.status() !== 429 || attempt === attempts) return result;

    const retryAfter =
      typeof result.body === 'object' &&
      result.body &&
      'retry_after' in result.body &&
      typeof result.body.retry_after === 'number' &&
      result.body.retry_after > 0
        ? result.body.retry_after * 1000
        : 10_000 + attempt * 2_000;
    await page.waitForTimeout(retryAfter);
  }

  // Should never hit this due return paths above.
  return login(page, payload);
}

/**
 * Authenticate a test user and inject the JWT into the browser.
 * After calling this, the page can navigate to any protected route.
 */
export async function loginViaAPI(page: Page, user: TestUser = TEST_USER): Promise<void> {
  const cacheKey = `${user.email}::${user.tenantId ?? ''}`;
  let tokens = TOKEN_CACHE.get(cacheKey);
  const now = Date.now();
  const tokenBufferMs = 30_000;

  if (
    tokens?.expiresAt &&
    tokens.expiresAt - now <= tokenBufferMs
  ) {
    TOKEN_CACHE.delete(cacheKey);
    tokens = undefined;
  }

  if (!tokens) {
    const payload: { email: string; password: string; tenant_id?: string } = {
      email: user.email,
      password: user.password,
    };
    if (user.tenantId) {
      payload.tenant_id = user.tenantId;
    }

    const { response, body } = await loginWithRetry(page, payload);

    if (response.ok()) {
      tokens = {
        accessToken: body.access_token,
        refreshToken: body.refresh_token,
        tokenType: body.token_type,
        expiresAt: decodeJwtExpiryMs(body.access_token),
      };
    } else {
      const detail = body && typeof body === 'object' ? body.detail : null;
      const availableTenants =
        detail && typeof detail === 'object' ? detail.available_tenants : null;

      if (response.status() === 400 && Array.isArray(availableTenants) && availableTenants.length) {
        const selectedTenant =
          user.tenantId && availableTenants.includes(user.tenantId)
            ? user.tenantId
            : String(availableTenants[0]);
        const retry = await loginWithRetry(page, {
          ...payload,
          tenant_id: selectedTenant,
        });
        if (!retry.response.ok()) {
          throw new Error(
            `Login retry failed (${retry.response.status()}): ${JSON.stringify(retry.body)}`,
          );
        }
        tokens = {
          accessToken: retry.body.access_token,
          refreshToken: retry.body.refresh_token,
          tokenType: retry.body.token_type,
          expiresAt: decodeJwtExpiryMs(retry.body.access_token),
        };
      } else {
        throw new Error(`Login failed (${response.status()}): ${JSON.stringify(body)}`);
      }
    }

    TOKEN_CACHE.set(cacheKey, tokens);
  }

  // Inject tokens into localStorage (matching src/lib/auth.ts keys).
  await page.goto('/');
  await page.evaluate(
    ({ access, refresh, tokenType }) => {
      localStorage.setItem('access_token', access);
      if (refresh) localStorage.setItem('refresh_token', refresh);
      if (tokenType) localStorage.setItem('token_type', tokenType);
    },
    {
      access: tokens.accessToken,
      refresh: tokens.refreshToken,
      tokenType: tokens.tokenType ?? 'bearer',
    },
  );

  await page.goto(POST_LOGIN_URL, { waitUntil: 'load' });
  await page.waitForURL(/\/dashboard/, { timeout: 20_000 });
}

/**
 * Login via the UI login form (for the login flow test itself).
 */
export async function loginViaUI(page: Page, user: TestUser = TEST_USER): Promise<void> {
  await page.goto('/');
  await page.getByLabel(/work email|email/i).fill(user.email);
  await page.getByLabel(/password/i).fill(user.password);
  await page.getByRole('button', { name: /sign\s*in|log\s*in/i }).click();
}
