// features/smart-picker/smart-picker-api.service.ts
// Feature-scoped HTTP service per §10.C and §3.D (NOT providedIn root)
// Scoped via smart-picker.routes.ts providers[] for lazy tree-shake

import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiClient } from '@core/api/api-client.service';
import {
  SuggestResponse,
  SuperCategoriesResponse,
  LeavesResponse,
  CreateProductResponse,
} from './smart-picker.model';

@Injectable()
export class SmartPickerApiService {
  private readonly api = inject(ApiClient);

  /**
   * POST /api/v1/categories/suggest
   * AI-powered category suggestion — backend caches by SHA-256(description) 24h
   * retryOn503: true because Gemini cold starts can trigger 503
   */
  suggest(description: string): Observable<SuggestResponse> {
    return this.api.post<SuggestResponse>(
      '/categories/suggest',
      { description },
      { retryOn503: true },
    );
  }

  /**
   * GET /api/v1/categories
   * Returns super-category list for browse fallback
   */
  getSuperCategories(): Observable<SuperCategoriesResponse> {
    return this.api.get<SuperCategoriesResponse>('/categories');
  }

  /**
   * GET /api/v1/categories/:superCategoryId/leaves?search=...&limit=20
   * Leaf-category search within a super-category (pg_trgm-backed)
   */
  searchLeaves(superCategoryId: string, search: string): Observable<LeavesResponse> {
    return this.api.get<LeavesResponse>(
      `/categories/${superCategoryId}/leaves`,
      { params: { search, limit: 20 } },
    );
  }

  /**
   * POST /api/v1/products
   * Creates a draft product with the selected leaf category.
   * 422 with detail:'customer.profile_incomplete_for_category' must be handled upstream.
   */
  createProduct(leafCategoryId: string): Observable<CreateProductResponse> {
    return this.api.post<CreateProductResponse>('/products', {
      leaf_category_id: leafCategoryId,
    });
  }
}
