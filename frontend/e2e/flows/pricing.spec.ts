/**
 * Flow: Price calculator (Estimated Bank Settlement).
 *
 * Wave plan: PQE-E2E-02 (happy), PQE-E2E-03 (negative warning). Covers the LOCKED
 * settlement model surfaced to the seller: enter a selling price → Calculate → the
 * P&L breakdown renders with the headline Estimated Bank Settlement + the disclaimer;
 * a selling price that yields a negative settlement shows the NEGATIVE_SETTLEMENT
 * alert (a 200 + warning, NOT an error page).
 *
 * Selectors LIVE-VERIFIED (QA Wave C, qa-pricing 2026-06-22) — see selector_registry.md
 * § mfe-pricing. The mfe-pricing data-testids landed in #439.
 *
 * Drives a REAL product created through the smart picker (createProductViaPicker →
 * real UUID): a smart-picker category is a census leaf, so it HAS a pricing-lookup
 * row and price-calc returns a 200 breakdown.
 *
 * Pre-authenticated via the worker-scoped authed-context fixture (rotation-safe).
 * Ports come from playwright.config.ts (the page objects navigate the shell only).
 */
import { authedTest as test, expect } from '../fixtures/auth';
import { CatalogPage } from '../page-objects/catalog.page';
import { PricingPage } from '../page-objects/pricing.page';

test.describe('Price calculator', () => {
  test('PQE-E2E-02: entering a selling price renders the settlement breakdown + disclaimer', async ({
    authedPage,
  }) => {
    const catalog = new CatalogPage(authedPage);
    const pricing = new PricingPage(authedPage);

    // Real product (smart-picker leaf → has a pricing-lookup row).
    const productId = await catalog.createProductViaPicker();
    await pricing.goto(productId);

    // The pricing remote loaded (not the remote-failure fallback) and the form is shown.
    await expect(authedPage).toHaveURL(new RegExp(`/catalogs/${productId}/pricing`));
    await expect(pricing.sellingPriceInput).toBeVisible();

    // Calculate a positive settlement.
    await pricing.calculate('70');

    // VISIBLE outcomes: the headline settlement value + the breakdown region + the
    // server-sent disclaimer all render; no negative alert for a positive settlement.
    await expect(pricing.settlementValue).toBeVisible({ timeout: 20_000 });
    await expect(pricing.settlementValue).toHaveText(/₹\s?-?\d/); // a rupee amount
    await expect(pricing.breakdown).toBeVisible();
    await expect(pricing.disclaimer).toBeVisible();
    await expect(pricing.disclaimer).not.toHaveText(/^\s*$/); // non-empty server copy
    await expect(pricing.negativeAlert).toHaveCount(0);
  });

  test('PQE-E2E-03: a selling price that yields a negative settlement shows the warning alert', async ({
    authedPage,
  }) => {
    const catalog = new CatalogPage(authedPage);
    const pricing = new PricingPage(authedPage);

    const productId = await catalog.createProductViaPicker();
    await pricing.goto(productId);
    await expect(pricing.sellingPriceInput).toBeVisible();

    // A tiny selling price drives the settlement negative (fees exceed the price).
    await pricing.calculate('1');

    // VISIBLE outcome: the NEGATIVE_SETTLEMENT alert chip is shown (a 200 + warning,
    // never an error page) — the settlement value still renders, in its negative form.
    await expect(pricing.negativeAlert).toBeVisible({ timeout: 20_000 });
    await expect(pricing.negativeAlert).toContainText(/negative settlement/i);
    await expect(pricing.settlementValue).toBeVisible();
    await expect(pricing.settlementValue).toHaveText(/₹\s?-/); // a negative rupee amount
  });
});
