/**
 * Flow: Silent refresh across shell→remote navigation. (E2E-AUTH-03, QA Wave 2.)
 *
 * Taxonomy / WAVE_PLAN §4.3: the POSITIVE counterpart to the logout-guard sentinel
 * and the E2E face of the refresh-interceptor red (FE-AUTH-01/02). When the
 * in-memory access token is gone, the app must SILENTLY refresh from the HttpOnly
 * cookie and keep the seller authenticated across the federation boundary — NOT
 * bounce to /login.
 *
 * How the access token is forced to drop (no fixed dev TTL wait needed):
 *   The access JWT is held IN MEMORY only (Decision #14 / FE-D5) and CANNOT survive
 *   a fresh page load. The shell's APP_INITIALIZER bootstrap() refreshes from the
 *   refresh cookie on EVERY page load. So a brand-new page in the authed context
 *   starts with NO in-memory access token, and reaching a protected route at all
 *   PROVES a transparent /auth/refresh succeeded. We then cross shell→remote to
 *   prove the refreshed session survives the federation boundary (the singleton
 *   AuthService class — FED-1).
 *
 * Uses the worker-scoped authed-context fixture (`authedPage` is a fresh page in
 * the shared, already-authenticated context — exactly the "fresh page, no
 * in-memory token" condition). The single-use rotating refresh cookie stays valid
 * within that one context. Selectors from the registry via page objects; ports
 * from config.
 *
 * Asserted VISIBLE outcomes: the protected dashboard heading is visible on a fresh
 * page (silent refresh happened); after crossing into a remote the protected remote
 * DOM is visible; the URL is NEVER /login.
 */
import { authedTest as test, expect } from '../fixtures/auth';
import { DashboardPage } from '../page-objects/dashboard.page';
import { CatalogPage } from '../page-objects/catalog.page';
import { ShellPage } from '../page-objects/shell.page';

test.describe('Silent refresh across federation nav', () => {
  test('a fresh page silently refreshes and the session survives shell→remote nav (no /login bounce)', async ({ authedPage }) => {
    const dashboard = new DashboardPage(authedPage);
    const catalog = new CatalogPage(authedPage);
    const shell = new ShellPage(authedPage);

    // Fresh page in the authed context → NO in-memory access token. Reaching the
    // protected dashboard heading proves bootstrap() silently refreshed from the
    // cookie (a transparent POST /auth/refresh → 200). If refresh had failed, the
    // authGuard would have redirected to /login.
    await dashboard.goto();
    await expect(dashboard.heading).toBeVisible();
    await expect(authedPage).not.toHaveURL(/\/login/);

    // Cross the federation boundary into the catalog remote. The refreshed,
    // in-memory access token must be shared via the @mesell/core AuthService
    // singleton (FED-1) so the remote's authGuard sees an authenticated user — the
    // protected smart-picker renders rather than a /login redirect.
    await catalog.gotoNew();
    await expect(catalog.categoryDescription).toBeVisible();
    await expect(authedPage).not.toHaveURL(/\/login/);

    // Navigate back shell-side; the session is still alive (another silent refresh
    // is fine — it stays transparent and we never see /login).
    await dashboard.goto();
    await expect(dashboard.heading).toBeVisible();
    await expect(authedPage).not.toHaveURL(/\/login/);

    // And it is NOT a degraded remote-load fallback masquerading as "authed".
    await expect(shell.remoteFailureFallback).toHaveCount(0);
  });
});
