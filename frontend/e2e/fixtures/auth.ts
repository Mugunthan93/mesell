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
import {
  test as base,
  expect,
  type Page,
  type BrowserContext,
  type Route,
} from '@playwright/test';
import { STORAGE_STATE, REMOTE_PORTS } from '../playwright.config';
import { resetRateLimits } from './rate-limit';

/**
 * applyManifestPortFix — OPT-IN dev-stack repair (env: MEESELL_FIX_MANIFEST_PORTS=1).
 *
 * WHY (federation_quirks.md — manifest port-MAPPING mismatch): a dev stack brought
 * up with the remotes bound to ALPHABETICAL ports (mfe-auth :4201, mfe-billing :4202,
 * …, mfe-pricing :4207) while the SERVED federation.manifest.json still maps remotes
 * in DECLARATION order (mfe-auth → :4206, which is actually serving mfe-onboarding)
 * makes the shell load the WRONG remote: navigating to /login fetches `./LoginComponent`
 * from the remote on :4206 → "Unknown exposed module ./LoginComponent in remote
 * mfe-auth" → the D12 remote-failure fallback renders instead of the login form.
 * VERIFIED LIVE this session against slot-0.
 *
 * This shim is the TEST-SIDE repair of that MISCONFIGURED DEV STACK (the real fix is
 * infra's: bring the stack up with a manifest whose ports match the running remotes).
 * It is NOT a hardcoded port in a spec: it rewrites the served manifest using the
 * canonical REMOTE_PORTS from playwright.config.ts (env-overridable). It is OFF by
 * default, so a correctly-wired stack is untouched. Apply it to a CONTEXT (so every
 * page inherits the route) before the first navigation.
 */
export async function applyManifestPortFix(target: BrowserContext | Page): Promise<void> {
  if (process.env.MEESELL_FIX_MANIFEST_PORTS !== '1') return;
  const host = process.env.MEESELL_REMOTE_HOST ?? 'localhost';
  const fixed: Record<string, string> = {};
  for (const [name, port] of Object.entries(REMOTE_PORTS)) {
    fixed[name] = `http://${host}:${port}/remoteEntry.json`;
  }
  await target.route('**/federation.manifest.json', (route: Route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(fixed),
    }),
  );
}

/** Dedicated E2E test identity. 10-digit only (the +91 is a display prefix the
 *  LoginComponent prepends; the validator is /^[6-9]\d{9}$/). Override via env. */
export const TEST_PHONE_10 = process.env.MEESELL_E2E_PHONE_10 ?? '9700000123';
export const DEV_OTP = process.env.MEESELL_E2E_OTP ?? '000000';

/**
 * Fill the seller-profile onboarding form with valid data and submit.
 *
 * Post the qa-onboarding persist-fix (#399) the form is the manufacturer/packer/
 * country set (NOT the old businessName/city/gst). The fields are `mee-input`
 * wrappers with NO testid — they render a real `<label [for]>` → `<input>`, so they
 * are driven with `getByLabel` (LIVE-VERIFIED 2026-06-22, see selector_registry.md).
 * Country of Origin defaults to "India" (pre-valid) and is left untouched.
 *
 * Submitting now PERSISTS via PATCH /seller-profile → refreshUser() → /dashboard.
 */
export async function fillOnboarding(page: Page): Promise<void> {
  await page.getByTestId('onboarding-submit').waitFor({ state: 'visible' });
  await page.getByLabel('Manufacturer Name').fill('E2E QA Manufacturing');
  await page.getByLabel('Manufacturer Address').fill('12 Industrial Estate, Tirupur');
  await page.getByLabel('Manufacturer Pincode').fill('641604');
  await page.getByLabel('Packer Name').fill('E2E QA Packers');
  await page.getByLabel('Packer Address').fill('12 Industrial Estate, Tirupur');
  await page.getByLabel('Packer Pincode').fill('641604');
  // Country of Origin pre-filled "India" — leave it.
  await page.getByTestId('onboarding-submit').locator('button').click();
}

/**
 * Drive the real phone-OTP login UI to an authenticated dashboard.
 *
 * login → request OTP → otp-verify → (a fresh user lands on /onboarding: fill the
 * seller-profile form + submit, which persists then routes to /dashboard) → assert
 * the dashboard heading. Returns once the dashboard heading is visible.
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
    await fillOnboarding(page);
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
      // Repair the dev-stack manifest port mismatch (no-op unless opted in).
      await applyManifestPortFix(context);
      const page = await context.newPage();
      let seeded = false;
      if (haveSeed) {
        // Try to activate the seeded session: navigate to a protected route;
        // bootstrap() refreshes from the seed cookie and rotates it within this
        // context. The seed cookie is SINGLE-USE with rotation, so it can already be
        // dead (consumed/rotated before this worker ran, or expired) — in which case
        // bootstrap()'s refresh 401s and the app bounces to /login. If so, fall
        // through to a fresh OTP login rather than failing the whole worker.
        await page.goto('/dashboard');
        seeded = await page
          .getByTestId('dashboard-heading')
          .isVisible()
          .catch(() => false);
      }
      if (!seeded) {
        // No seed, or the seed cookie was dead → log in fresh into THIS shared
        // context (clears any /login state first). Clear the OTP rate limit so this
        // one worker login is not 429'd by accumulated sends (env reset, harness-side).
        await resetRateLimits();
        await context.clearCookies();
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

/**
 * freshLoginTest — for the flows that must start LOGGED OUT and drive a REAL fresh
 * OTP sign-in (onboarding happy / persist+resume / resume-incomplete / skip / the
 * logout-guard sentinel). Each such test consumes the per-IP OTP-send budget
 * (3/3600s), so this fixture performs the dev-env rate-limit reset BEFORE the test
 * sends its OTP, via an AUTO fixture (guaranteed to run for every test using this
 * `test` object — more reliable than a module-level beforeEach hook declared in an
 * imported helper). It clears the Valkey `meesell:rl:*` keys; the reset lives here in
 * the HARNESS (a fixture), never in a flow spec body, and is a no-op when no dev
 * Valkey/redis-cli is reachable. The reset runs serially (--workers=1), so it cannot
 * race a concurrent send.
 */
type RlResetFixture = { _rlReset: void; _manifestFix: void };
export const freshLoginTest = base.extend<RlResetFixture>({
  _rlReset: [
    async ({}, use) => {
      await resetRateLimits();
      await use();
    },
    { auto: true },
  ],
  // Repair the dev-stack manifest port mismatch on the test's page context BEFORE the
  // test navigates (no-op unless MEESELL_FIX_MANIFEST_PORTS=1). Auto so it always runs.
  _manifestFix: [
    async ({ page }, use) => {
      await applyManifestPortFix(page.context());
      await use();
    },
    { auto: true },
  ],
});

export { expect };
