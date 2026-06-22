/**
 * Flow: Google Sign-In. (E2E-AUTH-05 render KEEP, E2E-AUTH-06 click, QA Wave 2.)
 *
 * Three tests:
 *   1. (GREEN — E2E-AUTH-05) The GIS control RENDERS on the login page: the
 *      `login-google-host` is visible and the real GIS library injects its button
 *      iframe into it. (Kept from Wave 1, unchanged.)
 *   2. (GREEN — E2E-AUTH-06 partial) The GIS-STUB click drives the REAL app
 *      pipeline: injecting a fake `window.google` (avoiding the cross-origin OAuth
 *      iframe) lets a button click invoke the captured credential callback, which
 *      makes the app fire a REAL `POST /auth/google/verify`. We assert that request
 *      FIRES (the observable wiring outcome) against the flag-ON backend. This
 *      proves the GIS → AuthApiService.googleVerify wiring end-to-end without a real
 *      Google token.
 *   3. (FIXME — E2E-AUTH-06 success) The full success path (stubbed credential →
 *      dashboard) is BLOCKED: the backend `google.py` adapter calls
 *      `id_token.verify_oauth2_token` against Google's REAL published JWKs — there
 *      is NO runtime test-google-adapter seam (only pytest-level mocking), and
 *      there is NO `DEV_GOOGLE_BYPASS` (unlike `DEV_OTP_BYPASS_CODE`). VERIFIED
 *      LIVE: `POST /auth/google/verify` with a fake credential → 401 (the route IS
 *      mounted — flag-ON — so it is NOT a 404; it is a real signature rejection).
 *      Un-fixme requires a backend test-google-adapter seam (a way for a fake
 *      credential to "verify" without a real Google call). Recorded in
 *      federation_quirks.md and surfaced to the Director (owner: auth/ai-builder).
 *
 * The login page is public — no authentication needed. Selectors come from the
 * registry via the LoginPage page object; ports from config.
 */
import { test, expect } from '@playwright/test';
import { LoginPage } from '../page-objects/login.page';

test.describe('Google Sign-In', () => {
  test('the Google sign-in control renders on the login page', async ({ page }) => {
    const login = new LoginPage(page);
    await login.goto();

    // Visible outcome: the GIS host is visible and GIS injected its button iframe.
    await expect(login.googleHost).toBeVisible();
    await expect(login.googleHost.locator('iframe')).toHaveCount(1, { timeout: 15_000 });
  });

  test('a stubbed GIS credential makes the app fire a real POST /auth/google/verify', async ({ page }) => {
    const login = new LoginPage(page);

    // Inject the fake window.google BEFORE the app boots so the real
    // GoogleIdentityService.initialize() captures the component callback and
    // renderButton() renders a clickable stub button into the host.
    await login.installGisStub();
    await login.goto();

    // The host renders and our stub button lands inside it (proves
    // GoogleIdentityService.load()/initialize()/renderButton() all ran against the
    // stub — the real wiring).
    await expect(login.googleHost).toBeVisible();
    await expect(login.gisStubButton).toBeVisible();

    // Clicking invokes the captured credential callback → LoginComponent
    // .onGoogleCredential() → AuthApiService.googleVerify() → POST. Assert the REAL
    // request fires (the observable wiring outcome) and reaches the flag-ON route.
    const verifyReq = page.waitForRequest(
      (r) => r.url().includes('/auth/google/verify') && r.method() === 'POST',
      { timeout: 15_000 },
    );
    await login.gisStubButton.click();
    const req = await verifyReq;

    // The route is mounted (flag-ON): the request resolves to a real response, not
    // a 404 route-absent. A fake credential is rejected (401) — that is the EXPECTED
    // outcome without a backend test-adapter seam; we assert the wiring, not a
    // forged dashboard success.
    const resp = await req.response();
    expect(resp).not.toBeNull();
    expect(resp!.status()).not.toBe(404);
  });

  test.fixme('a stubbed GIS credential signs in and lands on the dashboard', async ({ page }) => {
    // BLOCKED: no backend test-google-adapter seam. `backend/app/adapters/google.py`
    // verifies the credential against Google's REAL published JWKs and there is no
    // DEV_GOOGLE_BYPASS, so a fake credential returns 401 and the dashboard is
    // unreachable through the UI. VERIFIED LIVE (slot-0 :4200 → backend :8000):
    // POST /auth/google/verify with a fake credential → 401 (route mounted, flag-ON).
    // Un-fixme when the backend exposes a dev/test google-verify seam. See
    // federation_quirks.md.
    const login = new LoginPage(page);
    await login.installGisStub();
    await login.goto();
    await login.gisStubButton.click();
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.getByTestId('dashboard-heading')).toBeVisible();
  });
});
