import { HttpErrorResponse } from '@angular/common/http';

/**
 * Shared user-facing error mappers for the auth pages (login + signup + otp).
 * Kept remote-private (not promoted to @mesell/*) — only mfe-auth consumes them.
 * Copy follows the existing tone across the auth flow.
 */

/** Map a phone-OTP-send error to a user-facing message. */
export function mapSendOtpError(err: unknown): string {
  const status = (err as HttpErrorResponse)?.status;
  if (status === 0) return 'You appear to be offline. Please try again.';
  if (status === 429) return 'Too many attempts. Please try again later.';
  if (status === 400) return 'Invalid phone number. Please check and try again.';
  return 'Something went wrong. Please try again.';
}

/** Map a Google-verify error to a user-facing message (§D.3 of the design doc). */
export function mapGoogleError(err: unknown): string {
  const status = (err as HttpErrorResponse)?.status;
  if (status === 0) return 'You appear to be offline. Please try again.';
  if (status === 429) return 'Too many attempts. Please try again later.';
  if (status === 400 || status === 401) return 'Google sign-in failed. Please try again.';
  return 'Something went wrong. Please try again.';
}

/** Map an OTP-verify error to a user-facing message. */
export function mapVerifyOtpError(err: unknown): string {
  const status = (err as HttpErrorResponse)?.status;
  if (status === 0) return 'You appear to be offline. Please try again.';
  if (status === 429) return 'Too many attempts. Please try again later.';
  if (status === 400 || status === 401) return 'Invalid or expired code. Please try again.';
  return 'Something went wrong. Please try again.';
}

