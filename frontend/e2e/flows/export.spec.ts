/**
 * Flow: Export (Meesho-format XLSX).
 *
 * Wave plan: PQE-E2E-01 (export page renders for a real product) + the productId-fix
 * outcome + PQE-E2E-05 (the actual file download — env-blocked, test.fixme).
 *
 * Taxonomy (design §5.3): Export button clicked → file download event → non-empty file.
 *
 * PRODUCT BUG UPDATE (QA Wave C, qa-pricing 2026-06-22): the Wave-1 placeholder bug
 * (`onGenerate()` hardcoded productId='current-product-id') is FIXED — the component
 * now calls `resolveExportProductId(this.route.snapshot.paramMap)`. VERIFIED LIVE:
 * clicking Generate on /catalogs/{realPid}/export POSTs to the REAL product UUID. For a
 * fresh DRAFT product the backend returns a real 422 validation outcome ("Your product
 * isn't ready…"), which the page renders as the pre-export checklist. So the export
 * page render + the productId-fix outcome are GREEN; only the `ready`→download path
 * stays test.fixme (env-blocked — see below + federation_quirks.md).
 *
 * Pre-authenticated via the worker-scoped authed-context fixture.
 */
import { authedTest as test, expect } from '../fixtures/auth';
import { CatalogPage } from '../page-objects/catalog.page';
import { ExportPage } from '../page-objects/export.page';

test.describe('Export', () => {
  test('PQE-E2E-01: the export page renders the Generate button for a real product', async ({
    authedPage,
  }) => {
    const catalog = new CatalogPage(authedPage);
    const exportPage = new ExportPage(authedPage);

    // Chain create → export so the route carries a REAL product UUID.
    const productId = await catalog.createProductViaPicker();
    await exportPage.goto(productId);

    // Visible outcome: the export Generate trigger is shown on the export page.
    await expect(authedPage).toHaveURL(new RegExp(`/catalogs/${productId}/export`));
    await expect(exportPage.generateButton).toBeVisible();
  });

  test('clicking Generate on a draft product shows the real not-ready validation (productId fix is live)', async ({
    authedPage,
  }) => {
    // This locks the FIX of the Wave-1 placeholder bug: Generate now POSTs the REAL
    // route productId (not 'current-product-id'), so the backend can validate the real
    // product and return its real quality gate. A freshly-created product is a DRAFT
    // with no front image, so the gate blocks export and the page renders the reason.
    const catalog = new CatalogPage(authedPage);
    const exportPage = new ExportPage(authedPage);

    const productId = await catalog.createProductViaPicker();
    await exportPage.goto(productId);
    await expect(exportPage.generateButton).toBeVisible();

    await exportPage.generateButton.click();

    // VISIBLE outcome: the pre-export checklist surfaces the real quality-gate message
    // for THIS product (not a generic placeholder error). If the placeholder bug were
    // still present, the POST would hit 'current-product-id' and this product-specific
    // not-ready copy would never appear.
    await expect(
      authedPage.getByText(/isn'?t ready|front image is required/i).first(),
    ).toBeVisible({ timeout: 20_000 });

    // And the download link is NOT shown (the product is not `ready`).
    await expect(exportPage.downloadLink).toHaveCount(0);
  });

  test.fixme('PQE-E2E-05: clicking Generate triggers a non-empty file download', async ({
    authedPage,
  }) => {
    // ENV-BLOCKED (no longer the productId placeholder bug — that is FIXED). Reaching the
    // `ready` state + the `export-download` link requires (a) a product that passes the
    // quality gate (all required fields + a front image) AND (b) the backend export
    // pipeline producing a GCS signed URL. In LOCAL dev there is no GCS (POST
    // /products/{id}/images → 502 gcs.unavailable, and the ready→signed-URL step needs
    // GCS too), so a downloadable `ready` export is unreachable. Un-fixme on a
    // GCS-credentialed env (or a fake/MinIO) with a ready, front-image product.
    // See federation_quirks.md.
    const catalog = new CatalogPage(authedPage);
    const exportPage = new ExportPage(authedPage);

    const productId = await catalog.createProductViaPicker();
    await exportPage.goto(productId);

    const downloadPromise = authedPage.waitForEvent('download');
    await exportPage.generateButton.click();
    await expect(exportPage.downloadLink).toBeVisible({ timeout: 30_000 });
    await exportPage.downloadLink.click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/\.(xlsx|zip)$/);
  });
});
