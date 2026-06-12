/**
 * pricing.service.ts — PricingApiService.
 * Wires POST /api/v1/products/{id}/price-calc (endpoint #25, V1_FEATURE_SPEC §5).
 *
 * Scoping: @Injectable() with NO providedIn — route/component-scoped.
 * Listed in PricingComponent.providers[] → tree-shakes with the lazy route chunk.
 * Mirror pattern: DashboardApiService (Wave B) + ExportApiService (Wave C export-lane).
 *
 * API client: inject(ApiClient) from @mesell/core — jwtInterceptor attaches Bearer.
 * NO raw HttpClient, NO manual auth headers (interceptors own the auth layer, Wave A).
 * NO ApiClient retryOn503 (defective — retries ALL errors, not 503-only; and this is
 *   a POST — even a correct retry would risk non-idempotent behaviour, spec §3.2).
 * Degradation matrix (R-W6-1, DECISION-1 — NEVER a local-math fallback):
 *   401  → EMPTY                          (refreshInterceptor handles retry; logout path owns it)
 *   404  → emit PriceCalcUnavailableError  (flag off OR product not found)
 *   422  → emit PriceCalcCommissionMissingError (no commission rate for category)
 *   400  → emit PriceCalcValidationError   (Pydantic constraint violation)
 *   5xx  → emit PriceCalcServerError       (§3.1: explicit error + retry affordance)
 *   non-HTTP / network → emit PriceCalcServerError (§3.1: explicit error + retry affordance)
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
  PriceCalcServerError,
} from './pricing.model';

/** Endpoint path constant — single source of truth (no duplication across service + spec). */
const PRICE_CALC_PATH = (productId: string) =>
  `/api/v1/products/${productId}/price-calc`;

@Injectable()
export class PricingApiService {
  private readonly api = inject(ApiClient);

  /**
   * POST /api/v1/products/{productId}/price-calc
   *
   * On 200: emits PriceCalcResponse (all monetary fields are Decimal strings, R-W6-6).
   * On error: emits a PriceCalcErrorShape (404/422/400) or EMPTY (401/5xx).
   * NEVER computes a local fallback — server-calc only (DECISION-1 + R-W6-1).
   *
   * @param productId UUID of the product (from route :id param)
   * @param body      {input_cost, target_margin_pct} — Decimal strings to preserve 2dp precision
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

  /** Maps HTTP errors to typed error shapes per the degradation matrix (spec §3.1). */
  private _handleError(
    err: unknown,
  ): Observable<PriceCalcErrorShape> {
    // Network drop or non-HTTP error → emit server_error so the component can render
    // the explicit "Couldn't calculate — please try again" banner (spec §3.1).
    if (!(err instanceof HttpErrorResponse)) {
      return of({ kind: 'server_error' } satisfies PriceCalcServerError);
    }

    const status = err.status;

    if (status === 401) {
      // refreshInterceptor (Wave A) already handled retry + re-login.
      // If we reach here the logout path fired — stay EMPTY (auth layer owns this).
      return EMPTY;
    }

    if (status === 404) {
      // Flag off (FEATURE_PRICE_CALCULATOR_ENABLED=false) or product not found / cross-tenant.
      const reason = err.error?.detail?.includes('not found') ? 'not_found' : 'flag_off';
      return of({ kind: 'unavailable', reason } as const);
    }

    if (status === 422) {
      // pricing.commission.missing — category has no usable commission rate.
      return of({
        kind: 'commission_missing',
        detail: err.error?.detail ?? 'Pricing is unavailable for this category.',
        error_code: err.error?.error_code ?? 'pricing.commission.missing',
      } as const);
    }

    if (status === 400) {
      // validation.price.invalid_input — Pydantic constraint (should be caught by FE validators).
      return of({
        kind: 'validation',
        detail: err.error?.detail ?? 'Invalid pricing input.',
      } as const);
    }

    // 5xx and any other HTTP status → emit server_error so the component can render
    // the explicit retry affordance banner (spec §3.1).
    return of({ kind: 'server_error' } satisfies PriceCalcServerError);
  }
}
