/**
 * ExportPage — page object for the export remote (mfe-export).
 *
 * Route (mounted under the shell): catalogs/:id/export.
 *
 * Selectors LIVE-VERIFIED (QA Wave 1) — see selector_registry.md.
 *
 * PRODUCT BUG (filed): export.component.ts hardcodes productId='current-product-id'
 * in onGenerate() instead of reading the route param, so clicking the trigger POSTs
 * to a non-existent product and the `ready` state + download link are unreachable
 * through the UI. The download assertion is therefore test.fixme in export.spec.ts.
 */
import type { Page, Locator } from '@playwright/test';

export class ExportPage {
  constructor(private readonly page: Page) {}

  /** "Generate Export" button (mee-button → inner <button>). */
  get generateButton(): Locator {
    return this.page.getByTestId('export-trigger').locator('button');
  }

  /** The download link (<a download>), ONLY rendered in the `ready` state. */
  get downloadLink(): Locator {
    return this.page.getByTestId('export-download');
  }

  async goto(productId: string): Promise<void> {
    await this.page.goto(`/catalogs/${productId}/export`);
  }
}
