// features/account/account-api.service.ts
// Feature-scoped HTTP service for /auth/otp/* + /seller-profile/* per §2.C.2 + §7

import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';
import { ApiClient } from '@core/api/api-client.service';
import { AuthService } from '@core/auth/auth.service';
import { SellerProfile, RequiredProfileFields } from '@core/models/seller-profile.model';

// NOTE: providedIn feature route (not 'root') so it can be lazy-tree-shaken
// The feature's route provider array wires this: providers: [AccountApiService]

interface OtpSendRequest {
  phone: string;
}

interface OtpSendResponse {
  requestId: string;
  message: string;
}

interface OtpVerifyRequest {
  requestId: string;
  otp: string;
}

interface OtpVerifyResponse {
  access_token: string;
  expires_in: number;
  profileComplete: boolean;
}

@Injectable()
export class AccountApiService {
  private readonly api = inject(ApiClient);
  private readonly auth = inject(AuthService);

  /** POST /api/v1/auth/otp/send — initiate OTP flow */
  sendOtp(request: OtpSendRequest): Observable<OtpSendResponse> {
    return this.api.post<OtpSendResponse>('/auth/otp/send', request);
  }

  /**
   * POST /api/v1/auth/otp/verify — verify OTP, receive access token.
   * On success, calls auth.setAccess() to store in-memory token per FE-D5.
   */
  verifyOtp(request: OtpVerifyRequest): Observable<OtpVerifyResponse> {
    return this.api.post<OtpVerifyResponse>('/auth/otp/verify', request).pipe(
      tap(response => this.auth.setAccess(response)),
    );
  }

  /** GET /api/v1/seller-profile/required-fields — drives conditional onboarding steps */
  getRequiredFields(): Observable<RequiredProfileFields> {
    return this.api.get<RequiredProfileFields>('/seller-profile/required-fields');
  }

  /** GET /api/v1/seller-profile — read existing profile for /profile route */
  getProfile(): Observable<SellerProfile> {
    return this.api.get<SellerProfile>('/seller-profile');
  }

  /** PUT /api/v1/seller-profile — write for onboarding submit + profile edit */
  updateProfile(profile: Partial<SellerProfile>): Observable<SellerProfile> {
    return this.api.put<SellerProfile>('/seller-profile', profile);
  }
}
