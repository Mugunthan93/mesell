// core/auth/auth.service.ts
// AuthService — per §4.C + FE-D5 (NO localStorage writes; in-memory signal only).
// The access token is an in-memory signal lost on page reload by design.
// Bootstrap is the ONLY way the app recovers a token across reloads.

import { computed, inject, Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { catchError, map, Observable, of, tap } from 'rxjs';
import { API_BASE_URL } from '@core/tokens/api-base-url.token';
import { decodeJwt, JwtPayload, UUID } from './jwt-payload.model';
import { PlanTier } from '@shared/enums/plan-tier.enum';

interface RefreshResponse {
  access_token: string;
  expires_in: number;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly baseUrl = inject(API_BASE_URL);

  /** Scheduled refresh timer handle */
  private refreshTimer: ReturnType<typeof setTimeout> | null = null;

  // ── Signals (the public reactive surface) ──

  /**
   * In-memory access token per FE-D5.
   * NEVER write to localStorage, sessionStorage, IndexedDB, or document.cookie.
   * Lost on page reload by design; bootstrap() recovers it.
   */
  readonly accessToken = signal<string | null>(null);

  readonly userId = computed<UUID | null>(() => this.decodePayload()?.sub ?? null);

  readonly plan = computed<PlanTier | null>(() => this.decodePayload()?.plan ?? null);

  readonly isAuthenticated = computed<boolean>(() => this.accessToken() !== null);

  // ── Internal helpers ──

  private decodePayload(): JwtPayload | null {
    return decodeJwt(this.accessToken());
  }

  // ── Lifecycle methods ──

  /**
   * Called by AuthGuard.canActivate when accessToken is null.
   * Fires POST /api/v1/auth/refresh; emits true on success, false on 401.
   * The browser sends the HttpOnly refresh cookie automatically.
   * Schedules the next refresh via scheduleRefresh().
   */
  bootstrap(): Observable<boolean> {
    return this.http.post<RefreshResponse>(
      `${this.baseUrl}/auth/refresh`,
      null,
      { withCredentials: true },
    ).pipe(
      tap(response => this.setAccess(response)),
      map(() => true),
      catchError(() => of(false)),
    );
  }

  /**
   * Called by AccountApiService after successful /auth/otp/verify,
   * or by RefreshInterceptor after successful /auth/refresh.
   * Updates the in-memory accessToken signal and schedules refresh.
   */
  setAccess(response: { access_token: string; expires_in: number }): void {
    this.accessToken.set(response.access_token);
    this.scheduleRefresh(response.expires_in);
  }

  /**
   * Schedules a silent refresh at (expiresInSeconds - 30s).
   * The 30-second safety margin prevents racing the 401 window.
   * No env coupling — trusts the expires_in value from the backend per FE-D6.
   * Cancels any previously scheduled refresh.
   */
  scheduleRefresh(expiresInSeconds: number): void {
    if (this.refreshTimer !== null) {
      clearTimeout(this.refreshTimer);
      this.refreshTimer = null;
    }
    const delayMs = Math.max((expiresInSeconds - 30) * 1000, 0);
    this.refreshTimer = setTimeout(() => {
      this.http.post<RefreshResponse>(
        `${this.baseUrl}/auth/refresh`,
        null,
        { withCredentials: true },
      ).pipe(
        catchError(() => {
          // Silent refresh failed — let the next API call hit 401 and RefreshInterceptor recover,
          // or AuthGuard on next navigation
          this.clear();
          return of(null);
        }),
      ).subscribe(response => {
        if (response) this.setAccess(response);
      });
    }, delayMs);
  }

  /**
   * Called by navbar logout button.
   * Fires POST /api/v1/auth/logout (backend revokes Valkey allowlist + clears cookie).
   * Clears the in-memory accessToken signal. Navigates to /.
   */
  logout(): Observable<void> {
    this.clear();
    return this.http.post<void>(
      `${this.baseUrl}/auth/logout`,
      null,
      { withCredentials: true },
    ).pipe(
      tap(() => this.router.navigate(['/'])),
      catchError(() => {
        // Even if backend call fails, the client-side state is already cleared
        this.router.navigate(['/']);
        return of(undefined);
      }),
    );
  }

  /**
   * Called by ErrorInterceptor on unrecoverable 401 (refresh failed).
   * Wipes accessToken signal and cancels scheduled refresh.
   * Does NOT call /auth/logout — the server-side state is already gone.
   */
  clear(): void {
    this.accessToken.set(null);
    if (this.refreshTimer !== null) {
      clearTimeout(this.refreshTimer);
      this.refreshTimer = null;
    }
  }
}
