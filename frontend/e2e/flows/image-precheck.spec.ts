/**
 * Flow: Image upload + precheck.
 *
 * Taxonomy (design §5.3): Upload valid JPEG → quality gate result card visible
 * with numeric score.
 *
 * STUB — fleshed out by the QA wave. Pre-authenticated via storageState. The
 * exploration phase must pin the file input + the precheck result card / score,
 * and a small fixture JPEG must be added under e2e/fixtures/ before completion.
 */
import { test, expect } from '@playwright/test';
import { CatalogPage } from '../page-objects/catalog.page';

// A catalog id to attach images to. Seed/override per environment.
const CATALOG_ID = process.env.MEESELL_E2E_CATALOG_ID ?? '00000000-0000-0000-0000-000000000000';

test.describe('Image precheck', () => {
  test.fixme('uploading a valid JPEG shows a quality-gate result card with a numeric score', async ({ page }) => {
    const catalog = new CatalogPage(page);

    await catalog.gotoImages(CATALOG_ID);

    // Upload a valid JPEG fixture. (Add e2e/fixtures/valid-product.jpg in the QA wave.)
    await catalog.imageFileInput.setInputFiles('./fixtures/valid-product.jpg');

    // Asserted outcome: the quality-gate result card is visible AND carries a numeric score.
    await expect(catalog.precheckResultCard).toBeVisible();
    await expect(catalog.precheckScore).toHaveText(/\d/);
  });
});
