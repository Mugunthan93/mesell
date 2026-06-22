/**
 * Flow: W3-E2-4 — Catalog list → edit → delete round-trip.
 *
 * Plan §4.3 W3-E2-4 asked to: from dashboard/list, open a product, edit a field
 * (autosave), then DELETE it, and assert the row disappears.
 *
 * PARTIALLY BLOCKED — there is NO delete control in the UI, and the list cards/
 * buttons carry NO data-testids.
 *   VERIFIED LIVE this wave (agent-browser + source on develop @ a94e013):
 *     - catalog-list.component.ts renders per-product cards with "Edit" and "Preview"
 *       mee-buttons ONLY. There is NO delete / remove / trash control anywhere in the
 *       component (grep: zero matches for delete|remove|trash).
 *     - The list cards, the Edit button, and the Preview button have NO data-testid /
 *       no [testId] binding — so there is no LIVE-VERIFIED selector to target a
 *       specific row's controls.
 *     - The backend DOES expose DELETE /products/{id} (covered by the backend lane
 *       W3-BE-15), but it is unreachable through the UI.
 *
 *   The EDIT leg is exercised by W3-E2-1 (wizard-save.spec.ts) via the edit-form
 *   autosave path. The DELETE leg cannot be E2E-tested until the UI gains a delete
 *   control with a LIVE-VERIFIED selector.
 *
 * Un-fixme condition: when catalog-list.component.ts (a) adds a delete control AND
 *   (b) per-row controls carry data-testids (e.g. catalog-list-row /
 *   catalog-list-delete) that are then LIVE-VERIFIED in selector_registry.md.
 *   Request the data-testids + the delete control via the QA coordinator → frontend
 *   lead memo (E2E does NOT add data-testids or feature controls itself).
 */
import { authedTest as test } from '../fixtures/auth';

test.describe('W3-E2-4 Catalog list edit + delete round-trip', () => {
  test.fixme(
    'editing then deleting a product removes its row from the list',
    async () => {
      // BLOCKED: no delete control + no per-row data-testids in catalog-list
      // (develop @ a94e013, verified live). The edit leg is covered by W3-E2-1.
      // Un-fixme when the list gains a delete control + LIVE-VERIFIED per-row
      // selectors (frontend-lead memo via the QA coordinator).
    },
  );
});
