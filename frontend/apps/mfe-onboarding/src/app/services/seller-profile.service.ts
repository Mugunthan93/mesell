/**
 * SellerProfileService — HTTP wiring for the customer-profile endpoints.
 *
 * Endpoints served (all JWT-authenticated; interceptor chain: jwt→refresh→error):
 *   #7  GET  /api/v1/seller-profile           → getProfile()
 *   #8  PATCH /api/v1/seller-profile          → patchProfile()
 *   #9  PATCH /api/v1/seller-profile/active-categories  → patchActiveCategories() [STUB — Option A deferred]
 *   #10 PATCH /api/v1/seller-profile/compliance/{id}    → [DEFERRED — follow-up slice]
 *   #11 GET  /api/v1/seller-profile/required-fields     → getRequiredFields()
 *
 * Scope: mfe-onboarding ONLY (remote-private, SP05 D32).
 * Scoping: @Injectable() with NO providedIn — components list this in providers[].
 *
 * Error matrix (R-W6-1 — MUST be present; merge gate rejects without it):
 *   401  → refreshInterceptor retries silently; terminal 401 → logout() already
 *          handled by the interceptor chain. Method returns FRESH_SELLER_PROFILE
 *          (for getProfile) or rethrows (for patches) so the component can show
 *          a banner without crashing.
 *   402  → plan_guard — customer module is plan_guard-EXCLUDED (router docstring);
 *          treated same as 5xx (fallback + rethrow).
 *   404  → getProfile: 404 means "no profile row yet" (first-time seller).
 *          Map to FRESH_SELLER_PROFILE (NOT an error banner).
 *          getRequiredFields: 404 should not occur; map to empty RequiredFieldsResponse.
 *          patchProfile: 404 should not occur (PATCH creates on first write).
 *   422  → validation error (bad pincode / extra="forbid" rejection).
 *          Extract `detail`/`validation_message_id`/`errors` from the typed envelope.
 *          Rethrow a ProfileValidationError so the component can map to field errors.
 *   5xx  → rethrow with a ProfileNetworkError for the component banner.
 *
 * No manual Authorization header — jwtInterceptor owns Bearer attachment.
 * No localStorage / sessionStorage access.
 * No withCredentials (not a cookie-auth endpoint).
 *
 * Wave 6 · Wave B · lane 2 — authored by meesell-angular-service-builder (session-1).
 */

import { Injectable, inject } from '@angular/core';
import { HttpErrorResponse, HttpStatusCode } from '@angular/common/http';
import { Observable, of, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { ApiClient } from '@mesell/core';
import type { ApiErrorEnvelope } from '@mesell/core';

import type {
  SellerProfile,
  PatchProfileRequest,
  PatchActiveCategoriesRequest,
  RequiredFieldsResponse,
} from '../seller-profile.model';
import { FRESH_SELLER_PROFILE } from '../seller-profile.model';

// ─────────────────────────────────────────────────────────────────────────────
// Typed error classes (for component-level catchError / template state)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Thrown when the backend returns 422.
 * Carries the typed error envelope so the component can map to field-level errors.
 */
export class ProfileValidationError extends Error {
  constructor(
    public readonly envelope: Partial<ApiErrorEnvelope>,
    public readonly status: number = HttpStatusCode.UnprocessableEntity,
  ) {
    super(
      envelope.validation_message_id ??
        envelope.detail ??
        'Validation failed — check the highlighted fields.',
    );
    this.name = 'ProfileValidationError';
  }
}

/**
 * Thrown for 5xx / unexpected errors.
 * Carries the original HttpErrorResponse for logging.
 */
export class ProfileNetworkError extends Error {
  constructor(
    public readonly originalError: HttpErrorResponse,
    message = 'A network error occurred. Please try again.',
  ) {
    super(message);
    this.name = 'ProfileNetworkError';
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Endpoint paths — single source of truth per spec §3.1
// ─────────────────────────────────────────────────────────────────────────────

const SELLER_PROFILE_PATH = '/api/v1/seller-profile';
const ACTIVE_CATEGORIES_PATH = '/api/v1/seller-profile/active-categories';
const REQUIRED_FIELDS_PATH = '/api/v1/seller-profile/required-fields';

const EMPTY_REQUIRED_FIELDS: RequiredFieldsResponse = {
  base_fields: [],
  extension_fields: {},
  completed: {},
};

// ─────────────────────────────────────────────────────────────────────────────
// SellerProfileService
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Route-scoped service — list in component's providers[] array.
 * NOT providedIn:'root' (mfe-onboarding-private state, SP05 D32 / spec §3.1 B5).
 */
@Injectable()
export class SellerProfileService {
  private readonly api = inject(ApiClient);

  // ---------------------------------------------------------------------------
  // #7 GET /api/v1/seller-profile
  // ---------------------------------------------------------------------------

  /**
   * Load the seller's profile from the backend.
   *
   * Error matrix:
   *   - 404 → no profile row yet (first-time seller); returns FRESH_SELLER_PROFILE.
   *   - 401 → interceptor handles retry; terminal 401 → interceptor calls logout().
   *           Returns FRESH_SELLER_PROFILE so the UI stays functional.
   *   - 422 → unexpected for a GET; throws ProfileValidationError.
   *   - 5xx → throws ProfileNetworkError.
   */
  getProfile(): Observable<SellerProfile> {
    return this.api.get<SellerProfile>(SELLER_PROFILE_PATH).pipe(
      catchError((err: unknown) => this.handleGetProfileError(err)),
    );
  }

  // ---------------------------------------------------------------------------
  // #8 PATCH /api/v1/seller-profile
  // ---------------------------------------------------------------------------

  /**
   * Submit the base SellerProfile fields.
   * Only send fields this method is given — the backend uses extra="forbid".
   * Pincode fields MUST match ^\d{6}$ or a 422 is returned.
   *
   * Error matrix:
   *   - 422 → throws ProfileValidationError (carries validation_message_id + errors[]).
   *   - 401 → interceptor handles retry; terminal 401 → interceptor calls logout().
   *           Rethrows a ProfileNetworkError so the component can navigate.
   *   - 5xx → throws ProfileNetworkError.
   *   - 404 → should not occur (PATCH creates on first write); treats as 5xx.
   */
  patchProfile(body: PatchProfileRequest): Observable<SellerProfile> {
    return this.api.patch<SellerProfile>(SELLER_PROFILE_PATH, body).pipe(
      catchError((err: unknown) => this.handleMutationError(err)),
    );
  }

  // ---------------------------------------------------------------------------
  // #11 GET /api/v1/seller-profile/required-fields
  // ---------------------------------------------------------------------------

  /**
   * Load the FieldSpec wizard schema that drives the onboarding form.
   * base_fields drives the base-profile section; extension_fields drives
   * per-super compliance sections (deferred to follow-up slice for UI).
   *
   * Error matrix:
   *   - 404 → unexpected; returns EMPTY_REQUIRED_FIELDS (graceful degradation).
   *   - 401 → interceptor handles retry; terminal 401 → interceptor logout.
   *           Returns EMPTY_REQUIRED_FIELDS so the form still renders (static fallback).
   *   - 5xx → throws ProfileNetworkError.
   */
  getRequiredFields(): Observable<RequiredFieldsResponse> {
    return this.api.get<RequiredFieldsResponse>(REQUIRED_FIELDS_PATH).pipe(
      catchError((err: unknown) => this.handleRequiredFieldsError(err)),
    );
  }

  // ---------------------------------------------------------------------------
  // #9 PATCH /api/v1/seller-profile/active-categories — STUB (Option A defer)
  // ---------------------------------------------------------------------------

  /**
   * STUB — deferred to a follow-up slice per Founder ruling OPTION A.
   * Active-categories picker is a multi-step surface (spec §2.6 + §3.1 B2).
   * Typed correctly so component-builder can reference it when the follow-up slice ships.
   */
  patchActiveCategories(_body: PatchActiveCategoriesRequest): Observable<SellerProfile> {
    return this.api.patch<SellerProfile>(ACTIVE_CATEGORIES_PATH, _body).pipe(
      catchError((err: unknown) => this.handleMutationError(err)),
    );
  }

  // ---------------------------------------------------------------------------
  // Private error handlers
  // ---------------------------------------------------------------------------

  private handleGetProfileError(err: unknown): Observable<SellerProfile> {
    if (err instanceof HttpErrorResponse) {
      if (err.status === HttpStatusCode.NotFound) {
        // 404 = first-time seller, no profile row yet. This is expected — not an error.
        return of({ ...FRESH_SELLER_PROFILE });
      }
      if (err.status === HttpStatusCode.Unauthorized) {
        // 401 terminal (refresh already tried by refreshInterceptor).
        // Return fresh profile so the UI does not crash before the redirect completes.
        return of({ ...FRESH_SELLER_PROFILE });
      }
      if (err.status === HttpStatusCode.UnprocessableEntity) {
        return throwError(() => new ProfileValidationError(this.extractEnvelope(err)));
      }
    }
    // 5xx, network errors, unexpected status
    return throwError(
      () => new ProfileNetworkError(
        err instanceof HttpErrorResponse ? err : new HttpErrorResponse({ status: 0 }),
      ),
    );
  }

  private handleRequiredFieldsError(err: unknown): Observable<RequiredFieldsResponse> {
    if (err instanceof HttpErrorResponse) {
      if (
        err.status === HttpStatusCode.NotFound ||
        err.status === HttpStatusCode.Unauthorized
      ) {
        // Graceful degradation — return empty shape; static form fallback renders.
        return of({ ...EMPTY_REQUIRED_FIELDS });
      }
    }
    return throwError(
      () => new ProfileNetworkError(
        err instanceof HttpErrorResponse ? err : new HttpErrorResponse({ status: 0 }),
      ),
    );
  }

  private handleMutationError(err: unknown): Observable<never> {
    if (err instanceof HttpErrorResponse) {
      if (err.status === HttpStatusCode.UnprocessableEntity) {
        return throwError(() => new ProfileValidationError(this.extractEnvelope(err)));
      }
    }
    return throwError(
      () => new ProfileNetworkError(
        err instanceof HttpErrorResponse ? err : new HttpErrorResponse({ status: 0 }),
      ),
    );
  }

  /**
   * Extract the typed error envelope from a 422 HttpErrorResponse.
   * Backend emits: { detail, code, validation_message_id, request_id, errors? }
   * (errors.interceptor.ts ApiErrorEnvelope — errorInterceptor already normalised it).
   */
  private extractEnvelope(err: HttpErrorResponse): Partial<ApiErrorEnvelope> {
    const body = err.error as Partial<ApiErrorEnvelope> | null;
    return body ?? {};
  }
}
