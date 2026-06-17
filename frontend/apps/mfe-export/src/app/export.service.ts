/**
 * ExportApiService — real HTTP wiring for mfe-export (Wave 6 Wave C lane 2).
 *
 * Endpoints:
 *   #27  POST /api/v1/products/{product_id}/export-xlsx  → ExportInitiatedResponse (202)
 *   #28  GET  /api/v1/exports/{export_id}               → ExportResponseDTO (200)
 *
 * Auth: jwtInterceptor (Wave A, frozen) attaches `Authorization: Bearer` automatically.
 * NO manual Authorization header here.
 *
 * D18 TIMER-PRESERVE: The poll rhythm is driven by the component's setInterval, NOT by
 * RxJS interval/polling operators. This service exposes ONE single GET per call on poll().
 * The component calls poll() inside its setInterval tick and calls clearInterval when the
 * returned status is terminal (isTerminalStatus) or on ngOnDestroy.
 *
 * retryOn503 POLICY:
 *   - initiate (POST) → NO retry (non-idempotent — would double-enqueue the job).
 *   - poll (GET)    → retryOn503:true (idempotent read; backend may transiently 503 on restart).
 *
 * Error matrix (R-W6-1 — merge gate REJECTS if absent):
 *   POST initiate:
 *     401 → refreshInterceptor retries; if still 401, EMPTY (interceptor logged out; no crash)
 *     404 → flag-off OR product not found → of({ notReady: true, errorCode: 'export.unavailable' })
 *     422 → export.product_not_ready / export.front_image_missing → surface detail + error_code
 *     400 → bad request → EMPTY + console.error
 *     5xx → EMPTY + console.error (component will surface retry affordance)
 *   GET poll:
 *     401 → EMPTY (interceptor handles terminal logout; stop polling gracefully)
 *     404 → export record not found → ExportNotFoundError (component stops polling, shows error)
 *     5xx → EMPTY (poll loop will retry on next tick naturally — bounded by component's maxPolls)
 *
 * Feature-scoped service — NOT providedIn: 'root'.
 * Provided via ExportComponent.providers[] so it tree-shakes with the route chunk (D28a/D32).
 */
import { Injectable, inject } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { Observable, EMPTY, of, throwError, timer } from 'rxjs';
import { catchError, retry } from 'rxjs/operators';

import { ApiClient } from '@mesell/core';

import { ExportInitiatedResponse, ExportResponseDTO } from './export.model';

// ── Endpoint paths (single source of truth) ────────────────────────────────────
/** POST /api/v1/products/{product_id}/export-xlsx */
const EXPORT_INITIATE_PATH = (productId: string) =>
  `/api/v1/products/${productId}/export-xlsx`;

/** GET /api/v1/exports/{export_id} */
const EXPORT_STATUS_PATH = (exportId: string) =>
  `/api/v1/exports/${exportId}`;

// ── Error shapes (surface to component) ────────────────────────────────────────

/** Thrown by poll() when the export record is not found (404). */
export class ExportNotFoundError extends Error {
  constructor(exportId: string) {
    super(`Export record not found: ${exportId}`);
    this.name = 'ExportNotFoundError';
  }
}

/**
 * Emitted by initiate() when the backend returns 422 export.product_not_ready or
 * export.front_image_missing. Component should surface the error_code to the user.
 */
export interface InitiateValidationError {
  readonly kind: 'validation';
  readonly detail: string;
  readonly error_code: string | null;
}

/**
 * Emitted by initiate() when the backend returns 404 (flag-off or product not found).
 * The export router is flag-gated (FEATURE_XLSX_EXPORT_ENABLED).
 */
export interface InitiateUnavailableError {
  readonly kind: 'unavailable';
  readonly error_code: 'export.unavailable';
}

export type InitiateErrorShape = InitiateValidationError | InitiateUnavailableError;

@Injectable()
export class ExportApiService {
  private readonly api = inject(ApiClient);

  /**
   * POST /api/v1/products/{product_id}/export-xlsx
   *
   * Initiates XLSX export generation. Returns Observable<ExportInitiatedResponse> on 202.
   * On 422: emits an InitiateValidationError object (NOT a thrown error) so the component
   * can display the actionable message without crashing.
   * On 404 (flag-off / product not found): emits InitiateUnavailableError.
   * On 401 / 400 / 5xx: returns EMPTY (component renders error affordance).
   *
   * NEVER add retryOn503 here — POST is non-idempotent (double-enqueue risk, D18 spec §4.2).
   *
   * @param productId - the product UUID (from ActivatedRoute snapshot.params['id'])
   * @param format    - export format (V1 default: 'xlsx_with_images')
   */
  initiate(
    productId: string,
    format: 'xlsx_only' | 'xlsx_with_images' = 'xlsx_with_images',
  ): Observable<ExportInitiatedResponse | InitiateErrorShape> {
    return this.api
      .post<ExportInitiatedResponse>(EXPORT_INITIATE_PATH(productId), { format })
      .pipe(
        catchError((err: HttpErrorResponse) => {
          switch (err.status) {
            case 401:
              // refreshInterceptor has already retried + logged out on terminal 401.
              // Return EMPTY — component observes no emission and can show a generic error.
              return EMPTY;

            case 404: {
              // Flag-off (FEATURE_XLSX_EXPORT_ENABLED=false) OR product not found / cross-tenant.
              const unavailable: InitiateUnavailableError = {
                kind: 'unavailable',
                error_code: 'export.unavailable',
              };
              return of(unavailable);
            }

            case 422: {
              // export.product_not_ready / export.front_image_missing.
              // Surface to the component as an actionable error shape (GAP-1 Option A real gate).
              const body = err.error as { detail?: string; error_code?: string } | undefined;
              const validation: InitiateValidationError = {
                kind: 'validation',
                detail: body?.detail ?? 'Product is not ready for export.',
                error_code: body?.error_code ?? null,
              };
              return of(validation);
            }

            case 400:
              console.error('[ExportApiService] 400 on initiate — unexpected bad request', err);
              return EMPTY;

            default:
              // 5xx / network errors.
              console.error('[ExportApiService] initiate failed', err.status, err.message);
              return EMPTY;
          }
        }),
      );
  }

  /**
   * GET /api/v1/exports/{export_id}
   *
   * Fetches the current status of an export job. Called once per setInterval tick
   * (D18 timer-preserve — the component owns the interval, NOT this service).
   * retryOn503: true because GET is idempotent and 503 is common during pod restarts.
   *
   * On 404: throws ExportNotFoundError — component must clearInterval + surface error.
   * On 401: returns EMPTY — interceptor has logged out; component's interval keeps ticking
   *         but service returns nothing, so the component should cap with maxPolls.
   * On 5xx: returns EMPTY — next tick will retry naturally (bounded by maxPolls in component).
   *
   * @param exportId - the export UUID from ExportInitiatedResponse.export_id
   */
  /**
   * GET /api/v1/exports/{export_id}
   *
   * Fetches the current status of an export job. Called once per setInterval tick
   * (D18 timer-preserve — the component owns the interval, NOT this service).
   *
   * retryOn503 POLICY for poll: The retry is applied in THIS service's pipe, NOT via
   * ApiClient's retryOn503 option. Reason: ApiClient.applyRetry wraps retry() BEFORE
   * catchError, meaning ALL errors (including 404) would be retried. By applying retry
   * AFTER catchError here, we can distinguish 503 (re-throw to trigger retry) from
   * 404 (throw ExportNotFoundError — component stops polling) and 401 / 5xx (EMPTY).
   *
   * V1.5 CLEANUP: ApiClient.applyRetry is now status-filtered (503/504/network only —
   * frozen-surface amendment 2026-06-12), so a bare `{ retryOn503: true }` would no longer
   * retry a 404. This hand-rolled post-catchError retry can be simplified to the ApiClient
   * flag in V1.5. Left as-is for V1 (the bespoke pipe also encodes the 404→stop-polling
   * semantics, so the simplification is non-trivial — defer, do not rewire now).
   *
   * Pipe order: http.get → catchError → retry(on 503 only)
   *
   * On 404: throws ExportNotFoundError — component must clearInterval + surface error.
   * On 401: returns EMPTY — interceptor has logged out; component's interval keeps ticking
   *         but service returns nothing, so the component should cap with maxPolls.
   * On 503: re-throws so the retry(2, backoff) above can retry it up to 2 times.
   * On 5xx: returns EMPTY — next tick will retry naturally (bounded by maxPolls in component).
   *
   * @param exportId - the export UUID from ExportInitiatedResponse.export_id
   */
  poll(exportId: string): Observable<ExportResponseDTO> {
    return this.api
      .get<ExportResponseDTO>(EXPORT_STATUS_PATH(exportId))  // NO retryOn503 at ApiClient level
      .pipe(
        catchError((err: HttpErrorResponse) => {
          if (err.status === 404) {
            // Export record not found (race condition or wrong ID) — unrecoverable.
            return throwError(() => new ExportNotFoundError(exportId));
          }
          if (err.status === 401) {
            // Terminal 401 after refresh failure — interceptor already called logout().
            return EMPTY;
          }
          if (err.status === 503) {
            // Transient 503 (pod restart / backend overload) — re-throw to allow retry below.
            return throwError(() => err);
          }
          // 5xx / network: return EMPTY — next tick will retry naturally.
          console.error('[ExportApiService] poll error', err.status, err.message);
          return EMPTY;
        }),
        // Retry only on re-thrown 503 errors (from above). Max 2 retries, 1s/2s backoff.
        // retryWhen pattern: retry fires only if catchError re-threw (503 path).
        retry({
          count: 2,
          delay: (err: unknown, retryCount: number) => {
            // Only retry if this is the re-thrown 503 HttpErrorResponse.
            if (err instanceof HttpErrorResponse && err.status === 503) {
              return timer(retryCount * 1000);
            }
            // For ExportNotFoundError or other errors: don't retry — throw immediately.
            return throwError(() => err);
          },
        }),
      );
  }
}
