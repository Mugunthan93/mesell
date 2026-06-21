/**
 * Flow: Phone OTP onboarding.
 *
 * Taxonomy (design §5.3): OTP input → verify → plan screen → dashboard heading visible.
 *
 * STUB — fleshed out by the QA wave. Marked test.fixme so a bootstrap CI run does
 * not fail on unverified selectors. The exploration phase verifies the login DOM
 * + plan-screen DOM, records selectors in selector_registry.md, then this body is
 * completed and the fixme removed.
 *
 * NOTE: this flow does NOT reuse storageState — it exercises a FRESH OTP sign-in
 * from a clean context, so it overrides the project storageState to an empty one.
 */
import { test, expect } from '@playwright/test';
import { ShellPage } from '../page-objects/shell.page';
import { DashboardPage } from '../page-objects/dashboard.page';

// Fresh, unauthenticated context — onboarding is the one flow that must start logged out.
test.use({ storageState: { cookies: [], origins: [] } });

const TEST_PHONE = process.env.MEESELL_E2E_PHONE ?? '+919999900000';
const DEV_OTP = process.env.MEESELL_E2E_OTP ?? '000000';

test.describe('Onboarding — phone OTP', () => {
  test.fixme('completes OTP sign-in and lands on the dashboard', async ({ page }) => {
    const shell = new ShellPage(page);
    const dashboard = new DashboardPage(page);

    await shell.gotoRoute('login');

    // OTP input → request → verify with dev bypass.
    await page.getByTestId('login-phone-input').fill(TEST_PHONE);
    await page.getByTestId('login-request-otp').click();
    await page.getByTestId('otp-input').fill(DEV_OTP);
    await page.getByTestId('otp-verify-submit').click();

    // Asserted outcome: plan screen is shown to a new seller, then the dashboard heading is visible.
    await expect(page.getByTestId('plan-screen')).toBeVisible();
    await page.getByTestId('plan-continue').click();
    await expect(dashboard.heading).toBeVisible();
  });
});
