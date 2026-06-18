import { Injectable, signal, computed, inject, OnDestroy } from '@angular/core';
import { Router } from '@angular/router';
import {
  Observable,
  switchMap,
  map,
  catchError,
  EMPTY,
  shareReplay,
  finalize,
} from 'rxjs';
import { AuthApiService } from './auth-api.service';
import type { MeResponse, RefreshResponse } from './auth-api.service';

/**
 * AuthUser — DECISION-3 additive-optional reconciliation.
 *
 * Legacy fields (id, name) kept OPTIONAL so existing inline constructors
 * (otp-verify mock, SP06 C4 smoke) don't break at compile time — they use
 * {id, name, phone} which is still valid against this interface.
 *
 * Real backend fields (from MeResponse / GET /auth/me) are additive-optional.
 * phone is REQUIRED — present in both legacy mock and real MeResponse.
 *
 * The real-login path (§4.3) populates user_id/plan/created_at from /me.
 * The legacy id/name fields fade out as otp-verify migrates to the real flow.
 */
export interface AuthUser {
  // Legacy mock fields — kept OPTIONAL (DECISION-3: additive, no breaking change)
  id?: number;
  name?: string;
  // Required in both legacy and real
  phone: string;
  // Additive from MeResponse (DECISION-3)
  user_id?: string;       // MeResponse.user_id (UUID)
  plan?: 'free';          // MeResponse.plan (V1 always free)
  created_at?: string;    // MeResponse.created_at (ISO-8601 TZ)
  last_login_at?: string | null;
  // Onboarding gate (Stage-1 wire, Path B) — additive-optional. Drives the shell
  // Onboarding nav-item visibility (hidden when true). Absent on legacy mock users.
  onboarding_complete?: boolean;
}

/** Minimal AuthUser shape derived from MeResponse. */
function meToUser(me: MeResponse): AuthUser {
  return {
    phone: me.phone,
    user_id: me.user_id,
    plan: me.plan,
    created_at: me.created_at,
    last_login_at: me.last_login_at,
    onboarding_complete: me.onboarding_complete,
  };
}

/**
 * Minimum delay (ms) between scheduled refresh fires, regardless of expires_in.
 * Prevents an immediate-refire loop when token TTL is tiny (D-D fix).
 */
const MIN_REFRESH_DELAY_MS = 5_000;

@Injectable({ providedIn: 'root' })
export class AuthService implements OnDestroy {
  // FE-D5: in-memory token only — never persisted to localStorage/sessionStorage
  private readonly _token = signal<string | null>(null);
  private readonly _user  = signal<AuthUser | null>(null);

  readonly isAuthenticated = computed(() => this._token() !== null);
  readonly currentUser     = computed(() => this._user());

  /** Timer handle for proactive silent refresh (scheduleRefresh). */
  private _refreshTimer: ReturnType<typeof setTimeout> | null = null;

  /**
   * Single-flight refresh Observable (stampede fix).
   * Non-null while a /auth/refresh call is in-flight. Reset to null by finalize()
   * when the Observable completes or errors — so the next genuine refresh starts fresh.
   * All three callers (interceptor handle401, _doSilentRefresh, bootstrap) route through
   * refreshShared() to guarantee AT MOST ONE concurrent POST /auth/refresh.
   */
  private _refreshInFlight: Observable<RefreshResponse> | null = null;

  /**
   * Logout-once guard (cascade fix).
   * Set to true by forceLogout(); subsequent forceLogout() calls are no-ops.
   * Reset to false by setSession() so a fresh login window is valid.
   */
  private _loggedOut = false;

  /** AuthApiService injected via DI (avoids NG0203 outside injection context). */
  private readonly authApi = inject(AuthApiService);
  /** Router injected for forceLogout() navigation. */
  private readonly router  = inject(Router);

  // ── Public API ─────────────────────────────────────────────────────────────

  /**
   * Called by login/OTP flow after backend confirms token.
   *
   * Frozen-surface amendment (2026-06-12, founder-approved §7.3): setSession
   * now AUTO-PAIRS with scheduleRefresh. When the optional `expiresIn` (seconds)
   * is supplied, a proactive silent refresh is scheduled automatically — the
   * caller no longer has to remember the setSession → scheduleRefresh pairing.
   *
   * BACKWARD COMPATIBLE: when `expiresIn` is omitted (the existing 2-arg
   * call shape — otp-verify mock, SP06 C4 smoke, bootstrap pre-hydration),
   * behaviour is UNCHANGED: token + user are set, no refresh is scheduled.
   * scheduleRefresh() remains public and callable for those paths.
   */
  setSession(token: string, user: AuthUser, expiresIn?: number): void {
    // A fresh setSession re-arms the logout guard so a subsequent forceLogout()
    // can navigate cleanly after this login window.
    this._loggedOut = false;
    this._token.set(token);
    this._user.set(user);
    if (expiresIn !== undefined) {
      this.scheduleRefresh(expiresIn);
    }
  }

  /**
   * Soft logout (called by the logout button / explicit user action).
   * Clears local state without navigating — the caller handles navigation.
   * Does NOT set _loggedOut because this is intentional, not a cascade guard.
   */
  logout(): void {
    this._cancelRefreshTimer();
    this._refreshInFlight = null;
    this._loggedOut = false;
    this._token.set(null);
    this._user.set(null);
  }

  /**
   * Force a one-time logout on token rotation failure (cascade guard).
   *
   * Logout-ONCE: cancel the refresh timer, clear in-flight refresh state,
   * null token/user, navigate(['/login']) EXACTLY once.
   * Subsequent calls (e.g. 20 concurrent 401s all arriving) are no-ops
   * because _loggedOut is set true on first call — prevents re-navigation
   * and stops the cascade hammer on the backend.
   *
   * Called by:
   *   - _doSilentRefresh catchError on 401 from the silent refresh (D-C fix).
   *   - refreshInterceptor handle401 catchError on refresh-401.
   */
  forceLogout(): void {
    if (this._loggedOut) {
      // Already logged out — no-op (cascade guard)
      return;
    }
    this._loggedOut = true;
    this._cancelRefreshTimer();
    this._refreshInFlight = null;
    this._token.set(null);
    this._user.set(null);
    // Navigate exactly once — subsequent no-ops prevent duplicate navigations.
    void this.router.navigate(['/login']);
  }

  /** Returns bearer token for HTTP interceptor */
  getToken(): string | null {
    return this._token();
  }

  // ── Single-flight refresh (stampede fix) ───────────────────────────────────

  /**
   * Single-flight refresh gate — the ONLY path to POST /auth/refresh.
   *
   * If a refresh is already in-flight, all callers share the SAME Observable
   * (shareReplay so late subscribers still get the cached emission).
   * When the Observable completes or errors, finalize() clears _refreshInFlight
   * so the next genuine refresh starts fresh (D-A + D-B fixed by construction).
   *
   * shareReplay options:
   *   - bufferSize: 1 — late subscribers get the last emitted value.
   *   - refCount: false — source is NOT re-subscribed when ref count drops to 0
   *     between emission and a late subscriber arriving (prevents a second HTTP call
   *     on a hot-path race).
   *
   * Emits RefreshResponse so callers can read access_token/expires_in.
   */
  refreshShared(): Observable<RefreshResponse> {
    if (this._refreshInFlight) {
      return this._refreshInFlight;
    }

    this._refreshInFlight = this.authApi.refresh().pipe(
      shareReplay({ bufferSize: 1, refCount: false }),
      finalize(() => {
        // Reset in-flight on complete OR error — the NEXT refresh starts fresh.
        this._refreshInFlight = null;
      }),
    );

    return this._refreshInFlight;
  }

  // ── Silent-refresh scheduling (§4.2) ───────────────────────────────────────

  /**
   * Schedule a proactive token refresh BEFORE the access token expires.
   * expires_in: seconds-to-live from verify/refresh response.
   *
   * Delay formula (D-D fix — prevents zero/negative delay loop):
   *   skew    = min(30, expiresIn * 0.1)
   *   delayMs = max((expiresIn - skew) * 1000, MIN_REFRESH_DELAY_MS)
   *
   * The MIN_REFRESH_DELAY_MS floor (5 000 ms) ensures even a 1 s TTL schedules
   * the next refresh at 5 s rather than 0 ms, breaking any hot-loop.
   *
   * Clears any previous timer (idempotent — safe to call after every setSession).
   */
  scheduleRefresh(expiresIn: number): void {
    this._cancelRefreshTimer();
    const skew    = Math.min(30, expiresIn * 0.1);
    const delayMs = Math.max((expiresIn - skew) * 1000, MIN_REFRESH_DELAY_MS);
    this._refreshTimer = setTimeout(() => {
      this._doSilentRefresh();
    }, delayMs);
  }

  /**
   * App-init bootstrap — page-reload survival path (FE-D5).
   * Routes through refreshShared() so bootstrap racing _doSilentRefresh
   * produces exactly ONE POST /auth/refresh.
   * On SUCCESS → setSession(new token, user from /me) + scheduleRefresh.
   * On FAILURE (401 — no/expired cookie) → stay logged-out, no redirect.
   *   The route guard handles unauthorised navigation.
   *
   * MUST resolve (never reject) — a rejected APP_INITIALIZER hangs app init.
   * Called from shell app.config.ts APP_INITIALIZER / provideAppInitializer.
   */
  bootstrap(): Promise<void> {
    return new Promise<void>((resolve) => {
      this.refreshShared()
        .pipe(
          switchMap((refreshResp) => {
            const newToken = refreshResp.access_token;
            this._token.set(newToken);
            return this.authApi.me().pipe(
              catchError(() => {
                this.scheduleRefresh(refreshResp.expires_in);
                return EMPTY;
              }),
              switchMap((me) => {
                this.setSession(newToken, meToUser(me));
                this.scheduleRefresh(refreshResp.expires_in);
                return EMPTY;
              }),
            );
          }),
          catchError(() => {
            return EMPTY;
          }),
        )
        .subscribe({ complete: () => resolve() });
    });
  }

  /**
   * Re-hydrate the shared user from GET /auth/me WITHOUT touching the token or
   * the refresh timer.
   */
  refreshUser(): Observable<void> {
    return this.authApi.me().pipe(
      map((me) => {
        this._user.set(meToUser(me));
      }),
      catchError(() => EMPTY),
    );
  }

  // ── Private helpers ────────────────────────────────────────────────────────

  private _cancelRefreshTimer(): void {
    if (this._refreshTimer !== null) {
      clearTimeout(this._refreshTimer);
      this._refreshTimer = null;
    }
  }

  private _doSilentRefresh(): void {
    this.refreshShared()
      .pipe(
        switchMap((resp) => {
          this._token.set(resp.access_token);
          return this.authApi.me().pipe(
            catchError(() => {
              this.scheduleRefresh(resp.expires_in);
              return EMPTY;
            }),
            switchMap((me) => {
              this.setSession(resp.access_token, meToUser(me));
              this.scheduleRefresh(resp.expires_in);
              return EMPTY;
            }),
          );
        }),
        catchError((err: unknown) => {
          const status = (err as { status?: number })?.status;
          if (status === 401) {
            this.forceLogout();
          }
          return EMPTY;
        }),
      )
      .subscribe();
  }

  ngOnDestroy(): void {
    this._cancelRefreshTimer();
  }
}
