/**
 * CatalogListApiService — HTTP wiring for the CatalogListComponent (Wave 3).
 *
 * Endpoints:
 *   GET    /api/v1/products?page=&limit=  → DashboardWireResponse (dashboard-owned endpoint)
 *   DELETE /api/v1/products/{id}          → 204 No Content (soft-delete, backend W3-BE-15)
 *
 * Auth: jwtInterceptor attaches `Authorization: Bearer` automatically.
 * NO manual Authorization header. NO raw HttpClient — ApiClient only.
 *
 * Architecture note: This endpoint is OWNED by the dashboard module (BACKEND_ARCHITECTURE.md §2.7/§13.B).
 * The catalog MFE calls it as a consumer but defines its own local types (CatalogListWireItem,
 * DashboardWireResponse) — it does NOT import from mfe-dashboard. This is the section-parallel
 * model isolation rule.
 *
 * Feature-scoped — NOT providedIn: 'root'.
 * Provided via catalog.routes.ts path:'' providers:[CatalogListApiService] (added in Wave 3.2).
 *
 * Error matrix (gate REJECTS if absent):
 *   listProducts:
 *     401 → of(emptyListResponse) — auth expired (interceptor already retried); graceful empty
 *     404 → of(emptyListResponse) — not expected (empty inventory = 200+[]); guard against it
 *     5xx → rethrow             — component renders MeeAlertBanner + retry button
 *     other → rethrow
 *
 *   deleteProduct:
 *     204/200 → EMPTY (void completion) — row removed by component
 *     401     → EMPTY — refreshInterceptor owns auth cascade; component keeps row
 *     404     → EMPTY — already gone / cross-tenant; info-leak-safe treat-as-success idiom
 *     5xx     → rethrow — component surfaces non-blocking error and keeps the row
 *     other   → rethrow
 *
 * V1: page-1-only (no pagination UI). Component always calls listProducts({ page: 1, limit: 20 }).
 */

import { Injectable, inject } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { EMPTY, Observable, of } from 'rxjs';
import { map, catchError } from 'rxjs/operators';

import { ApiClient } from '@mesell/core';

import {
  DashboardWireResponse,
  CatalogListResponse,
  adaptDashboardResponse,
  emptyListResponse,
} from './catalog-list.model';

/** Server-bound params for GET /api/v1/products. */
export interface ListProductsParams {
  page: number;
  limit?: number;
}

@Injectable()
export class CatalogListApiService {
  private readonly api = inject(ApiClient);

  /**
   * listProducts — GET /api/v1/products?page=&limit=
   *
   * Maps DashboardWireResponse → CatalogListResponse via adapter.
   * onboarding_completeness is present on the wire and is intentionally dropped.
   *
   * @param params - page (1-based) + optional limit (default 20)
   * @returns Observable<CatalogListResponse>
   */
  listProducts(params: ListProductsParams): Observable<CatalogListResponse> {
    const limit = params.limit ?? 20;
    return this.api
      .get<DashboardWireResponse>('/api/v1/products', {
        params: { page: params.page, limit },
      })
      .pipe(
        map(wire => adaptDashboardResponse(wire)),
        catchError((err: HttpErrorResponse) => {
          if (err.status === 401 || err.status === 404) {
            return of(emptyListResponse(params.page, limit));
          }
          throw err;
        }),
      );
  }

  /**
   * deleteProduct — DELETE /api/v1/products/{id}
   *
   * Soft-deletes the product on the backend (W3-BE-15).
   * Completes without emitting a value on success (204/200).
   * 401 and 404 are both treated as silent completions (no emission):
   *   — 401: refreshInterceptor owns auth cascade; caller keeps the row.
   *   — 404: product already gone (or cross-tenant); info-leak-safe treat-as-success.
   * 5xx/other rethrows so the component can surface a non-blocking error toast
   * and keep the row in the list.
   *
   * @param id - product UUID (CatalogListItem.id)
   * @returns Observable<void> — completes on success/404/401; errors on 5xx
   */
  deleteProduct(id: string): Observable<void> {
    return this.api
      .delete<void>(`/api/v1/products/${id}`)
      .pipe(
        map(() => undefined as void),
        catchError((err: HttpErrorResponse) => {
          if (err.status === 401 || err.status === 404) {
            return EMPTY;
          }
          throw err;
        }),
      );
  }
}
