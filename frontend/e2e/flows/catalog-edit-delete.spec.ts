/**
 * Flow: W3-E2-4 — Catalog list → delete round-trip.
 *
 * DE-FIXME'd (qa de-fixme lane, SPEC B group R / #9, 2026-07-06). The original
 * blocker ("no delete control + no per-row testids") is RESOLVED: PR #425 (77b5db0)
 * added a per-row inline delete affordance + literal data-testids in
 * catalog-list.component.ts — `catalog-row` (carries `data-product-id`), `catalog-edit-btn`,
 * `catalog-delete-btn`, `catalog-delete-confirm`, `catalog-delete-cancel`, `catalog-empty`.
 *
 * The delete UX is an INLINE confirm (no PrimeNG dialog): clicking Delete swaps the
 * row's edit/delete buttons for a "Delete this catalog?" row with Cancel + Confirm;
 * Confirm calls DELETE /products/{id} and removes the row on completion.
 *
 * SELECTOR PROVENANCE (honest disclosure): `catalog-empty` was LIVE-VERIFIED on the
 * deployed build (2026-07-06). The per-row controls are SOURCE-GROUND-TRUTHED at develop
 * c5529f6 — live-verification of a rendered row was env-blocked (the deployed backend's
 * product-creation is down: the AI smart-picker suggest returns empty responses and the
 * category browse tree is unseeded, so no catalog row could be created/rendered live).
 * They run live when the suite executes on a working stack (createProductViaPicker needs
 * a working suggest). The EDIT leg is covered by W3-E2-1 (wizard-save.spec.ts).
 *
 * Pre-authenticated via the worker-scoped authed-context fixture (rotation-safe).
 * Ports come from playwright.config.ts (the page objects navigate the shell only).
 */
import { authedTest as test, expect } from '../fixtures/auth';
import { CatalogPage } from '../page-objects/catalog.page';

test.describe('W3-E2-4 Catalog list delete round-trip', () => {
  test('deleting a product removes its row from the list', async ({ authedPage }) => {
    const catalog = new CatalogPage(authedPage);

    // Create a real product — its row appears in the catalog list.
    const productId = await catalog.createProductViaPicker();

    // Open the list; the new product's row is present (anchored by data-product-id).
    await catalog.gotoList();
    const row = catalog.rowFor(productId);
    await expect(row).toBeVisible();

    // Delete: click Delete → the inline confirm affordance → Confirm delete.
    await catalog.deleteButtonIn(row).click();
    await catalog.deleteConfirmIn(row).click();

    // VISIBLE outcome: the row disappears from the list.
    await expect(row).toHaveCount(0);
  });
});
