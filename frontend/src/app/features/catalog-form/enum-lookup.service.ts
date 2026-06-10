// features/catalog-form/enum-lookup.service.ts
// EnumLookupService — server-side fuzzy search for dropdown_api primitive values.
// NOT providedIn: 'root' — provided via CATALOG_FORM_ROUTES providers array.
//
// GET /api/v1/categories/:id/enum/:field_name?q=<query>&limit=<n>
//   200 — EnumValue[] (code + label pairs)
//
// IMPORTANT: code is the Meesho export value (never shown to seller).
//            label is the display label shown to the seller per CORE_PHILOSOPHY M4.
//            The dropdown_api primitive MUST bind to `label` for display,
//            and pass `code` to the form value only at export time.

import { inject, Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';
import { ApiClient } from '@core/api/api-client.service';

// ─── Feature-local type ───────────────────────────────────────────────────────

/**
 * A single enumerated value for a category field.
 * code  — Meesho's export identifier (never display to seller)
 * label — Human-readable display label per CORE_PHILOSOPHY M4
 */
export interface EnumValue {
  readonly code: string;
  readonly label: string;
}

/** Shape returned by the API endpoint (wraps the array with metadata) */
interface EnumLookupResponse {
  readonly field_name: string;
  readonly values: Array<{ code: string; label: string }>;
}

// ─── Service ──────────────────────────────────────────────────────────────────

@Injectable()
export class EnumLookupService {
  private readonly api = inject(ApiClient);

  /**
   * Fetches enum values for a category field via server-side fuzzy search.
   *
   * @param categoryId  UUID of the leaf category
   * @param fieldName   canonical_name of the field (e.g. 'fabric_type')
   * @param query       Fuzzy search term entered by the seller (e.g. 'cotton')
   * @param limit       Max results to return; defaults to 20
   *
   * Returns an Observable of EnumValue[] — an empty array when no matches.
   */
  lookupEnum(
    categoryId: string,
    fieldName: string,
    query: string,
    limit?: number,
  ): Observable<EnumValue[]> {
    const params: Record<string, string | number> = {
      q: query,
      limit: limit ?? 20,
    };
    return this.api
      .get<EnumLookupResponse>(`/categories/${categoryId}/enum/${fieldName}`, { params })
      .pipe(map(res => res.values));
  }
}
