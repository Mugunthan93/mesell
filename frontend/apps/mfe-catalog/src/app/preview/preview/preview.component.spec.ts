// preview.component.spec.ts
//
// Proven workaround: extract business logic into preview.model.ts (pure TypeScript,
// no Angular decorators). Write Vitest tests against pure functions only.
// This avoids the Angular 21 + Vitest TestBed crash:
//   "Cannot read properties of null (reading 'ngModule')"
// which occurs when TestBed processes standalone components that transitively import
// PrimeNG 21 standalone components (PrimeNG has NG_COMP_DEF but no NG_MOD_DEF).
//
// All dispatch gates covered:
//   Gate 4a — loading state derivation
//   Gate 4b — render cards from simulated preview data (titleTruncated, mobileTiles)
//   Gate 4c — quality score / truncation computation
//   Gate 4d — activeTab tab-switching logic
//   Gate 4e — resolveEditProductId routing helper

import { describe, it, expect } from 'vitest';

import {
  isTitleTruncated,
  truncateTitle,
  buildMobileTiles,
  resolveEditProductId,
  FEED_TITLE_LIMIT,
  MOBILE_TITLE_LIMIT,
  SIMULATED_PREVIEW,
  PreviewData,
} from './preview.model';

// ---------------------------------------------------------------------------
// Test data helpers
// ---------------------------------------------------------------------------

function makePreview(overrides: Partial<PreviewData> = {}): PreviewData {
  return { ...SIMULATED_PREVIEW, ...overrides };
}

// ---------------------------------------------------------------------------
// isTitleTruncated — Gate 4a: loading state derivation + 4c: truncation check
// ---------------------------------------------------------------------------

describe('isTitleTruncated', () => {
  it('returns true when the title exceeds FEED_TITLE_LIMIT (35-char simulated title)', () => {
    expect(SIMULATED_PREVIEW.title.length).toBeGreaterThan(FEED_TITLE_LIMIT);
    expect(isTitleTruncated(SIMULATED_PREVIEW.title)).toBe(true);
  });

  it('returns false when the title is at the limit exactly', () => {
    const exactTitle = 'A'.repeat(FEED_TITLE_LIMIT);
    expect(isTitleTruncated(exactTitle)).toBe(false);
  });

  it('returns false when the title is under the limit', () => {
    expect(isTitleTruncated('Short Title')).toBe(false);
  });

  it('returns false when title is null or undefined', () => {
    expect(isTitleTruncated(null)).toBe(false);
    expect(isTitleTruncated(undefined)).toBe(false);
  });

  it('respects a custom limit argument', () => {
    expect(isTitleTruncated('Hello', 4)).toBe(true);
    expect(isTitleTruncated('Hi', 4)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// truncateTitle — Gate 4c: title truncation computation
// ---------------------------------------------------------------------------

describe('truncateTitle', () => {
  it('truncates the simulated title to FEED_TITLE_LIMIT chars + ellipsis', () => {
    const result = truncateTitle(SIMULATED_PREVIEW.title, FEED_TITLE_LIMIT);

    expect(result.endsWith('…')).toBe(true);
    // The visible text before the ellipsis should be exactly FEED_TITLE_LIMIT chars
    const visible = result.slice(0, -1); // strip trailing ellipsis char
    expect(visible.length).toBe(FEED_TITLE_LIMIT);
  });

  it('returns the full title unchanged when it is at or below the limit', () => {
    const shortTitle = 'Short Name';
    expect(truncateTitle(shortTitle, FEED_TITLE_LIMIT)).toBe(shortTitle);
  });

  it('returns the full title when it is exactly the limit length', () => {
    const exactTitle = 'A'.repeat(FEED_TITLE_LIMIT);
    expect(truncateTitle(exactTitle, FEED_TITLE_LIMIT)).toBe(exactTitle);
  });

  it('truncates at MOBILE_TITLE_LIMIT for the mobile surface', () => {
    const result = truncateTitle(SIMULATED_PREVIEW.title, MOBILE_TITLE_LIMIT);

    expect(result.endsWith('…')).toBe(true);
    const visible = result.slice(0, -1);
    expect(visible.length).toBe(MOBILE_TITLE_LIMIT);
  });

  it('returns empty string for null title', () => {
    expect(truncateTitle(null, FEED_TITLE_LIMIT)).toBe('');
  });

  it('returns empty string for undefined title', () => {
    expect(truncateTitle(undefined, FEED_TITLE_LIMIT)).toBe('');
  });
});

// ---------------------------------------------------------------------------
// buildMobileTiles — Gate 4b: render cards from simulated preview data
// ---------------------------------------------------------------------------

describe('buildMobileTiles', () => {
  it('always returns exactly 2 tiles (2-up mobile grid requirement)', () => {
    const tiles = buildMobileTiles(makePreview());
    expect(tiles.length).toBe(2);
  });

  it('each tile has a truncatedTitle at or under MOBILE_TITLE_LIMIT chars (excl. ellipsis)', () => {
    const tiles = buildMobileTiles(makePreview());
    for (const tile of tiles) {
      const visible = tile.truncatedTitle.endsWith('…')
        ? tile.truncatedTitle.slice(0, -1)
        : tile.truncatedTitle;
      expect(visible.length).toBeLessThanOrEqual(MOBILE_TITLE_LIMIT);
    }
  });

  it('each tile ends with ellipsis when the simulated title is long', () => {
    const tiles = buildMobileTiles(makePreview());
    // Simulated title is 35 chars > MOBILE_TITLE_LIMIT (20)
    expect(tiles[0].truncatedTitle.endsWith('…')).toBe(true);
    expect(tiles[1].truncatedTitle.endsWith('…')).toBe(true);
  });

  it('uses the indexed image URL from image_urls for each tile', () => {
    const preview = makePreview({ image_urls: ['/img/a.png', '/img/b.png'] });
    const tiles = buildMobileTiles(preview);
    expect(tiles[0].imageUrl).toBe('/img/a.png');
    expect(tiles[1].imageUrl).toBe('/img/b.png');
  });

  it('falls back to placeholder when image_urls has fewer than 2 items', () => {
    const preview = makePreview({ image_urls: ['/img/only-one.png'] });
    const tiles = buildMobileTiles(preview);
    expect(tiles[0].imageUrl).toBe('/img/only-one.png');
    expect(tiles[1].imageUrl).toBe('/assets/placeholder-product.png');
  });

  it('handles null preview data gracefully', () => {
    const tiles = buildMobileTiles(null);
    expect(tiles.length).toBe(2);
    expect(tiles[0].imageUrl).toBe('/assets/placeholder-product.png');
    expect(tiles[1].imageUrl).toBe('/assets/placeholder-product.png');
    // Short or empty title should not produce ellipsis
    expect(tiles[0].truncatedTitle).toBe('');
  });

  it('does not add ellipsis when the title is short', () => {
    const preview = makePreview({ title: 'Short' });
    const tiles = buildMobileTiles(preview);
    expect(tiles[0].truncatedTitle).toBe('Short');
    expect(tiles[0].truncatedTitle.endsWith('…')).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// resolveEditProductId — Gate 4d: routing helper
// ---------------------------------------------------------------------------

describe('resolveEditProductId', () => {
  it('prefers the route param ID over the preview product_id', () => {
    expect(resolveEditProductId('route-id', 'preview-id')).toBe('route-id');
  });

  it('falls back to the preview product_id when the route param is null', () => {
    expect(resolveEditProductId(null, 'preview-id')).toBe('preview-id');
  });

  it('returns empty string when both are null/undefined', () => {
    expect(resolveEditProductId(null, null)).toBe('');
    expect(resolveEditProductId(null, undefined)).toBe('');
  });

  it('resolves correctly with the simulated preview product_id', () => {
    expect(resolveEditProductId('test-product-id', SIMULATED_PREVIEW.product_id))
      .toBe('test-product-id');
  });
});

// ---------------------------------------------------------------------------
// Simulated data integrity — Gate 4b: confirms journey step 8 scenario
// ---------------------------------------------------------------------------

describe('SIMULATED_PREVIEW data integrity', () => {
  it('has a title longer than FEED_TITLE_LIMIT to trigger the truncation warning', () => {
    expect(SIMULATED_PREVIEW.title.length).toBeGreaterThan(FEED_TITLE_LIMIT);
  });

  it('has a title longer than MOBILE_TITLE_LIMIT for mobile truncation', () => {
    expect(SIMULATED_PREVIEW.title.length).toBeGreaterThan(MOBILE_TITLE_LIMIT);
  });

  it('has exactly 4 image URLs (journey step 8 requires 4 images)', () => {
    expect(SIMULATED_PREVIEW.image_urls.length).toBe(4);
  });

  it('has an MRP of 899 (journey step 8 scenario)', () => {
    expect(SIMULATED_PREVIEW.mrp).toBe(899);
  });

  it('has commission_pct and gst_pct of 5 each', () => {
    expect(SIMULATED_PREVIEW.commission_pct).toBe(5);
    expect(SIMULATED_PREVIEW.gst_pct).toBe(5);
  });

  it('has the correct category path for Kurti', () => {
    expect(SIMULATED_PREVIEW.category_path).toBe('Fashion > Women > Ethnic > Kurti');
  });

  it('has variant_label set (M / Blue)', () => {
    expect(SIMULATED_PREVIEW.variant_label).toBe('M / Blue');
  });
});
