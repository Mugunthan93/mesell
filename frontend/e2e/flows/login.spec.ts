/**
 * Flow: Pure OTP login → dashboard. (E2E-AUTH-01, QA Wave 2.)
 *
 * Taxonomy / WAVE_PLAN §4.3: a FOCUSED login assertion distinct from the
 * onboarding flow — phone (10-digit) → request OTP → fill the dev bypass `000000`
 * → verify → assert the eventual AUTHED surface (the dashboard heading).
 *
 * A fresh OTP user is routed via /onboarding first (me.onboarding_complete=false,
 * and the onboarding submit is a client-side mock that routes to /dashboard — see
 * selector_registry.md), so this flow handles BOTH the onboarding-first and the
 * straight-to-dashboard paths and asserts the dashboard heading either way. The
 * point of this case (vs onboarding.spec.ts) is the LOGIN assertion: a valid OTP
 * exchange lands the seller on an authenticated, protected surface.
 *
 * It uses its OWN fresh OTP login (the shared worker fixture is for already-authed
 * flows) — one OTP send, under the 3/3600s-per-IP budget. Selectors come from the
 * registry via the LoginPage / DashboardPage page objects; ports from config.
 *
 * Asserted VISIBLE outcome: the dashboard heading is visible and the URL is the
 * authenticated /dashboard (NOT /login).
 */
import { test, expect } from '@playwright/test';
import { LoginPage } from '../page-objects/login.page';
import { DashboardPage } from '../page-objects/dashboard.page';

// Dedicated phone so this flow's OTP send is independent of the other identities.
const LOGIN_PHONE_10 = process.env.MEESELL_E2E_LOGIN_PHONE_10 ?? '9700000234';
const DEV_OTP = process.env.MEESELL_E2E_OTP ?? '000000';

test.describe('Pure OTP login', () => {
  test('a valid phone OTP exchange lands the seller on the authenticated dashboard', async ({ page }) => {
    const login = new LoginPage(page);
    const dashboard = new DashboardPage(page);

    await login.goto();

    // Phone (10-digit only — the +91 is a display prefix the component prepends).
    await login.phoneInput.waitFor({ state: 'visible' });
    await login.phoneInput.fill(LOGIN_PHONE_10);
    await login.requestOtpButton.click();

    // OTP verify with the dev bypass code (field is `otp`, 6 cells).
    await page.waitForURL(/\/otp-verify/);
    await login.otpCells.first().waitFor({ state: 'visible' });
    const n = await login.otpCells.count();
    for (let i = 0; i < n; i++) {
      await login.otpCells.nth(i).fill(DEV_OTP[i] ?? '0');
    }
    await login.verifyButton.click();

    // A fresh seller routes via /onboarding (mock submit → /dashboard); a returning
    // seller goes straight to /dashboard. Handle both, then assert the authed surface.
    await page.waitForURL(/\/(onboarding|dashboard)/);
    if (/\/onboarding/.test(page.url())) {
      await page.getByTestId('onboarding-business-name').fill('E2E QA Shop');
      await page.getByTestId('onboarding-submit').locator('button').click();
    }

    // Asserted outcome: the authenticated dashboard heading is visible and we are
    // NOT on /login.
    await page.waitForURL(/\/dashboard/);
    await expect(dashboard.heading).toBeVisible();
    await expect(page).not.toHaveURL(/\/login/);
  });
});
