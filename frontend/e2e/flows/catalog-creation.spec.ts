/**
 * Flow: Catalog creation wizard.
 *
 * Taxonomy (design §5.3): Shell → catalog remote → all wizard steps complete →
 * saved catalog appears in dashboard list.
 *
 * STUB — fleshed out by the QA wave. Pre-authenticated via storageState (the
 * default project setup). The exploration phase must pin the wizard step controls
 * and the saved-catalog list item before this is completed.
 */
import { test, expect } from '@playwright/test';
import { CatalogPage } from '../page-objects/catalog.page';
import { DashboardPage } from '../page-objects/dashboard.page';

test.describe('Catalog creation', () => {
  test.fixme('walks the wizard and the saved catalog shows in the dashboard list', async ({ page }) => {
    const catalog = new CatalogPage(page);
    const dashboard = new DashboardPage(page);

    // Shell → catalog remote (new wizard).
    await catalog.gotoNew();

    // Walk every wizard step. (Exploration phase fills in per-step field entry.)
    await catalog.wizardNext.click();
    // ... category pick, attributes, images steps ...
    await catalog.saveDraft.click();

    // Asserted outcome: the saved catalog appears in the dashboard list.
    await dashboard.gotoCatalogs();
    await expect(dashboard.catalogList).toBeVisible();
    await expect(dashboard.catalogCardByName('E2E Test Catalog')).toBeVisible();
  });
});
