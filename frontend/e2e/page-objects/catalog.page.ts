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

  // ── Smart-picker browse-fallback + empty-state (CAT-E2E-03 / 04 / 07) ──
  // SELECTOR PROVENANCE: these two surfaces ship NO data-testid in the
  // integration-tip source (smart-picker.component.ts + the EmptyState composite).
  // They are targeted by accessible role/name, DERIVED FROM SOURCE on
  // feature/qa-catalog/integration @ 3476b0e — NOT yet agent-browser LIVE-VERIFIED
  // (the Wave-C live exploration was environment-blocked; see federation_quirks.md
  // "Wave-C environment blocker"). The flows that rely on these are test.fixme until
  // live-verified, and a data-testid is requested via the coordinator memo.

  /**
   * Secondary "Browse if none match" link, shown UNDER the suggestion cards when
   * fallback_offered=true AND there are results. Source: a bare
   * <button class="mee-browse-link"> with aria-label
   * "Browse all categories if none of the suggestions match".
   */
  get browseIfNoneMatch(): Locator {
    return this.page.getByRole('button', {
      name: /browse all categories if none of the suggestions match/i,
    });
  }
  /**
   * The picker empty-state shown when fallback_offered=true AND zero suggestions.
   * Source: <mee-empty-state role="status"> whose aria-label is the message
   * "No automatic suggestions found. Browse the full category list manually."
   */
  get pickerEmptyState(): Locator {
    return this.page.getByRole('status', { name: /no automatic suggestions found/i });
  }
  /** The empty-state's "Browse all categories" CTA (mee-empty-state cta_label). */
  get pickerEmptyStateBrowse(): Locator {
    return this.page.getByRole('button', { name: /^browse all categories$/i });
  }

  // ── Catalog form (/catalogs/:id/edit) ──
  /** mee-button → inner <button>. */
  get formNext(): Locator {
    return this.page.getByTestId('catalog-form-next').locator('button');
  }
  /** AI auto-fill button (mee-button → inner <button>). */
  get aiFill(): Locator {
    return this.page.getByTestId('catalog-ai-fill').locator('button');
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

  // ── Catalog list rows + inline delete (/catalogs) — #425 testids ──
  // SELECTOR PROVENANCE: literal data-testids added by PR #425 (77b5db0) in
  // catalog-list.component.ts. `catalog-empty` was LIVE-VERIFIED on the deployed
  // build (2026-07-06). The per-row controls (`catalog-row` + the edit/delete/
  // confirm/cancel <span> wrappers around mee-buttons) are SOURCE-GROUND-TRUTHED at
  // develop c5529f6 — their live-verification was env-blocked (the deployed backend's
  // product-creation is down: Gemini suggest returns empty + category browse is
  // unseeded, so no row could be rendered live). They are exercised live when the
  // suite runs on a working stack. The delete controls are `<span data-testid>`
  // wrapping a `<mee-button>` (whose (clicked) fires from the inner <button>), so
  // click `.locator('button')` inside the span — same pattern as the other mee-buttons.

  /** All catalog rows (one `<div data-testid="catalog-row" [data-product-id]>` per product). */
  get catalogRows(): Locator {
    return this.page.getByTestId('catalog-row');
  }
  /** The empty-state shown when there are no catalogs (LIVE-VERIFIED on deployed). */
  get catalogEmpty(): Locator {
    return this.page.getByTestId('catalog-empty');
  }
  /** The row for a specific product, anchored by its data-product-id (unique). */
  rowFor(productId: string): Locator {
    return this.page.locator(`[data-testid="catalog-row"][data-product-id="${productId}"]`);
  }
  /** Delete button within a row (mee-button → inner <button>). Opens the inline confirm. */
  deleteButtonIn(row: Locator): Locator {
    return row.getByTestId('catalog-delete-btn').locator('button');
  }
  /** "Confirm delete" button in a row's inline confirm affordance (mee-button → <button>). */
  deleteConfirmIn(row: Locator): Locator {
    return row.getByTestId('catalog-delete-confirm').locator('button');
  }
  /** "Cancel" button in a row's inline confirm affordance (mee-button → <button>). */
  deleteCancelIn(row: Locator): Locator {
    return row.getByTestId('catalog-delete-cancel').locator('button');
  }
  /** Edit button within a row (mee-button → inner <button>). */
  editButtonIn(row: Locator): Locator {
    return row.getByTestId('catalog-edit-btn').locator('button');
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
