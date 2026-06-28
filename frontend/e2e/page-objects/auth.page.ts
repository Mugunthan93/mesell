/**
 * AuthPage — page object for the auth remote (mfe-auth): /login + /otp-verify.
 *
 * Selectors are LIVE-VERIFIED (QA Wave 1 + qa-onboarding Wave C) — see
 * selector_registry.md. The ui-kit wrapper interaction rules apply:
 *   - mee-input  → the testid IS the inner <input> → fill directly.
 *   - mee-button → the testid is the <p-button> host → click `.locator('button')`.
 *   - mee-otp-input → the testid is the <p-inputotp> wrapper → 6 inner <input> cells.
 *   - the error banner is a mee-alert-banner (no testid) → role="alert".
 */
import type { Page, Locator } from '@playwright/test';

/** The fake credential the GIS stub sends through the REAL verify pipeline. */
export const FAKE_GIS_CREDENTIAL = 'FAKE_E2E_GIS_CREDENTIAL';

/**
 * The dev/test google-verify BYPASS SENTINEL (PR #480) — a TEST sentinel, NEVER a
 * real credential. When the backend runs non-prod with FEATURE_GOOGLE_AUTH_ENABLED
 * =True and DEV_GOOGLE_BYPASS_TOKEN set to this exact `dev-google:{sub}:{email}`
 * string, POST /api/v1/auth/google/verify with this value as the credential returns
 * 200 + an access JWT + refresh cookie + a synthetic dual-identity user (phone NULL,
 * google_sub/email from the sentinel) — WITHOUT calling real Google. Driving the GIS
 * stub with this credential exercises the FULL Google sign-in SUCCESS path headlessly.
 * Overridable via env so the test identity stays in lockstep with the backend's
 * configured DEV_GOOGLE_BYPASS_TOKEN (no hardcoded coupling).
 */
export const DEV_GOOGLE_BYPASS_CREDENTIAL =
  process.env.MEESELL_DEV_GOOGLE_BYPASS_TOKEN ?? 'dev-google:e2e-sub-001:e2e.user@example.com';

/** testid the GIS stub puts on the button it renders into the GIS host. */
export const GIS_STUB_BUTTON_TESTID = 'gis-stub-button';

export class AuthPage {
  constructor(private readonly page: Page) {}

  // ── /login ──
  get phoneInput(): Locator {
    return this.page.getByTestId('login-phone-input');
  }
  get requestOtpButton(): Locator {
    return this.page.getByTestId('login-request-otp');
  }
  /** The Google Identity Services host div (GIS injects its button iframe into it). */
  get googleHost(): Locator {
    return this.page.getByTestId('login-google-host');
  }
  /** The GIS-stub button (only present after installGisStub() + the app's render). */
  get gisStubButton(): Locator {
    return this.page.getByTestId(GIS_STUB_BUTTON_TESTID);
  }

  // ── /otp-verify ──
  /** The 6 inner OTP cells of the mee-otp-input wrapper. */
  get otpCells(): Locator {
    return this.page.getByTestId('otp-input').locator('input');
  }
  get verifyButton(): Locator {
    return this.page.getByTestId('otp-verify-submit');
  }

  /** The error banner (mee-alert-banner → role="alert"), shared by login + otp-verify. */
  get errorBanner(): Locator {
    return this.page.getByRole('alert');
  }

  async gotoLogin(): Promise<void> {
    await this.page.goto('/login');
  }

  /** Enter a phone (10-digit) and request an OTP → navigates to /otp-verify. */
  async requestOtp(phone10: string): Promise<void> {
    await this.phoneInput.waitFor({ state: 'visible' });
    await this.phoneInput.fill(phone10);
    await this.requestOtpButton.locator('button').click();
    await this.page.waitForURL(/\/otp-verify/);
  }

  /** Fill the 6 OTP cells with the given code (padded/truncated to cell count). */
  async fillOtp(code: string): Promise<void> {
    await this.otpCells.first().waitFor({ state: 'visible' });
    const n = await this.otpCells.count();
    for (let i = 0; i < n; i++) {
      await this.otpCells.nth(i).fill(code[i] ?? '0');
    }
  }

  /** Submit the OTP verify form (mee-button → click the inner <button>). */
  async submitOtp(): Promise<void> {
    await this.verifyButton.locator('button').click();
  }

  /**
   * installGisStub() — inject a fake `window.google.accounts.id` BEFORE the app
   * boots so GoogleIdentityService.isReady() is true, initialize() captures the
   * LoginComponent's REAL credential callback, and renderButton() renders a
   * clickable test button into the GIS host. Clicking it invokes the captured
   * callback with a fake credential → the app runs its REAL pipeline
   * (LoginComponent.onGoogleCredential → AuthApiService.googleVerify → POST
   * /api/v1/auth/google/verify), WITHOUT the cross-origin Google OAuth iframe.
   *
   * MUST be called before navigating to /login — addInitScript runs on every
   * navigation in the page/context. Stubbing the browser GIS API (not the app DOM)
   * is the only way to drive the real wiring headlessly; the host selector itself
   * (login-google-host) is LIVE-VERIFIED in selector_registry.md.
   */
  async installGisStub(credential: string = FAKE_GIS_CREDENTIAL): Promise<void> {
    await this.page.addInitScript(
      ({ cred, btnTestId }) => {
        let captured: ((r: { credential: string }) => void) | null = null;
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (window as any).google = {
          accounts: {
            id: {
              initialize: (cfg: { callback: (r: { credential: string }) => void }) => {
                captured = cfg.callback;
              },
              renderButton: (el: HTMLElement) => {
                const b = document.createElement('button');
                b.setAttribute('data-testid', btnTestId);
                b.type = 'button';
                b.textContent = 'Stub Google sign-in';
                b.addEventListener('click', () => {
                  if (captured) captured({ credential: cred });
                });
                el.appendChild(b);
              },
              cancel: () => {},
              disableAutoSelect: () => {},
            },
          },
        };
      },
      { cred: credential, btnTestId: GIS_STUB_BUTTON_TESTID },
    );
  }

  /**
   * Drive the GIS stub button → invoke the captured credential callback with the
   * dev-google BYPASS SENTINEL → the app runs its REAL pipeline
   * (LoginComponent.onGoogleCredential → AuthApiService.googleVerify → POST
   * /api/v1/auth/google/verify) which the backend bypass seam answers 200 + an
   * access JWT + refresh cookie. Waits for the app to navigate OFF /login. MUST be
   * preceded by `installGisStub(DEV_GOOGLE_BYPASS_CREDENTIAL)` + `gotoLogin()`.
   *
   * LIVE PRODUCT REALITY (selector_registry.md): the synthetic Google user is brand
   * new (onboarding_complete=false), so the post-login default landing is
   * /onboarding — but the session IS fully authed (the authed shell sidebar renders
   * and /dashboard is reachable directly). So this resolves once the URL is no longer
   * /login; the caller asserts the authed dashboard outcome separately.
   */
  async clickGisStub(): Promise<void> {
    await this.gisStubButton.waitFor({ state: 'visible' });
    await this.gisStubButton.click();
    await this.page.waitForURL((url) => !/\/login(\b|$)/.test(url.pathname), {
      timeout: 20_000,
    });
  }
}
