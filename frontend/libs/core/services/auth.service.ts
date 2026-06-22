import { Injectable, signal, computed, inject, OnDestroy } from '@angular/core';
import { Router } from '@angular/router';
import {
  Observable,
  Subject,
  of,
  tap,
  switchMap,
  map,
  catchError,
  EMPTY,
  connectable,
  finalize,
} from 'rxjs';
import { AuthApiService } from './auth-api.service';
import type { MeResponse, RefreshResponse, VerifyOtpResponse } from './auth-api.service';

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
 *
 * Wave 3 billing widening: plan literal expanded from 'free' to the full 7-value
 * PRICING_LOCKED v2 vocabulary. trial_ends_at and entitlement added (additive,
 * DECISION-3). Source: handoff_contract_razorpay.md §1.
 */
export interface AuthUser {
  // Legacy mock fields — kept OPTIONAL (DECISION-3: additive, no breaking change)
  id?: number;
  name?: string;
  // Present in both legacy and real, but NULLABLE for dual-identity:
  // a Google-only user has no phone (mirrors MeResponse.phone: string | null).
  phone: string | null;
  // Additive from MeResponse (DECISION-3)
  user_id?: string;       // MeResponse.user_id (UUID)
  /**
   * Raw billing plan — same as MeResponse.plan (the 7-value vocabulary).
   * Gate feature UI on `entitlement` (resolved, 4-value), NOT this field.
   * Use `plan` only for the billing-management screen (show the exact cadence).
   */
  plan?: 'free' | 'starter' | 'pro' | 'pro_annual' | 'business' | 'business_annual' | 'ltd';
  created_at?: string;    // MeResponse.created_at (ISO-8601 TZ)
  last_login_at?: string | null;
  // Onboarding gate (Stage-1 wire, Path B) — additive-optional. Drives the shell
  // Onboarding nav-item visibility (hidden when true). Absent on legacy mock users.
  onboarding_complete?: boolean;
  /**
   * ISO-8601 UTC expiry of the 14-day Pro trial. null = no trial started.
   * Non-null + in the future → user is in a live Pro trial.
   * After expiry the field may remain set (past timestamp) — use entitlement to
   * determine the current effective access level.
   */
  trial_ends_at?: string | null;
  /**
   * RESOLVED effective entitlement — the single field to gate feature visibility on.
   * Collapse: free(no trial)=>free | free+trial=>pro | starter=>starter |
   *   pro/pro_annual/ltd=>pro | business/business_annual=>business.
   * Absent on pre-Wave-3 cached users — treat undefined as 'free'.
   * Backend (plan_guard.resolve_entitlement) is authoritative.
   */
  entitlement?: 'free' | 'starter' | 'pro' | 'business';
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
    // Wave 3 billing additions (additive-optional — undefined is safe for older tokens)
    trial_ends_at: me.trial_ends_at,
    entitlement: me.entitlement,
  };
}

/**
 * Minimum delay (ms) between scheduled refresh fires, regardless of expires_in.
 * Prevents an immediate-refire loop when token TTL is tiny (D-D fix).
 */
const MIN_REFRESH_DELAY_MS = 5_000;

/**
 * Cross-context refresh debounce (ms). A refreshShared() call arriving within this window
 * AFTER a successful refresh returns the just-minted token WITHOUT a network call.
 * Collapses a burst from multiple AuthService instances (broken federation singleton dedup)
 * into ONE POST /auth/refresh per rotation window. Distinct from MIN_REFRESH_DELAY_MS.
 * FE-D5 compliant: no localStorage/sessionStorage — purely in-memory.
 *
 * IMPORTANT — which callers use the debounce:
 *   refreshShared()  => used by _doSilentRefresh + bootstrap (proactive paths). Debounce ACTIVE.
 *   refreshForced()  => used by the refresh interceptor on genuine 401. Debounce BYPASSED.
 *
 * A genuine 401 means the server has already rejected the current token, so returning a
 * cached token would just trigger another 401. The interceptor MUST always hit the network.
 */
const REFRESH_DEBOUNCE_MS = 2_000;

@Injectable({ providedIn: 'root' })
export class AuthService implements OnDestroy {
  // FE-D5: in-memory token only — never persisted to localStorage/sessionStorage
  private readonly _token = signal<string | null>(null);
  private readonly _user  = signal<AuthUser | null>(null);

  readonly isAuthenticated = computed(() => this._token() !== null);
  readonly currentUser     = computed(() => this._user());

  /**
   * Effective entitlement signal — the billing gating primitive.
   *
   * Sourced from currentUser().entitlement (resolved server-side by plan_guard).
   * Defaults to 'free' when the user is unauthenticated or on a pre-Wave-3
   * cached /me response that lacks the field.
   *
   * Gate billing CTAs, feature visibility, and SKU-cap banners on THIS signal —
   * never directly on plan (which encodes cadence like 'pro_annual', not access level).
   *
   * Components inject AuthService and read:  auth.entitlement()
   * Template: @if (auth.entitlement() === 'free') { ... }
   */
  readonly entitlement = computed(
    (): 'free' | 'starter' | 'pro' | 'business' =>
      this._user()?.entitlement ?? 'free',
  );

  /** Timer handle for proactive silent refresh (scheduleRefresh). */
  private _refreshTimer: ReturnType<typeof setTimeout> | null = null;

  /**
   * Single-flight refresh Observable (stampede fix).
   *
   * Non-null while a /auth/refresh call is in-flight. Shared by BOTH refreshShared()
   * and refreshForced() — concurrent callers always join this same multicast, ensuring
   * AT MOST ONE POST /auth/refresh is in flight at any time regardless of call site.
   *
   * Implementation uses connectable() + Subject (W2-FE-1 determinism fix).
   * The Subject delivers complete/error to ALL current subscribers synchronously in the
   * same microtask, BEFORE the finalize-equivalent cleanup in _refreshNetwork() resets
   * _refreshInFlight. This eliminates the finalize-vs-shareReplay microtask race
   * where a late subscriber arriving in the same tick as finalize could either:
   *   (a) get the replayed value before _refreshInFlight is null, or
   *   (b) see null _refreshInFlight and create a second HTTP call.
   *
   * With Subject-multicast the reset happens AFTER all subscriber callbacks complete —
   * deterministic regardless of microtask ordering.
   */
  private _refreshInFlight: Observable<RefreshResponse> | null = null;

  /**
   * Logout-once guard (cascade fix).
   * Set to true by forceLogout(); subsequent forceLogout() calls are no-ops.
   * Reset to false by setSession() so a fresh login window is valid.
   */
  private _loggedOut = false;

  /**
   * Timestamp (Date.now()) of the last successful refresh completion.
   * Used by the cross-context debounce backstop (B03) in refreshShared().
   * Initial value 0 means "no refresh has ever completed" => debounce inactive on first call.
   */
  private _lastRefreshAt = 0;

  /** AuthApiService injected via DI (avoids NG0203 outside injection context). */
  private readonly authApi = inject(AuthApiService);
  /** Router injected for forceLogout() navigation. */
  private readonly router  = inject(Router);

  // Public API

  /**
   * Called by login/OTP flow after backend confirms token.
   *
   * Frozen-surface amendment (2026-06-12, founder-approved §7.3): setSession
   * now AUTO-PAIRS with scheduleRefresh. When the optional expiresIn (seconds)
   * is supplied, a proactive silent refresh is scheduled automatically — the
   * caller no longer has to remember the setSession => scheduleRefresh pairing.
   *
   * BACKWARD COMPATIBLE: when expiresIn is omitted (the existing 2-arg
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
   * completeLogin — shared post-credential success tail (Google + OTP).
   *
   * Given an access token + expiry from ANY verify endpoint
   * (otp/verify or google/verify — both return VerifyOtpResponse):
   *   set token => fetch /me => setSession(token, user, expires_in) (which
   *   auto-schedules the silent refresh) => resolve with the routing target.
   *
   * Onboarding gate (Path B): when me.onboarding_complete === false the user
   * is routed to /onboarding; otherwise to /dashboard. This is the single place
   * the gate decision lives, shared by every success site.
   *
   * On /me FAILURE: still set a MINIMAL session and schedule the refresh, then
   * resolve with a SAFE DEFAULT route (/dashboard). NEVER errors on /me failure —
   * mirrors the bootstrap()/_doSilentRefresh() graceful-degrade behaviour so a
   * transient /me hiccup never blocks login.
   *
   * fallbackUser lets the caller seed the minimal session on /me failure:
   *   - OTP path passes { phone } (known at verify time) so the phone survives.
   *   - Google path passes nothing => { phone: null } (Google-only user, no phone).
   */
  completeLogin(
    resp: VerifyOtpResponse,
    fallbackUser?: AuthUser,
  ): Observable<{ route: string[] }> {
    const token = resp.access_token;
    // Set the token first so the jwtInterceptor can authorize the /me call.
    this._token.set(token);
    return this.authApi.me().pipe(
      map((me) => {
        this.setSession(token, meToUser(me), resp.expires_in);
        const route = me.onboarding_complete === false
          ? ['/onboarding']
          : ['/dashboard'];
        return { route };
      }),
      catchError(() => {
        // /me failed — keep the user logged in with a minimal session and a
        // scheduled refresh, route to a safe default. Do NOT propagate the error.
        this.setSession(token, fallbackUser ?? { phone: null }, resp.expires_in);
        return of({ route: ['/dashboard'] });
      }),
    );
  }

  /**
   * Soft logout (called by the logout button / explicit user action).
   * Best-effort server revoke (fire-and-forget) => clear state => navigate to /login.
   * Does NOT set _loggedOut because this is an intentional user action, not a cascade guard.
   */
  logout(): void {
    // Fire-and-forget cookie revoke — never blocks local logout on network failure.
    this.authApi.logout().subscribe({ error: () => {} });
    this._cancelRefreshTimer();
    this._refreshInFlight = null;
    this._loggedOut = false;
    this._token.set(null);
    this._user.set(null);
    void this.router.navigate(['/login']);
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
    // Best-effort server revoke before clearing state (fire-and-forget; cascade may mean cookie already gone).
    this.authApi.logout().subscribe({ error: () => {} });
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

  // Single-flight refresh (stampede fix)

  /**
   * Single-flight refresh for PROACTIVE paths (_doSilentRefresh, bootstrap).
   *
   * Includes the B03 cross-context debounce: if a refresh completed within
   * REFRESH_DEBOUNCE_MS AND a live token exists, returns the current token
   * without a network call. This collapses duplicate proactive refresh attempts
   * from broken federation singleton instances into a single POST /auth/refresh.
   *
   * DO NOT call from the 401-retry interceptor path — a genuine 401 means the
   * server rejected the current token; returning it again causes another 401.
   * Use refreshForced() for that path.
   */
  refreshShared(): Observable<RefreshResponse> {
    // B03 cross-context debounce
    const currentToken = this._token();
    if (currentToken && Date.now() - this._lastRefreshAt < REFRESH_DEBOUNCE_MS) {
      return of({
        access_token: currentToken,
        expires_in: 0,
        token_type: 'bearer' as const,
      });
    }

    return this._refreshNetwork();
  }

  /**
   * Single-flight refresh for REACTIVE paths (refresh interceptor on genuine 401).
   *
   * Bypasses the B03 cross-context debounce. A genuine 401 means the server has
   * rejected the current access token — returning a cached version would just
   * repeat the 401. The interceptor MUST always hit the network.
   *
   * Still shares _refreshInFlight with refreshShared() so concurrent 401s across
   * multiple in-flight requests produce exactly ONE POST /auth/refresh (stampede fix).
   */
  refreshForced(): Observable<RefreshResponse> {
    return this._refreshNetwork();
  }

  // Silent-refresh scheduling (§4.2)

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
   * On SUCCESS => setSession(new token, user from /me) + scheduleRefresh.
   * On FAILURE (401 — no/expired cookie) => stay logged-out, no redirect.
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

  // Private helpers

  private _cancelRefreshTimer(): void {
    if (this._refreshTimer !== null) {
      clearTimeout(this._refreshTimer);
      this._refreshTimer = null;
    }
  }

  /**
   * Core single-flight network refresh (W2-FE-1 determinism fix).
   *
   * If _refreshInFlight is non-null, returns the shared multicast Observable —
   * the caller joins the in-progress refresh without firing a second HTTP call.
   *
   * Otherwise, creates a new connectable Observable backed by a Subject.
   * Using connectable + Subject (instead of shareReplay + finalize) makes the
   * reset of _refreshInFlight DETERMINISTIC:
   *
   *   - shareReplay({refCount:false}) + finalize race: finalize fires in a microtask
   *     AFTER the last emission propagates. A subscriber arriving in the same tick as
   *     finalize can observe _refreshInFlight either null or non-null depending on
   *     microtask order — hence the ~40% spec flake.
   *
   *   - Subject multicast: when the HTTP source completes/errors, the Subject's
   *     complete()/error() is delivered to ALL current subscribers synchronously in
   *     the same callstack frame. Only after all subscriber callbacks return does
   *     finalize() run and reset _refreshInFlight. This order is guaranteed by RxJS
   *     Subject semantics — no microtask race.
   *
   * The connected Subscription is managed internally by connectable.connect().
   */
  private _refreshNetwork(): Observable<RefreshResponse> {
    if (this._refreshInFlight) {
      return this._refreshInFlight;
    }

    const source = this.authApi.refresh().pipe(
      tap(() => {
        this._lastRefreshAt = Date.now(); // arm B03 debounce window for refreshShared()
      }),
      finalize(() => {
        // Reset in-flight AFTER all current subscribers have been notified.
        // Subject delivers synchronously; finalize runs after all callbacks return.
        this._refreshInFlight = null;
      }),
    );

    // connectable wraps source with a Subject multicast connector.
    // resetOnDisconnect:false keeps the Subject open after connect() so late
    // subscribers that arrive while the HTTP call is in-flight still receive
    // the emission via the Subject, not a stale closed Subject.
    const shared = connectable(source, {
      connector: () => new Subject<RefreshResponse>(),
      resetOnDisconnect: false,
    });

    // Connect immediately so the HTTP call starts. All current + future subscribers
    // to shared receive the same emission from the one active HTTP request.
    shared.connect();

    this._refreshInFlight = shared;
    return shared;
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
