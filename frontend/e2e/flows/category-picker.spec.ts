/**
 * Flow: Category smart-picker.
 *
 * Taxonomy (design §5.3): Description typed → top-3 suggestions appear → selecting
 * one advances the flow (creates the product and routes to its edit form).
 *
 * The suggest call is Gemini-backed (POST /categories/suggest) and takes a few
 * seconds; the page object waits generously for the first suggestion to render.
 *
 * Pre-authenticated via the worker-scoped authed-context fixture.
 * Asserted VISIBLE outcomes: suggestion cards are visible, and selecting one
 * navigates to the catalog edit form (the form field/route updates).
 */
import { authedTest as test, expect } from '../fixtures/auth';
import { CatalogPage } from '../page-objects/catalog.page';

test.describe('Category smart-picker', () => {
  test('typing a description shows suggestions and selecting one advances the flow', async ({ authedPage }) => {
    const catalog = new CatalogPage(authedPage);

    await catalog.gotoNew();
    await expect(catalog.categoryDescription).toBeVisible();

    // Type a clear product description (mee-textarea → fill directly).
    await catalog.categoryDescription.fill('Blue cotton kurti with mirror work for women size M to XXL');

    // Visible outcome 1: top suggestion cards appear (AI latency — generous wait).
    await expect(catalog.categorySuggestions.first()).toBeVisible({ timeout: 30_000 });
    expect(await catalog.categorySuggestions.count()).toBeGreaterThan(0);

    // Visible outcome 2: selecting a suggestion advances to the catalog edit form
    // for a freshly-created product (the selection updates the flow/route).
    await catalog.categorySelectButtons.first().click();
    await expect(authedPage).toHaveURL(/\/catalogs\/[0-9a-f-]+\/edit/);
    await expect(catalog.formNext).toBeVisible();
  });
});
