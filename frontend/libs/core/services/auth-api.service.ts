import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '@mesell/env';

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
 *
 * DUAL-IDENTITY: a user may sign up with phone OTP OR Google. A Google-only
 * user has NO phone, so `phone` is NULLABLE. [RECONCILE-BE] backend must return
 * null (not omit / not synthesise) for Google users without a phone.
 */
export interface MeResponse {
  user_id: string;
  phone: string | null;
  plan: 'free';
  created_at: string;
  last_login_at: string | null;
  onboarding_complete: boolean;
}

const AUTH_OTP_SEND     = `${environment.apiBase}/api/v1/auth/otp/send`;
const AUTH_OTP_VERIFY   = `${environment.apiBase}/api/v1/auth/otp/verify`;
const AUTH_GOOGLE_VERIFY = `${environment.apiBase}/api/v1/auth/google/verify`;
const AUTH_REFRESH      = `${environment.apiBase}/api/v1/auth/refresh`;
const AUTH_LOGOUT       = `${environment.apiBase}/api/v1/auth/logout`;
const AUTH_ME           = `${environment.apiBase}/api/v1/auth/me`;

@Injectable({ providedIn: 'root' })
export class AuthApiService {
  private readonly http = inject(HttpClient);

  sendOtp(phone: string): Observable<SendOtpResponse> {
    return this.http.post<SendOtpResponse>(AUTH_OTP_SEND, { phone });
  }

  verifyOtp(phone: string, otp: string): Observable<VerifyOtpResponse> {
    return this.http.post<VerifyOtpResponse>(
      AUTH_OTP_VERIFY,
      { phone, otp },
      { withCredentials: true },
    );
  }

  /**
   * POST /api/v1/auth/google/verify  [RECONCILE-BE]
   *
   * credential = the Google Identity Services ID token (JWT) from the GIS callback.
   * withCredentials: true — the response sets the HttpOnly refresh_token cookie,
   * IDENTICAL to verifyOtp(). Reuses VerifyOtpResponse (dual-identity, symmetric
   * with the OTP path so the success-wiring tail is shared via completeLogin()).
   *
   * The credential is sent in the body, never logged, never persisted (FE-D5).
   */
  googleVerify(credential: string): Observable<VerifyOtpResponse> {
    return this.http.post<VerifyOtpResponse>(
      AUTH_GOOGLE_VERIFY,
      { credential },
      { withCredentials: true },
    );
  }

  refresh(): Observable<RefreshResponse> {
    return this.http.post<RefreshResponse>(
      AUTH_REFRESH,
      {},
      { withCredentials: true },
    );
  }

  logout(): Observable<void> {
    return this.http.post<void>(
      AUTH_LOGOUT,
      {},
      { withCredentials: true },
    );
  }

  me(): Observable<MeResponse> {
    return this.http.get<MeResponse>(AUTH_ME);
  }
}
