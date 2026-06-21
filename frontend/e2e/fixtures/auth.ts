/**
 * auth.ts — the authentication helper + worker-scoped authenticated-context fixture.
 *
 * WHY a worker-scoped shared context instead of plain `storageState` reuse:
 *   The MeeSell refresh token is SINGLE-USE with server-side rotation (Decision
 *   #14 / FE-D5 + the iam Lua rotation): every POST /auth/refresh DELetes the old
 *   Valkey allowlist entry and SETs a new one. The shell's APP_INITIALIZER
 *   bootstrap() ALWAYS refreshes on every page load (the in-memory access token
 *   cannot survive a fresh page). So if N flows reuse ONE saved storageState.json,
 *   only the FIRST flow's first navigation succeeds (refresh→200); every later
 *   flow reuses the ALREADY-ROTATED cookie and gets refresh→401→/login.
 *   (Verified live in QA Wave 1 — see federation_quirks.md.)
 *
 *   The robust pattern for single-use rotation: log in ONCE per worker into a
 *   SHARED browser context, and give each test a fresh PAGE in that SAME context.
 *   The rotating cookie stays valid within the one context. With --workers=1
 *   (required to bound RAM on the dev box) this is exactly ONE OTP login for the
 *   whole authed suite — which also stays under the OTP-send rate limit
 *   (3/3600s per IP).
 *
 * Selectors come from selector_registry.md (live-verified). Ports come from
 * playwright.config.ts (never hardcoded).
 */
import { existsSync } from 'node:fs';
import { test as base, expect, type Page, type BrowserContext } from '@playwright/test';
import { STORAGE_STATE } from '../playwright.config';

/** Dedicated E2E test identity. 10-digit only (the +91 is a display prefix the
 *  LoginComponent prepends; the validator is /^[6-9]\d{9}$/). Override via env. */
export const TEST_PHONE_10 = process.env.MEESELL_E2E_PHONE_10 ?? '9700000123';
export const DEV_OTP = process.env.MEESELL_E2E_OTP ?? '000000';

/**
 * Drive the real phone-OTP login UI to an authenticated dashboard.
 *
 * login → request OTP → otp-verify → (a fresh user lands on /onboarding: fill the
 * business name + submit, which client-side routes to /dashboard) → assert the
 * dashboard heading. Returns once the dashboard heading is visible.
 *
 * This is the single source of the login sequence — both the onboarding flow and
 * the worker-scoped authed fixture call it.
 */
export async function loginViaOtp(page: Page, phone10: string = TEST_PHONE_10): Promise<void> {
  await page.goto('/login');

  // mee-input → testid is ON the inner <input> → fill directly.
  await page.getByTestId('login-phone-input').waitFor({ state: 'visible' });
  await page.getByTestId('login-phone-input').fill(phone10);

  // mee-button → testid is on the <p-button> host; click the inner <button>.
  await page.getByTestId('login-request-otp').locator('button').click();

  await page.waitForURL(/\/otp-verify/);

  // mee-otp-input → testid on the <p-inputotp> wrapper; 6 inner cells.
  const cells = page.getByTestId('otp-input').locator('input');
  await cells.first().waitFor({ state: 'visible' });
  const n = await cells.count();
  for (let i = 0; i < n; i++) {
    await cells.nth(i).fill(DEV_OTP[i] ?? '0');
  }
  await page.getByTestId('otp-verify-submit').locator('button').click();

  // A fresh OTP user is routed to /onboarding (me.onboarding_complete=false);
  // a returning user goes straight to /dashboard.
  await page.waitForURL(/\/(onboarding|dashboard)/);
  if (/\/onboarding/.test(page.url())) {
    await page.getByTestId('onboarding-business-name').fill('E2E QA Shop');
    await page.getByTestId('onboarding-submit').locator('button').click();
    await page.waitForURL(/\/dashboard/);
  }

  await expect(page.getByTestId('dashboard-heading')).toBeVisible();
}

/**
 * authedContext (worker-scoped) — a BrowserContext logged in exactly once per worker.
 * authedPage (test-scoped)       — a fresh page in that shared context per test.
 */
type AuthWorkerFixtures = {
  authedContext: BrowserContext;
};
type AuthTestFixtures = {
  authedPage: Page;
};

/**
 * authedTest — the test object the authenticated flows import. Defines both the
 * worker-scoped shared authed context and the per-test fresh page in ONE extend so
 * the fixture types compose cleanly.
 */
export const authedTest = base.extend<AuthTestFixtures, AuthWorkerFixtures>({
  // Worker-scoped: created once per worker and authenticated ONCE, then reused by
  // every test in that worker. The shared context keeps the rotating refresh cookie
  // valid (each navigation refreshes + rotates within this one context).
  //
  // It SEEDS from the storageState.json the `setup` project produced (the cookie
  // saved right after login, before any rotation) — so this costs ZERO extra OTP
  // sends (important: OTP send is rate-limited 3/3600s per IP). The first
  // navigation here consumes + rotates that cookie within this context. If the
  // storageState is missing (e.g. running a single flow without the setup project),
  // it falls back to a fresh OTP login.
  authedContext: [
    async ({ browser }, use) => {
      const haveSeed = existsSync(STORAGE_STATE);
      const context = await browser.newContext(
        haveSeed ? { storageState: STORAGE_STATE } : undefined,
      );
      const page = await context.newPage();
      if (haveSeed) {
        // Activate the seeded session: navigate to a protected route; bootstrap()
        // refreshes from the seed cookie and rotates it within this context.
        await page.goto('/dashboard');
        await expect(page.getByTestId('dashboard-heading')).toBeVisible();
      } else {
        await loginViaOtp(page);
      }
      await page.close();
      await use(context);
      await context.close();
    },
    { scope: 'worker' },
  ],

  // Per-test fresh page in the shared authed context.
  authedPage: async ({ authedContext }, use) => {
    const page = await authedContext.newPage();
    await use(page);
    await page.close();
  },
});

export { expect };
