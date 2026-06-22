/**
 * Flow: Google Sign-In.
 *
 * Taxonomy (design §5.3): GIS button clickable → redirect → dashboard.
 *
 * Three tests:
 *   1. (GREEN — E2E-AUTH-05, KEEP) The Google Identity Services (GIS) control
 *      RENDERS on the login page: the `login-google-host` is visible and the real GIS
 *      library injects its button iframe into it. A real, observable render outcome.
 *   2. (GREEN — E2E-AUTH-06, un-fixme'd by the qa-auth-contract salvage) The GIS-STUB
 *      click drives the REAL app pipeline: injecting a fake `window.google` (which
 *      sidesteps the cross-origin Google OAuth iframe) lets a button click invoke the
 *      captured credential callback, which makes the app fire a REAL
 *      POST /api/v1/auth/google/verify. We assert that request FIRES and that the
 *      route is MOUNTED (response != 404) — proving the GIS →
 *      LoginComponent.onGoogleCredential → AuthApiService.googleVerify wiring
 *      end-to-end without a real Google token.
 *   3. (FIXME — E2E-AUTH-06 success path, BLOCKED) The full success path (stubbed
 *      credential → dashboard) is blocked: the backend google adapter verifies the
 *      credential against Google's REAL published JWKs and there is NO dev/test
 *      google-verify seam (no DEV_GOOGLE_BYPASS analogue of DEV_OTP_BYPASS_CODE), so
 *      a fake credential is rejected with 401 and the dashboard is unreachable through
 *      the UI. VERIFIED LIVE this session (slot-0 :4200 → backend :8000): POST
 *      /api/v1/auth/google/verify with a fake credential → 401 (route mounted,
 *      flag-ON — NOT a 404). Un-fixme requires a backend test-google-adapter seam.
 *      Recorded in federation_quirks.md (owner: auth/ai-builder).
 *
 * The login page is public — no authentication needed. Selectors come from
 * selector_registry.md via the AuthPage page object (GIS host + stub button);
 * ports come from playwright.config.ts (never hardcoded).
 */
import { test, expect } from '@playwright/test';
import { AuthPage } from '../page-objects/auth.page';
import { applyManifestPortFix } from '../fixtures/auth';

test.describe('Google Sign-In', () => {
  // Repair the dev-stack manifest port mismatch before each test navigates (no-op
  // unless MEESELL_FIX_MANIFEST_PORTS=1 — see federation_quirks.md).
  test.beforeEach(async ({ page }) => {
    await applyManifestPortFix(page.context());
  });

  test('the Google sign-in control renders on the login page', async ({ page }) => {
    const auth = new AuthPage(page);
    await auth.gotoLogin();

    // Visible outcome: the GIS host is visible and GIS injected its button iframe.
    await expect(auth.googleHost).toBeVisible();
    await expect(auth.googleHost.locator('iframe')).toHaveCount(1, { timeout: 15_000 });
  });

  test('a stubbed GIS credential makes the app fire a real POST /auth/google/verify', async ({
    page,
  }) => {
    const auth = new AuthPage(page);

    // Inject the fake window.google BEFORE the app boots so the real
    // GoogleIdentityService.initialize() captures the LoginComponent callback and
    // renderButton() renders a clickable stub button into the host.
    await auth.installGisStub();
    await auth.gotoLogin();

    // VISIBLE outcome (the wiring proof): the host renders and our stub button lands
    // inside it — i.e. GoogleIdentityService load()/initialize()/renderButton() all
    // ran against the stub (the real wiring), not the cross-origin Google iframe.
    await expect(auth.googleHost).toBeVisible();
    await expect(auth.gisStubButton).toBeVisible();

    // Clicking invokes the captured credential callback → LoginComponent
    // .onGoogleCredential() → AuthApiService.googleVerify() → POST. Assert the REAL
    // request fires (the observable wiring outcome) and reaches the flag-ON route.
    const verifyReq = page.waitForRequest(
      (r) => r.url().includes('/auth/google/verify') && r.method() === 'POST',
      { timeout: 15_000 },
    );
    await auth.gisStubButton.click();
    const req = await verifyReq;

    // The route is mounted (flag-ON): the request resolves to a real response, not a
    // 404 route-absent. A fake credential is rejected (401) — that is the EXPECTED
    // outcome without a backend test-adapter seam; we assert the wiring + the route is
    // reachable, NOT a forged dashboard success.
    const resp = await req.response();
    expect(resp, 'the google/verify request must resolve to a real response').not.toBeNull();
    expect(resp!.status(), 'the google/verify route must be mounted (flag-ON), not 404').not.toBe(
      404,
    );
  });

  test.fixme(
    'a stubbed GIS credential signs in and lands on the dashboard',
    async ({ page }) => {
      // BLOCKED: no backend test-google-adapter seam. The google adapter verifies the
      // credential against Google's REAL published JWKs and there is no
      // DEV_GOOGLE_BYPASS, so a fake credential returns 401 and the dashboard is
      // unreachable through the UI. VERIFIED LIVE (slot-0 :4200 → backend :8000): POST
      // /api/v1/auth/google/verify with a fake credential → 401 (route mounted,
      // flag-ON). Un-fixme when the backend exposes a dev/test google-verify seam.
      // See federation_quirks.md.
      const auth = new AuthPage(page);
      await auth.installGisStub();
      await auth.gotoLogin();
      await auth.gisStubButton.click();
      await expect(page).toHaveURL(/\/dashboard/);
      await expect(page.getByTestId('dashboard-heading')).toBeVisible();
    },
  );
});
