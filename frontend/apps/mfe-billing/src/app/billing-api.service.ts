/**
 * BillingApiService — the 4 billing endpoint methods.
 *
 * Route-scoped (@Injectable() NOT providedIn:'root') — provided in billing.routes.ts
 * so the service travels with the Routes-array expose (D28a/D32 precedent from mfe-catalog).
 * Consumed by plans.component.ts and account-billing.component.ts.
 *
 * Contract source: handoff_contract_razorpay.md §2 + WAVE5_FRONTEND_TASKSPEC.md §7.
 *
 * CRITICAL rules (see spec §1, §7):
 *  - withCredentials MUST be false/default (JWT Bearer path, NOT the cookie path).
 *    Billing routes use the access-token set by jwtInterceptor in the Authorization header.
 *    DO NOT pass { withCredentials: true } to any of these calls.
 *  - subscribe does NOT grant the plan — poll getSubscription() after widget closes.
 *  - catchError maps the ApiErrorEnvelope to typed BillingErrorShape so components
 *    can switch on code/status without re-handling raw HttpErrorResponse.
 *  - 401s are intentionally NOT caught here — the refreshInterceptor/forceLogout
 *    chain owns them (pass-through is correct).
 */

import { Injectable, inject } from '@angular/core';
import { Observable, catchError, throwError } from 'rxjs';
import { HttpErrorResponse } from '@angular/common/http';

import { ApiClient } from '@mesell/core';

import type {
  BillingSubscribeRequest,
  BillingSubscribeResponse,
  BillingStartTrialResponse,
  BillingCancelResponse,
  BillingSubscriptionResponse,
  BillingErrorShape,
} from './billing.model';

// ─── Endpoint paths ───────────────────────────────────────────────────────────

const BILLING_SUBSCRIBE     = '/api/v1/billing/subscribe';
const BILLING_START_TRIAL   = '/api/v1/billing/start-trial';
const BILLING_CANCEL        = '/api/v1/billing/cancel';
const BILLING_SUBSCRIPTION  = '/api/v1/billing/subscription';

// ─── Error mapping ────────────────────────────────────────────────────────────

/**
 * Map an HttpErrorResponse to a typed BillingErrorShape.
 * 409 → BillingError (with validation_message_id code)
 * 404 → BillingError (billing.subscription.none_active for cancel path)
 * 502 → BillingProviderUnavailableError (Razorpay upstream outage)
 * 401 → re-throw (interceptor chain handles it)
 * others → BillingServerError
 */
function mapBillingError(rawErr: unknown): Observable<never> {
  if (!(rawErr instanceof HttpErrorResponse)) {
    return throwError((): BillingErrorShape => ({ kind: 'server_error', status: 0 }));
  }

  const err: HttpErrorResponse = rawErr;

  if (err.status === 401) {
    // Let the refresh interceptor + forceLogout chain handle this — never swallow.
    return throwError(() => err);
  }

  if (err.status === 502) {
    return throwError(
      (): BillingErrorShape => ({ kind: 'provider_unavailable', status: 502 }),
    );
  }

  if (err.status === 409 || err.status === 404) {
    // Backend error envelope: { detail, code, validation_message_id }
    const envelope = err.error as {
      detail?: string;
      validation_message_id?: string;
    } | null;

    return throwError(
      (): BillingErrorShape => ({
        kind: 'billing_error',
        code: envelope?.validation_message_id ?? `http.${err.status}`,
        detail: envelope?.detail ?? err.message,
        status: err.status,
      }),
    );
  }

  return throwError(
    (): BillingErrorShape => ({ kind: 'server_error', status: err.status }),
  );
}

// ─── Service ─────────────────────────────────────────────────────────────────

/**
 * BillingApiService — route-scoped (not providedIn:'root').
 * Provided in BILLING_ROUTES providers array so it is isolated to the billing
 * remote and not leaked into the shell or other remotes.
 */
@Injectable()
export class BillingApiService {
  private readonly api = inject(ApiClient);

  /**
   * POST /api/v1/billing/subscribe — initiate a subscription or LTD purchase.
   *
   * Returns BillingSubscribeResponse with the Razorpay checkout handle (ADVISORY).
   * The plan is NOT granted on 201 — open the widget, then poll getSubscription().
   *
   * On 201: caller opens Razorpay widget with checkout.key_id + subscription_id/order_id.
   * On 409 (billing.subscription.already_active): user already subscribed.
   * On 502: Razorpay upstream unavailable — show retry message.
   *
   * withCredentials is NOT set — JWT Bearer (jwtInterceptor provides the header).
   */
  subscribe(tier: BillingSubscribeRequest['tier']): Observable<BillingSubscribeResponse> {
    return this.api
      .post<BillingSubscribeResponse>(BILLING_SUBSCRIBE, { tier })
      .pipe(catchError(mapBillingError));
  }

  /**
   * POST /api/v1/billing/start-trial — start the 14-day app-side Pro trial.
   *
   * App-side only. No Razorpay, no charge. Grant is IMMEDIATE (unlike subscribe).
   * After 200 → call auth.refreshUser() to propagate new entitlement to the shell.
   *
   * On 409 (billing.trial.already_used): one trial per phone; hide CTA permanently.
   *
   * withCredentials is NOT set.
   */
  startTrial(): Observable<BillingStartTrialResponse> {
    return this.api
      .post<BillingStartTrialResponse>(BILLING_START_TRIAL, {})
      .pipe(catchError(mapBillingError));
  }

  /**
   * POST /api/v1/billing/cancel — schedule cancel at end of billing cycle.
   *
   * Schedules cancel_at_cycle_end. The subscription stays active until entitled_until.
   * The final plan downgrade is webhook-driven — do NOT flip to free in the UI.
   *
   * On 404 (billing.subscription.none_active): no active subscription to cancel.
   *   Treat as no-op; refresh the billing screen. This is the LTD path (perpetual).
   *
   * withCredentials is NOT set.
   */
  cancel(): Observable<BillingCancelResponse> {
    return this.api
      .post<BillingCancelResponse>(BILLING_CANCEL, {})
      .pipe(catchError(mapBillingError));
  }

  /**
   * GET /api/v1/billing/subscription — current billing status (DB-fresh).
   *
   * The canonical data source for the account-billing view.
   * ALSO the poll target after subscribe widget closes:
   *   poll until response.entitlement reflects the subscribed tier.
   *
   * On 404: FEATURE_BILLING_ENABLED is off — degrade gracefully (billing unavailable).
   * On 401: pass through (interceptor chain).
   *
   * withCredentials is NOT set.
   */
  getSubscription(): Observable<BillingSubscriptionResponse> {
    return this.api
      .get<BillingSubscriptionResponse>(BILLING_SUBSCRIPTION)
      .pipe(catchError(mapBillingError));
  }
}
