/**
 * dashboard.model.ts — Pure functions and types for the dashboard feature.
 *
 * NO Angular decorators in this file. Functions here can be imported and
 * tested directly in Vitest without requiring TestBed or @angular/compiler.
 *
 * Pattern from: image-uploader.model.ts
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ProductListItem {
  id: string;
  name: string;
  category_name: string;
  status: 'draft' | 'ready' | 'exported' | 'live' | 'deleted';
  updated_at: string; // ISO timestamp
}

export interface ProductListResponse {
  products: ProductListItem[];
  total: number;
  page: number;
}

export interface StatusCounts {
  draft: number;
  ready: number;
  exported: number;
  live: number;
}

export interface LoadProductsParams {
  page: number;
  limit?: number;
  status_filter?: string;
  search?: string;
}

// ---------------------------------------------------------------------------
// Pure functions
// ---------------------------------------------------------------------------

/**
 * Derives status counts from a product list array.
 * Used by DashboardApiService.deriveStatusCounts() and DashboardComponent.
 */
export function deriveStatusCounts(products: ProductListItem[]): StatusCounts {
  return products.reduce(
    (acc, p) => {
      if (p.status === 'draft')    { acc.draft++; }
      if (p.status === 'ready')    { acc.ready++; }
      if (p.status === 'exported') { acc.exported++; }
      if (p.status === 'live')     { acc.live++; }
      return acc;
    },
    { draft: 0, ready: 0, exported: 0, live: 0 } as StatusCounts
  );
}

/**
 * Applies status_filter and search params to a product list.
 * Used by DashboardApiService.loadProducts().
 */
export function filterProducts(
  products: ProductListItem[],
  params: Pick<LoadProductsParams, 'status_filter' | 'search'>
): ProductListItem[] {
  let filtered = [...products];

  if (params.status_filter) {
    filtered = filtered.filter(p => p.status === params.status_filter);
  }

  if (params.search?.trim()) {
    const q = params.search.trim().toLowerCase();
    filtered = filtered.filter(
      p =>
        p.name.toLowerCase().includes(q) ||
        p.category_name.toLowerCase().includes(q)
    );
  }

  return filtered;
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
