import { Injectable, inject } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { Observable, EMPTY, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { Router } from '@angular/router';

import { ApiClient, AuthService } from '@mesell/core';
import type { ImageUploadResponse, ImagesListResponse } from './image-uploader.model';

/**
 * ImageService — feature-scoped (NO providedIn).
 * Must be listed in the ImageUploaderComponent providers[] array.
 *
 * ## HTTP wiring (Wave D reconcile — D-IMG-1)
 * Uses ApiClient from @mesell/core. The global jwtInterceptor (registered in
 * apps/mfe-catalog/src/main.ts via withInterceptors([jwtInterceptor, ...])) attaches
 * Authorization: Bearer automatically from AuthService.getToken() (FE-D5 in-memory).
 * No manual authHeaders() is required or permitted.
 *
 * ## Retry policy
 * Upload (POST) — NO retry. Non-idempotent: retrying would double-enqueue + double-bill GCS.
 * Poll (GET) — NO ApiClient retryOn503 (defective: retries ALL errors, not just 503).
 *   Resilience comes from the caller's bounded recursive-setTimeout backoff (D18-class).
 *
 * ## Error surface decision (DIP — matches DashboardApiService / ExportApiService)
 * NO MeeToastService is injected here. Errors surface through the returned observable
 * shape only (EMPTY or safe fallback). The component layer decides whether to surface
 * a toast/snackbar.
 *
 * ## Error matrix
 * ### upload():
 *   401 → AuthService.logout() + navigate('/login') + EMPTY (refreshInterceptor already tried)
 *   402 → EMPTY (plan quota exceeded; caller shows plan-upgrade state)
 *   404 → EMPTY (FEATURE_IMAGE_PRECHECK_ENABLED=false; caller shows disabled state)
 *   400 → EMPTY (bad idx or invalid file; caller-validated responsibility)
 *   5xx → EMPTY
 *
 * ### listImages() / pollImages():
 *   401 → AuthService.logout() + navigate('/login') + EMPTY (post-refresh-failure fallback)
 *   404 → of({ images: [] })  (defensive; backend returns 200+{images:[]} when flag off)
 *   5xx → of({ images: [] })
 *   400 → of({ images: [] })
 */
@Injectable()
export class ImageService {
  private readonly api    = inject(ApiClient);
  private readonly router = inject(Router);
  private readonly auth   = inject(AuthService);

  // ── Private error handlers ────────────────────────────────────────────────────

  /** Error handler for upload() — per-method matrix. */
  private handleUploadError(err: HttpErrorResponse): Observable<never> {
    if (err.status === 401) {
      this.auth.logout();
      void this.router.navigate(['/login']);
    }
    // 401, 402, 404, 400, 5xx → all return EMPTY
    return EMPTY;
  }

  /** Error handler for listImages() / pollImages() — per-method matrix. */
  private handleListError(err: HttpErrorResponse): Observable<ImagesListResponse> {
    if (err.status === 401) {
      this.auth.logout();
      void this.router.navigate(['/login']);
      return EMPTY as Observable<ImagesListResponse>;
    }
    // 400 / 404 / 5xx → safe empty list
    return of({ images: [] });
  }

  // ── Public API ────────────────────────────────────────────────────────────────

  /**
   * POST /api/v1/products/{productId}/images
   *
   * Uploads a single image file for the given product at slot position idx (1–4).
   * Do NOT pass a Content-Type header — the browser sets multipart/form-data with
   * the correct boundary automatically when FormData is the request body.
   *
   * Returns 202 Accepted; the image transitions pending→ready|failed_precheck
   * asynchronously via a Celery worker. Use pollImages() to await resolution.
   *
   * @param productId — product UUID
   * @param file      — the File object to upload
   * @param idx       — slot index, 1-based (1..4, D1-LOCKED backend CHECK constraint)
   */
  upload(productId: string, file: File, idx: number): Observable<ImageUploadResponse> {
    const body = new FormData();
    body.append('file', file);
    body.append('idx', String(idx));

    // NOTE: Do NOT set Content-Type — browser sets multipart/form-data + boundary
    // NOTE: No retryOn503 — non-idempotent POST would double-enqueue
    return this.api
      .post<ImageUploadResponse>(`/api/v1/products/${productId}/images`, body)
      .pipe(
        catchError((err: HttpErrorResponse) => this.handleUploadError(err)),
      );
  }

  /**
   * GET /api/v1/products/{productId}/images
   *
   * Fetches the current image list (0–4 items, idx ASC).
   * Returns { images: [] } when no images exist or the feature flag is off.
   *
   * @param productId — product UUID
   */
  listImages(productId: string): Observable<ImagesListResponse> {
    // NOTE: No retryOn503 — ApiClient retry is defective (retries ALL errors, not just 503)
    return this.api
      .get<ImagesListResponse>(`/api/v1/products/${productId}/images`)
      .pipe(
        catchError((err: HttpErrorResponse) => this.handleListError(err)),
      );
  }

  /**
   * Backoff-poll GET /api/v1/products/{productId}/images until all images are resolved.
   *
   * Poll schedule (single-flight; no leaked timers):
   *   Delay before each poll (ms): 1000 → 2000 → 4000 → 8000 → 16000 → 30000 (cap).
   *   Maximum 6 polls; real stop is earlier once no image has status==='pending'.
   *
   * Implementation: recursive Observable constructor with setTimeout (D18-class pattern).
   *   - Each poll waits `delay`, fires one HTTP GET via ApiClient, then either completes
   *     (no pending) or schedules the next poll (pollIndex + 1, next delay from schedule).
   *   - takeWhile equivalent: the recursive chain stops naturally when hasPending() is
   *     false OR when pollIndex reaches MAX_POLLS - 1 (hard cap).
   *   - The teardown function clears the live setTimeout handle and cancels any in-flight
   *     HTTP subscription, so unsubscribing before completion leaves no leaked handles.
   *
   * Retry policy: NO ApiClient retryOn503 (defective). This bounded recursive-setTimeout
   * backoff IS the retry and resilience mechanism (D18-class, preserved exactly per spec).
   *
   * @param productId — product UUID
   */
  pollImages(productId: string): Observable<ImagesListResponse> {
    // Delay (ms) before poll at index n (0-based); index beyond array uses last value.
    const DELAYS_MS = [1000, 2000, 4000, 8000, 16000, 30000];
    const MAX_POLLS = DELAYS_MS.length; // 6 total polls hard cap

    const hasPending = (r: ImagesListResponse): boolean =>
      r.images.some((img) => img.status === 'pending');

    const poll = (pollIndex: number): Observable<ImagesListResponse> => {
      const delayMs = DELAYS_MS[Math.min(pollIndex, DELAYS_MS.length - 1)];

      return new Observable<ImagesListResponse>((subscriber) => {
        let done = false;
        let timerHandle: ReturnType<typeof setTimeout> | undefined;
        let httpSub: { unsubscribe(): void } | undefined;

        timerHandle = setTimeout(() => {
          // NOTE: No retryOn503 — D18 bounded backoff is the resilience mechanism
          httpSub = this.api
            .get<ImagesListResponse>(`/api/v1/products/${productId}/images`)
            .pipe(catchError((err: HttpErrorResponse) => this.handleListError(err)))
            .subscribe({
              next: (response) => {
                if (done) return;
                subscriber.next(response);
                if (!hasPending(response) || pollIndex >= MAX_POLLS - 1) {
                  // All resolved (or hard cap reached) — complete the stream
                  done = true;
                  subscriber.complete();
                } else {
                  // Schedule next poll and propagate its emissions to our subscriber
                  const nextSub = poll(pollIndex + 1).subscribe({
                    next: (r) => { if (!done) subscriber.next(r); },
                    error: (e: unknown) => { if (!done) subscriber.error(e); },
                    complete: () => { if (!done) subscriber.complete(); },
                  });
                  subscriber.add(() => nextSub.unsubscribe());
                }
              },
              error: (e: unknown) => {
                if (!done) subscriber.error(e);
              },
            });
        }, delayMs);

        // Teardown: cancel timer and in-flight HTTP on unsubscribe
        return () => {
          done = true;
          clearTimeout(timerHandle);
          httpSub?.unsubscribe();
        };
      });
    };

    return poll(0);
  }
}
