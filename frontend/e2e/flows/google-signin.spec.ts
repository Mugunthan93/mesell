/**
 * Flow: Google Sign-In.
 *
 * Taxonomy (design §5.3): GIS button clickable → redirect → dashboard.
 *
 * Two tests:
 *   1. (GREEN) The Google Identity Services (GIS) control RENDERS on the login page:
 *      the `login-google-host` is visible and GIS has injected its button iframe into
 *      it. This is a real, observable render outcome (the "codify the render" ask).
 *   2. (FIXME) The actual Google sign-in. GIS renders its button inside a
 *      cross-origin iframe served by accounts.google.com and the click drives REAL
 *      Google OAuth — it cannot be driven headlessly (the dev origin is also not an
 *      allowed GIS origin: "The given origin is not allowed for the given client
 *      ID"). Driving it would require a Google test account + an allow-listed origin,
 *      or stubbing the GIS credential callback. Recorded in federation_quirks.md.
 *
 * The login page is public — no authentication needed.
 */
import { test, expect } from '@playwright/test';
import { ShellPage } from '../page-objects/shell.page';

test.describe('Google Sign-In', () => {
  test('the Google sign-in control renders on the login page', async ({ page }) => {
    new ShellPage(page); // shell host
    await page.goto('/login');

    // Visible outcome: the GIS host is visible and GIS injected its button iframe.
    const host = page.getByTestId('login-google-host');
    await expect(host).toBeVisible();
    await expect(host.locator('iframe')).toHaveCount(1, { timeout: 15_000 });
  });

  test.fixme('clicking the Google button signs in and lands on the dashboard', async ({ page }) => {
    // BLOCKED headlessly: GIS button is a cross-origin Google iframe driving real
    // OAuth; the dev origin is not an allowed GIS origin. Requires a Google test
    // identity + allow-listed origin, or a stubbed GIS credential callback.
    await page.goto('/login');
    const host = page.getByTestId('login-google-host');
    await host.locator('iframe').first().click();
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.getByTestId('dashboard-heading')).toBeVisible();
  });
});
