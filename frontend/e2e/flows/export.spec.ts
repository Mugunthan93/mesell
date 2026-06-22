/**
 * Flow: Export download.
 *
 * Taxonomy (design §5.3): Export button clicked → file download event → non-empty file.
 *
 * Two tests, chaining create → export to use a REAL product:
 *   1. (GREEN) The export page renders with the Generate button for a real product —
 *      a reachable VISIBLE outcome.
 *   2. (FIXME) The actual download. Blocked by a PRODUCT BUG: export.component.ts
 *      `onGenerate()` hardcodes `productId='current-product-id'` instead of reading
 *      the route param, so clicking Generate POSTs to a non-existent product and the
 *      backend returns 422 — the `ready` state + the `export-download` link are
 *      UNREACHABLE through the UI regardless of the real product. Verified live. See
 *      federation_quirks.md (filed to meesell-frontend-coordinator). Un-fixme once
 *      the component reads ActivatedRoute.snapshot.params['id'].
 *
 * Pre-authenticated via the worker-scoped authed-context fixture.
 */
import { authedTest as test, expect } from '../fixtures/auth';
import { CatalogPage } from '../page-objects/catalog.page';
import { ExportPage } from '../page-objects/export.page';

test.describe('Export', () => {
  test('the export page renders with the Generate button for a real product', async ({ authedPage }) => {
    const catalog = new CatalogPage(authedPage);
    const exportPage = new ExportPage(authedPage);

    // Chain create → export so the route carries a REAL product UUID.
    const productId = await catalog.createProductViaPicker();
    await exportPage.goto(productId);

    // Visible outcome: the export Generate trigger is shown on the export page.
    await expect(authedPage).toHaveURL(new RegExp(`/catalogs/${productId}/export`));
    await expect(exportPage.generateButton).toBeVisible();
  });

  // W3-E2-3 — un-fixme condition (re-verified QA Wave 3, develop @ a94e013):
  // STILL BLOCKED — export.component.ts onGenerate() (line ~431) STILL hardcodes
  // `const productId = 'current-product-id';` on develop; the route-read fix is in an
  // in-progress worktree (feature/mfe-export-productid/frontend) but NOT merged to
  // develop. mfe-export PR #398 is the gating change.
  // UN-FIXME ONLY WHEN: develop's frontend/apps/mfe-export/src/app/export.component.ts
  // reads `route.snapshot.paramMap.get('id')` (or ActivatedRoute.snapshot.params['id'])
  // in onGenerate() instead of the hardcoded 'current-product-id'.
  // SELECTOR NOTE (verified live): the download link testid is `export-download`
  // (a literal <a download>, rendered ONLY in the `ready` state) — NOT
  // `export-download-button` (which does not exist). The trigger is `export-trigger`.
  test.fixme('clicking Generate triggers a non-empty file download', async ({ authedPage }) => {
    // BLOCKED by product bug: onGenerate() ignores the route productId.
    const catalog = new CatalogPage(authedPage);
    const exportPage = new ExportPage(authedPage);

    const productId = await catalog.createProductViaPicker();
    await exportPage.goto(productId);

    const downloadPromise = authedPage.waitForEvent('download');
    await exportPage.generateButton.click();
    // (Once fixed) the export reaches `ready` and the download link appears.
    await expect(exportPage.downloadLink).toBeVisible({ timeout: 30_000 });
    await exportPage.downloadLink.click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/\.(xlsx|zip)$/);
  });
});
