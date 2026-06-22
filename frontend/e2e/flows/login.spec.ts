/**
 * Flow: Pure OTP login → dashboard, ISOLATED from onboarding. (E2E-AUTH-01,
 * qa-auth-contract salvage lane.)
 *
 * Why this exists distinct from onboarding.spec.ts: develop covers the OTP journey
 * ONLY implicitly inside the onboarding flow. This file is the FOCUSED login
 * assertion — a valid phone-OTP exchange lands the seller on an authenticated,
 * protected surface, and (for a returning seller) lands DIRECTLY on /dashboard
 * rather than being bounced through /onboarding.
 *
 * Two complementary cases:
 *
 *   1. (raw login, fresh-user-aware) Drive the real /login → request OTP →
 *      otp-verify → dev bypass `000000` UI from a LOGGED-OUT start, and assert the
 *      authenticated surface. `loginViaOtp` (the develop login helper) handles the
 *      fresh-user onboarding bounce (a brand-new seller is routed via /onboarding,
 *      where the seller-profile form is filled + persisted, then routed to
 *      /dashboard). Either way the assertion is the LOGIN outcome: the dashboard
 *      heading is visible, the URL is /dashboard, and we are NOT on /login.
 *
 *   2. (isolated, returning user) Once a seller's profile is persisted, a fresh
 *      login must land DIRECTLY on /dashboard — never /onboarding. This is the
 *      pure "login ≠ onboarding" assertion the salvage analysis flagged as absent
 *      on develop. The first login (case 1's helper) persists the profile; this
 *      case re-logs-in the SAME identity and asserts the straight-to-dashboard path.
 *
 * Decision #14 / FE-D5: the access JWT is held IN MEMORY and the refresh token is an
 * HttpOnly cookie — NO token is injected into (or expected in) localStorage. This
 * file additionally asserts that NO auth token leaked into localStorage after login.
 *
 * Selectors come from selector_registry.md via the AuthPage / DashboardPage page
 * objects (all LIVE-VERIFIED). Ports come from playwright.config.ts (never hardcoded).
 *
 * Uses freshLoginTest (logged-out start; clears the per-IP OTP-send rate limit before
 * the test sends its OTP) — NOT the worker-scoped authed fixture, because the whole
 * point is to exercise the login UI itself.
 */
import { freshLoginTest as test, expect, loginViaOtp } from '../fixtures/auth';
import { AuthPage } from '../page-objects/auth.page';
import { DashboardPage } from '../page-objects/dashboard.page';

const DEV_OTP = process.env.MEESELL_E2E_OTP ?? '000000';

// A run-scoped, returning-user identity. The dev DB is shared + persistent, so this
// flow does its OWN first login (which persists a seller profile via loginViaOtp's
// onboarding handling) and THEN re-logs-in the same phone to prove the
// straight-to-dashboard returning-user path. A run-scoped suffix keeps each run's
// identity genuinely fresh on the first login. The dev OTP bypass `000000` accepts
// any phone; format stays valid /^[6-9]\d{9}$/ (the +91 is a display prefix).
const RUN = String(Date.now()).slice(-6);
const LOGIN_PHONE_10 = process.env.MEESELL_E2E_LOGIN_PHONE_10 ?? `9704${RUN}`;

test.describe('Pure OTP login (isolated from onboarding)', () => {
  test('a valid phone OTP exchange lands the seller on the authenticated dashboard, and re-login goes straight to the dashboard (not onboarding)', async ({
    page,
  }) => {
    const auth = new AuthPage(page);
    const dashboard = new DashboardPage(page);

    // ── Case 1: raw login from a logged-out start → authenticated dashboard ──
    // loginViaOtp drives the real /login → otp-verify UI and, for a fresh seller,
    // fills + PERSISTS the onboarding seller-profile before routing to /dashboard.
    await loginViaOtp(page, LOGIN_PHONE_10);

    // Asserted VISIBLE outcome: the authenticated dashboard heading is visible and
    // we are on /dashboard, NOT /login.
    await expect(dashboard.heading).toBeVisible();
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page).not.toHaveURL(/\/login/);

    // Decision #14 / FE-D5 guard: no auth token in localStorage (token lives in
    // memory; the refresh token is an HttpOnly cookie). Assert no auth-shaped key was
    // written client-side.
    const leakedAuthKeys = await page.evaluate(() => {
      const keys: string[] = [];
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        if (k && /token|auth|refresh|jwt|access/i.test(k)) keys.push(k);
      }
      return keys;
    });
    expect(leakedAuthKeys, 'no auth token should be persisted to localStorage (FE-D5)').toEqual([]);

    // ── Case 2 (isolated returning-user): re-login the SAME identity → /dashboard ──
    // The first login persisted the seller profile, so /auth/me.onboarding_complete
    // is now true → a returning seller must NOT be routed through /onboarding. This
    // is the pure "login is not onboarding" assertion.
    await page.context().clearCookies();
    await auth.gotoLogin();
    await auth.requestOtp(LOGIN_PHONE_10);
    await auth.fillOtp(DEV_OTP);
    await auth.submitOtp();

    // Asserted VISIBLE outcome: lands DIRECTLY on /dashboard, never /onboarding.
    await page.waitForURL(/\/dashboard/);
    expect(page.url(), 'a returning seller must skip onboarding').not.toMatch(/\/onboarding/);
    await expect(dashboard.heading).toBeVisible();
  });
});
