// Feature-local model for the Preview page.
// Represents the response shape of GET /api/v1/products/{id}/preview.
// Wave 6 will wire this to a real HTTP call; Wave 5 uses simulated data.
//
// Pure functions are exported so Vitest specs can test business logic
// without TestBed (avoids Angular 21 + PrimeNG 21 ngModule null crash).

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface PreviewData {
  product_id: string;
  title: string;
  mrp: number;
  category_path: string;     // e.g. "Fashion > Women > Ethnic > Kurti"
  commission_pct: number;
  gst_pct: number;
  primary_image_url: string; // GCS signed URL or local placeholder
  image_urls: string[];      // ordered, up to 6
  variant_label: string | null;
}

export type PreviewTab = 'feed' | 'detail' | 'mobile';

export interface MobileTile {
  imageUrl: string;
  truncatedTitle: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Meesho feed thumbnail truncation threshold (~30 visible chars). */
export const FEED_TITLE_LIMIT = 30;

/** Meesho mobile grid card truncation threshold (~20 visible chars). */
export const MOBILE_TITLE_LIMIT = 20;

/** Desktop breakpoint in pixels (same as Tailwind lg:). */
export const DESKTOP_BREAKPOINT_PX = 1024;

// ---------------------------------------------------------------------------
// Pure functions — testable without TestBed
// ---------------------------------------------------------------------------

/**
 * Returns true when the product title exceeds the feed display limit.
 * Drives the truncation warning panel visibility.
 */
export function isTitleTruncated(
  title: string | null | undefined,
  limit = FEED_TITLE_LIMIT
): boolean {
  return (title?.length ?? 0) > limit;
}

/**
 * Truncates the title at `limit` chars and appends an ellipsis character.
 * Returns the full title when it is at or below the limit.
 */
export function truncateTitle(
  title: string | null | undefined,
  limit: number
): string {
  const t = title ?? '';
  return t.length > limit ? t.slice(0, limit) + '…' : t;
}

/**
 * Builds exactly 2 MobileTile objects for the 2-up mobile grid preview.
 * Falls back to a placeholder image when the product has fewer than 2 images.
 */
export function buildMobileTiles(
  data: PreviewData | null,
  limit = MOBILE_TITLE_LIMIT
): MobileTile[] {
  const title   = data?.title ?? '';
  const imgUrls = data?.image_urls ?? [];
  const truncatedMobile = truncateTitle(title, limit);

  return [0, 1].map(i => ({
    imageUrl:       imgUrls[i] ?? '/assets/placeholder-product.png',
    truncatedTitle: truncatedMobile,
  }));
}

/**
 * Resolves the product ID to use when navigating to the edit page.
 * Prefers the route param ID; falls back to the preview data ID.
 */
export function resolveEditProductId(
  routeParamId: string | null,
  previewProductId: string | null | undefined
): string {
  return routeParamId ?? previewProductId ?? '';
}

// ---------------------------------------------------------------------------
// Simulated data — Journey step 8
// Title is 35 chars → triggers truncation warning (threshold: 30)
// ---------------------------------------------------------------------------

export const SIMULATED_PREVIEW: PreviewData = {
  product_id:        'demo-product-001',
  title:             'Blue Cotton Kurti With Mirror Work',
  mrp:               899,
  category_path:     'Fashion > Women > Ethnic > Kurti',
  commission_pct:    5,
  gst_pct:           5,
  primary_image_url: '/assets/placeholder-product.png',
  image_urls: [
    '/assets/placeholder-product.png',
    '/assets/placeholder-product.png',
    '/assets/placeholder-product.png',
    '/assets/placeholder-product.png',
  ],
  variant_label: 'M / Blue',
};
