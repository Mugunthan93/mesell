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
}
