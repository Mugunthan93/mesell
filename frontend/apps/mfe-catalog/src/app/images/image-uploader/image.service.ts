import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders, HttpErrorResponse } from '@angular/common/http';
import { Observable, EMPTY, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { Router } from '@angular/router';

import { AuthService } from '@mesell/core';
import type { ImageUploadResponse, ImagesListResponse } from './image-uploader.model';

/**
 * ImageService — feature-scoped (NO providedIn).
 * Must be listed in the ImageUploaderComponent providers[] array.
 *
 * ## HTTP wiring
 * Uses HttpClient directly (no global JWT interceptor — Wave 6 gap).
 * Bearer token is attached manually from AuthService.getToken().
 *
 * Migration note: when the global JWT interceptor ships (Wave 7 — see
 * frontend/src/app/core/interceptors/auth.interceptor.ts), add
 * withInterceptors([jwtInterceptor]) to provideHttpClient() in app.config.ts
 * AND apps/mfe-catalog/src/main.ts, then remove the authHeaders() helper and
 * the per-request { headers } option from this service.
 *
 * ## Error surface decision (DIP — matches CategoryService)
 * NO MeeToastService is injected here. Errors surface through the returned
 * observable shape only (EMPTY or safe fallback). The component layer decides
 * whether to surface a toast/snackbar.
 *
 * ## Error matrix
 * ### upload():
 *   401 → AuthService.logout() + return EMPTY (session invalidated)
 *   402 → return EMPTY (plan quota exceeded; caller shows plan-upgrade state)
 *   404 → return EMPTY (FEATURE_IMAGE_PRECHECK_ENABLED=false; caller shows disabled state)
 *   400 → return EMPTY (bad idx or invalid file; caller-validated responsibility)
 *   5xx → return EMPTY
 *
 * ### listImages() / pollImages():
 *   401 → AuthService.logout() + return EMPTY
 *   404 → return of({ images: [] })  (defensive; backend returns 200+{images:[]} when OFF)
 *   5xx → return of({ images: [] })
 *   400 → return of({ images: [] })
 */
@Injectable()
export class ImageService {
  private readonly http   = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly auth   = inject(AuthService);

  // ── Private helpers ───────────────────────────────────────────────────────────

  /**
   * Build Authorization header from the in-memory token (FE-D5: never localStorage).
   * Returns empty HttpHeaders when no token is present (unauthenticated state).
   */
  private authHeaders(): HttpHeaders {
    const token = this.auth.getToken();
    return token
      ? new HttpHeaders({ Authorization: `Bearer ${token}` })
      : new HttpHeaders();
  }

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

    return this.http
      .post<ImageUploadResponse>(`/api/v1/products/${productId}/images`, body, {
        headers: this.authHeaders(),
        // NOTE: Do NOT set Content-Type — browser sets multipart/form-data + boundary
      })
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
    return this.http
      .get<ImagesListResponse>(`/api/v1/products/${productId}/images`, {
        headers: this.authHeaders(),
      })
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
   * Implementation: recursive Observable constructor with setTimeout.
   *   - Each poll waits `delay`, fires one HTTP GET, then either completes (no pending)
   *     or schedules the next poll (pollIndex + 1, next delay from the schedule).
   *   - takeWhile equivalent: the recursive chain stops naturally when hasPending() is
   *     false OR when pollIndex reaches MAX_POLLS - 1 (hard cap).
   *   - The teardown function clears the live setTimeout handle and cancels any in-flight
   *     HTTP subscription, so unsubscribing before completion leaves no leaked handles.
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
          httpSub = this.http
            .get<ImagesListResponse>(`/api/v1/products/${productId}/images`, {
              headers: this.authHeaders(),
            })
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
