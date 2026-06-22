/**
 * OnboardingPage — page object for the onboarding remote (mfe-onboarding).
 *
 * Post the qa-onboarding persist-fix (#399) the form is the seller-profile
 * manufacturer/packer/country set with REAL persistence (PATCH /seller-profile →
 * refreshUser() → /dashboard). The OLD businessName/city/gst mock form is gone, and
 * `onboarding-business-name` no longer exists.
 *
 * Selector reality (LIVE-VERIFIED 2026-06-22, slot-1 shell :4210, integration tip
 * 7e86054 — see selector_registry.md):
 *   - The 7 form fields are `mee-input` wrappers with NO testid; each renders a real
 *     `<label [for]>` → `<input>`, so they are driven by getByLabel (substring match,
 *     so required labels rendered as "… *" still match).
 *   - The submit button is the ONE testid on the page (`onboarding-submit`) and is
 *     also the "fresh user routed to onboarding" visible marker.
 *   - The skip link is a plain <a role="button">I'll set this up later →</a> (no
 *     testid) → getByRole('button', { name: /set this up later/i }).
 *   - The submit-error banner is a mee-alert-banner (no testid) that emits
 *     role="alert" → getByRole('alert').
 */
import type { Page, Locator } from '@playwright/test';

export class OnboardingPage {
  constructor(private readonly page: Page) {}

  /** The Save & Continue submit button (the only testid on this page). */
  get submit(): Locator {
    return this.page.getByTestId('onboarding-submit');
  }

  /** The "I'll set this up later" skip link (role=button, no testid). */
  get skipLink(): Locator {
    return this.page.getByRole('button', { name: /set this up later/i });
  }

  /** The submit-error banner (mee-alert-banner → role="alert"). */
  get errorBanner(): Locator {
    return this.page.getByRole('alert');
  }

  /** A form field by its visible label (mee-input → real <label for>). */
  field(label: string): Locator {
    return this.page.getByLabel(label);
  }

  /** Fill the form with valid seller-profile data (Country of Origin left as "India"). */
  async fillValid(): Promise<void> {
    await this.submit.waitFor({ state: 'visible' });
    await this.field('Manufacturer Name').fill('E2E QA Manufacturing');
    await this.field('Manufacturer Address').fill('12 Industrial Estate, Tirupur');
    await this.field('Manufacturer Pincode').fill('641604');
    await this.field('Packer Name').fill('E2E QA Packers');
    await this.field('Packer Address').fill('12 Industrial Estate, Tirupur');
    await this.field('Packer Pincode').fill('641604');
  }

  /** Click Save & Continue (mee-button → click the inner <button>). */
  async submitForm(): Promise<void> {
    await this.submit.locator('button').click();
  }

  /** Click the skip link. */
  async skip(): Promise<void> {
    await this.skipLink.click();
  }
}
