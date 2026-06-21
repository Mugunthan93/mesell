/**
 * Flow: Image upload + precheck.
 *
 * Taxonomy (design §5.3): Upload a valid JPEG → quality-gate result card visible.
 *
 * Two tests:
 *   1. (GREEN) The image uploader page renders with its upload control after a real
 *      product is created — a reachable VISIBLE outcome in every environment.
 *   2. (FIXME) The full upload → precheck-card outcome. Blocked in LOCAL dev because
 *      `POST /products/{id}/images` returns 502 `gcs.unavailable` ("GCS upload
 *      failed: Forbidden") — the dev backend has no working GCS bucket/creds, so the
 *      upload 502s BEFORE any rembg precheck runs (FEATURE_IMAGE_PRECHECK_ENABLED is
 *      True). The PrimeNG advanced-uploader interaction itself is correct (verified
 *      live). See federation_quirks.md. Un-fixme on a GCS-credentialed env / MinIO.
 *
 * Pre-authenticated via the worker-scoped authed-context fixture. A real product is
 * created first (via the smart picker) so the images route has a valid :id.
 */
import { authedTest as test, expect } from '../fixtures/auth';
import { CatalogPage } from '../page-objects/catalog.page';

const FIXTURE_JPEG = './fixtures/valid-product.jpg';

test.describe('Image precheck', () => {
  test('the image uploader page renders with its upload control', async ({ authedPage }) => {
    const catalog = new CatalogPage(authedPage);

    // Create a real product, then open its images route.
    const productId = await catalog.createProductViaPicker();
    await catalog.gotoImages(productId);

    // Visible outcome: the PrimeNG advanced uploader is present and ready to receive
    // a file (the primary file input exists in the DOM).
    await expect(authedPage.locator('p-fileupload').first()).toBeVisible();
    await expect(catalog.primaryFileInput).toHaveCount(1);
  });

  test.fixme('uploading a valid JPEG shows a quality-gate result card', async ({ authedPage }) => {
    // BLOCKED in local dev: POST /products/{id}/images → 502 gcs.unavailable.
    const catalog = new CatalogPage(authedPage);
    const productId = await catalog.createProductViaPicker();
    await catalog.gotoImages(productId);

    // Drive the real PrimeNG advanced uploader: select the file, then click Upload.
    await catalog.primaryFileInput.setInputFiles(FIXTURE_JPEG);
    await catalog.uploadButton.click();

    // Asserted outcome (once GCS works): a quality-gate result card with a status.
    await expect(catalog.precheckCards.first()).toBeVisible({ timeout: 30_000 });
    await expect(catalog.precheckStatuses.first()).toBeVisible();
  });
});
