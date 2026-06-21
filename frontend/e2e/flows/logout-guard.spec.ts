/**
 * Flow: Logout + back-nav guard.
 *
 * Taxonomy (design §5.3): Logout → browser back → redirected to /login, protected
 * page not rendered.
 *
 * STUB — fleshed out by the QA wave. Pre-authenticated via storageState. This
 * flow protects against the federation auth-singleton regression class
 * (shell→remote navigation losing the session) — see federation_quirks.md. The
 * exploration phase confirms the logout control and the post-back redirect.
 */
import { test, expect } from '@playwright/test';
import { ShellPage } from '../page-objects/shell.page';
import { DashboardPage } from '../page-objects/dashboard.page';

test.describe('Logout + back-nav guard', () => {
  test.fixme('after logout, browser back does not render a protected page (redirects to /login)', async ({ page }) => {
    const shell = new ShellPage(page);
    const dashboard = new DashboardPage(page);

    // Start on a protected page.
    await dashboard.goto();
    await expect(dashboard.heading).toBeVisible();

    // Log out.
    await shell.logout();
    await expect(page).toHaveURL(/\/login$/);

    // Browser back must NOT re-render the protected page — the authGuard redirects to /login.
    await page.goBack();
    await expect(page).toHaveURL(/\/login$/);
    await expect(dashboard.heading).toHaveCount(0);
  });
});
