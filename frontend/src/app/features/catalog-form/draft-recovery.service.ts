// features/catalog-form/draft-recovery.service.ts
// DraftRecoveryService — fetches the latest autosaved draft for a product.
// NOT providedIn: 'root' — provided via CATALOG_FORM_ROUTES providers array.
//
// GET /api/v1/products/:id/draft
//   200 — draft exists; returns { fields, last_updated, autosave_count }
//   204 — no draft (product was never autosaved); returns null — NOT an error
//   404 — product not found; propagates as ApiError

import { inject, Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { ApiClient } from '@core/api/api-client.service';
import { ApiError } from '@core/api/api-error';

// ─── Feature-local type ───────────────────────────────────────────────────────

/**
 * Autosave draft shape returned by GET /api/v1/products/:id/draft (200 path).
 * The 204 path returns null (no draft exists yet) — this is the common initial state.
 */
export interface ProductDraft {
  readonly fields: Record<string, unknown>;
  /** ISO-8601 timestamp of the last autosave write */
  readonly lastUpdated: string;
  readonly autosaveCount: number;
}

// ─── Service ──────────────────────────────────────────────────────────────────

@Injectable()
export class DraftRecoveryService {
  private readonly api = inject(ApiClient);

  /**
   * Fetches the latest autosave draft for the given product.
   *
   * Returns:
   *   ProductDraft  — when a draft exists (200 with body)
   *   null          — when no draft exists yet (204 — common initial state)
   *
   * Throws:
   *   ApiError (status 404) — when the product does not exist
   *
   * Implementation note: Angular's HttpClient emits null for a 204 response
   * body. This arrives as null through ApiClient.get<ProductDraft>() since
   * there is no body to deserialise. The `map` operator converts the null
   * body to a typed null return, satisfying Observable<ProductDraft | null>.
   * A catchError guard ensures any ApiError with status !== 404 is also
   * surfaced (404 propagates naturally as a thrown error).
   */
  getDraft(productId: string): Observable<ProductDraft | null> {
    return this.api.get<ProductDraft | null>(`/products/${productId}/draft`).pipe(
      // 200 with body → ProductDraft; 204 with null body → null
      map(res => res ?? null),
      catchError((err: unknown) => {
        // Re-throw everything except the 204-as-error edge case.
        // In practice Angular HttpClient does NOT throw on 204 for GET — it
        // returns null body. This guard is a safety net for environments where
        // the HTTP adapter might behave differently.
        if (err instanceof ApiError && err.status === 204) {
          return of(null);
        }
        throw err;
      }),
    );
  }
}
