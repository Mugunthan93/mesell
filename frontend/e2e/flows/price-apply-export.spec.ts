/**
 * Flow: W3-E2-6 — Price-calc → apply → export chain.
 *
 * Plan §4.3 W3-E2-6 asked: for a created product, open pricing → calc → apply →
 * navigate to export → (download leg gated on E2-3).
 *
 * BLOCKED on two counts, both VERIFIED LIVE this wave (develop @ a94e013):
 *   1. The mfe-pricing component (pricing.component.ts) carries NO data-testids
 *      (grep: zero testId / data-testid) and exposes NO "apply price" control — it
 *      has a "Calculate" mee-button (no testid) and renders a read-only P&L
 *      breakdown. There is no apply-price button to click, and no LIVE-VERIFIED
 *      selector for the calculate button or the result, so neither "calc" nor
 *      "apply" can be driven from the UI.
 *   2. The export DOWNLOAD leg is GATED on W3-E2-3 / the mfe-export productId fix,
 *      which is NOT on develop (export.component.ts onGenerate() still hardcodes
 *      productId='current-product-id' — verified on develop @ a94e013).
 *
 * The backend price-calc → apply → export round-trip IS covered at the integration
 * layer (W3-BE-17, integration/test_price_export_roundtrip.py).
 *
 * Un-fixme condition: when (a) mfe-pricing gains data-testids on the calculate
 *   control + the P&L result + an apply-price control, all LIVE-VERIFIED in
 *   selector_registry.md, AND (b) the export download leg is un-fixme'd (W3-E2-3).
 *   The pricing testids + apply control are a frontend-lead request via the QA
 *   coordinator memo (E2E does NOT add data-testids or feature controls itself).
 */
import { authedTest as test } from '../fixtures/auth';

test.describe('W3-E2-6 Price-calc → apply → export chain', () => {
  test.fixme(
    'calculating then applying a price is reflected and the export page is reachable',
    async () => {
      // BLOCKED: mfe-pricing has no data-testids + no apply-price control
      // (develop @ a94e013, verified live), and the export download leg is gated on
      // W3-E2-3 (the mfe-export productId fix is not yet on develop). Backend
      // round-trip is covered by W3-BE-17. Un-fixme when pricing gains LIVE-VERIFIED
      // testids + an apply control AND W3-E2-3 is un-fixme'd.
    },
  );
});
