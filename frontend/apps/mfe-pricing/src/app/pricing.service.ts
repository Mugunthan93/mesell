/**
 * pricing.service.ts — PricingApiService.
 * Wires POST /api/v1/products/{id}/price-calc (endpoint #25, V1_FEATURE_SPEC §5).
 *
 * W3 REWRITE (2026-06-19): binds to W2 §2.1/§2.2 contract.
 *   NEW request body: { selling_price, commission_pct? } — backend extra="forbid".
 *   NEW 422 path: pricing.category.no_pricing_data (replaces retired commission_missing).
 *
 * Scoping: @Injectable() with NO providedIn — component-scoped.
 * Listed in PricingComponent.providers[] → tree-shakes with the lazy route chunk.
 *
 * API client: inject(ApiClient) from @mesell/core — jwtInterceptor attaches Bearer.
 * NO raw HttpClient. NO manual auth headers. Interceptors own the auth layer (Wave A).
 *
 * retryOn503: OFF permanently. Reason: POST is non-idempotent (spec §3.2). Even the
 * amended 503/504-only filter does not make a retry safe for a pricing POST that persists
 * a calculation row via pricing_repo.insert_calc().
 *
 * Degradation matrix (R-W6-1 — NEVER a local-math fallback):
 *   401  → EMPTY                           (refreshInterceptor handles retry/logout)
 *   404  → emit PriceCalcUnavailableError  (flag off OR product not found)
 *   422  → branch on error_code:
 *            pricing.category.no_pricing_data → PriceCalcNoPricingDataError
 *            other (Pydantic field constraint) → PriceCalcValidationError
 *   400  → emit PriceCalcValidationError   (defensive; W2 primarily uses 422)
 *   5xx / non-HTTP → emit PriceCalcServerError  (§3.1: explicit error + retry affordance)
 * The breakdown stays null on any error → component renders explicit error state.
 */

import { Injectable, inject } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { Observable, EMPTY, catchError, of } from 'rxjs';

import { ApiClient } from '@mesell/core';

import type {
  PriceCalcRequest,
  PriceCalcResponse,
  PriceCalcErrorShape,
  PriceCalcNoPricingDataError,
  PriceCalcServerError,
} from './pricing.model';

/** Endpoint path constant — single source of truth (no duplication across service + spec). */
const PRICE_CALC_PATH = (productId: string) =>
  `/api/v1/products/${productId}/price-calc`;

/** error_code emitted by W2 router when the product's category leaf is absent from the lookup. */
const NO_PRICING_DATA_CODE = 'pricing.category.no_pricing_data';

@Injectable()
export class PricingApiService {
  private readonly api = inject(ApiClient);

  /**
   * POST /api/v1/products/{productId}/price-calc
   *
   * On 200: emits PriceCalcResponse (all monetary fields are Decimal strings, R-W6-6).
   * On error: emits a typed PriceCalcErrorShape or EMPTY (401).
   * NEVER computes a local fallback — server-calc only (DECISION-1 + R-W6-1).
   *
   * @param productId  UUID of the product (from route :id param)
   * @param body       { selling_price, commission_pct? } — only these two fields;
   *                   backend extra="forbid" 422s on any extra key.
   *                   Omit commission_pct key entirely when not overriding (do NOT send "").
   */
  calc(
    productId: string,
    body: PriceCalcRequest,
  ): Observable<PriceCalcResponse | PriceCalcErrorShape> {
    return this.api
      .post<PriceCalcResponse>(PRICE_CALC_PATH(productId), body)
      .pipe(
        catchError((err: unknown) => this._handleError(err)),
      );
  }

  /**
   * Maps HTTP errors to typed error shapes per the W3 degradation matrix.
   * 422 is disambiguated: no_pricing_data (category lookup miss) vs validation (Pydantic).
   */
  private _handleError(
    err: unknown,
  ): Observable<PriceCalcErrorShape> {
    // Network drop or non-HTTP error → server_error (spec §3.1 explicit retry affordance).
    if (!(err instanceof HttpErrorResponse)) {
      return of({ kind: 'server_error' } satisfies PriceCalcServerError);
    }

    const status = err.status;

    if (status === 401) {
      // refreshInterceptor already handled retry + forced-logout path (Wave A).
      // Stay EMPTY — auth layer owns this; no emission to the component.
      return EMPTY;
    }

    if (status === 404) {
      // Flag off (FEATURE_PRICE_CALCULATOR_ENABLED=false) or product not found / cross-tenant.
      const reason = err.error?.detail?.includes('not found') ? 'not_found' : 'flag_off';
      return of({ kind: 'unavailable', reason } as const);
    }

    if (status === 422) {
      // Disambiguate between the two W2 422 paths:
      //   (a) pricing.category.no_pricing_data → category leaf absent from lookup → PriceCalcNoPricingDataError
      //   (b) Pydantic field constraint (e.g. selling_price<=0, extra="forbid" stale field) → PriceCalcValidationError
      const errorCode: string | undefined = err.error?.error_code;
      if (errorCode === NO_PRICING_DATA_CODE) {
        return of({
          kind: 'no_pricing_data',
          detail: err.error?.detail ?? 'Pricing is unavailable for this category.',
          error_code: errorCode,
        } satisfies PriceCalcNoPricingDataError);
      }
      // Pydantic validation 422 (selling_price format, extra field, etc.)
      return of({
        kind: 'validation',
        detail: err.error?.detail ?? 'Invalid pricing input.',
      } as const);
    }

    if (status === 400) {
      // Defensive: W2 primarily uses 422, but handle 400 for belt-and-suspenders.
      return of({
        kind: 'validation',
        detail: err.error?.detail ?? 'Invalid pricing input.',
      } as const);
    }

    // 5xx and any other HTTP status → server_error (spec §3.1 retry affordance).
    return of({ kind: 'server_error' } satisfies PriceCalcServerError);
  }
}
