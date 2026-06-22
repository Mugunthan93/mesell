/**
 * Flow: W3-E2-2 — Live Product Preview page.
 *
 * Plan §4.3 W3-E2-2 asked to open the Live Product Preview page for a created product
 * and assert it renders the product name + ≥1 field value.
 *
 * BLOCKED — the Live Product Preview PAGE/ROUTE WAS RETIRED.
 *   The frontend preview route `/catalogs/:id/preview` was retired in PR #278
 *   (feat/my-live-listings). On develop @ a94e013 there is NO preview component, NO
 *   preview route, and the catalog-list "Preview" button was repointed to
 *   `:id/edit` in PR #395 (3c63b55) precisely because the preview route no longer
 *   exists (the shell wildcard caught the miss and bounced to /login).
 *   VERIFIED LIVE this wave (agent-browser, develop tip): there is no preview surface
 *   in the UI to drive — the catalog-list "Preview" button navigates to /edit.
 *
 *   The BACKEND route `GET /products/{id}/preview` still exists and is covered by the
 *   QA Wave-3 BACKEND lane (W3-BE-1…5). There is simply no FRONTEND page to E2E.
 *
 * Un-fixme condition: ONLY if a frontend Live Product Preview page is re-introduced
 *   (a route + a component with LIVE-VERIFIED selectors for the product name + a
 *   field value). Until then this is a spec gap to escalate to the QA coordinator →
 *   frontend-coordinator, NOT an E2E to write. No selector may be invented for a
 *   page that does not exist.
 */
import { authedTest as test } from '../fixtures/auth';

test.describe('W3-E2-2 Live Product Preview', () => {
  test.fixme(
    'the preview page renders the product name and a field value',
    async () => {
      // BLOCKED: the frontend /catalogs/:id/preview route was retired (#278); the
      // "Preview" button now navigates to /edit (#395). There is no preview page to
      // drive. Backend GET /products/{id}/preview is covered by the backend lane.
      // Un-fixme only when a frontend preview page is re-introduced and its
      // selectors are LIVE-VERIFIED in selector_registry.md.
    },
  );
});
