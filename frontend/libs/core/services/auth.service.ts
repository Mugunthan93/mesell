import { Injectable, signal, computed, inject, OnDestroy } from '@angular/core';
import { switchMap, catchError, EMPTY } from 'rxjs';
import { AuthApiService } from './auth-api.service';
import type { MeResponse } from './auth-api.service';

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
}

/** Minimal AuthUser shape derived from MeResponse. */
function meToUser(me: MeResponse): AuthUser {
  return {
    phone: me.phone,
    user_id: me.user_id,
    plan: me.plan,
    created_at: me.created_at,
    last_login_at: me.last_login_at,
  };
}

@Injectable({ providedIn: 'root' })
export class AuthService implements OnDestroy {
  // FE-D5: in-memory token only — never persisted to localStorage/sessionStorage
  private readonly _token = signal<string | null>(null);
  private readonly _user  = signal<AuthUser | null>(null);

  readonly isAuthenticated = computed(() => this._token() !== null);
  readonly currentUser     = computed(() => this._user());

  /** Timer handle for proactive silent refresh (scheduleRefresh). */
  private _refreshTimer: ReturnType<typeof setTimeout> | null = null;

  /** AuthApiService injected via constructor (Angular DI — avoids NG0203 outside injection context). */
  private readonly authApi = inject(AuthApiService);

  // ── Public API ─────────────────────────────────────────────────────────────

  /**
   * Called by login/OTP flow after backend confirms token.
   * scheduleRefresh() is the caller's responsibility AFTER setSession
   * (otp-verify calls it explicitly; bootstrap() calls it after hydration).
   */
  setSession(token: string, user: AuthUser): void {
    this._token.set(token);
    this._user.set(user);
  }

  logout(): void {
    this._cancelRefreshTimer();
    this._token.set(null);
    this._user.set(null);
  }

  /** Returns bearer token for HTTP interceptor */
  getToken(): string | null {
    return this._token();
  }

  // ── Silent-refresh scheduling (§4.2) ───────────────────────────────────────

  /**
   * Schedule a proactive token refresh BEFORE the access token expires.
   * expires_in: seconds-to-live from verify/refresh response.
   * Fires at (expires_in - 30)s to give a 30-second window before expiry.
   * The 401-path refresh (refreshInterceptor) is the safety net.
   *
   * Clears any previous timer (idempotent — safe to call after every setSession).
   */
  scheduleRefresh(expiresIn: number): void {
    this._cancelRefreshTimer();
    const delayMs = Math.max((expiresIn - 30) * 1000, 0);
    this._refreshTimer = setTimeout(() => {
      this._doSilentRefresh();
    }, delayMs);
  }

  /**
   * App-init bootstrap — page-reload survival path (FE-D5).
   * Calls POST /auth/refresh (the HttpOnly cookie is auto-sent by the browser).
   * On SUCCESS → setSession(new token, user from /me) + scheduleRefresh.
   * On FAILURE (401 — no/expired cookie) → stay logged-out, no redirect.
   *   The route guard handles unauthorised navigation.
   *
   * MUST resolve (never reject) — a rejected APP_INITIALIZER hangs app init.
   * Called from shell app.config.ts APP_INITIALIZER / provideAppInitializer.
   */
  bootstrap(): Promise<void> {
    return new Promise<void>((resolve) => {
      this.authApi
        .refresh()
        .pipe(
          switchMap((refreshResp) => {
            // Got a new access token — hydrate user from /me
            const newToken = refreshResp.access_token;
            return this.authApi.me().pipe(
              catchError(() => {
                // /me failed but we have a token — use minimal user object
                this._token.set(newToken);
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
            // refresh 401 — no valid cookie; stay logged-out
            return EMPTY;
          }),
        )
        .subscribe({ complete: () => resolve() });
    });
  }

  // ── Private helpers ────────────────────────────────────────────────────────

  private _cancelRefreshTimer(): void {
    if (this._refreshTimer !== null) {
      clearTimeout(this._refreshTimer);
      this._refreshTimer = null;
    }
  }

  private _doSilentRefresh(): void {
    this.authApi
      .refresh()
      .pipe(
        switchMap((resp) =>
          this.authApi.me().pipe(
            catchError(() => {
              this._token.set(resp.access_token);
              this.scheduleRefresh(resp.expires_in);
              return EMPTY;
            }),
            switchMap((me) => {
              this.setSession(resp.access_token, meToUser(me));
              this.scheduleRefresh(resp.expires_in);
              return EMPTY;
            }),
          ),
        ),
        catchError(() => {
          // Silent refresh failed — let the 401-interceptor handle the next request
          return EMPTY;
        }),
      )
      .subscribe();
  }

  ngOnDestroy(): void {
    this._cancelRefreshTimer();
  }
}
