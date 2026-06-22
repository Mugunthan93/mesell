/**
 * LoginPage — page object for the auth remote's login surface (mfe-auth, mounted
 * at /login under the shell).
 *
 * Encapsulates the phone-OTP entry, the OTP-verify step, and the Google Identity
 * Services (GIS) host. The GIS-stub helper (`installGisStub`) injects a fake
 * `window.google` BEFORE the app loads so the REAL app pipeline
 * (GoogleIdentityService.initialize → LoginComponent.onGoogleCredential →
 * AuthApiService.googleVerify → POST /auth/google/verify) runs without the
 * cross-origin Google OAuth iframe. See google-signin.spec.ts.
 *
 * Selectors are LIVE-VERIFIED (QA Wave 1/2) and recorded in
 * `.claude/agent-memory/meesell-e2e-test-writer/selector_registry.md`.
 *   mee-input    testid IS the inner <input>  → fill directly.
 *   mee-button   testid is on <p-button> host → click the inner <button>.
 *   mee-otp-input testid is on <p-inputotp>   → 6 inner cells.
 *   login-google-host is a LITERAL data-testid on the host <div>.
 */
import type { Page, Locator } from '@playwright/test';

/** The fake credential string the GIS stub sends through the real verify pipeline. */
export const FAKE_GIS_CREDENTIAL = 'FAKE_E2E_GIS_CREDENTIAL';
/** testid the stub puts on the button it renders into the GIS host. */
export const GIS_STUB_BUTTON_TESTID = 'gis-stub-button';

export class LoginPage {
  constructor(private readonly page: Page) {}

  // ── Phone OTP entry ──
  /** mee-input → the inner <input>; fill the 10-digit number directly. */
  get phoneInput(): Locator {
    return this.page.getByTestId('login-phone-input');
  }
  /** mee-button → click the inner <button>. */
  get requestOtpButton(): Locator {
    return this.page.getByTestId('login-request-otp').locator('button');
  }

  // ── OTP verify ──
  /** mee-otp-input → the 6 inner cells. */
  get otpCells(): Locator {
    return this.page.getByTestId('otp-input').locator('input');
  }
  /** mee-button → click the inner <button>. */
  get verifyButton(): Locator {
    return this.page.getByTestId('otp-verify-submit').locator('button');
  }

  // ── Google sign-in (GIS) ──
  /** Literal data-testid on the host <div> GIS renders its button into. */
  get googleHost(): Locator {
    return this.page.getByTestId('login-google-host');
  }
  /** The stub button (only present after installGisStub() + render). */
  get gisStubButton(): Locator {
    return this.page.getByTestId(GIS_STUB_BUTTON_TESTID);
  }

  async goto(): Promise<void> {
    await this.page.goto('/login');
  }

  /**
   * installGisStub() — inject a fake `window.google.accounts.id` BEFORE the app
   * boots so GoogleIdentityService.isReady() is true, initialize() captures the
   * component's real credential callback, and renderButton() renders a clickable
   * test button into the host. Clicking it invokes the captured callback with a
   * fake credential → the app POSTs /auth/google/verify (the real pipeline).
   *
   * MUST be called before navigating to /login (addInitScript runs on every
   * navigation in the page/context).
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
}
