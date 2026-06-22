/**
 * Flow: Catalog creation (V1 Feature 3). EXTENDED for QA Wave C (qa-catalog).
 *
 * Taxonomy (design §5.3): Shell → catalog remote → create a product → the saved
 * product appears in the dashboard list.
 *
 * Reality: the "wizard" entry point is the Smart Category Picker (/catalogs/new).
 * Typing a description → picking a suggested category POSTs a new product and
 * routes to /catalogs/:id/edit (a REAL product UUID). The created product then
 * shows up in the dashboard product list.
 *
 * Pre-authenticated via the worker-scoped authed-context fixture (rotation-safe).
 * Ports from playwright.config.ts; NO token in localStorage.
 *
 * Wave-C cases (design §3.D):
 *   CAT-E2E-02  create → dashboard row  (existing, kept)
 *   CAT-E2E-05  autosave persist then reload
 *   CAT-E2E-06  AI-fill applies on the edit form
 */
import { authedTest as test, expect } from '../fixtures/auth';
import { CatalogPage } from '../page-objects/catalog.page';
import { DashboardPage } from '../page-objects/dashboard.page';

test.describe('Catalog creation', () => {
  // ── CAT-E2E-02 (existing — kept) ────────────────────────────────────────────
  test('creating a product via the smart picker shows it in the dashboard list', async ({ authedPage }) => {
    const catalog = new CatalogPage(authedPage);
    const dashboard = new DashboardPage(authedPage);

    // Shell → catalog remote (smart picker) → pick a category → real product created.
    const productId = await catalog.createProductViaPicker();
    expect(productId).toMatch(/^[0-9a-f-]{36}$/);

    // Visible outcome 1: we are on the catalog edit form for the new product.
    await expect(authedPage).toHaveURL(new RegExp(`/catalogs/${productId}/edit`));
    await expect(catalog.formNext).toBeVisible();

    // Visible outcome 2: the saved product appears in the dashboard list.
    await dashboard.goto();
    await expect(dashboard.heading).toBeVisible();
    await expect(dashboard.productRows.first()).toBeVisible();
  });

  // ── CAT-E2E-05 — autosave persist then reload ───────────────────────────────
  // Create a product, type into the first schema-driven text field, wait for the
  // autosave status to settle to "Saved", reload, and assert the typed value is
  // retained (the draft autosave round-trips through PATCH /products + reload).
  //
  // The form fields are /schema-driven (the labels depend on the picked category),
  // so this targets the FIRST mee-input text field generically — it does not hardcode
  // a field name. The `catalog-save-status` testid is registry-LIVE-VERIFIED.
  test('CAT-E2E-05: autosave persists a field value across a reload', async ({ authedPage }) => {
    const catalog = new CatalogPage(authedPage);

    const productId = await catalog.createProductViaPicker();
    await expect(authedPage).toHaveURL(new RegExp(`/catalogs/${productId}/edit`));
    await expect(catalog.formNext).toBeVisible();

    // First fillable text input on the schema-driven form (NOT a number field, to
    // keep the round-trip value-stable). mee-input testid is the inner <input>.
    const firstText = authedPage.locator('mee-input input[type="text"]').first();
    await firstText.waitFor({ state: 'visible', timeout: 15_000 });
    const value = `QA E2E ${Date.now()}`;
    await firstText.fill(value);
    // Blur to trigger the field's (blur)=onFieldBlur autosave.
    await firstText.blur();

    // Autosave indicator settles to "Saved" (registry-verified testid).
    await expect(catalog.saveStatus).toHaveText(/saved/i, { timeout: 15_000 });

    // Reload — the draft must rehydrate the typed value.
    await authedPage.reload();
    const firstTextAfter = authedPage.locator('mee-input input[type="text"]').first();
    await firstTextAfter.waitFor({ state: 'visible', timeout: 15_000 });
    await expect(firstTextAfter).toHaveValue(value);
  });

  // ── CAT-E2E-06 — AI-fill applies on the edit form ───────────────────────────
  // Click the AI auto-fill button (registry-verified `catalog-ai-fill`) and assert a
  // target field gains a value (a visible value change). FEATURE_AI_AUTOFILL_ENABLED
  // is on in dev. Asserts a VISIBLE outcome: more inputs are populated after the
  // autofill round-trip than before.
  test('CAT-E2E-06: AI auto-fill populates form fields', async ({ authedPage }) => {
    const catalog = new CatalogPage(authedPage);

    const productId = await catalog.createProductViaPicker();
    await expect(authedPage).toHaveURL(new RegExp(`/catalogs/${productId}/edit`));
    await expect(catalog.aiFill).toBeVisible();

    // Snapshot the filled-field count before autofill.
    const inputs = authedPage.locator('mee-input input, mee-textarea textarea');
    const filledBefore = await inputs.evaluateAll(
      (els) => els.filter((e) => (e as HTMLInputElement).value.trim().length > 0).length,
    );

    await catalog.aiFill.click();

    // Visible outcome: after the autofill round-trip (Gemini-backed — generous wait),
    // MORE fields are populated than before. Poll until the count rises.
    await expect
      .poll(
        async () =>
          inputs.evaluateAll(
            (els) => els.filter((e) => (e as HTMLInputElement).value.trim().length > 0).length,
          ),
        { timeout: 30_000 },
      )
      .toBeGreaterThan(filledBefore);
  });
});
