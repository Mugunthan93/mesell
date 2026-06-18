/**
 * live-listings.model.spec.ts
 *
 * Pure-function Vitest spec (NO TestBed, NO Angular imports).
 * Covers all exported functions in live-listings.model.ts.
 */
import { describe, it, expect } from 'vitest';

import {
  toBase36,
  slugify,
  buildMeeshoUrl,
  buildColumnIndexMap,
  assertInventoryColumns,
  mapSheetToInventory,
  InvalidInventoryFileError,
  MEESHO_PDP_BASE,
  COL_PRODUCT_ID,
  COL_PRODUCT_NAME,
  LOCAL_STORAGE_KEY,
} from './live-listings.model';

// ─── toBase36 ─────────────────────────────────────────────────────────────────

describe('toBase36', () => {
  it('converts small numeric string to base36', () => {
    // 0 in base36 = '0'
    expect(toBase36('0')).toBe('0');
  });

  it('converts a typical Meesho product id', () => {
    // 100 in base36 = '2s'
    expect(toBase36('100')).toBe('2s');
  });

  it('converts an id that exceeds Number.MAX_SAFE_INTEGER via BigInt', () => {
    // 9999999999999999 (16 nines) exceeds MAX_SAFE_INTEGER (2^53 - 1 = 9007199254740991)
    const largeId = '9999999999999999';
    const result = toBase36(largeId);
    // Verify BigInt roundtrip: parseInt(result, 36) would lose precision; use BigInt comparison
    expect(BigInt(largeId).toString(36)).toBe(result);
    expect(result).not.toBe('');
  });

  it('returns empty string for non-numeric input', () => {
    expect(toBase36('abc')).toBe('');
    expect(toBase36('12abc')).toBe('');
    expect(toBase36('')).toBe('');
    expect(toBase36('1.5')).toBe('');
  });

  it('handles a very large id correctly (not a JS safe integer)', () => {
    // 123456789012345678 — well beyond Number.MAX_SAFE_INTEGER
    const id = '123456789012345678';
    const expected = BigInt(id).toString(36);
    expect(toBase36(id)).toBe(expected);
  });
});

// ─── slugify ──────────────────────────────────────────────────────────────────

describe('slugify', () => {
  it('lower-cases the name and replaces spaces with dashes', () => {
    expect(slugify('Blue Shirt')).toBe('blue-shirt');
  });

  it('strips punctuation and special characters', () => {
    expect(slugify('T-shirt (100% cotton)!')).toBe('t-shirt-100-cotton');
  });

  it('strips diacritics', () => {
    expect(slugify('Café Latté')).toBe('cafe-latte');
  });

  it('collapses multiple consecutive dashes', () => {
    expect(slugify('Hello   World')).toBe('hello-world');
  });

  it('trims leading and trailing dashes', () => {
    expect(slugify('  -hello-  ')).toBe('hello');
  });

  it('returns "product" for an empty string', () => {
    expect(slugify('')).toBe('product');
  });

  it('returns "product" when the result after stripping is empty', () => {
    // Input is all non-alnum: !!!! -> '' -> 'product'
    expect(slugify('!!!!')).toBe('product');
  });

  it('handles mixed Hindi romanisation safely (all non-alnum stripped)', () => {
    // Unicode non-ASCII letters get stripped after NFD normalisation
    // (any remaining non-[a-z0-9] chars are replaced by '-')
    const result = slugify('कुर्ता');
    expect(typeof result).toBe('string');
    expect(result.length).toBeGreaterThan(0);
  });
});

// ─── buildMeeshoUrl ───────────────────────────────────────────────────────────

describe('buildMeeshoUrl', () => {
  it('builds the correct URL shape', () => {
    const url = buildMeeshoUrl('100', 'Blue Shirt');
    // 100 in base36 = '2s'
    expect(url).toBe(`${MEESHO_PDP_BASE}/blue-shirt/p/2s`);
  });

  it('the slug is cosmetic: two different names with the same id share the same /p/ segment', () => {
    const url1 = buildMeeshoUrl('100', 'Blue Shirt');
    const url2 = buildMeeshoUrl('100', 'Red Shirt');
    // Same /p/ base36 segment
    expect(url1.split('/p/')[1]).toBe(url2.split('/p/')[1]);
    // Different slugs
    expect(url1.split('/p/')[0]).not.toBe(url2.split('/p/')[0]);
  });

  it('uses MEESHO_PDP_BASE as the origin', () => {
    const url = buildMeeshoUrl('1', 'test');
    expect(url.startsWith(MEESHO_PDP_BASE)).toBe(true);
  });

  it('contains /p/ as separator before the base36 id', () => {
    const url = buildMeeshoUrl('36', 'Saree');
    // 36 in base36 = '10'
    expect(url).toContain('/p/10');
  });
});

// ─── buildColumnIndexMap ──────────────────────────────────────────────────────

describe('buildColumnIndexMap', () => {
  it('maps column headers to their indices', () => {
    const header = ['SERIAL NO', 'CATALOG NAME', 'PRODUCT ID', 'PRODUCT NAME'];
    const map = buildColumnIndexMap(header);
    expect(map.get('PRODUCT ID')).toBe(2);
    expect(map.get('PRODUCT NAME')).toBe(3);
  });

  it('handles reordered columns (PRODUCT NAME before PRODUCT ID)', () => {
    const header = ['PRODUCT NAME', 'OTHER COL', 'PRODUCT ID'];
    const map = buildColumnIndexMap(header);
    expect(map.get('PRODUCT NAME')).toBe(0);
    expect(map.get('PRODUCT ID')).toBe(2);
  });

  it('normalises by trimming and upper-casing', () => {
    const header = ['  product id  ', '  product name  '];
    const map = buildColumnIndexMap(header);
    expect(map.get('PRODUCT ID')).toBe(0);
    expect(map.get('PRODUCT NAME')).toBe(1);
  });

  it('collapses inner whitespace during normalisation', () => {
    const header = ['PRODUCT  ID', 'PRODUCT  NAME'];
    const map = buildColumnIndexMap(header);
    expect(map.get('PRODUCT ID')).toBe(0);
    expect(map.get('PRODUCT NAME')).toBe(1);
  });

  it('handles numeric cells (non-string) by converting to string', () => {
    const header = [42, 'PRODUCT ID'];
    const map = buildColumnIndexMap(header);
    expect(map.get('42')).toBe(0);
    expect(map.get('PRODUCT ID')).toBe(1);
  });
});

// ─── assertInventoryColumns ───────────────────────────────────────────────────

describe('assertInventoryColumns', () => {
  it('does not throw when both required columns are present', () => {
    const cols = new Map([
      [COL_PRODUCT_ID, 4],
      [COL_PRODUCT_NAME, 3],
    ]);
    expect(() => assertInventoryColumns(cols)).not.toThrow();
  });

  it('throws InvalidInventoryFileError when PRODUCT ID is missing', () => {
    const cols = new Map([[COL_PRODUCT_NAME, 3]]);
    expect(() => assertInventoryColumns(cols)).toThrow(InvalidInventoryFileError);
  });

  it('throws InvalidInventoryFileError when PRODUCT NAME is missing', () => {
    const cols = new Map([[COL_PRODUCT_ID, 4]]);
    expect(() => assertInventoryColumns(cols)).toThrow(InvalidInventoryFileError);
  });

  it('throws InvalidInventoryFileError when both columns are missing', () => {
    const cols = new Map<string, number>();
    expect(() => assertInventoryColumns(cols)).toThrow(InvalidInventoryFileError);
  });

  it('error message identifies the missing column', () => {
    const cols = new Map([[COL_PRODUCT_NAME, 3]]);
    try {
      assertInventoryColumns(cols);
    } catch (e) {
      expect((e as Error).message).toContain(COL_PRODUCT_ID);
    }
  });
});

// ─── mapSheetToInventory ──────────────────────────────────────────────────────

describe('mapSheetToInventory', () => {
  /**
   * Fixture mirroring the 11-column Meesho Inventory Update File structure.
   * Row 0: display label row (ignored by parser)
   * Row 1: actual column headers
   * Row 2+: data rows
   */
  const makeRows = (dataRows: unknown[][]): unknown[][] => [
    // Row 0: first header row (ignored)
    [
      'Inventory Update Data',
      null, null, null, null, null, null, null, null, null, null,
    ],
    // Row 1: actual column header row
    [
      'SERIAL NO',
      'CATALOG NAME',
      'CATALOG ID',
      'PRODUCT NAME',
      'PRODUCT ID',
      'STYLE ID(SKU)',
      'VARIATION ID',
      'VARIATION',
      'STOCK',
      'SYSTEM STOCK COUNT',
      'YOUR STOCK COUNT',
    ],
    ...dataRows,
  ];

  it('returns empty listings for a file with only header rows', () => {
    const rows = makeRows([]);
    const result = mapSheetToInventory(rows);
    expect(result.listings).toHaveLength(0);
    expect(result.skippedCount).toBe(0);
  });

  it('parses a well-formed data row', () => {
    const rows = makeRows([
      [1, 'My Catalog', 999, 'Blue Shirt', 123456, 'SKU001', 'VAR001', 'S', 10, 10, 10],
    ]);
    const result = mapSheetToInventory(rows);
    expect(result.listings).toHaveLength(1);
    expect(result.listings[0].productId).toBe('123456');
    expect(result.listings[0].productName).toBe('Blue Shirt');
    expect(result.listings[0].base36).toBe(toBase36('123456'));
    expect(result.listings[0].meeshoUrl).toContain('/p/');
  });

  it('skips the 2 header rows (row 0 and row 1)', () => {
    // Only one data row — result should have 1 listing, not 3
    const rows = makeRows([
      [1, 'Cat', 999, 'Shirt', 100, 'S1', 'V1', 'M', 5, 5, 5],
    ]);
    const result = mapSheetToInventory(rows);
    expect(result.listings).toHaveLength(1);
  });

  it('skips rows with blank PRODUCT ID and counts them in skippedCount', () => {
    const rows = makeRows([
      [1, 'Cat', 999, 'Valid',   100, 'S1', 'V1', 'M', 5, 5, 5],
      [2, 'Cat', 999, 'NoId',   '',  'S2', 'V2', 'L', 0, 0, 0],  // blank id
      [3, 'Cat', 999, 'NullId', null,'S3', 'V3', 'S', 3, 3, 3],  // null id
    ]);
    const result = mapSheetToInventory(rows);
    expect(result.listings).toHaveLength(1);
    expect(result.skippedCount).toBe(2);
  });

  it('skips rows with non-numeric PRODUCT ID and counts them', () => {
    const rows = makeRows([
      [1, 'Cat', 999, 'Valid',   '100',   'S1', 'V1', 'M', 5, 5, 5],
      [2, 'Cat', 999, 'NonNum', 'N/A',   'S2', 'V2', 'L', 0, 0, 0],
    ]);
    const result = mapSheetToInventory(rows);
    expect(result.listings).toHaveLength(1);
    expect(result.skippedCount).toBe(1);
  });

  it('handles reordered columns (PRODUCT NAME before PRODUCT ID)', () => {
    // Non-standard column order — buildColumnIndexMap should resolve correctly
    const rowsReordered: unknown[][] = [
      ['First header row label', null, null, null, null],
      ['PRODUCT NAME', 'SERIAL NO', 'CATALOG ID', 'PRODUCT ID', 'EXTRA'],
      ['Red Kurti', 1, 999, '987654', 'x'],
    ];
    const result = mapSheetToInventory(rowsReordered);
    expect(result.listings).toHaveLength(1);
    expect(result.listings[0].productId).toBe('987654');
    expect(result.listings[0].productName).toBe('Red Kurti');
  });

  it('handles a product id larger than Number.MAX_SAFE_INTEGER', () => {
    const largeId = '9999999999999999';
    const rows = makeRows([
      [1, 'Cat', 999, 'Large ID Product', largeId, 'S1', 'V1', 'M', 1, 1, 1],
    ]);
    const result = mapSheetToInventory(rows);
    expect(result.listings[0].productId).toBe(largeId);
    expect(result.listings[0].base36).toBe(toBase36(largeId));
  });

  it('throws InvalidInventoryFileError when the required columns are missing', () => {
    const rowsNoCols: unknown[][] = [
      ['First row'],
      ['WRONG COL A', 'WRONG COL B'],
      ['data', 'data'],
    ];
    expect(() => mapSheetToInventory(rowsNoCols)).toThrow(InvalidInventoryFileError);
  });

  it('throws InvalidInventoryFileError when there are fewer than 2 rows', () => {
    expect(() => mapSheetToInventory([['only one row']])).toThrow(InvalidInventoryFileError);
    expect(() => mapSheetToInventory([])).toThrow(InvalidInventoryFileError);
  });

  it('exports LOCAL_STORAGE_KEY constant for use in component', () => {
    // Just verify it is exported and non-empty
    expect(typeof LOCAL_STORAGE_KEY).toBe('string');
    expect(LOCAL_STORAGE_KEY.length).toBeGreaterThan(0);
  });
});
