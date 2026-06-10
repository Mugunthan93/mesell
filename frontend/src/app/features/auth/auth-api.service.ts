// features/auth/auth-api.service.ts
// Wraps POST /api/v1/auth/otp/send + POST /api/v1/auth/otp/verify
// per FRONTEND_ARCHITECTURE.md §7 + BACKEND_ARCHITECTURE.md §7.B

import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';
import { ApiClient } from '@core/api/api-client.service';
import { AuthService } from '@core/auth/auth.service';
import {
  OtpSendRequest,
  OtpSendResponse,
  OtpVerifyRequest,
  OtpVerifyResponse,
} from './auth.model';

@Injectable()
export class AuthApiService {
  private readonly api = inject(ApiClient);
  private readonly auth = inject(AuthService);

  /** POST /api/v1/auth/otp/send — 202 on success; 429 on 3/h rate limit */
  sendOtp(req: OtpSendRequest): Observable<OtpSendResponse> {
    return this.api.post<OtpSendResponse>('/auth/otp/send', req);
  }

  /**
   * POST /api/v1/auth/otp/verify
   * On 200: calls AuthService.setAccess() to store token in-memory (FE-D5).
   * Refresh cookie set by backend via Set-Cookie (HttpOnly, SameSite=Strict).
   */
  verifyOtp(req: OtpVerifyRequest): Observable<OtpVerifyResponse> {
    return this.api.post<OtpVerifyResponse>('/auth/otp/verify', req).pipe(
      tap(res => this.auth.setAccess(res)),
    );
  }
}
