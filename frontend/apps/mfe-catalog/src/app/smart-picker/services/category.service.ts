import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay } from 'rxjs/operators';

import type { CategorySuggestion, SuggestResponse } from '../smart-picker.model';

// Simulated response using §9.E-locked shapes.
// service-builder (Phase B) replaces the of(...) bodies with real HttpClient calls.
const SIMULATED_RESPONSE: SuggestResponse = {
  suggestions: [
    {
      category_id: 'cat-kurti-uuid',
      super_id: 'super-fashion-uuid',
      super_name: 'Fashion',
      path: 'Fashion > Women > Ethnic > Kurti',
      leaf_name: 'Kurti',
      confidence: 0.94,
      reasons: ['Top seller in Fashion Women', 'Mirror work matches Ethnic Kurti attributes'],
    },
    {
      category_id: 'cat-kurta-set-uuid',
      super_id: 'super-fashion-uuid',
      super_name: 'Fashion',
      path: 'Fashion > Women > Ethnic > Kurta Set',
      leaf_name: 'Kurta Set',
      confidence: 0.71,
      reasons: ['Matching top and bottom set typically Kurta Set category'],
    },
    {
      category_id: 'cat-tunic-uuid',
      super_id: 'super-fashion-uuid',
      super_name: 'Fashion',
      path: 'Fashion > Women > Tops > Tunic',
      leaf_name: 'Tunic',
      confidence: 0.52,
      reasons: ['Single top garment alternative'],
    },
  ],
  fallback_offered: false,
};

/**
 * CategoryService — feature-scoped service. No providedIn.
 * Provided via the SmartPickerComponent providers:[CategoryService] array.
 *
 * Phase A (this commit): D4 rename from SmartPickerApiService. Simulated bodies preserved.
 * Phase B (service-builder): replaces of(SIMULATED_RESPONSE) with real HttpClient.get calls.
 *
 * Method signatures match §9.E SuggestResponse — do NOT change signatures.
 */
@Injectable()
export class CategoryService {
  /**
   * GET /api/v1/categories/suggest?q=<description>
   * Returns SuggestResponse with up to 5 CategorySuggestion items (§9.E).
   * Simulated: returns SIMULATED_RESPONSE after 1200ms.
   */
  suggest(_description: string): Observable<SuggestResponse> {
    return of(SIMULATED_RESPONSE).pipe(delay(1200));
  }

  /**
   * POST /api/v1/catalogs — creates a catalog with the picked category, then navigates.
   * Returns an object with the new catalog id.
   * Simulated: returns a draft catalog after 500ms.
   */
  selectCategory(_categoryId: string): Observable<{ id: string }> {
    return of({ id: 'draft-catalog-' + Date.now() }).pipe(delay(500));
  }

  /**
   * Navigate to the manual category browse page (/categories/browse).
   * Phase B: service-builder replaces this with Router.navigate(['/categories/browse']).
   */
  browseRedirect(): void {
    // Phase B: Router.navigate(['/categories/browse'])
  }
}
