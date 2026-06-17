/**
 * dashboard.model.ts — Pure functions and types for the dashboard feature.
 *
 * NO Angular decorators in this file. Functions here can be imported and
 * tested directly in Vitest without requiring TestBed or @angular/compiler.
 *
 * Pattern from: image-uploader.model.ts
 *
 * === Wave 6 Wave B (2026-06-12) — wire to backend contract ===
 * ProductListItem reconciled to dashboard/schemas.py ProductListItem:
 *   - product_id (not id) — renamed at the dashboard boundary (A7)
 *   - category_id (UUID) — no display name on the wire; Category column dropped (A4)
 *   - status 2-value 'draft'|'ready' (not 5-value — §13.A.1 narrows; A2)
 *   - created_at added
 * DashboardResponse: adds limit + onboarding_completeness vs old ProductListResponse (A5)
 * StatusCounts narrowed to {draft, ready} — V1 wire is 2-value (A2)
 * LoadProductsParams narrowed: server params are page+limit ONLY (A3)
 *   search kept as LOCAL-only client-side filter helper; never sent to server
 */

// ---------------------------------------------------------------------------
// Types (transcribed verbatim from dashboard/schemas.py — §1.1 contract chain)
// ---------------------------------------------------------------------------

/** Transcribed from dashboard/schemas.py class ProductListItem. */
export interface ProductListItem {
  product_id: string;         // UUID as string — note: "product_id" NOT "id"
  name: string | null;        // nullable until seller fills it
  category_id: string;        // UUID as string — no display name on the wire (A4)
  status: 'draft' | 'ready'; // 2-value V1 wire (§13.A.1 narrows; A2)
  created_at: string;         // ISO-8601 TZ
  updated_at: string;         // ISO-8601 TZ
}

/** Transcribed from dashboard/schemas.py class ProfileCompletenessSummary. */
export interface ProfileCompletenessSummary {
  base_complete_count: number;
  base_total_count: number;        // always 10 per §8.F
  extension_complete_count: number;
  extension_total_count: number;
  onboarding_complete: boolean;
}

/** Transcribed from dashboard/schemas.py class DashboardResponse. Array key = "products" (confirmed §2.1/A1). */
export interface DashboardResponse {
  products: ProductListItem[];
  total: number;
  page: number;
  limit: number;
  /** Decoded but NOT rendered in V1 dashboard (A5). Type it; leave it unrendered. */
  onboarding_completeness: ProfileCompletenessSummary;
}

/**
 * V1 2-value status counts — narrowed from the legacy 4-key shape.
 * exported/live do NOT exist on the V1 wire (A2).
 */
export interface StatusCounts {
  draft: number;
  ready: number;
}

/**
 * Server-bound params for GET /api/v1/products: page + limit ONLY.
 * (DashboardQuery extra="forbid" — §2.4 / A3).
 */
export interface LoadProductsParams {
  page: number;
  limit?: number;
}

// ---------------------------------------------------------------------------
// Pure functions
// ---------------------------------------------------------------------------

/**
 * Derives status counts from a product list array.
 * V1 counts only draft + ready (the 2 values the wire returns — A2).
 */
export function deriveStatusCounts(products: ProductListItem[]): StatusCounts {
  return products.reduce(
    (acc, p) => {
      if (p.status === 'draft') { acc.draft++; }
      if (p.status === 'ready') { acc.ready++; }
      return acc;
    },
    { draft: 0, ready: 0 } as StatusCounts,
  );
}

/**
 * Client-side name search over the current page's rows (A3).
 * NEVER sent to the server. Applied AFTER the server response arrives.
 * Searches `name` field only (category_id is a UUID — not searchable as text).
 */
export function filterProductsByName(
  products: ProductListItem[],
  search: string,
): ProductListItem[] {
  if (!search.trim()) return products;
  const q = search.trim().toLowerCase();
  return products.filter(p => (p.name ?? '').toLowerCase().includes(q));
}

/**
 * Formats an ISO timestamp as a human-readable relative time string.
 * Used by DashboardComponent.formatRelativeTime().
 */
export function formatRelativeTime(isoString: string): string {
  const diffMs = Date.now() - new Date(isoString).getTime();
  const diffMins = Math.floor(diffMs / 60_000);
  if (diffMins < 60) { return `${diffMins}m ago`; }
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) { return `${diffHours}h ago`; }
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}
