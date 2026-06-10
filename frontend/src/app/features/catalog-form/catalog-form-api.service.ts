// features/catalog-form/catalog-form-api.service.ts
// CatalogFormApiService — feature-scoped per §11.C coordinator decision.
// NOT providedIn: 'root' — provided via CATALOG_FORM_ROUTES providers array.
//
// CRITICAL: autosaveProduct MUST include the X-Autosave: true header per
// BACKEND_ARCHITECTURE.md §10.B.2 + §11.A.1 amendment. Without it, the
// backend only updates products.fields_jsonb (manual save path). With it,
// the backend additionally upserts the product_drafts row (autosave path).

import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiClient } from '@core/api/api-client.service';
import { AiSuggestion } from '@core/models/ai-suggestion.model';

// ─── Feature-local types ─────────────────────────────────────────────────────

/**
 * Full product detail shape returned by GET /api/v1/products/:id
 * and PATCH /api/v1/products/:id.
 *
 * NOTE: This differs from @core/models/product.model.ts (Product) which mirrors
 * the DB ORM shape with catalogId/userId camelCase fields. The actual API
 * response shape uses snake_case backend fields remapped as below.
 * TODO(cross-cutting): Reconcile Product model with actual API response shape
 * once backend §10 CATALOG module is locked.
 */
export interface ProductDetail {
  readonly id: string;
  readonly leafCategoryId: string;
  readonly leafCategoryName: string;
  readonly superCategoryId: string;
  readonly status: 'draft' | 'ready' | 'exported';
  readonly fields: Record<string, unknown>;
  readonly aiSuggestions: Record<string, Pick<AiSuggestion, 'value' | 'confidence' | 'accepted' | 'rejectedReason'>>;
  readonly createdAt: string;
  readonly updatedAt: string;
}

/**
 * Response from POST /api/v1/products/:id/autofill.
 * fallback_offered: true when budget is exhausted but cached/heuristic suggestions
 * are returned. This is still HTTP 200 — do NOT treat as error.
 */
export interface AutofillResponse {
  readonly suggestions: Record<string, { suggested_value: unknown; confidence: number }>;
  readonly fieldsFilled: number;
  readonly fallbackOffered: boolean;
}

// ─── Service ──────────────────────────────────────────────────────────────────

@Injectable()
export class CatalogFormApiService {
  private readonly api = inject(ApiClient);

  /**
   * GET /api/v1/products/:id
   * Fetches full product detail including field values and AI suggestions.
   * 404 propagates as ApiError with code 'catalog.product_not_found'.
   */
  getProduct(productId: string): Observable<ProductDetail> {
    return this.api.get<ProductDetail>(`/products/${productId}`);
  }

  /**
   * PATCH /api/v1/products/:id — manual save path.
   * NO X-Autosave header. Only updates products.fields_jsonb server-side.
   * Partial update: only the provided fields are merged (server-side merge).
   */
  saveProduct(productId: string, fields: Record<string, unknown>): Observable<ProductDetail> {
    return this.api.patch<ProductDetail>(`/products/${productId}`, { fields });
  }

  /**
   * PATCH /api/v1/products/:id — autosave path.
   * MUST include X-Autosave: true header per §10.B.2 + §11.A.1 amendment.
   * With this header, backend additionally upserts product_drafts row.
   * Rate limit: 600/h per-IP. On 429, ApiClient propagates ApiError.
   */
  autosaveProduct(productId: string, fields: Record<string, unknown>): Observable<ProductDetail> {
    return this.api.patch<ProductDetail>(
      `/products/${productId}`,
      { fields },
      { headers: { 'X-Autosave': 'true' } },
    );
  }

  /**
   * POST /api/v1/products/:id/autofill — triggers AI autofill.
   * retryOn503: true — Gemini cold starts may cause transient 503s.
   * Rate limit: 50/h per user. 429 propagates as ApiError.
   */
  requestAutofill(productId: string): Observable<AutofillResponse> {
    return this.api.post<AutofillResponse>(
      `/products/${productId}/autofill`,
      {},
      { retryOn503: true },
    );
  }
}
