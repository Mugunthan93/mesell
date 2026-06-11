import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders, HttpErrorResponse } from '@angular/common/http';
import { Observable, EMPTY, of } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';
import { Router } from '@angular/router';

import { AuthService } from '@mesell/core';
import type { SuggestResponse } from '../smart-picker.model';

/**
 * CategoryService — feature-scoped (no providedIn).
 * Must be listed in the SmartPickerComponent providers[] array.
 *
 * ## HTTP wiring
 * Uses HttpClient directly (no global JWT interceptor exists in V1 — Wave 6 gap).
 * Bearer token is attached manually from AuthService.getToken().
 *
 * Migration note: when the global JWT interceptor ships (frontend/src/app/core/interceptors/
 * auth.interceptor.ts — deferred to Wave 7), add withInterceptors([authInterceptor]) to
 * provideHttpClient() in app.config.ts AND apps/mfe-catalog/src/main.ts, then remove the
 * authHeaders() helper and the per-request { headers } option from this service.
 *
 * ## Error surface decision (lead ruling — mesell-smart-picker-port-frontend-session-2)
 * NO root MeeToastService is wired to services in this slice. MeeToastService lives in
 * @mesell/ui-kit but the service layer has no injected reference to it. Errors surface
 * through the returned fallback shape only (SOLID DIP).
 *
 * ## Error matrix
 * - 401 → AuthService.logout() + return EMPTY (session invalidated)
 * - 402 → return of({ suggestions: [], fallback_offered: true }) (plan-guard quota exceeded)
 * - 400 → return EMPTY (invalid q param — caller's validation responsibility)
 * - 404 → return of({ suggestions: [], fallback_offered: true }) (FEATURE_SMART_PICKER_ENABLED=false)
 * - 5xx  → return of({ suggestions: [], fallback_offered: true }) (server unavailable)
 */
@Injectable()
export class CategoryService {
  private readonly http   = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly auth   = inject(AuthService);

  // ── Private helpers ────────────────────────────────────────────────────────

  /**
   * Build Authorization header from the in-memory token (FE-D5: never localStorage).
   * Returns an empty HttpHeaders if no token is present (public/unauthenticated state).
   */
  private authHeaders(): HttpHeaders {
    const token = this.auth.getToken();
    return token
      ? new HttpHeaders({ Authorization: `Bearer ${token}` })
      : new HttpHeaders();
  }

  /**
   * Shared error handler for CategoryService.suggest().
   * Maps HTTP error codes to the contract fallback shapes per the error matrix above.
   * Does NOT use MeeToastService — surfaces errors through observable shape only.
   */
  private handleSuggestError(
    err: HttpErrorResponse,
  ): Observable<SuggestResponse> {
    switch (err.status) {
      case 401:
        this.auth.logout();
        return EMPTY;
      case 402:
        return of({ suggestions: [], fallback_offered: true });
      case 400:
        return EMPTY;
      case 404:
        // Feature flag disabled (FEATURE_SMART_PICKER_ENABLED=false)
        return of({ suggestions: [], fallback_offered: true });
      default:
        // 5xx and any other error → graceful fallback shape
        return of({ suggestions: [], fallback_offered: true });
    }
  }

  // ── Public API ─────────────────────────────────────────────────────────────

  /**
   * GET /api/v1/categories/suggest?q=<description>
   *
   * Returns up to 5 CategorySuggestion items (§9.E — LOCKED).
   * Frontend renders top 3 (SmartPickerComponent.suggestions().slice(0, 3)).
   *
   * Backend contract:
   * - 200 always returned for AI failures (fallback_offered=true, suggestions=[]) — never 503
   * - 400 when q is outside 1..500 chars
   * - 401 auth-gated
   * - 402 plan-guard quota exceeded
   * - 404 when FEATURE_SMART_PICKER_ENABLED=false
   *
   * @param description — product description string (1–500 chars). Validation is the caller's responsibility.
   */
  suggest(description: string): Observable<SuggestResponse> {
    return this.http
      .get<SuggestResponse>('/api/v1/categories/suggest', {
        params: { q: description },
        headers: this.authHeaders(),
      })
      .pipe(
        catchError((err: HttpErrorResponse) => this.handleSuggestError(err)),
      );
  }

  /**
   * POST /api/v1/catalogs { category_id }
   *
   * Creates a new catalog draft for the selected category and navigates to
   * /catalogs/:id/edit on success.
   *
   * The component mirrors the simulated contract shape — callers subscribe and
   * receive Observable<{ id: string }>. The navigation side-effect fires inside
   * tap() so the component does not need to manage routing itself.
   *
   * @param categoryId — UUID of the selected leaf category
   */
  selectCategory(categoryId: string): Observable<{ id: string }> {
    return this.http
      .post<{ id: string }>('/api/v1/catalogs', { category_id: categoryId }, {
        headers: this.authHeaders(),
      })
      .pipe(
        tap((catalog) => {
          void this.router.navigate(['/catalogs', catalog.id, 'edit']);
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
