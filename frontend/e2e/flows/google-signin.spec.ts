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
 *   3. (GREEN — E2E-AUTH-06 success path, UN-FIXME'd by PR #480) The full success
 *      path (stubbed credential → authed dashboard). The backend now ships a
 *      prod-hard-disabled dev/test seam (adapters/google.py): when it runs non-prod
 *      with FEATURE_GOOGLE_AUTH_ENABLED=True and DEV_GOOGLE_BYPASS_TOKEN set to a
 *      `dev-google:{sub}:{email}` sentinel, POST /auth/google/verify with that exact
 *      sentinel as the credential returns 200 + an access JWT + refresh cookie + a
 *      synthetic dual-identity user — WITHOUT calling real Google. We drive the GIS
 *      stub with the sentinel, the app fires the REAL POST, the seam answers 200, and
 *      the session is fully authed. VERIFIED LIVE (slot-0 :4200 → backend :8000):
 *      verify → 200; the app navigates off /login; /auth/me returns the synthetic
 *      user (phone NULL); the authed dashboard heading renders. (PRODUCT REALITY: the
 *      synthetic user is brand-new → onboarding_complete=false → the default landing
 *      is /onboarding, but the session is authed and /dashboard is reachable — see
 *      selector_registry.md. We assert the authed dashboard heading: the VISIBLE
 *      authed outcome the brief requires.) The test SKIPS (not fails) if the running
 *      backend lacks the dev seam env, so it is green-or-skipped, never falsely red.
 *
 * The login page is public — no authentication needed. Selectors come from
 * selector_registry.md via the AuthPage / DashboardPage page objects (GIS host +
 * stub button + dashboard heading); ports come from playwright.config.ts (never
 * hardcoded). The bypass sentinel is a TEST sentinel (env-overridable), never a real
 * credential.
 */
import { test, expect } from '@playwright/test';
import { AuthPage, DEV_GOOGLE_BYPASS_CREDENTIAL } from '../page-objects/auth.page';
import { DashboardPage } from '../page-objects/dashboard.page';
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

  test('a stubbed GIS credential with the dev-bypass sentinel signs in to the authed dashboard', async ({
    page,
  }) => {
    const auth = new AuthPage(page);

    // Stub GIS so the captured callback fires with the DEV-BYPASS SENTINEL (not the
    // generic fake credential). The app POSTs the sentinel → the backend seam answers
    // 200 only when it runs non-prod with FEATURE_GOOGLE_AUTH_ENABLED + the matching
    // DEV_GOOGLE_BYPASS_TOKEN. Capture the verify status to honestly skip (not fail)
    // when the running stack lacks the seam env.
    await auth.installGisStub(DEV_GOOGLE_BYPASS_CREDENTIAL);
    await auth.gotoLogin();

    await expect(auth.googleHost).toBeVisible();
    await expect(auth.gisStubButton).toBeVisible();

    let verifyStatus = 0;
    page.on('response', (r) => {
      if (r.url().includes('/auth/google/verify') && r.request().method() === 'POST') {
        verifyStatus = r.status();
      }
    });

    // Drive the stub → real pipeline → seam → 200 → app navigates off /login. The
    // synthetic user is brand-new so the default landing is /onboarding; the session
    // is fully authed regardless (see selector_registry.md).
    await auth.clickGisStub();

    // Honest skip if the seam is not configured in the target stack: the verify came
    // back non-2xx (e.g. 401 real-verify of the sentinel) → the success path is not
    // exercisable here, so skip rather than red. The render + POST-fires cases above
    // still prove the wiring.
    test.skip(
      verifyStatus < 200 || verifyStatus >= 300,
      `dev-google bypass seam not active on this stack (verify → ${verifyStatus}); ` +
        'run the backend non-prod with FEATURE_GOOGLE_AUTH_ENABLED=True + ' +
        'DEV_GOOGLE_BYPASS_TOKEN matching MEESELL_DEV_GOOGLE_BYPASS_TOKEN.',
    );

    // VISIBLE authed outcome: the authed dashboard heading renders (and the URL is
    // not /login). /dashboard is reachable for the authed session even though the
    // brand-new synthetic user's default landing is /onboarding.
    const dashboard = new DashboardPage(page);
    await dashboard.goto();
    await expect(page).not.toHaveURL(/\/login(\b|$)/);
    await expect(dashboard.heading).toBeVisible();
  });
});
