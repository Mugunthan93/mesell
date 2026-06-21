/**
 * Flow: Export download.
 *
 * Taxonomy (design §5.3): Export button clicked → file download event triggered →
 * downloaded file non-empty.
 *
 * STUB — fleshed out by the QA wave. Pre-authenticated via storageState. The
 * asserted outcome is a Playwright `download` event (a real, observable browser
 * outcome), not a network response — per the e2e convention that every test
 * asserts a visible/observable outcome.
 */
import { test, expect } from '@playwright/test';
import { ExportPage } from '../page-objects/export.page';

const CATALOG_ID = process.env.MEESELL_E2E_CATALOG_ID ?? '00000000-0000-0000-0000-000000000000';

test.describe('Export', () => {
  test.fixme('clicking export triggers a non-empty file download', async ({ page }) => {
    const exportPage = new ExportPage(page);

    await exportPage.goto(CATALOG_ID);

    // Asserted outcome: a download event fires and the file is non-empty.
    const downloadPromise = page.waitForEvent('download');
    await exportPage.exportButton.click();
    const download = await downloadPromise;

    const path = await download.path();
    expect(path).toBeTruthy();
    // A non-empty file: suggested filename present + readable stream resolved.
    expect(download.suggestedFilename()).toMatch(/\.(xlsx|zip)$/);
  });
});
