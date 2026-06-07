// features/catalog-form/category-schema.service.ts
// CategorySchemaService — fetches the field schema for a leaf category.
// Feature-private per §11.C coordinator decision — stays inside catalog-form.
// NOT providedIn: 'root' — provided via CATALOG_FORM_ROUTES providers array.
//
// GET /api/v1/categories/:id/schema?locale=en
//   200 — CategorySchema with fields array
//   Backend sends Cache-Control: max-age=86400, stale-while-revalidate=3600
//   No application-level cache here — browser HTTP cache handles it.

import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiClient } from '@core/api/api-client.service';
import { FieldSchema } from '@core/models/field-schema.model';

// ─── Feature-local type ───────────────────────────────────────────────────────

/**
 * Full category schema returned by GET /api/v1/categories/:id/schema.
 *
 * NOTE: @core/models/category.model.ts has a CategorySchema interface but it
 * lacks the `categoryName` field present in the actual API response.
 * Defining a richer feature-local type here to capture the full response.
 * TODO(cross-cutting): Update @core/models/category.model.ts to include
 * categoryName in CategorySchema, then remove this duplicate definition.
 */
export interface CategorySchemaFull {
  readonly categoryId: string;
  readonly categoryName: string;
  readonly fields: FieldSchema[];
}

// ─── Service ──────────────────────────────────────────────────────────────────

@Injectable()
export class CategorySchemaService {
  private readonly api = inject(ApiClient);

  /**
   * Fetches the full field schema for a leaf category.
   *
   * @param categoryId  UUID of the leaf category
   * @param locale      Locale code for label resolution; defaults to 'en'
   *
   * The backend returns Cache-Control: max-age=86400, stale-while-revalidate=3600.
   * No app-level caching is implemented — the browser HTTP cache is sufficient
   * for the schema's 24-hour TTL per §6.3 (MVP_ARCHITECTURE.md §6).
   */
  getSchema(categoryId: string, locale?: string): Observable<CategorySchemaFull> {
    const params: Record<string, string> = { locale: locale ?? 'en' };
    return this.api.get<CategorySchemaFull>(`/categories/${categoryId}/schema`, { params });
  }
}
