// features/auth/auth.model.ts
// OTP flow types — per BACKEND_ARCHITECTURE.md §7.B locked contracts

export interface OtpSendRequest {
  phone: string; // E.164 format: +91XXXXXXXXXX
}

export interface OtpSendResponse {
  request_id: string; // MSG91 correlation ID — opaque; log for support
}

export interface OtpVerifyRequest {
  phone: string; // E.164 — same phone used in send
  otp: string;   // 6-digit code
}

export interface OtpVerifyResponse {
  access_token: string;
  expires_in: number; // seconds — prod 900
  token_type: 'bearer';
}
