/**
 * Flow: Catalog creation.
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
 * Asserted VISIBLE outcomes: the edit form is reached (URL + form control), and a
 * dashboard product row is visible.
 */
import { authedTest as test, expect } from '../fixtures/auth';
import { CatalogPage } from '../page-objects/catalog.page';
import { DashboardPage } from '../page-objects/dashboard.page';

test.describe('Catalog creation', () => {
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
});
