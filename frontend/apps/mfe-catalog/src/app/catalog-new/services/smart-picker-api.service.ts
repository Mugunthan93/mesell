import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay } from 'rxjs/operators';

export interface CategorySuggestion {
  id: string;
  path: string;
  confidence: number;
  commission_pct: number;
}

export interface CreateProductRequest {
  category_id: string;
}

export interface CreateProductResponse {
  id: string;
  category_id: string;
  status: 'draft';
}

const SIMULATED_SUGGESTIONS: CategorySuggestion[] = [
  {
    id: 'cat-kurti-uuid',
    path: 'Fashion > Women > Ethnic > Kurti',
    confidence: 94,
    commission_pct: 5,
  },
  {
    id: 'cat-kurta-set-uuid',
    path: 'Fashion > Women > Ethnic > Kurta Set',
    confidence: 71,
    commission_pct: 6,
  },
  {
    id: 'cat-tunic-uuid',
    path: 'Fashion > Women > Tops > Tunic',
    confidence: 52,
    commission_pct: 7,
  },
];

/**
 * Feature-scoped service — no providedIn.
 * Must be listed in the route's providers[] array.
 * Wave 5: all responses are simulated; Wave 6 will wire real HTTP via ApiClient.
 */
@Injectable()
export class SmartPickerApiService {
  /**
   * GET /api/v1/categories/suggest?q=<description>
   * Simulated: returns SIMULATED_SUGGESTIONS after 1200ms.
   */
  suggest(_description: string): Observable<CategorySuggestion[]> {
    return of(SIMULATED_SUGGESTIONS).pipe(delay(1200));
  }

  /**
   * POST /api/v1/products
   * Simulated: returns a draft product after 500ms.
   */
  createProduct(request: CreateProductRequest): Observable<CreateProductResponse> {
    return of({
      id: 'draft-' + Date.now(),
      category_id: request.category_id,
      status: 'draft' as const,
    }).pipe(delay(500));
  }
}
