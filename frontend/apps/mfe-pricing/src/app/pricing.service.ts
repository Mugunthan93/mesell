/**
 * pricing.service.ts — PricingApiService (§12.M forward estimator, 2026-06-18).
 *
 * Wires POST /api/v1/products/{id}/price-calc (endpoint #25, V1_FEATURE_SPEC §5).
 * Backend contract: backend/app/modules/pricing/schemas.py (PR #285, commit fd4331d).
 *
 * Scoping: @Injectable() with NO providedIn — route/component-scoped.
 * Listed in PricingComponent.providers[] to tree-shake with the lazy route chunk.
 *
 * API client: inject(ApiClient) from @mesell/core — jwtInterceptor attaches Bearer.
 * NO raw HttpClient, NO manual auth headers (interceptors own the auth layer).
 * NO ApiClient retryOn503 — POST is non-idempotent (spec §3.2, permanent rule).
 *
 * §12.M changes vs §12.E:
 *   - Request primary field: meesho_price (was: input_cost + target_margin_pct).
 *   - 422 branch REMOVED: commission is now seller-entered (default 4%), never missing.
 *   - New response fields: wdrp_price, estimated_payout, estimated_payout_wdrp,
 *     margin_pct, markup_pct, total_deductions, referral_commission, shipping_charge,
 *     logistics_fee, fixed_fee, gst_on_fees, tcs, tds, rto_expected_loss.
 *   - Dead response fields: seller_price, commission_amount, gst_amount, profit_pct.
 *   - Dead alerts: HIGH_MRP_MULTIPLIER, THIN_PROFIT.
 *   - New alerts: NEGATIVE_PAYOUT, SHIPPING_DOMINATES.
 *
 * Degradation matrix (R-W6-1, DECISION-1 — NEVER a local-math fallback):
 *   401  → EMPTY                          (refreshInterceptor handles retry; logout path owns it)
 *   404  → emit PriceCalcUnavailableError (flag off OR product not found)
 *   400  → emit PriceCalcValidationError  (Pydantic constraint violation)
 *   5xx  → emit PriceCalcServerError      (§3.1: explicit error + retry affordance)
 *   non-HTTP / network → emit PriceCalcServerError
 *   422  → NOT a valid path (§12.M (4): 422 dead) — treated defensively as server_error
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

/** Endpoint path — single source of truth (no duplication across service + spec). */
const PRICE_CALC_PATH = (productId: string) =>
  `/api/v1/products/${productId}/price-calc`;

@Injectable()
export class PricingApiService {
  private readonly api = inject(ApiClient);

  /**
   * POST /api/v1/products/{productId}/price-calc (§12.M forward estimator).
   *
   * On 200: emits PriceCalcResponse (all monetary/pct fields are Decimal strings, R-W6-6).
   * On error: emits a PriceCalcErrorShape (404/400) or EMPTY (401).
   * 422 is structurally impossible in §12.M — treated defensively as server_error.
   * NEVER computes a local fallback — server-calc only (DECISION-1).
   *
   * @param productId UUID of the product (from route :id param)
   * @param body      PriceCalcRequest — meesho_price + input_cost required; all Decimal strings
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
  private _handleError(err: unknown): Observable<PriceCalcErrorShape> {
    // Network drop or non-HTTP error → emit server_error for the retry-affordance banner.
    if (!(err instanceof HttpErrorResponse)) {
      return of({ kind: 'server_error' } satisfies PriceCalcServerError);
    }

    const status = err.status;

    if (status === 401) {
      // refreshInterceptor (auth layer) already handled retry + re-login.
      // If we reach here the logout path fired — stay EMPTY (auth layer owns this).
      return EMPTY;
    }

    if (status === 404) {
      // Flag off (FEATURE_PRICE_CALCULATOR_ENABLED=false) or product not found / cross-tenant.
      // Backend detail: "Price Calculator is disabled..." (flag off)
      //                 contains "not found" phrase (cross-tenant ownership gate).
      const detail: string = err.error?.detail ?? '';
      const reason = detail.toLowerCase().includes('not found') ? 'not_found' : 'flag_off';
      return of({ kind: 'unavailable', reason } as const);
    }

    if (status === 400) {
      // validation.price.invalid_input — Pydantic constraint (meesho_price <= 0, etc.).
      // Form validators should prevent most; surface if server returns 400.
      return of({
        kind: 'validation',
        detail: err.error?.detail ?? 'Invalid pricing input.',
      } as const);
    }

    // 422 is structurally dead in §12.M (4), but treat defensively as server_error.
    // All 5xx and any other HTTP status → emit server_error for the retry-affordance banner.
    return of({ kind: 'server_error' } satisfies PriceCalcServerError);
  }
}
