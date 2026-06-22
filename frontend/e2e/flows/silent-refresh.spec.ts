/**
 * Flow: Silent refresh across shell→remote federation nav. (E2E-AUTH-03,
 * qa-auth-contract salvage lane — the HIGHEST-VALUE salvage.)
 *
 * This is the E2E face of the production refresh-storm / cascade-logout bug and the
 * POSITIVE counterpart to the logout-guard sentinel (logout-guard.spec.ts guards the
 * inverse: a logged-out user STAYS out). When the in-memory access token is gone, the
 * app must SILENTLY refresh from the HttpOnly cookie and keep the seller
 * authenticated across the federation boundary — it must NOT bounce to /login.
 *
 * How the access token is forced to drop WITHOUT waiting on a dev TTL:
 *   The access JWT is held IN MEMORY only (Decision #14 / FE-D5) and CANNOT survive a
 *   fresh page load. The shell's APP_INITIALIZER bootstrap() refreshes from the
 *   refresh cookie on EVERY page load. So a brand-new page in the authed context
 *   starts with NO in-memory access token — reaching a protected route at all PROVES
 *   a transparent POST /api/v1/auth/refresh → 200 happened. We then cross
 *   shell→remote to prove the refreshed session survives the federation boundary
 *   (the shared @mesell/core AuthService singleton — FED-1).
 *
 * Uses the worker-scoped authed-context fixture: `authedPage` is a FRESH page in the
 * shared, already-authenticated context — exactly the "fresh page, no in-memory
 * access token" condition. The single-use rotating refresh cookie stays valid within
 * that one context (see federation_quirks.md: single-use rotation breaks shared
 * storageState across separate contexts, so a shared context is the rotation-safe
 * pattern).
 *
 * Asserted VISIBLE outcomes:
 *   - a transparent POST /api/v1/auth/refresh returns 200 on the fresh page,
 *   - the protected dashboard heading is visible,
 *   - after crossing into the catalog remote the protected remote DOM is visible,
 *   - the URL is NEVER /login, and it is NOT the degraded remote-failure fallback.
 *
 * Selectors from selector_registry.md via page objects; ports from playwright.config.ts.
 */
import { authedTest as test, expect } from '../fixtures/auth';
import { DashboardPage } from '../page-objects/dashboard.page';
import { CatalogPage } from '../page-objects/catalog.page';
import { ShellPage } from '../page-objects/shell.page';

test.describe('Silent refresh across federation nav', () => {
  test('a fresh page silently refreshes (POST /auth/refresh 200) and the session survives shell→remote nav with no /login bounce', async ({
    authedPage,
  }) => {
    const dashboard = new DashboardPage(authedPage);
    const catalog = new CatalogPage(authedPage);
    const shell = new ShellPage(authedPage);

    // Start watching for the transparent refresh BEFORE the navigation that triggers
    // bootstrap(). The fresh page has no in-memory access token, so bootstrap() MUST
    // refresh from the cookie. We assert that POST /auth/refresh returns 200.
    const refresh = authedPage.waitForResponse(
      (r) =>
        /\/api\/v1\/auth\/refresh\b/.test(r.url()) && r.request().method() === 'POST',
      { timeout: 30_000 },
    );

    await dashboard.goto();

    // Silent-refresh outcome (the explicit network assertion the case requires): the
    // refresh succeeded transparently — 200, not a 401 → /login cascade.
    const refreshResp = await refresh;
    expect(refreshResp.status(), 'bootstrap() must silently refresh from the cookie').toBe(200);

    // VISIBLE outcome: the protected dashboard heading is visible and we are NOT on
    // /login. If refresh had failed, the authGuard would have redirected to /login.
    await expect(dashboard.heading).toBeVisible();
    await expect(authedPage).not.toHaveURL(/\/login/);

    // Cross the federation boundary into the catalog remote. The refreshed in-memory
    // access token must be shared via the @mesell/core AuthService singleton (FED-1)
    // so the remote's authGuard sees an authenticated user — the protected
    // smart-picker renders rather than a /login redirect.
    await catalog.gotoNew();
    await expect(catalog.categoryDescription).toBeVisible();
    await expect(authedPage).not.toHaveURL(/\/login/);

    // Navigate back shell-side; the session is still alive (another silent refresh is
    // fine — it stays transparent and we never see /login).
    await dashboard.goto();
    await expect(dashboard.heading).toBeVisible();
    await expect(authedPage).not.toHaveURL(/\/login/);

    // And the protected surface is NOT a degraded remote-load fallback masquerading
    // as "authed".
    await expect(shell.remoteFailureFallback).toHaveCount(0);
  });
});
