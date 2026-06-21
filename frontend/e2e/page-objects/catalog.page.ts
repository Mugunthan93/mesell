/**
 * CatalogPage — page object for the catalog remote (mfe-catalog, :4205).
 *
 * Routes owned by this remote (mounted under the shell):
 *   catalogs            → list
 *   catalogs/new        → smart-picker + fast catalog wizard
 *   catalogs/:id/edit   → edit
 *   catalogs/:id/images → image upload + precheck
 *   catalogs/live       → live preview
 *
 * Drives the catalog-creation, image-precheck, and category-smart-picker flows.
 *
 * Selectors are PROVISIONAL (see ShellPage note). The wizard step controls and
 * the precheck result card are the highest-value selectors for the exploration
 * phase to pin first.
 */
import type { Page, Locator } from '@playwright/test';

export class CatalogPage {
  constructor(private readonly page: Page) {}

  // ── Wizard controls ──
  get wizardNext(): Locator {
    return this.page.getByTestId('wizard-next');
  }
  get wizardBack(): Locator {
    return this.page.getByTestId('wizard-back');
  }
  get saveDraft(): Locator {
    return this.page.getByTestId('save-draft');
  }

  // ── Smart category picker ──
  get categorySearch(): Locator {
    return this.page.getByTestId('category-search');
  }
  /** The top-3 category suggestion list returned by the smart picker. */
  get categorySuggestions(): Locator {
    return this.page.getByTestId('category-suggestion');
  }

  // ── Image upload + precheck ──
  get imageFileInput(): Locator {
    return this.page.getByTestId('image-file-input');
  }
  /** The quality-gate result card (carries the numeric precheck score). */
  get precheckResultCard(): Locator {
    return this.page.getByTestId('precheck-result-card');
  }
  get precheckScore(): Locator {
    return this.page.getByTestId('precheck-score');
  }

  // ── Navigation helpers ──
  async gotoList(): Promise<void> {
    await this.page.goto('/catalogs');
  }
  async gotoNew(): Promise<void> {
    await this.page.goto('/catalogs/new');
  }
  async gotoImages(catalogId: string): Promise<void> {
    await this.page.goto(`/catalogs/${catalogId}/images`);
  }
  async gotoLivePreview(): Promise<void> {
    await this.page.goto('/catalogs/live');
  }
}
