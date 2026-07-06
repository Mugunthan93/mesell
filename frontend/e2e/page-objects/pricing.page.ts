/**
 * PricingPage — page object for the pricing remote (mfe-pricing).
 *
 * Route (mounted under the shell): catalogs/:id/pricing.
 *
 * Selectors LIVE-VERIFIED (QA Wave C — qa-pricing, 2026-06-22; the SPEC-C apply trio
 * re-verified 2026-07-06 against the DEPLOYED build) — see selector_registry.md
 * § mfe-pricing. Testids from #439 (form + breakdown) and #439/SPEC-C (apply trio).
 *
 * Interaction rules (the ui-kit wrapper [testId] passthrough — see selector_registry.md):
 *  - pricing-cost-input / pricing-commission-input sit on `mee-input` → the testid IS
 *    the inner <input>, so getByTestId(x).fill(value) DIRECTLY.
 *  - pricing-calculate-btn sits on the `mee-button` <p-button> host → click the inner
 *    <button> (.locator('button')).
 *  - pricing-breakdown / pricing-settlement-value / pricing-disclaimer /
 *    pricing-negative-alert are literal data-testid attributes on the element itself.
 *  - pricing-apply-btn / pricing-applied-status / pricing-apply-error are literal
 *    data-testids on NATIVE elements (federation strips [testId] on mee-* wrappers per
 *    the source comment at pricing.component.ts L666) → pricing-apply-btn IS the
 *    <button> (click it DIRECTLY, NO .locator('button')).
 *
 * Render reality (LIVE, deployed build 2026-07-06):
 *  - pricing-cost-input, pricing-commission-input, pricing-calculate-btn, the
 *    pricing-breakdown result region, and pricing-apply-btn all render ON LOAD.
 *  - pricing-apply-btn is DISABLED on load ([disabled]="!breakdown()…") and enables
 *    only after a successful calc; its text is "Save & Continue".
 *  - pricing-settlement-value + pricing-disclaimer render only AFTER a successful calc.
 *  - pricing-negative-alert renders only when the settlement is negative.
 *  - pricing-applied-status renders only after the apply POST returns 204 (and may
 *    unmount immediately as onSaveContinue() navigates to export); pricing-apply-error
 *    renders only when the apply POST errors. (Both confirmed count 0 on load.)
 */
import type { Page, Locator } from '@playwright/test';

export class PricingPage {
  constructor(private readonly page: Page) {}

  /** Selling-price input (mee-input → testid IS the <input>; fill directly). */
  get sellingPriceInput(): Locator {
    return this.page.getByTestId('pricing-cost-input');
  }

  /** Optional commission % override (mee-input → fill directly). */
  get commissionInput(): Locator {
    return this.page.getByTestId('pricing-commission-input');
  }

  /** Calculate button (mee-button → click the inner <button>). */
  get calculateButton(): Locator {
    return this.page.getByTestId('pricing-calculate-btn').locator('button');
  }

  /** The result region — present on load; populated after a calc. */
  get breakdown(): Locator {
    return this.page.getByTestId('pricing-breakdown');
  }

  /** Headline Estimated Bank Settlement value — rendered after a successful calc. */
  get settlementValue(): Locator {
    return this.page.getByTestId('pricing-settlement-value');
  }

  /** Server-sent disclaimer fine-print — rendered after a successful calc. */
  get disclaimer(): Locator {
    return this.page.getByTestId('pricing-disclaimer');
  }

  /** NEGATIVE_SETTLEMENT warning chip — rendered only when settlement < 0. */
  get negativeAlert(): Locator {
    return this.page.getByTestId('pricing-negative-alert');
  }

  // ── SPEC-C apply-price trio (native elements — testid IS the element) ──
  /**
   * "Save & Continue" apply-price button — a NATIVE <button> carrying the testid
   * directly (click it, NO .locator('button')). Disabled until a calc breakdown
   * exists; on click onSaveContinue() POSTs /apply-price and (on 204) navigates to
   * /catalogs/:id/export. LIVE-VERIFIED on the deployed build (2026-07-06): native
   * <button>, disabled on load, text "Save & Continue".
   */
  get applyButton(): Locator {
    return this.page.getByTestId('pricing-apply-btn');
  }

  /** "Price applied" success chip — renders only after the apply POST returns 204
   *  (may unmount as the flow navigates to export). */
  get appliedStatus(): Locator {
    return this.page.getByTestId('pricing-applied-status');
  }

  /** Apply-error chip ("Could not apply price…") — renders only when apply errors. */
  get applyError(): Locator {
    return this.page.getByTestId('pricing-apply-error');
  }

  async goto(productId: string): Promise<void> {
    await this.page.goto(`/catalogs/${productId}/pricing`);
  }

  /** Enter a selling price and click Calculate. */
  async calculate(sellingPrice: string): Promise<void> {
    await this.sellingPriceInput.waitFor({ state: 'visible' });
    await this.sellingPriceInput.fill(sellingPrice);
    await this.calculateButton.click();
  }

  /** Click "Save & Continue" (apply-price). Requires a prior successful calc — the
   *  button is disabled until a breakdown exists. */
  async applyPrice(): Promise<void> {
    await this.applyButton.click();
  }
}
