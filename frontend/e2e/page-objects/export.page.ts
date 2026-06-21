/**
 * ExportPage — page object for the export remote (mfe-export, :4202).
 *
 * Route (mounted under the shell): catalogs/:id/export.
 * Drives the XLSX export-download flow: click export → assert a file download
 * event fires → assert the downloaded file is non-empty.
 *
 * Selectors are PROVISIONAL (see ShellPage note). The download trigger is the
 * key selector; the asserted outcome is a Playwright `download` event, not a
 * network call (per the e2e taxonomy: assert a VISIBLE/observable outcome).
 */
import type { Page, Locator } from '@playwright/test';

export class ExportPage {
  constructor(private readonly page: Page) {}

  get exportButton(): Locator {
    return this.page.getByTestId('export-download-button');
  }

  /** Optional status/toast surfaced while the export is built. */
  get exportStatus(): Locator {
    return this.page.getByTestId('export-status');
  }

  async goto(catalogId: string): Promise<void> {
    await this.page.goto(`/catalogs/${catalogId}/export`);
  }
}
