/**
 * PricingPage — page object for the pricing remote (mfe-pricing).
 *
 * Route (mounted under the shell): catalogs/:id/pricing.
 *
 * Selectors LIVE-VERIFIED (QA Wave C — qa-pricing, 2026-06-22) against the running
 * federated stack with the integration-tip mfe-pricing build (testids from #439).
 * See selector_registry.md § mfe-pricing.
 *
 * Interaction rules (the ui-kit wrapper [testId] passthrough — see selector_registry.md):
 *  - pricing-cost-input / pricing-commission-input sit on `mee-input` → the testid IS
 *    the inner <input>, so getByTestId(x).fill(value) DIRECTLY.
 *  - pricing-calculate-btn sits on the `mee-button` <p-button> host → click the inner
 *    <button> (.locator('button')).
 *  - pricing-breakdown / pricing-settlement-value / pricing-disclaimer /
 *    pricing-negative-alert are literal data-testid attributes on the element itself.
 *
 * Render reality (LIVE):
 *  - pricing-cost-input, pricing-commission-input, pricing-calculate-btn, and the
 *    pricing-breakdown result region render ON LOAD (the region is always present).
 *  - pricing-settlement-value + pricing-disclaimer render only AFTER a successful calc.
 *  - pricing-negative-alert renders only when the settlement is negative.
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

  async goto(productId: string): Promise<void> {
    await this.page.goto(`/catalogs/${productId}/pricing`);
  }

  /** Enter a selling price and click Calculate. */
  async calculate(sellingPrice: string): Promise<void> {
    await this.sellingPriceInput.waitFor({ state: 'visible' });
    await this.sellingPriceInput.fill(sellingPrice);
    await this.calculateButton.click();
  }
}
