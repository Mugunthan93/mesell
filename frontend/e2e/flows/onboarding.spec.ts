/**
 * Flow: Phone OTP onboarding (qa-onboarding Wave C — OB-E2E-01..05).
 *
 * The new-user journey across the federation boundary, exercised with REAL fresh
 * OTP sign-ins (dev bypass 000000). These flows START LOGGED OUT, so they use the
 * `freshLoginTest` fixture (clears the per-IP OTP-send rate limit before each test)
 * rather than the worker-scoped authed-context fixture.
 *
 * Coverage:
 *   OB-E2E-01 happy             — login → OTP → onboarding → submit → /dashboard.
 *   OB-E2E-02 wrong-OTP error   — wrong code → error banner, stays on /otp-verify.
 *   OB-E2E-03 persist + resume  — submit PERSISTS → re-login lands on /dashboard
 *                                 (NOT /onboarding). The data-loss-bug (#399) guard.
 *   OB-E2E-04 resume incomplete — fresh user with no profile is routed to /onboarding.
 *   OB-E2E-05 skip-setup        — skip link → /dashboard (client-side, no persist).
 *
 * Selectors: getByTestId / page objects, all LIVE-VERIFIED (selector_registry.md).
 * Ports: from playwright.config.ts (never hardcoded). Auth: in-memory token + HttpOnly
 * cookie (Decision #14) — no token is injected into localStorage.
 *
 * Every test asserts a VISIBLE outcome (DOM element / URL / redirect).
 */
import { freshLoginTest as test, expect } from '../fixtures/auth';
import { AuthPage } from '../page-objects/auth.page';
import { OnboardingPage } from '../page-objects/onboarding.page';
import { DashboardPage } from '../page-objects/dashboard.page';

const DEV_OTP = process.env.MEESELL_E2E_OTP ?? '000000';

// Fresh-user phones — UNIQUE PER RUN. The fresh-user scenarios (happy/persist/resume/
// skip) assume a seller with NO persisted profile so the shell routes them to
// /onboarding. The dev DB is shared + persistent, so reusing a fixed phone across runs
// would leave a profile behind and the user would skip onboarding on the next run
// (flaky). A run-scoped suffix keeps each run's users genuinely fresh. The dev OTP
// bypass `000000` accepts any phone. Format stays valid /^[6-9]\d{9}$/ (the +91 is a
// display prefix). The persist+resume test reuses ITS phone within the test (the
// resume is the same returning user) — that is intentional.
const RUN = String(Date.now()).slice(-6); // 6 digits, unique per run
const PHONE_HAPPY = process.env.MEESELL_E2E_ONBOARDING_PHONE_10 ?? `9701${RUN}`;
const PHONE_RESUME = process.env.MEESELL_E2E_RESUME_PHONE_10 ?? `9702${RUN}`;
const PHONE_SKIP = process.env.MEESELL_E2E_SKIP_PHONE_10 ?? `9703${RUN}`;

test.describe('Onboarding — phone OTP journey', () => {
  // OB-E2E-01 (happy) + OB-E2E-03 (persist + resume) in one flow: the second login
  // is the regression guard that the submit PERSISTED the seller profile.
  test('OB-E2E-01/03: completes onboarding, persists, and re-login lands on the dashboard', async ({ page }) => {
    const auth = new AuthPage(page);
    const onboarding = new OnboardingPage(page);
    const dashboard = new DashboardPage(page);

    // ── First login (fresh user) → onboarding → submit → dashboard (OB-E2E-01) ──
    await auth.gotoLogin();
    await auth.requestOtp(PHONE_HAPPY);
    await auth.fillOtp(DEV_OTP);
    await auth.submitOtp();

    // A fresh seller (no profile) is routed to /onboarding.
    await page.waitForURL(/\/onboarding/);
    await expect(onboarding.submit).toBeVisible();

    // Fill the seller-profile form and submit → PATCH /seller-profile persists →
    // refreshUser() → /dashboard.
    await onboarding.fillValid();
    const patch = page.waitForResponse(
      (r) => /\/api\/v1\/.*seller-profile/.test(r.url()) && r.request().method() === 'PATCH',
    );
    await onboarding.submitForm();
    expect((await patch).status()).toBe(200); // persistence actually happened
    await page.waitForURL(/\/dashboard/);
    await expect(dashboard.heading).toBeVisible();

    // ── Re-login the SAME user → must land on /dashboard, NOT /onboarding (OB-E2E-03) ──
    // Because the profile persisted, /auth/me.onboarding_complete is now true, so the
    // shell routes a returning user past onboarding. This is the data-loss-bug guard.
    await page.context().clearCookies();
    await auth.gotoLogin();
    await auth.requestOtp(PHONE_HAPPY);
    await auth.fillOtp(DEV_OTP);
    await auth.submitOtp();

    await page.waitForURL(/\/dashboard/);
    expect(page.url()).not.toMatch(/\/onboarding/);
    await expect(dashboard.heading).toBeVisible();
  });

  // OB-E2E-02 (wrong-OTP error) + OB-E2E-04 (resume incomplete) share one login: a
  // wrong code on the otp-verify page surfaces the error banner without consuming a
  // second OTP send, then the correct code routes the fresh user to /onboarding.
  test('OB-E2E-02/04: a wrong OTP shows an error, then the verified fresh user resumes onboarding', async ({ page }) => {
    const auth = new AuthPage(page);
    const onboarding = new OnboardingPage(page);

    await auth.gotoLogin();
    await auth.requestOtp(PHONE_RESUME);

    // OB-E2E-02: a WRONG code → backend 401 → error banner visible, stays on /otp-verify.
    await auth.fillOtp('123456');
    await auth.submitOtp();
    await expect(auth.errorBanner).toBeVisible();
    await expect(auth.errorBanner).toContainText(/invalid|expired|try again/i);
    await expect(page).toHaveURL(/\/otp-verify/);

    // OB-E2E-04: the CORRECT code → a fresh user (no profile) is routed to /onboarding,
    // where the onboarding form (submit button) is the visible resume marker.
    await auth.fillOtp(DEV_OTP);
    await auth.submitOtp();
    await page.waitForURL(/\/onboarding/);
    await expect(onboarding.submit).toBeVisible();
    await expect(onboarding.field('Manufacturer Name')).toBeVisible();
  });

  // OB-E2E-05: the skip-setup path routes to the dashboard without persisting a profile.
  test('OB-E2E-05: skipping setup lands on the dashboard', async ({ page }) => {
    const auth = new AuthPage(page);
    const onboarding = new OnboardingPage(page);
    const dashboard = new DashboardPage(page);

    await auth.gotoLogin();
    await auth.requestOtp(PHONE_SKIP);
    await auth.fillOtp(DEV_OTP);
    await auth.submitOtp();

    await page.waitForURL(/\/onboarding/);
    await expect(onboarding.skipLink).toBeVisible();

    // Click "I'll set this up later" → routed to /dashboard (client-side, no persist).
    await onboarding.skip();
    await page.waitForURL(/\/dashboard/);
    await expect(dashboard.heading).toBeVisible();
  });
});
