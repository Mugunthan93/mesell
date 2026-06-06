// features/dashboard/dashboard-api.service.ts
// Feature-scoped HTTP service for /products (list + delete) per §9.C + §13.B.1
// Provided in dashboard.routes.ts providers array — NOT providedIn: 'root'

import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiClient } from '@core/api/api-client.service';

// ── Response shape types (BFF-specific per §9.C — live here, not in @core/models/) ──

export interface ProductListItem {
  product_id: string;
  name: string | null;
  category_id: string;
  status: 'draft' | 'ready' | 'exported';
  created_at: string;
  updated_at: string;
}

export interface ProfileCompletenessSummary {
  base_complete_count: number;
  base_total_count: number;
  extension_complete_count: number;
  extension_total_count: number;
  profile_complete: boolean;
}

export interface DashboardResponse {
  products: ProductListItem[];
  total: number;
  page: number;
  limit: number;
  profile_completeness: ProfileCompletenessSummary;
}

// ── Query params (§13.B.1 exact param names) ──

export interface ProductListParams {
  page?: number;
  limit?: number;
  /** §13.B.1: "status_filter" — NOT "status" */
  status_filter?: 'draft' | 'ready' | 'exported' | null;
  /** §13.B.1: "search" — NOT "q"; max 100 chars */
  search?: string | null;
}

@Injectable()
export class DashboardApiService {
  private readonly api = inject(ApiClient);

  /**
   * GET /api/v1/products — paginated product list with profile completeness summary.
   * Filters out null/undefined values before passing to ApiClient (which accepts only
   * Record<string, string | number | boolean>).
   */
  listProducts(params: ProductListParams = {}): Observable<DashboardResponse> {
    const cleanParams: Record<string, string | number | boolean> = {};

    if (params.page != null) cleanParams['page'] = params.page;
    if (params.limit != null) cleanParams['limit'] = params.limit;
    if (params.status_filter != null) cleanParams['status_filter'] = params.status_filter;
    if (params.search != null && params.search !== '') cleanParams['search'] = params.search;

    return this.api.get<DashboardResponse>('/products', { params: cleanParams });
  }

  /** DELETE /api/v1/products/{id} → 204 No Content */
  deleteProduct(productId: string): Observable<void> {
    return this.api.delete<void>(`/products/${productId}`);
  }
}
