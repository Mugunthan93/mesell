/**
 * Flow: Phone OTP onboarding.
 *
 * Taxonomy (design §5.3): OTP input → verify → onboarding → dashboard heading visible.
 *
 * This is the ONE flow that must start logged OUT and exercise a FRESH OTP sign-in
 * (it does not use the worker-scoped authed fixture). A fresh seller lands on
 * /onboarding after verifying (me.onboarding_complete=false), fills the business
 * name, and is routed to /dashboard.
 *
 * Asserted VISIBLE outcomes: the onboarding form, then the dashboard heading.
 */
import { test, expect } from '@playwright/test';
import { ShellPage } from '../page-objects/shell.page';
import { DashboardPage } from '../page-objects/dashboard.page';

// Dedicated phone for this flow (distinct from the fixture/setup identities so its
// own OTP send is independent). 10-digit only — the +91 is a display prefix.
const ONBOARDING_PHONE_10 = process.env.MEESELL_E2E_ONBOARDING_PHONE_10 ?? '9700000456';
const DEV_OTP = process.env.MEESELL_E2E_OTP ?? '000000';

test.describe('Onboarding — phone OTP', () => {
  test('completes OTP sign-in, fills onboarding, and lands on the dashboard', async ({ page }) => {
    const shell = new ShellPage(page);
    const dashboard = new DashboardPage(page);

    await shell.gotoRoute('login');

    // Phone (mee-input → testid is the inner <input>; fill directly) → request OTP
    // (mee-button → click the inner <button>).
    await page.getByTestId('login-phone-input').waitFor({ state: 'visible' });
    await page.getByTestId('login-phone-input').fill(ONBOARDING_PHONE_10);
    await page.getByTestId('login-request-otp').locator('button').click();

    // OTP verify (mee-otp-input → 6 inner cells).
    await page.waitForURL(/\/otp-verify/);
    const cells = page.getByTestId('otp-input').locator('input');
    await cells.first().waitFor({ state: 'visible' });
    const n = await cells.count();
    for (let i = 0; i < n; i++) {
      await cells.nth(i).fill(DEV_OTP[i] ?? '0');
    }
    await page.getByTestId('otp-verify-submit').locator('button').click();

    // A fresh seller is routed to /onboarding — assert the onboarding form is visible.
    await page.waitForURL(/\/onboarding/);
    await expect(page.getByTestId('onboarding-business-name')).toBeVisible();

    // Fill the business name and submit → routed to /dashboard.
    await page.getByTestId('onboarding-business-name').fill('E2E QA Shop');
    await page.getByTestId('onboarding-submit').locator('button').click();

    // Asserted outcome: the dashboard heading is visible.
    await page.waitForURL(/\/dashboard/);
    await expect(dashboard.heading).toBeVisible();
  });
});
