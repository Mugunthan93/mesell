import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Observable, EMPTY, of, throwError } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';
import { Router } from '@angular/router';

import { AuthService } from '@mesell/core';
import { environment } from '@mesell/env';
import type { BrowseResponse, SuggestResponse } from '../smart-picker.model';

/**
 * CategoryService — feature-scoped (no providedIn).
 * Must be listed in the SmartPickerComponent providers[] array.
 *
 * ## HTTP wiring (Wave 6 Wave A)
 * Uses HttpClient directly. Bearer token is now attached globally by jwtInterceptor
 * (registered in app.config.ts + all 6 remote main.ts). The manual authHeaders() helper
 * has been REMOVED — it is no longer necessary.
 *
 * ## Error surface decision (lead ruling — mesell-smart-picker-port-frontend-session-2)
 * NO root MeeToastService is wired to services in this slice. MeeToastService lives in
 * @mesell/ui-kit but the service layer has no injected reference to it. Errors surface
 * through the returned fallback shape only (SOLID DIP).
 *
 * ## Error matrix (finding #4 aligned)
 * - 401 → AuthService.logout() + return EMPTY (session invalidated)
 * - 402 → return of({ suggestions: [], fallback_offered: true }) (plan-guard quota exceeded)
 * - 404 → return of({ suggestions: [], fallback_offered: true }) (feature flag off — silent degrade)
 * - 5xx → return of({ suggestions: [], fallback_offered: true }) (AI unavailable — silent degrade)
 * - 400, 422, 429 → throwError(() => err) — component decides toast vs inline
 */
@Injectable()
export class CategoryService {
  private readonly http   = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly auth   = inject(AuthService);

  // ── Private helpers ────────────────────────────────────────────────────────

  /**
   * Shared error handler for CategoryService.suggest().
   * Maps HTTP error codes to the contract fallback shapes per the error matrix above.
   * Does NOT use MeeToastService — surfaces errors through observable shape only.
   *
   * Error matrix (finding #4 aligned):
   * - 401 → logout + EMPTY
   * - 402 → fallback shape (plan quota)
   * - 404 → fallback shape (feature flag off — not surfaced to user as error)
   * - 422, 400, 429 → throwError (validation / rate-limit — component surfaces inline copy or toast)
   * - 5xx → fallback shape (AI unavailable — degrade gracefully, show browse CTA)
   */
  private handleSuggestError(
    err: HttpErrorResponse,
  ): Observable<SuggestResponse> {
    if (err.status === 401) {
      this.auth.logout();
      return EMPTY;
    }
    if (err.status === 402 || err.status === 404 || err.status >= 500) {
      // Plan quota exceeded, feature flag off, or server error → graceful fallback shape
      return of({ suggestions: [], fallback_offered: true });
    }
    // 400, 422, 429 → rethrow so the component can surface correct inline copy or toast
    return throwError(() => err);
  }

  // ── Public API ─────────────────────────────────────────────────────────────

  /**
   * POST /api/v1/categories/suggest { q: description }
   *
   * Returns up to 5 CategorySuggestion items (§9.E — LOCKED).
   * Frontend renders top 3 (SmartPickerComponent.suggestions().slice(0, 3)).
   *
   * Backend contract (finding #4 — POST migration):
   * - Body: { "q": "<1 to 5000 characters>" }  — extra fields forbidden (extra="forbid")
   * - 200 always returned for AI failures (fallback_offered=true, suggestions=[]) — never 503
   * - 422 when q is empty, > 5000 chars, or extra fields are present
   * - 401 auth-gated
   * - 402 plan-guard quota exceeded
   * - 404 when FEATURE_SMART_PICKER_ENABLED=false
   *
   * @param description — product description string (1–5000 chars). Validation is the caller's responsibility.
   */
  suggest(description: string): Observable<SuggestResponse> {
    return this.http
      .post<SuggestResponse>(`${environment.apiBase}/api/v1/categories/suggest`, { q: description })
      .pipe(
        catchError((err: HttpErrorResponse) => this.handleSuggestError(err)),
      );
  }

  /**
   * Shared error handler for CategoryService.browse().
   * Maps HTTP error codes to the contract fallback shapes.
   * - 401 → AuthService.logout() + return EMPTY (session invalidated)
   * - 4xx/5xx → return empty results fallback shape
   */
  private handleBrowseError(err: HttpErrorResponse): Observable<BrowseResponse> {
    if (err.status === 401) {
      this.auth.logout();
      return EMPTY;
    }
    if (err.status === 400 || err.status === 422) {
      // Validation errors → rethrow so browse.component.ts can show inline error
      return throwError(() => err);
    }
    // 404, 429, 5xx → return empty results (browse degrades gracefully)
    return of({ results: [], total: 0 });
  }

  /**
   * GET /api/v1/categories/browse?q=<query>[&super_id=<uuid>]&limit=<n>&offset=<n>
   *
   * Returns paginated BrowseResultRow items matching the query string.
   * Supports optional super_id filter to restrict results to one top-level group.
   *
   * @param q       — search string
   * @param superId — optional super-category UUID filter
   * @param limit   — page size (default 20)
   * @param offset  — pagination offset (default 0)
   */
  browse(q: string, superId?: string, limit = 20, offset = 0): Observable<BrowseResponse> {
    let params = new HttpParams()
      .set('q', q)
      .set('limit', String(limit))
      .set('offset', String(offset));
    if (superId) params = params.set('super_id', superId);
    return this.http
      .get<BrowseResponse>(`${environment.apiBase}/api/v1/categories/browse`, { params })
      .pipe(catchError((err: HttpErrorResponse) => this.handleBrowseError(err)));
  }

  /**
   * POST /api/v1/products { category_id }
   *
   * DISCREPANCY-1 fix (DECISION-2 — Wave 6 Wave A): re-pointed from /api/v1/catalogs.
   * Creates a new product draft for the selected category.
   *   - catalog_id: null → backend auto-creates a default-named catalog (CreateProductRequest §2.4)
   *   - name: null → defaults to "Untitled product"
   *   - Response id is a PRODUCT id; /catalogs/:id/edit navigation is correct (route loads by product id)
   *
   * The component mirrors the simulated contract shape — callers subscribe and
   * receive Observable<{ id: string }>. The navigation side-effect fires inside
   * tap() so the component does not need to manage routing itself.
   *
   * @param categoryId — UUID of the selected leaf category
   */
  selectCategory(categoryId: string): Observable<{ id: string }> {
    return this.http
      .post<{ id: string }>(`${environment.apiBase}/api/v1/products`, { category_id: categoryId })
      .pipe(
        tap((product) => {
          void this.router.navigate(['/catalogs', product.id, 'edit']);
        }),
        catchError((_err: HttpErrorResponse) => EMPTY),
      );
  }

  /**
   * Navigate to the manual category browse page.
   * Delegates routing to Router so the component stays decoupled.
   */
  browseRedirect(): void {
    void this.router.navigate(['/categories/browse']);
  }
}
