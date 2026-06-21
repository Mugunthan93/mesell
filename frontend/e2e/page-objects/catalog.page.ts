/**
 * CatalogPage — page object for the catalog remote (mfe-catalog).
 *
 * Routes (mounted under the shell):
 *   catalogs            → list
 *   catalogs/new        → smart category picker (the "create" entry point)
 *   catalogs/:id/edit   → fast catalog form
 *   catalogs/:id/images → image upload + precheck
 *   catalogs/live       → live listings
 *
 * Drives catalog-creation, category-picker, and image-precheck.
 *
 * Selectors + interaction patterns are LIVE-VERIFIED (QA Wave 1) — see
 * selector_registry.md. KEY: mee-button testids sit on <p-button> (click the
 * inner <button>); mee-textarea testid is the <textarea> itself.
 */
import type { Page, Locator } from '@playwright/test';

export class CatalogPage {
  constructor(private readonly page: Page) {}

  // ── Smart category picker (/catalogs/new) ──
  /** mee-textarea — testid IS the <textarea>; fill directly. */
  get categoryDescription(): Locator {
    return this.page.getByTestId('smart-picker-description');
  }
  /** The top-3 category suggestion cards. */
  get categorySuggestions(): Locator {
    return this.page.getByTestId('category-suggestion');
  }
  /** "Use this category" buttons (mee-button → inner <button>). */
  get categorySelectButtons(): Locator {
    return this.page.getByTestId('category-suggestion-select').locator('button');
  }

  // ── Catalog form (/catalogs/:id/edit) ──
  /** mee-button → inner <button>. */
  get formNext(): Locator {
    return this.page.getByTestId('catalog-form-next').locator('button');
  }
  /** Autosave status (renders during/after an autosave). */
  get saveStatus(): Locator {
    return this.page.getByTestId('catalog-save-status');
  }

  // ── Image upload + precheck (/catalogs/:id/images) ──
  /** The PrimeNG advanced uploader's native file input (the PRIMARY upload). */
  get primaryFileInput(): Locator {
    return this.page.locator('p-fileupload input[type=file]').first();
  }
  /** The PrimeNG advanced uploader's "Upload" button (customUpload trigger). */
  get uploadButton(): Locator {
    return this.page.locator('p-fileupload').getByRole('button', { name: /^upload$/i });
  }
  /** The hidden per-slot re-upload input (only for re-upload after a slot exists). */
  get reuploadFileInput(): Locator {
    return this.page.getByTestId('image-file-input');
  }
  /** The quality-gate result card (one per uploaded slot). */
  get precheckCards(): Locator {
    return this.page.getByTestId('precheck-card');
  }
  /** The precheck status badge ("ready" / "failed" / "pending"). */
  get precheckStatuses(): Locator {
    return this.page.getByTestId('precheck-status');
  }

  // ── Navigation helpers ──
  async gotoList(): Promise<void> {
    await this.page.goto('/catalogs');
  }
  async gotoNew(): Promise<void> {
    await this.page.goto('/catalogs/new');
  }
  async gotoEdit(productId: string): Promise<void> {
    await this.page.goto(`/catalogs/${productId}/edit`);
  }
  async gotoImages(productId: string): Promise<void> {
    await this.page.goto(`/catalogs/${productId}/images`);
  }
  async gotoLive(): Promise<void> {
    await this.page.goto('/catalogs/live');
  }

  /**
   * Create a product through the smart picker: type a description, wait for the
   * AI suggestions (Gemini-backed — generous timeout), pick the first, and return
   * the REAL product UUID parsed from the resulting /catalogs/:id/edit URL.
   */
  async createProductViaPicker(
    description = 'Blue cotton kurti with mirror work for women size M to XXL',
  ): Promise<string> {
    await this.gotoNew();
    await this.categoryDescription.waitFor({ state: 'visible' });
    await this.categoryDescription.fill(description);
    // AI suggestion latency — wait up to the suite expect timeout for the first card.
    await this.categorySelectButtons.first().waitFor({ state: 'visible', timeout: 30_000 });
    await this.categorySelectButtons.first().click();
    await this.page.waitForURL(/\/catalogs\/[0-9a-f-]+\/edit/);
    const match = this.page.url().match(/\/catalogs\/([0-9a-f-]+)\/edit/);
    if (!match) throw new Error(`Could not parse productId from URL: ${this.page.url()}`);
    return match[1];
  }
}
