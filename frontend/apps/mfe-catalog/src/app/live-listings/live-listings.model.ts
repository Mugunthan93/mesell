/**
 * live-listings.model.ts
 *
 * Pure TypeScript model for the "My Live Listings" feature.
 * No Angular imports. No xlsx import at module scope (lazy import only in component).
 */

// ─── Constants ────────────────────────────────────────────────────────────────

export const MEESHO_PDP_BASE = 'https://www.meesho.com';
export const INVENTORY_SHEET_NAME = 'Inventory-Update-Data-Fill This';
export const COL_PRODUCT_ID = 'PRODUCT ID';
export const COL_PRODUCT_NAME = 'PRODUCT NAME';

export const LOCAL_STORAGE_KEY = 'meesell_live_listings';

// ─── Interfaces ───────────────────────────────────────────────────────────────

export interface RawInventoryRow {
  productId: string;
  productName: string;
}

export interface LiveListing {
  productId: string;
  productName: string;
  base36: string;
  slug: string;
  meeshoUrl: string;
}

export interface ParsedInventory {
  listings: LiveListing[];
  skippedCount: number;
}

// ─── Error types ──────────────────────────────────────────────────────────────

export class InvalidInventoryFileError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'InvalidInventoryFileError';
    // Restore prototype chain (needed when targeting ES5 with tsc)
    Object.setPrototypeOf(this, InvalidInventoryFileError.prototype);
  }
}

// ─── Pure functions ───────────────────────────────────────────────────────────

/**
 * Convert a numeric product ID (as a string) to its base-36 representation.
 *
 * Uses BigInt to handle IDs that exceed Number.MAX_SAFE_INTEGER (Meesho
 * product IDs can be very large integers). Returns '' for non-numeric input.
 */
export function toBase36(productId: string): string {
  if (!/^\d+$/.test(productId)) {
    return '';
  }
  return BigInt(productId).toString(36);
}

/**
 * Convert a product name to a URL-safe slug.
 *
 * Steps:
 * 1. Strip diacritics via Unicode NFD normalisation
 * 2. Lower-case the result
 * 3. Replace any non-alphanumeric character with '-'
 * 4. Collapse consecutive '-' into one
 * 5. Trim leading/trailing '-'
 * 6. Fall back to 'product' when the result is empty
 */
export function slugify(name: string): string {
  if (!name) return 'product';

  const normalised = name
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '') // strip diacritics
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')    // non-alnum -> '-'
    .replace(/-+/g, '-')            // collapse multiple '-'
    .replace(/^-|-$/g, '');         // trim edge '-'

  return normalised || 'product';
}

/**
 * Build the public Meesho PDP URL for a product.
 *
 * Shape: https://www.meesho.com/{slug}/p/{base36(productId)}
 * The slug is cosmetic (any slug resolves on Meesho), only /p/{base36} matters.
 */
export function buildMeeshoUrl(productId: string, productName: string): string {
  return `${MEESHO_PDP_BASE}/${slugify(productName)}/p/${toBase36(productId)}`;
}

/**
 * Build a map from normalised column label to its index in the header row.
 *
 * Normalisation: trim whitespace, upper-case, collapse inner spaces.
 */
export function buildColumnIndexMap(headerRow: unknown[]): Map<string, number> {
  const map = new Map<string, number>();
  headerRow.forEach((cell, index) => {
    const raw = typeof cell === 'string' ? cell : String(cell ?? '');
    const normalised = raw.trim().toUpperCase().replace(/\s+/g, ' ');
    map.set(normalised, index);
  });
  return map;
}

/**
 * Assert that the required columns exist in the column index map.
 * Throws InvalidInventoryFileError if either PRODUCT ID or PRODUCT NAME is missing.
 */
export function assertInventoryColumns(cols: Map<string, number>): void {
  const missing: string[] = [];
  if (!cols.has(COL_PRODUCT_ID)) missing.push(COL_PRODUCT_ID);
  if (!cols.has(COL_PRODUCT_NAME)) missing.push(COL_PRODUCT_NAME);
  if (missing.length > 0) {
    throw new InvalidInventoryFileError(
      `Required columns not found: ${missing.join(', ')}. ` +
      `This doesn't look like a Meesho Inventory Update File.`
    );
  }
}

/**
 * Parse a 2D array of sheet data (from xlsx sheet_to_json with header:1) into
 * a ParsedInventory.
 *
 * The Meesho Inventory Update File has TWO header rows followed by data rows.
 * Row 0: merged/label row (ignored)
 * Row 1: the actual column header row (used for index resolution)
 * Row 2+: data rows
 *
 * Rows are skipped and counted in skippedCount when:
 * - The PRODUCT ID cell is blank/missing
 * - The PRODUCT ID cell is not a sequence of digits (non-numeric)
 */
export function mapSheetToInventory(rows: unknown[][]): ParsedInventory {
  if (rows.length < 2) {
    throw new InvalidInventoryFileError(
      'File does not have enough rows. Expected at least 2 header rows.'
    );
  }

  const headerRow = rows[1] as unknown[];
  const cols = buildColumnIndexMap(headerRow);
  assertInventoryColumns(cols);

  const productIdIdx = cols.get(COL_PRODUCT_ID)!;
  const productNameIdx = cols.get(COL_PRODUCT_NAME)!;

  const listings: LiveListing[] = [];
  let skippedCount = 0;

  for (let i = 2; i < rows.length; i++) {
    const row = rows[i] as unknown[];

    const rawProductId = row[productIdIdx];
    const rawProductName = row[productNameIdx];

    const productId = typeof rawProductId === 'number'
      ? String(rawProductId)
      : typeof rawProductId === 'string'
        ? rawProductId.trim()
        : '';

    // Skip blank or non-numeric product IDs
    if (!productId || !/^\d+$/.test(productId)) {
      skippedCount++;
      continue;
    }

    const productName = typeof rawProductName === 'string'
      ? rawProductName.trim()
      : typeof rawProductName === 'number'
        ? String(rawProductName)
        : '';

    const base36 = toBase36(productId);
    const slug = slugify(productName || 'product');
    const meeshoUrl = buildMeeshoUrl(productId, productName || 'product');

    listings.push({ productId, productName, base36, slug, meeshoUrl });
  }

  return { listings, skippedCount };
}
