/**
 * Flow: W3-E2-6 — Price-calc → apply → export chain (the end-to-end journey).
 *
 * DE-FIXME'd (qa-pricing e2e lane, SPEC A §3.3, 2026-07-06). The original fixme
 * blockers are BOTH resolved on develop:
 *   1. mfe-pricing now ships the SPEC-C apply control + testids (#439). The apply
 *      button `pricing-apply-btn` was LIVE-VERIFIED on the deployed build (2026-07-06):
 *      a native <button>, disabled on load, enabling after a successful calc.
 *   2. The mfe-export productId placeholder bug is fixed (`resolveExportProductId`), so
 *      the export page renders for the real product (verified in export.spec.ts).
 *
 * This asserts the calc → apply → export-PAGE-REACHABLE chain (URL + the export
 * Generate control). The export DOWNLOAD leg stays OUT of scope here — it is
 * storage-env-blocked (no GCS/fake-gcs in dev/CI) and owned by SPEC B PQE-E2E-05.
 *
 * OVERLAP NOTE: this journey overlaps the apply-flow assertion in PQE-E2E-04
 * (flows/pricing.spec.ts). PQE-E2E-04 is the primary apply-CONTROL test; W3-E2-6 is
 * the named wave-plan CHAIN. Both use the same rotation-safe worker-scoped auth
 * fixture and config-driven ports (the page objects navigate the shell only).
 */
import { authedTest as test, expect } from '../fixtures/auth';
import { CatalogPage } from '../page-objects/catalog.page';
import { PricingPage } from '../page-objects/pricing.page';
import { ExportPage } from '../page-objects/export.page';

test.describe('W3-E2-6 Price-calc → apply → export chain', () => {
  test('calculating then applying a price makes the export page reachable', async ({
    authedPage,
  }) => {
    const catalog = new CatalogPage(authedPage);
    const pricing = new PricingPage(authedPage);
    const exportPage = new ExportPage(authedPage);

    // Real product (smart-picker leaf → has a pricing-lookup row so calc 200s).
    const productId = await catalog.createProductViaPicker();

    // Calculate a settlement (the apply button is disabled until a breakdown exists).
    await pricing.goto(productId);
    await pricing.calculate('70');
    await expect(pricing.settlementValue).toBeVisible({ timeout: 20_000 });
    await expect(pricing.applyButton).toBeEnabled();

    // Apply the price → onSaveContinue()'s 204 navigates to the export page.
    await pricing.applyPrice();

    // VISIBLE outcome: the export page is reachable (URL) and its Generate control
    // is present. The download leg is intentionally NOT asserted (env-blocked).
    await expect(authedPage).toHaveURL(new RegExp(`/catalogs/${productId}/export`), {
      timeout: 15_000,
    });
    await expect(exportPage.generateButton).toBeVisible();
  });
});
