import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '@mesell/env';

/**
 * Auth IAM response shapes — transcribed from backend/app/modules/iam/schemas.py L31-83.
 * MeResponse is exported (consumed by bootstrap + dashboard greeting + onboarding).
 * The others are auth-infra-local (single consumer — AuthApiService) but exported
 * for spec file usage.
 */

/** POST /api/v1/auth/otp/send — schemas.py L37-40 */
export interface SendOtpResponse {
  request_id: string;
}

/**
 * POST /api/v1/auth/otp/verify — schemas.py L50-59
 * Response also sets Set-Cookie: refresh_token (HttpOnly, handled by browser)
 */
export interface VerifyOtpResponse {
  access_token: string;
  expires_in: number;
  token_type: 'bearer';
}

/**
 * POST /api/v1/auth/refresh — schemas.py L62-71
 * Response rotates the Set-Cookie: refresh_token
 */
export interface RefreshResponse {
  access_token: string;
  expires_in: number;
  token_type: 'bearer';
}

/**
 * GET /api/v1/auth/me — schemas.py L74-83
 * The real AuthUser identity from the backend.
 * Exported because bootstrap() + other services hydrate AuthUser from this shape.
 */
export interface MeResponse {
  user_id: string;        // UUID
  phone: string;          // E.164
  plan: 'free';           // V1 always free
  created_at: string;     // ISO-8601 TZ
  last_login_at: string | null;
}

// ── Endpoint path constants (single source of truth) ─────────────────────────
// environment.apiBase is prepended so cross-origin deployments only need
// environment.prod.ts changed — zero churn in this file.
const AUTH_OTP_SEND    = `${environment.apiBase}/api/v1/auth/otp/send`;
const AUTH_OTP_VERIFY  = `${environment.apiBase}/api/v1/auth/otp/verify`;
const AUTH_REFRESH     = `${environment.apiBase}/api/v1/auth/refresh`;
const AUTH_LOGOUT      = `${environment.apiBase}/api/v1/auth/logout`;
const AUTH_ME          = `${environment.apiBase}/api/v1/auth/me`;

/**
 * AuthApiService — typed HTTP wrapper for the IAM endpoints.
 *
 * Placement: libs/core (NOT mfe-auth) to avoid shell→remote circular dependency.
 * bootstrap() + refreshInterceptor (both core-owned) call refresh() + me() here.
 * mfe-auth page components call sendOtp() + verifyOtp() (from the same singleton).
 *
 * withCredentials scope (R-W6-5):
 *   ONLY on verifyOtp / refresh / logout — the refresh-cookie path.
 *   NOT on sendOtp (public, no cookie) or me (Bearer-auth, no cookie needed).
 *
 * Base: path constants above include environment.apiBase prefix.
 * At apiBase='' (dev + prod V1), paths are byte-identical to previous literals.
 */
@Injectable({ providedIn: 'root' })
export class AuthApiService {
  private readonly http = inject(HttpClient);

  /**
   * POST /api/v1/auth/otp/send
   * Phone MUST be E.164 (caller normalises: +91 + 10-digit form value).
   * No withCredentials — public endpoint.
   * Rate-limited 3/h/phone (backend Valkey sliding window).
   */
  sendOtp(phone: string): Observable<SendOtpResponse> {
    return this.http.post<SendOtpResponse>(AUTH_OTP_SEND, { phone });
  }

  /**
   * POST /api/v1/auth/otp/verify
   * withCredentials: true — response sets HttpOnly refresh_token cookie (Path=/api/v1/auth).
   * The browser auto-attaches the cookie on subsequent /api/v1/auth/* requests.
   */
  verifyOtp(phone: string, otp: string): Observable<VerifyOtpResponse> {
    return this.http.post<VerifyOtpResponse>(
      AUTH_OTP_VERIFY,
      { phone, otp },
      { withCredentials: true },
    );
  }

  /**
   * POST /api/v1/auth/refresh
   * withCredentials: true — sends the HttpOnly refresh cookie; receives a rotated one.
   * Called by: refreshInterceptor (on 401), AuthService.bootstrap() (on page load),
   * AuthService.scheduleRefresh() (proactive silent refresh).
   */
  refresh(): Observable<RefreshResponse> {
    return this.http.post<RefreshResponse>(
      AUTH_REFRESH,
      {},
      { withCredentials: true },
    );
  }

  /**
   * POST /api/v1/auth/logout
   * withCredentials: true — backend clears the refresh cookie (max_age=0) + Valkey DEL.
   * Returns 204 No Content (typed as void).
   */
  logout(): Observable<void> {
    return this.http.post<void>(
      AUTH_LOGOUT,
      {},
      { withCredentials: true },
    );
  }

  /**
   * GET /api/v1/auth/me
   * Bearer-auth (jwtInterceptor attaches the token).
   * No withCredentials — Bearer-only, no cookie needed (R-W6-5).
   * Hydrates AuthUser with real backend fields (user_id, plan, created_at, etc.).
   */
  me(): Observable<MeResponse> {
    return this.http.get<MeResponse>(AUTH_ME);
  }
}
