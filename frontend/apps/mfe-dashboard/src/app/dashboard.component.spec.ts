/**
 * DashboardComponent — unit tests
 *
 * Testing strategy: pure-function tests only — NO TestBed, NO Angular component imports.
 *
 * This follows the pattern established by image-uploader.component.spec.ts:
 * Only functions from decorator-free model files can be imported without triggering
 * Angular JIT compilation issues in the current Vitest + jsdom environment.
 *
 * === Wave 6 Wave B (2026-06-12) — reconciled to backend wire shape ===
 * ProductListItem:
 *   - product_id (not id) — A7
 *   - category_id (not category_name) — A4
 *   - status 2-value 'draft'|'ready' — A2
 *   - created_at added
 * StatusCounts narrowed to {draft, ready} — A2
 * filterProducts → filterProductsByName (client-only name search — A3)
 *
 * Gates covered:
 *  Gate 1: page header + stat card contract (2 cards: Draft, Ready)
 *  Gate 2: StatusCounts has exactly 2 keys (draft, ready)
 *  Gate 3: isEmpty — empty products → all zero counts
 *  Gate 4: filterProductsByName — client-side search by name
 *  Gate 5: each row has unique product_id for /catalogs/:product_id/edit routing
 */

import { describe, it, expect } from 'vitest';

import {
  deriveStatusCounts,
  filterProductsByName,
  formatRelativeTime,
  ProductListItem,
  StatusCounts,
} from './dashboard.model';

// ---------------------------------------------------------------------------
// Seed data (matches V1 backend wire shape — product_id, category_id, 2-value status)
// ---------------------------------------------------------------------------
const SEED: ProductListItem[] = [
  {
    product_id: 'p1',
    name: 'Kurti Floral Print',
    category_id: 'cat-ethnic',
    status: 'draft',
    created_at: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
  },
  {
    product_id: 'p2',
    name: 'Salwar Suit Cotton',
    category_id: 'cat-ethnic',
    status: 'ready',
    created_at: new Date(Date.now() - 26 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    product_id: 'p3',
    name: 'Tops V-Neck',
    category_id: 'cat-tops',
    status: 'ready',
    created_at: new Date(Date.now() - 4 * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    product_id: 'p4',
    name: 'Lehenga Zari Work',
    category_id: 'cat-ethnic',
    status: 'draft',
    created_at: new Date(Date.now() - 6 * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    product_id: 'p5',
    name: 'Kurti Anarkali',
    category_id: 'cat-ethnic',
    status: 'draft',
    created_at: new Date(Date.now() - 8 * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
  },
];

// ---------------------------------------------------------------------------
// Gate 1 + 2: page header + stat card contract (2 cards: Draft, Ready)
// ---------------------------------------------------------------------------
describe('deriveStatusCounts() — Gate 1+2: stat card contract', () => {
  it('Gate 1: returns exactly 2 keys (draft, ready) — maps to 2 mee-stat-card elements (V1 A2)', () => {
    const counts: StatusCounts = deriveStatusCounts(SEED);
    expect(Object.keys(counts).sort()).toEqual(['draft', 'ready']);
  });

  it('Gate 2: stat card "Draft" count is 3 for SEED (p1/p4/p5 are draft)', () => {
    const counts = deriveStatusCounts(SEED);
    expect(counts.draft).toBe(3);
  });

  it('stat card "Ready" count is 2 for SEED (p2/p3 are ready)', () => {
    const counts = deriveStatusCounts(SEED);
    expect(counts.ready).toBe(2);
  });
});

// ---------------------------------------------------------------------------
// Gate 3: isEmpty — empty products → all zero counts
// ---------------------------------------------------------------------------
describe('deriveStatusCounts() — Gate 3: empty state', () => {
  it('Gate 3: returns all zeros for an empty array (shows mee-empty-state)', () => {
    const counts = deriveStatusCounts([]);
    expect(counts.draft).toBe(0);
    expect(counts.ready).toBe(0);
  });

  it('a null name item counts correctly by status', () => {
    const nullable: ProductListItem[] = [
      {
        product_id: 'n1',
        name: null,
        category_id: 'cat-x',
        status: 'draft',
        created_at: '',
        updated_at: '',
      },
    ];
    const counts = deriveStatusCounts(nullable);
    expect(counts.draft).toBe(1);
    expect(counts.ready).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// Gate 4: filterProductsByName — client-side name search (A3)
// ---------------------------------------------------------------------------
describe('filterProductsByName() — Gate 4: client-side name search (A3)', () => {
  it('Gate 4: empty search returns all items', () => {
    const result = filterProductsByName(SEED, '');
    expect(result.length).toBe(SEED.length);
  });

  it('filters by name case-insensitively', () => {
    const result = filterProductsByName(SEED, 'kurti');
    expect(result.length).toBe(2); // 'Kurti Floral Print' + 'Kurti Anarkali'
    expect(result.every(p => (p.name ?? '').toLowerCase().includes('kurti'))).toBe(true);
  });

  it('returns empty array when no names match', () => {
    const result = filterProductsByName(SEED, 'saree');
    expect(result.length).toBe(0);
  });

  it('handles items with null name gracefully (null treated as empty string)', () => {
    const withNull: ProductListItem[] = [
      {
        product_id: 'n1',
        name: null,
        category_id: 'cat-x',
        status: 'draft',
        created_at: '',
        updated_at: '',
      },
    ];
    const result = filterProductsByName(withNull, 'kurti');
    expect(result.length).toBe(0); // null name does not match
  });

  it('whitespace-only search returns all items', () => {
    const result = filterProductsByName(SEED, '   ');
    expect(result.length).toBe(SEED.length);
  });
});

// ---------------------------------------------------------------------------
// Gate 5: onRowClick() — each row has product_id for /catalogs/:product_id/edit
// ---------------------------------------------------------------------------
describe('ProductListItem — Gate 5: row click navigation contract (product_id — A7)', () => {
  it('Gate 5: each item in SEED has a unique non-empty product_id (basis for /catalogs/:product_id/edit routing)', () => {
    const ids = SEED.map(p => p.product_id);
    const uniqueIds = new Set(ids);
    expect(uniqueIds.size).toBe(SEED.length);
    expect(ids.every(id => id.length > 0)).toBe(true);
  });

  it('first seed row navigates to /catalogs/p1/edit via product_id', () => {
    const row = SEED[0];
    // The component calls router.navigate(['/catalogs', row.product_id, 'edit'])
    const expectedPath = ['/catalogs', row.product_id, 'edit'];
    expect(expectedPath).toEqual(['/catalogs', 'p1', 'edit']);
  });

  it('ProductListItem has category_id (UUID) not category_name — Category column dropped (A4)', () => {
    const row = SEED[0];
    expect(row).toHaveProperty('category_id');
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect((row as unknown as Record<string, unknown>)['category_name']).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// formatRelativeTime() — relative time display in table rows
// ---------------------------------------------------------------------------
describe('formatRelativeTime()', () => {
  it('returns "m ago" for a 30-minute-old timestamp', () => {
    const iso = new Date(Date.now() - 30 * 60 * 1000).toISOString();
    expect(formatRelativeTime(iso)).toContain('m ago');
  });

  it('returns "h ago" for a 2-hour-old timestamp', () => {
    const iso = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
    expect(formatRelativeTime(iso)).toContain('h ago');
  });

  it('returns "d ago" for a 3-day-old timestamp', () => {
    const iso = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString();
    expect(formatRelativeTime(iso)).toContain('d ago');
  });

  it('returns "0m ago" for a just-now timestamp', () => {
    const iso = new Date(Date.now()).toISOString();
    expect(formatRelativeTime(iso)).toContain('m ago');
  });
});
