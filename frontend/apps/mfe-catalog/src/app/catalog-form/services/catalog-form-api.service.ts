/**
 * CatalogFormApiService — Wave 6 Wave C
 *
 * Real HTTP wiring for the catalog-form funnel page.
 * Replaces the Wave 5 all-mock service.
 *
 * Endpoints:
 *   #15  GET  /api/v1/categories/{id}/schema          → SchemaResponseDTO (ETag deferred V1)
 *   #16  GET  /api/v1/categories/{id}/field-enum/{n}  → FieldEnumResponseDTO (lazy, on dropdown-open)
 *   #18  PATCH /api/v1/products/{id}                  → ProductResponse (X-Autosave header)
 *   #19  POST  /api/v1/products/{id}/autofill          → AutofillResponse (FEATURE_AI_AUTOFILL_ENABLED)
 *   #22  GET   /api/v1/products/{id}/draft             → ProductDraftResponse | null (204 → null)
 *
 * Auth: jwtInterceptor (Wave A, frozen) attaches `Authorization: Bearer` automatically.
 * NO manual Authorization header. NO raw HttpClient — ApiClient only (mirror DashboardApiService).
 *
 * Feature-scoped — NOT providedIn: 'root'.
 * Provided via catalog.routes.ts :id/edit providers:[CatalogFormApiService] (already wired).
 *
 * ETag: V1 does NOT send If-None-Match. Backend returns 200+body on every call.
 * 304 is unreachable in V1 — documented here; no client-side ETag logic.
 *
 * GAP-1 (spec §4): No GET /products/{id} exists. category_id must be passed via
 * navigation state from smart-picker. On hard-reload where nav-state is absent the
 * form shows an explicit error state (see catalog-form.component.ts).
 *
 * GAP-2 (spec §4): FEATURE_CATALOG_FORM_ENABLED=false → #18/#19/#22 return 404.
 *   FEATURE_AI_AUTOFILL_ENABLED=false → #19 returns 404.
 * All 404s are handled gracefully per the error matrix below.
 *
 * Error matrix (R-W6-1 — merge gate REJECTS if absent):
 *
 *   getSchema:
 *     401 → rethrow (component renders error state)
 *     404 → of([]) — schema/category not found OR flag OFF → graceful empty schema
 *     5xx → of([]) — component shows retry affordance
 *     other → of([])
 *
 *   getDraft:
 *     204/404 → of(null) — never autosaved / feature flag OFF → graceful
 *     401 → rethrow (component handles)
 *     5xx → of(null) — non-fatal for draft recovery
 *
 *   autosave:
 *     401 → rethrow (component sets saveStatus='error')
 *     422 → rethrow (component surfaces field-level errors; user input preserved)
 *     400 → rethrow (caller's validation is responsible)
 *     5xx → rethrow (component shows autosave failure, preserves user input)
 *
 *   autofill:
 *     401 → rethrow (component handles)
 *     402 → rethrow status=402 (component shows "AI fill quota reached" toast)
 *     404 → rethrow status=404 (flag OFF → component disables AI button)
 *     5xx → rethrow (component shows retry toast)
 *
 *   getFieldEnum:
 *     any error → of([]) — graceful; dropdown shows empty
 */

import { Injectable, inject } from '@angular/core';
import { HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { map, catchError } from 'rxjs/operators';

import { ApiClient } from '@mesell/core';

import {
  SchemaResponseDTO,
  FieldEnumResponseDTO,
  EnumEntryDTO,
  ProductResponse,
  ProductDraftResponse,
  AutofillResponse,
  FieldGroup,
  adaptSchemaResponse,
} from '../models/field-schema.model';

// ── Endpoint path constants (single source of truth, R-W6-1) ──────────────────
const CATEGORIES_PATH = '/api/v1/categories';
const PRODUCTS_PATH   = '/api/v1/products';

/**
 * CatalogFormApiService — feature-scoped, route-provided.
 * Inject ApiClient from @mesell/core barrel only (no raw HttpClient).
 */
@Injectable()
export class CatalogFormApiService {
  private readonly api = inject(ApiClient);

  // ── #15 — GET /categories/{id}/schema ─────────────────────────────────────

  /**
   * getSchema — fetches the category field schema and adapts flat list → FieldGroup[].
   *
   * @param categoryId - UUID of the category (from navigation state — GAP-1 interim)
   * @returns Observable<FieldGroup[]> — 3-section view-model; [] on non-401 error
   *
   * ETag: deferred V1 — no If-None-Match sent → always 200+body.
   * retryOn503: DEFERRED — ApiClient retry fires on all errors (not just 503),
   * so using it would incorrectly retry 401/404 responses. Deferred until
   * ApiClient retry is filtered by status code.
   */
  getSchema(categoryId: string): Observable<FieldGroup[]> {
    return this.api
      .get<SchemaResponseDTO>(`${CATEGORIES_PATH}/${categoryId}/schema`)
      .pipe(
        map(dto => adaptSchemaResponse(dto)),
        catchError((err: HttpErrorResponse) => {
          if (err.status === 401) throw err;
          // 404: schema not found OR FEATURE_CATALOG_FORM_ENABLED=false → graceful empty
          // 5xx: server unavailable → graceful empty + component shows retry affordance
          return of([] as FieldGroup[]);
        }),
      );
  }

  // ── #22 — GET /products/{id}/draft ────────────────────────────────────────

  /**
   * getDraft — fetches autosaved field values for resume-on-reload.
   *
   * @param productId - UUID of the product
   * @returns Observable<ProductDraftResponse | null>
   *   null → 204 (never autosaved), 404 (flag OFF or not found), or 5xx (graceful)
   *
   * Note: HttpClient maps a 204 response (no body) to null body — not an error.
   * The catchError handles network errors and flag-OFF 404s uniformly as null.
   */
  getDraft(productId: string): Observable<ProductDraftResponse | null> {
    return this.api
      .get<ProductDraftResponse | null>(`${PRODUCTS_PATH}/${productId}/draft`)
      .pipe(
        catchError((err: HttpErrorResponse) => {
          if (err.status === 401) throw err;
          // 404: feature flag OFF or product not found → graceful null
          // 5xx / 0 (network): non-fatal for draft recovery → graceful null
          return of(null);
        }),
      );
  }

  // ── #18 — PATCH /products/{id} (autosave) ─────────────────────────────────

  /**
   * autosave — sends a PATCH with the current field values.
   *
   * X-Autosave: true header signals the backend this is an incremental autosave.
   * PatchProductRequest requires ≥1 of fields/status — sending {fields} satisfies it.
   *
   * @param productId - UUID of the product
   * @param fields    - current form values (Record<string, unknown>)
   * @returns Observable<ProductResponse>
   *
   * Errors are re-thrown so the component can:
   *   - 401: set saveStatus='error', show toast (refreshInterceptor already retried)
   *   - 422: surface field-level validation errors from the error envelope
   *   - 400: log (should not occur if FE validates)
   *   - 5xx: show autosave failure banner; user input is NEVER lost
   */
  autosave(productId: string, fields: Record<string, unknown>): Observable<ProductResponse> {
    return this.api
      .patch<ProductResponse>(
        `${PRODUCTS_PATH}/${productId}`,
        { fields },
        { headers: new HttpHeaders({ 'X-Autosave': 'true' }) },
      )
      .pipe(
        catchError((err: HttpErrorResponse) => {
          throw err;
        }),
      );
  }

  // ── #19 — POST /products/{id}/autofill ────────────────────────────────────

  /**
   * autofill — calls the AI autofill endpoint.
   *
   * @param productId   - UUID of the product
   * @param description - product description (1..2000 chars, REQUIRED by backend schema)
   * @returns Observable<AutofillResponse>
   *
   * Errors are re-thrown so the component can:
   *   - 402: show "AI fill quota reached" toast (plan guard)
   *   - 404: disable the AI fill button (FEATURE_AI_AUTOFILL_ENABLED=false — GAP-2)
   *   - 5xx: show retry toast
   */
  autofill(productId: string, description: string): Observable<AutofillResponse> {
    return this.api
      .post<AutofillResponse>(
        `${PRODUCTS_PATH}/${productId}/autofill`,
        { description },
      )
      .pipe(
        catchError((err: HttpErrorResponse) => {
          throw err;
        }),
      );
  }

  // ── #16 — GET /categories/{id}/field-enum/{name} ──────────────────────────

  /**
   * getFieldEnum — lazy-loads options for `dropdown_api_search` fields.
   * Called on dropdown-open event, not on page-load.
   *
   * @param categoryId - UUID of the category
   * @param fieldName  - canonical_name of the field (e.g. 'brand')
   * @returns Observable<EnumEntryDTO[]> — [] on any error (graceful)
   *
   * All errors → of([]) — dropdown shows empty, user can type in a free-text field.
   */
  getFieldEnum(categoryId: string, fieldName: string): Observable<EnumEntryDTO[]> {
    return this.api
      .get<FieldEnumResponseDTO>(
        `${CATEGORIES_PATH}/${categoryId}/field-enum/${fieldName}`,
      )
      .pipe(
        map(resp => resp.enum_entries),
        catchError(() => of([] as EnumEntryDTO[])),
      );
  }
}

// Re-export DTOs and adapters for consumers that import from this service path.
export type {
  SchemaResponseDTO,
  SchemaFieldDTO,
  FieldEnumResponseDTO,
  EnumEntryDTO,
  ProductResponse,
  ProductDraftResponse,
  AutofillResponse,
  AutofillSuggestion,
  FieldGroup,
  FieldSchema,
} from '../models/field-schema.model';
export { adaptSchemaResponse, adaptSchemaField, mapPrimitiveToWidget } from '../models/field-schema.model';
