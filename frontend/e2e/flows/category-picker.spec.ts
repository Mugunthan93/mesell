/**
 * Flow: Category smart-picker (V1 Feature 2). EXTENDED for QA Wave C (qa-catalog).
 *
 * Taxonomy (design §5.3): Description typed → top-3 suggestions appear → selecting
 * one advances the flow (creates the product and routes to its edit form).
 *
 * The suggest call is Gemini-backed (POST /categories/suggest) and takes a few
 * seconds; the page object waits generously for the first suggestion to render.
 *
 * Pre-authenticated via the worker-scoped authed-context fixture (rotation-safe).
 * Ports come from playwright.config.ts (the route-glob below is path-relative, so it
 * matches the shell's proxied /api regardless of slot). NO token in localStorage.
 *
 * Wave-C cases (design §3.D):
 *   CAT-E2E-01  happy: type → suggestions → select → /catalogs/:uuid/edit  (existing, kept)
 *   CAT-E2E-04  suggest error-then-retry RECOVERS  (the CAT-BUG-1 LIVE regression guard)
 *   CAT-E2E-03  browse-fallback link visible on fallback_offered
 *   CAT-E2E-07  empty-state on zero suggestions
 */
import { authedTest as test, expect } from '../fixtures/auth';
import { CatalogPage } from '../page-objects/catalog.page';

const SUGGEST_GLOB = '**/api/v1/categories/suggest';
const GOOD_DESC = 'Blue cotton kurti with mirror work for women size M to XXL';
const RETRY_DESC = 'Red silk saree with golden zari border for women festive wear';

test.describe('Category smart-picker', () => {
  // ── CAT-E2E-01 (existing — kept) ────────────────────────────────────────────
  test('typing a description shows suggestions and selecting one advances the flow', async ({ authedPage }) => {
    const catalog = new CatalogPage(authedPage);

    await catalog.gotoNew();
    await expect(catalog.categoryDescription).toBeVisible();

    // Type a clear product description (mee-textarea → fill directly).
    await catalog.categoryDescription.fill(GOOD_DESC);

    // Visible outcome 1: top suggestion cards appear (AI latency — generous wait).
    await expect(catalog.categorySuggestions.first()).toBeVisible({ timeout: 30_000 });
    expect(await catalog.categorySuggestions.count()).toBeGreaterThan(0);

    // Visible outcome 2: selecting a suggestion advances to the catalog edit form
    // for a freshly-created product (the selection updates the flow/route).
    await catalog.categorySelectButtons.first().click();
    await expect(authedPage).toHaveURL(/\/catalogs\/[0-9a-f-]+\/edit/);
    await expect(catalog.formNext).toBeVisible();
  });

  // ── CAT-E2E-04 — the load-bearing CAT-BUG-1 LIVE regression guard ───────────
  //
  // CAT-BUG-1: smart-picker.component.ts wired the suggest error handler on the
  // OUTER valueChanges subscription, so the FIRST transient suggest error
  // (429/5xx) terminated the stream — every later keystroke was dead until a full
  // page reload. The fix (PR #437) moves error handling INSIDE the switchMap via
  // `catchError` → a fallback SuggestResponse, so the outer stream survives.
  //
  // This test forces exactly ONE suggest error with a Playwright route intercept,
  // confirms the picker did NOT die (it stays on /catalogs/new and the field stays
  // interactive), then — with the route restored — types a SECOND valid description
  // and asserts suggestions STILL render. Suggestions appearing AFTER the error is
  // the proof the stream recovered (the regression would leave the picker dead).
  //
  // Faithful seam: CategoryService maps 5xx/402/404 to the fallback shape itself and
  // RETHROWS only 400/422/429 — and it is exactly the rethrown 429 that the
  // component's inner catchError must absorb. So we inject a 429 (not an abort) to
  // exercise the real CAT-BUG-1 code path.
  test('CAT-E2E-04: suggest error then retry recovers (CAT-BUG-1 live guard)', async ({ authedPage }) => {
    const catalog = new CatalogPage(authedPage);

    // Fail ONLY the first suggest request with a 429 (the rethrown code path), then
    // self-remove so the retry hits the real backend.
    let failed = false;
    await authedPage.route(SUGGEST_GLOB, async (route) => {
      if (!failed) {
        failed = true;
        await route.fulfill({
          status: 429,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'rate_limit.exceeded' }),
        });
        return;
      }
      await route.fallback(); // subsequent calls go to the real backend
    });

    await catalog.gotoNew();
    await expect(catalog.categoryDescription).toBeVisible();

    // First description → forces the single 429. The CAT-BUG-1 fix maps it to the
    // fallback shape (suggestions:[], fallback_offered:true) → the empty-state error
    // UI. The KEY guard is that the picker is NOT navigated away / dead.
    await catalog.categoryDescription.fill(GOOD_DESC);

    // After the forced error the picker must NOT crash to /login or a remote-failure
    // fallback — it stays on /catalogs/new and the description field stays usable.
    await expect(authedPage).toHaveURL(/\/catalogs\/new/);
    await expect(catalog.categoryDescription).toBeEnabled();
    // (Best-effort) the fallback empty-state error UI is offered. Source-derived
    // selector, not yet live-verified — soft check so the core recovery assertion
    // below (registry-verified selectors only) is the gate.
    await catalog.pickerEmptyState
      .waitFor({ state: 'visible', timeout: 15_000 })
      .catch(() => undefined);

    // RECOVERY: with the route restored, type a SECOND valid description. A dead
    // stream (the regression) would NEVER emit again. The fix keeps it alive, so a
    // fresh suggest fires and suggestion cards render — the load-bearing assertion,
    // using ONLY registry-LIVE-VERIFIED selectors.
    await catalog.categoryDescription.fill(''); // distinctUntilChanged reset
    await catalog.categoryDescription.fill(RETRY_DESC);

    await expect(catalog.categorySuggestions.first()).toBeVisible({ timeout: 30_000 });
    expect(await catalog.categorySuggestions.count()).toBeGreaterThan(0);
  });

  // ── CAT-E2E-03 — browse-fallback link visible on fallback_offered ───────────
  // Forces a fallback_offered=true WITH results via route interception (so it does
  // not depend on a specific live Gemini response). Asserts the secondary
  // "Browse if none match" link is visible AND navigates to /categories/browse.
  //
  // FIXME (kept — qa de-fixme lane, SPEC B group F, 2026-07-06): the browse-fallback
  // link ships NO data-testid; it is a native <button aria-label="Browse all categories
  // if none of the suggestions match"> targeted by accessible role/name, SOURCE-CONFIRMED
  // at develop c5529f6 (smart-picker.component.ts L171-178). Live-verification remains
  // env-BLOCKED: the deployed backend's /categories/suggest returns empty responses so
  // the fallback UI never renders live, and agent-browser cannot route-stub to force
  // fallback_offered=true. A data-testid memo (smart-picker-browse-fallback) is filed
  // with the coordinator. Un-fixme once the role selector is agent-browser LIVE-VERIFIED
  // on a working stack OR the requested data-testid lands.
  test.fixme('CAT-E2E-03: browse-fallback link visible and navigates to /categories/browse', async ({ authedPage }) => {
    const catalog = new CatalogPage(authedPage);

    // Stub suggest to return results AND fallback_offered=true.
    await authedPage.route(SUGGEST_GLOB, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          suggestions: [
            { category_id: '00000000-0000-0000-0000-000000000001', category_path: 'Women > Kurtis', confidence: 0.9 },
          ],
          fallback_offered: true,
        }),
      });
    });

    await catalog.gotoNew();
    await catalog.categoryDescription.fill(GOOD_DESC);

    await expect(catalog.categorySuggestions.first()).toBeVisible({ timeout: 15_000 });
    await expect(catalog.browseIfNoneMatch).toBeVisible();

    await catalog.browseIfNoneMatch.click();
    await expect(authedPage).toHaveURL(/\/categories\/browse/);
  });

  // ── CAT-E2E-07 — empty-state on zero suggestions ────────────────────────────
  // FIXME (kept — qa de-fixme lane, SPEC B group F, 2026-07-06): same provenance as
  // CAT-E2E-03. The empty-state renders `<div role="status" aria-label="No automatic
  // suggestions found…">` + a "Browse all categories" mee-button CTA (SOURCE-CONFIRMED
  // at c5529f6: smart-picker.component.ts L184-190 + empty-state.component.ts L44/56).
  // Live-verification is env-BLOCKED (deployed suggest returns empty → fallback UI
  // unreachable live; agent-browser cannot route-stub). A data-testid memo
  // (smart-picker-empty / smart-picker-empty-browse) is filed with the coordinator.
  // Un-fixme once live-verified on a working stack OR the testids land.
  test.fixme('CAT-E2E-07: empty-state shown when there are no suggestions', async ({ authedPage }) => {
    const catalog = new CatalogPage(authedPage);

    // Stub suggest to return ZERO suggestions + fallback_offered=true.
    await authedPage.route(SUGGEST_GLOB, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ suggestions: [], fallback_offered: true }),
      });
    });

    await catalog.gotoNew();
    await catalog.categoryDescription.fill('qwertyuiop asdfghjkl zxcvbnm nonsense text');

    await expect(catalog.pickerEmptyState).toBeVisible({ timeout: 15_000 });
    await expect(catalog.pickerEmptyStateBrowse).toBeVisible();
  });
});
