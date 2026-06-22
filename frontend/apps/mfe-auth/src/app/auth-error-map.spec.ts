/**
 * auth-error-map.spec.ts — QA Wave 2 (FE-AUTH-06)
 *
 * Table-driven unit tests for the three auth error-mapper pure functions.
 * These are remote-private functions in mfe-auth; no Angular TestBed is needed.
 *
 * Coverage: mapSendOtpError / mapVerifyOtpError / mapGoogleError
 * For each mapper: status ∈ {0, 400, 401, 429, 500} → expected copy fragment.
 * Google-auth is IN (flag-ON confirmed by founder 2026-06-22).
 *
 * Pure-function tests: import { describe, it, expect } from 'vitest' explicitly
 * (no globals — this project has no vitest.config.ts with globals:true).
 */
import { describe, it, expect } from 'vitest';
import { HttpErrorResponse } from '@angular/common/http';

import {
  mapSendOtpError,
  mapVerifyOtpError,
  mapGoogleError,
} from './auth-error-map';

/** Helper: build a minimal HttpErrorResponse stub for a given status. */
function makeErr(status: number): HttpErrorResponse {
  return new HttpErrorResponse({ status, error: { detail: 'err' }, url: '/test' });
}

// ── mapSendOtpError ───────────────────────────────────────────────────────────

describe('mapSendOtpError', () => {
  it('should return offline message when status is 0 (network error)', () => {
    expect(mapSendOtpError(makeErr(0))).toContain('offline');
  });

  it('should return invalid phone message when status is 400', () => {
    const msg = mapSendOtpError(makeErr(400));
    expect(msg).toContain('Invalid phone');
  });

  it('should return rate-limit message when status is 429', () => {
    const msg = mapSendOtpError(makeErr(429));
    expect(msg).toContain('Too many attempts');
  });

  it('should return generic error message when status is 500', () => {
    const msg = mapSendOtpError(makeErr(500));
    expect(msg).toContain('went wrong');
  });

  it('should return generic error message when status is 503 (any 5xx)', () => {
    expect(mapSendOtpError(makeErr(503))).toContain('went wrong');
  });

  it('should return generic error message for an unknown non-zero status', () => {
    expect(mapSendOtpError(makeErr(418))).toContain('went wrong');
  });

  it('should return offline message when called with a plain Error object (status absent)', () => {
    // mapSendOtpError casts to HttpErrorResponse — a plain Error has no .status
    // (status is undefined → none of the if-branches match → falls through to default)
    const plainErr = new Error('Network error');
    expect(mapSendOtpError(plainErr)).toContain('went wrong');
  });
});

// ── mapVerifyOtpError ─────────────────────────────────────────────────────────

describe('mapVerifyOtpError', () => {
  it('should return offline message when status is 0', () => {
    expect(mapVerifyOtpError(makeErr(0))).toContain('offline');
  });

  it('should return "Invalid or expired" message when status is 400', () => {
    expect(mapVerifyOtpError(makeErr(400))).toContain('Invalid or expired');
  });

  it('should return "Invalid or expired" message when status is 401 (wrong OTP)', () => {
    expect(mapVerifyOtpError(makeErr(401))).toContain('Invalid or expired');
  });

  it('should return rate-limit message when status is 429', () => {
    expect(mapVerifyOtpError(makeErr(429))).toContain('Too many attempts');
  });

  it('should return generic error message when status is 500', () => {
    expect(mapVerifyOtpError(makeErr(500))).toContain('went wrong');
  });

  it('should return generic error message for status 0 when called with a plain object', () => {
    // Simulate a network-error object (ProgressEvent) with status 0
    expect(mapVerifyOtpError({ status: 0 })).toContain('offline');
  });
});

// ── mapGoogleError ─────────────────────────────────────────────────────────────
// Google sign-in is IN (flag-ON, confirmed by founder 2026-06-22).

describe('mapGoogleError', () => {
  it('should return offline message when status is 0 (network error)', () => {
    expect(mapGoogleError(makeErr(0))).toContain('offline');
  });

  it('should return "Google sign-in failed" message when status is 400', () => {
    expect(mapGoogleError(makeErr(400))).toContain('Google sign-in failed');
  });

  it('should return "Google sign-in failed" message when status is 401 (token invalid)', () => {
    expect(mapGoogleError(makeErr(401))).toContain('Google sign-in failed');
  });

  it('should return rate-limit message when status is 429', () => {
    expect(mapGoogleError(makeErr(429))).toContain('Too many attempts');
  });

  it('should return generic error message when status is 500', () => {
    expect(mapGoogleError(makeErr(500))).toContain('went wrong');
  });
});
