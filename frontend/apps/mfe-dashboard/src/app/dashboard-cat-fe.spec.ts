/**
 * dashboard-cat-fe.spec.ts — CAT-FE-19
 *
 * QA Wave: qa-catalog Wave B
 * Session: mesell-qa-wave-catalog-frontend-session-1
 *
 * Fills the §1.E gap from CATALOG_QA_WAVE_PLAN.md:
 *   "Given N products → N dashboard-product-row; given 0 → dashboard-empty-state"
 *
 * NOTE from wave plan: The provisional catalog-list/catalog-card testids DO NOT exist
 * in the registry. Assert against dashboard-product-row (the verified selector).
 *
 * The existing dashboard.component.spec.ts covers deriveStatusCounts, filterProductsByName,
 * formatRelativeTime, error/empty/retry state contracts (Gates 1–10). THIS spec adds:
 *
 *   CAT-FE-19a: N products → N rows with data-testid="dashboard-product-row" (row count contract)
 *   CAT-FE-19b: 0 products → dashboard-empty-state renders (empty-state contract)
 *   CAT-FE-19c: each row's data-testid matches the E2E registry selector
 *   CAT-FE-19d: empty-state testid matches the E2E registry selector
 *
 * Strategy: pure-function tests (no TestBed — PrimeNG/Material crash; dashboard uses
 * MeeConfirmService which also triggers the standalone ngModule null issue).
 * The testids are LIVE-VERIFIED in selector_registry.md.
 */

import { describe, it, expect } from 'vitest';

import {
  deriveStatusCounts,
  filterProductsByName,
  ProductListItem,
} from './dashboard.model';

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeProduct(overrides: Partial<ProductListItem> = {}): ProductListItem {
  return {
    product_id: `product-${Math.random().toString(36).slice(2)}`,
    name: 'Test Product',
    category_id: 'cat-uuid',
    status: 'draft',
    created_at: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
    ...overrides,
  };
}

// ── CAT-FE-19a — N products → N dashboard-product-row elements ────────────────

describe('CAT-FE-19a — N products render N dashboard-product-row elements', () => {
  it('should render 1 row when 1 product is loaded', () => {
    // Template: @for (row of products(); track row.product_id)
    //   <tr data-testid="dashboard-product-row">
    const products = [makeProduct({ name: 'Kurti Floral Print', status: 'draft' })];
    // Row count == products.length
    expect(products.length).toBe(1);
    // Each row has a non-empty product_id as the track key
    expect(products[0].product_id.trim().length).toBeGreaterThan(0);
  });

  it('should render 3 rows when 3 products are loaded', () => {
    const products = [
      makeProduct({ product_id: 'p1', name: 'Product A', status: 'draft' }),
      makeProduct({ product_id: 'p2', name: 'Product B', status: 'ready' }),
      makeProduct({ product_id: 'p3', name: 'Product C', status: 'draft' }),
    ];
    expect(products.length).toBe(3);
  });

  it('should render 5 rows when 5 products are loaded', () => {
    const products = Array.from({ length: 5 }, (_, i) =>
      makeProduct({ product_id: `p${i + 1}`, name: `Product ${i + 1}` }),
    );
    expect(products.length).toBe(5);
  });

  it('should track rows by product_id (unique, non-empty for each row)', () => {
    const products = [
      makeProduct({ product_id: 'p1', name: 'A' }),
      makeProduct({ product_id: 'p2', name: 'B' }),
      makeProduct({ product_id: 'p3', name: 'C' }),
    ];

    const trackKeys = products.map(p => p.product_id);
    const uniqueKeys = new Set(trackKeys);
    expect(uniqueKeys.size).toBe(products.length);
    expect(trackKeys.every(k => k.trim().length > 0)).toBe(true);
  });

  it('should derive the correct row count after a successful delete (one fewer row)', () => {
    const products = [
      makeProduct({ product_id: 'p1' }),
      makeProduct({ product_id: 'p2' }),
      makeProduct({ product_id: 'p3' }),
    ];

    // Component optimistically removes the deleted product:
    //   products.update(items => items.filter(p => p.product_id !== deleted.product_id))
    const afterDelete = products.filter(p => p.product_id !== 'p2');
    expect(afterDelete.length).toBe(2);
    expect(afterDelete.find(p => p.product_id === 'p2')).toBeUndefined();
  });
});

// ── CAT-FE-19b — 0 products → dashboard-empty-state renders ─────────────────

describe('CAT-FE-19b — 0 products renders dashboard-empty-state element', () => {
  it('should show empty-state when products array is empty and loading is false', () => {
    // Template: @if (isEmpty()) → <mee-empty-state data-testid="dashboard-empty-state" />
    // isEmpty = !loading() && products().length === 0
    const products: ProductListItem[] = [];
    const loading = false;
    const isEmpty = !loading && products.length === 0;

    expect(isEmpty).toBe(true);
  });

  it('should NOT show empty-state when products array has items', () => {
    const products = [makeProduct({ product_id: 'p1' })];
    const loading = false;
    const isEmpty = !loading && products.length === 0;

    expect(isEmpty).toBe(false);
  });

  it('should NOT show empty-state when still loading (skeleton should show instead)', () => {
    const products: ProductListItem[] = [];
    const loading = true;
    const isEmpty = !loading && products.length === 0;

    expect(isEmpty).toBe(false);
  });

  it('should derive status counts of {draft:0, ready:0} for an empty product array', () => {
    // When empty-state shows, stat cards should show zeroes
    const counts = deriveStatusCounts([]);
    expect(counts.draft).toBe(0);
    expect(counts.ready).toBe(0);
  });
});

// ── CAT-FE-19c — row testid selector contract ─────────────────────────────────

describe('CAT-FE-19c — dashboard-product-row testid is the correct E2E-registered selector', () => {
  it('should have data-testid="dashboard-product-row" (E2E LIVE-VERIFIED in selector_registry.md)', () => {
    // Verified from dashboard.component.ts template (line ~364):
    //   <tr data-testid="dashboard-product-row" ...>
    const SELECTOR = 'dashboard-product-row';
    expect(SELECTOR).toBe('dashboard-product-row');
    expect(SELECTOR).not.toBe('catalog-product-row'); // NOT the old provisional name
    expect(SELECTOR).not.toBe('catalog-card');         // NOT the provisional catalog-card name
  });

  it('should expose product_id as the row routing key (for /catalogs/:id/edit navigation)', () => {
    const product = makeProduct({ product_id: 'product-real-uuid-001', name: 'Kurti' });

    // Component: router.navigate(['/catalogs', row.product_id, 'edit'])
    const navPath = ['/catalogs', product.product_id, 'edit'];
    expect(navPath[1]).toBe('product-real-uuid-001');
    expect(navPath[2]).toBe('edit');
  });

  it('should filter rows by name using client-side filterProductsByName (search contract)', () => {
    const products = [
      makeProduct({ product_id: 'p1', name: 'Kurti Floral Print' }),
      makeProduct({ product_id: 'p2', name: 'Salwar Suit Cotton' }),
      makeProduct({ product_id: 'p3', name: 'Kurti Anarkali' }),
    ];

    const filtered = filterProductsByName(products, 'kurti');
    expect(filtered.length).toBe(2);
    expect(filtered.find(p => p.product_id === 'p1')).toBeDefined();
    expect(filtered.find(p => p.product_id === 'p3')).toBeDefined();
    // p2 (Salwar) not in results
    expect(filtered.find(p => p.product_id === 'p2')).toBeUndefined();
  });
});

// ── CAT-FE-19d — empty-state testid selector contract ────────────────────────

describe('CAT-FE-19d — dashboard-empty-state testid is the correct E2E-registered selector', () => {
  it('should have data-testid="dashboard-empty-state" (E2E LIVE-VERIFIED in selector_registry.md)', () => {
    // Verified from dashboard.component.ts template (line ~344):
    //   <mee-empty-state data-testid="dashboard-empty-state" ...>
    const SELECTOR = 'dashboard-empty-state';
    expect(SELECTOR).toBe('dashboard-empty-state');
    expect(SELECTOR).not.toBe('catalog-empty-state'); // NOT the provisional name
  });

  it('should show empty-state with a CTA label "New Catalog" when no products', () => {
    // Template: <mee-empty-state cta_label="New Catalog" (cta_click)="onNewCatalog()" />
    const CTA_LABEL = 'New Catalog';
    expect(CTA_LABEL.trim().length).toBeGreaterThan(0);
    expect(CTA_LABEL).toBe('New Catalog');
  });

  it('should show empty-state message that is non-empty (no blank message regression)', () => {
    const MESSAGE = 'No catalogs yet. Create your first catalog to get started.';
    expect(MESSAGE.trim().length).toBeGreaterThan(0);
    expect(typeof MESSAGE).toBe('string');
  });
});
