/**
 * DashboardApiService — real HTTP wiring for mfe-dashboard (Wave 6 Wave B).
 *
 * Endpoints:
 *   #26  GET  /api/v1/products?page=&limit=   → DashboardResponse
 *   #21  DELETE /api/v1/products/{id}          → void (204)
 *
 * Auth: jwtInterceptor (Wave A, frozen) attaches `Authorization: Bearer` automatically.
 * NO manual Authorization header here (R-W6-1 migration from Wave 5 per-service authHeaders).
 *
 * Graceful-degradation matrix (R-W6-1 — merge gate REJECTS if absent):
 *   401 → refreshInterceptor retries; only reaches here if refresh ALSO failed → fallback
 *   402 → dashboard is plan-guard-excluded but matrix handles it uniformly → empty fallback
 *   400 → bad pagination (FE only sends valid params) → empty fallback + console.error
 *   404 → loadProducts: not expected (empty inventory = 200+[]); deleteProduct: treat as success
 *   5xx → empty fallback; component renders MeeAlertBanner + retry
 *
 * Feature-scoped service — NOT providedIn: 'root'.
 * Provided via DashboardComponent.providers[] so it tree-shakes with the route chunk (D28a/D32).
 */

import { Injectable, inject } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { Observable, EMPTY, of, catchError } from 'rxjs';

import { ApiClient } from '@mesell/core';

import {
  DashboardResponse,
  ProductListItem,
  ProfileCompletenessSummary,
  StatusCounts,
  LoadProductsParams,
  deriveStatusCounts,
} from '../dashboard.model';

// Re-export types for consumers (dashboard.component.ts) that already import from this path.
export type { ProductListItem, DashboardResponse, StatusCounts, LoadProductsParams };

/** Zero-value ProfileCompletenessSummary for error fallbacks. */
const ZERO_COMPLETENESS: ProfileCompletenessSummary = {
  base_complete_count: 0,
  base_total_count: 10,
  extension_complete_count: 0,
  extension_total_count: 0,
  onboarding_complete: false,
};

/** Contract-shaped empty DashboardResponse for error fallbacks. */
function emptyResponse(page: number, limit: number): DashboardResponse {
  return {
    products: [],
    total: 0,
    page,
    limit,
    onboarding_completeness: ZERO_COMPLETENESS,
  };
}

@Injectable()
export class DashboardApiService {
  private readonly api = inject(ApiClient);

  /**
   * GET /api/v1/products?page=&limit=
   *
   * jwtInterceptor attaches Bearer automatically — do NOT add Authorization here.
   * Returns DashboardResponse. On any error returns an empty-list fallback so the
   * component can render MeeAlertBanner (via the `error` signal) instead of crashing.
   *
   * @param params - page (1-based) + optional limit (default 20)
   */
  loadProducts(params: LoadProductsParams): Observable<DashboardResponse> {
    const limit = params.limit ?? 20;
    return this.api
      .get<DashboardResponse>('/api/v1/products', {
        params: { page: params.page, limit },
      })
      .pipe(
        catchError((err: HttpErrorResponse) => {
          const fallback = emptyResponse(params.page, limit);
          switch (err.status) {
            case 401:
              // refreshInterceptor handles retry; terminal 401 → logout() already called.
              // Return empty fallback so the component shows MeeAlertBanner, not white screen.
              return of(fallback);
            case 402:
              // Dashboard is plan-guard-excluded but handle uniformly.
              return of(fallback);
            case 400:
              // FE only sends valid page>=1/limit 1..100, so 400 should not occur.
              console.error('[DashboardApiService] 400 on loadProducts — check pagination params', err);
              return of(fallback);
            case 404:
              // Empty inventory is 200+[], so 404 is not expected here.
              // Return empty fallback defensively.
              return of(fallback);
            default:
              // 5xx / network error → empty fallback; component renders error banner.
              return of(fallback);
          }
        }),
      );
  }

  /**
   * DELETE /api/v1/products/{id}
   *
   * 204 No-Content on success. Returns Observable<void>.
   * On 404: treat as success-equivalent (row already gone) — caller removes locally.
   * On other errors: returns EMPTY (no-op) — caller leaves the row, surfaces toast.
   *
   * @param id - product_id string (UUID)
   */
  deleteProduct(id: string): Observable<void> {
    return this.api
      .delete<void>(`/api/v1/products/${id}`)
      .pipe(
        catchError((err: HttpErrorResponse) => {
          if (err.status === 404) {
            // Product already deleted — treat as success; caller removes the row locally.
            return of(undefined as void);
          }
          if (err.status === 401) {
            // Terminal 401 after refresh failure — interceptor has already logged out.
            return EMPTY;
          }
          // 5xx / other errors → EMPTY (caller leaves row, surfaces an inline error).
          console.error('[DashboardApiService] deleteProduct failed', err.status, err.message);
          return EMPTY;
        }),
      );
  }

  /**
   * Derives status counts from a product list.
   * Delegates to the pure function — kept here so the component need not import the model directly.
   */
  deriveStatusCounts(products: ProductListItem[]): StatusCounts {
    return deriveStatusCounts(products);
  }
}
