/**
 * catalog-list.model.ts — types and adapters for the CatalogListComponent (Wave 3).
 *
 * Defines the catalog-side view of the product list independently from mfe-dashboard.
 * The wire shape (DashboardWireResponse) mirrors dashboard/schemas.py DashboardResponse
 * WITHOUT importing from the dashboard MFE — section-parallel model isolation rule.
 *
 * V1: page-1-only; no pagination UI.
 */

// ── Wire shape (mirrors dashboard/schemas.py — NO import from mfe-dashboard) ──

/**
 * CatalogListWireItem — one element of DashboardWireResponse.products[].
 * Transcribed verbatim from dashboard/schemas.py ProductListItem.
 * Note: wire key is "product_id" NOT "id".
 */
export interface CatalogListWireItem {
  product_id: string;          // UUID as string — wire key is "product_id" (not "id")
  name: string | null;         // nullable until seller fills title
  category_id: string;         // UUID as string — no display name on wire
  status: 'draft' | 'ready';  // 2-value V1 wire
  created_at: string;          // ISO-8601 TZ
  updated_at: string;          // ISO-8601 TZ
}

/**
 * DashboardWireResponse — subset of GET /api/v1/products response that this MFE cares about.
 * onboarding_completeness is present on the wire but typed as unknown and intentionally dropped
 * by the adapter — the catalog MFE does not render onboarding state.
 */
export interface DashboardWireResponse {
  products: CatalogListWireItem[];
  total: number;
  page: number;
  limit: number;
  onboarding_completeness: unknown;  // present on wire, dropped by adapter — do NOT render
}

// ── View-model (consumed by CatalogListComponent) ─────────────────────────────

/**
 * CatalogListItem — per-product view-model for the list page.
 * Adapter maps from CatalogListWireItem → CatalogListItem.
 */
export interface CatalogListItem {
  /** product_id from wire — used as the route param in /catalogs/:id/edit */
  id: string;
  /** Display name; falls back to 'Untitled product' if null */
  name: string;
  /** status badge: 'draft' | 'ready' */
  status: 'draft' | 'ready';
  /** ISO-8601 — used by formatRelativeTime() in the component */
  updatedAt: string;
}

/**
 * CatalogListResponse — the view-model returned by CatalogListApiService.listProducts().
 */
export interface CatalogListResponse {
  items: CatalogListItem[];
  total: number;
  page: number;
  limit: number;
}

// ── Adapter: pure function ─────────────────────────────────────────────────────

/**
 * adaptDashboardResponse — maps DashboardWireResponse → CatalogListResponse.
 *
 * - drops onboarding_completeness (not rendered by catalog MFE)
 * - maps product_id → id
 * - applies name fallback ('Untitled product' when null)
 * - maps updated_at → updatedAt (camelCase)
 */
export function adaptDashboardResponse(wire: DashboardWireResponse): CatalogListResponse {
  return {
    items: wire.products.map(p => ({
      id:        p.product_id,
      name:      p.name ?? 'Untitled product',
      status:    p.status,
      updatedAt: p.updated_at,
    })),
    total: wire.total,
    page:  wire.page,
    limit: wire.limit,
  };
}

/** Zero-value CatalogListResponse for error fallbacks. */
export function emptyListResponse(page: number, limit: number): CatalogListResponse {
  return { items: [], total: 0, page, limit };
}
