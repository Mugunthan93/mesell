/**
 * Flow: Logout + back-nav guard. (The FED-1 / logout-fix regression sentinel.)
 *
 * Taxonomy (design §5.3): Logout → browser back → redirected to /login, protected
 * page not rendered.
 *
 * This flow also exercises shell→remote navigation (dashboard → catalog remote)
 * BEFORE logout, so it doubles as the auth-singleton sentinel: the session must
 * survive crossing the federation boundary, and logout must then fully clear it.
 *
 * It uses its OWN fresh OTP login (NOT the shared worker fixture) because logging
 * out tears the session down — doing that in the shared context would break the
 * other authed flows in the same worker.
 *
 * Asserted VISIBLE outcomes: logout lands on /login; browser-back stays on /login
 * and does NOT re-render the protected dashboard heading.
 */
import { test, expect } from '@playwright/test';
import { loginViaOtp } from '../fixtures/auth';
import { ShellPage } from '../page-objects/shell.page';
import { DashboardPage } from '../page-objects/dashboard.page';
import { CatalogPage } from '../page-objects/catalog.page';

// Dedicated phone so this flow's fresh login is independent.
const LOGOUT_PHONE_10 = process.env.MEESELL_E2E_LOGOUT_PHONE_10 ?? '9700000789';

test.describe('Logout + back-nav guard', () => {
  test('after logout, browser-back does not render a protected page (stays on /login)', async ({ page }) => {
    const shell = new ShellPage(page);
    const dashboard = new DashboardPage(page);
    const catalog = new CatalogPage(page);

    // Fresh login → dashboard.
    await loginViaOtp(page, LOGOUT_PHONE_10);
    await expect(dashboard.heading).toBeVisible();

    // Cross the federation boundary (shell → catalog remote) and back — the session
    // must survive (auth-singleton sentinel). The smart picker is a protected remote.
    await catalog.gotoNew();
    await expect(catalog.categoryDescription).toBeVisible();
    await dashboard.goto();
    await expect(dashboard.heading).toBeVisible();

    // Log out via the topbar button (revokes the cookie + navigates to /login).
    await shell.logout();
    await expect(page).toHaveURL(/\/login(\?.*)?$/);

    // Browser back must NOT re-render the protected dashboard — the authGuard
    // redirects back to /login (the logout fix: session fully cleared).
    await page.goBack();
    await expect(page).toHaveURL(/\/login(\?.*)?$/);
    await expect(dashboard.heading).toHaveCount(0);
  });
});
