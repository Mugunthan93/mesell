/**
 * auth-error-map.spec.ts — OB-FE-07
 *
 * Unit tests for the three public error-mapping functions in auth-error-map.ts.
 * These are pure functions (no Angular DI, no HTTP) — no TestBed required.
 *
 * Coverage axes (per OB-FE-07):
 *   - Every function returns a non-empty, human-readable string for EVERY status code.
 *   - No blank-i18n-key regressions (strings must NOT be empty or look like keys).
 *   - Specific messages per status: 0=offline, 429=too-many, 400/401=semantic-error,
 *     else=generic.
 */

import { describe, it, expect } from 'vitest';
import { HttpErrorResponse } from '@angular/common/http';
import { mapSendOtpError, mapGoogleError, mapVerifyOtpError } from './auth-error-map';

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeErr(status: number): HttpErrorResponse {
  return new HttpErrorResponse({ status, url: 'http://localhost/test' });
}

/**
 * Assert a mapped string is non-empty and does NOT look like a raw i18n key.
 * Raw keys look like 'auth.token_missing' or 'validation.q.missing'.
 * This catches blank-i18n regressions seen in earlier waves
 * (finding-i18n-generic-missing-gap.md).
 */
function assertMappedString(msg: string): void {
  expect(msg).toBeTruthy();
  expect(msg.length).toBeGreaterThan(4);
  // No raw i18n key format (word.word syntax with no spaces)
  expect(/^[a-z]+\.[a-z_]+$/.test(msg)).toBe(false);
}

// ── mapSendOtpError ───────────────────────────────────────────────────────────

describe('mapSendOtpError', () => {
  it('should map status 0 to an offline message', () => {
    const msg = mapSendOtpError(makeErr(0));
    assertMappedString(msg);
    expect(msg.toLowerCase()).toContain('offline');
  });

  it('should map status 429 to a rate-limit message', () => {
    const msg = mapSendOtpError(makeErr(429));
    assertMappedString(msg);
    expect(msg.toLowerCase()).toContain('many');
  });

  it('should map status 400 to an invalid phone message', () => {
    const msg = mapSendOtpError(makeErr(400));
    assertMappedString(msg);
    expect(msg.toLowerCase()).toContain('phone');
  });

  it('should return a generic non-empty message for status 500 (unexpected error)', () => {
    const msg = mapSendOtpError(makeErr(500));
    assertMappedString(msg);
  });

  it('should return a non-empty message for null/undefined error', () => {
    const msg = mapSendOtpError(null);
    assertMappedString(msg);
  });

  it('should return a non-empty message for a plain object (non-HttpError)', () => {
    const msg = mapSendOtpError({ message: 'unknown' });
    assertMappedString(msg);
  });
});

// ── mapVerifyOtpError ─────────────────────────────────────────────────────────

describe('mapVerifyOtpError', () => {
  it('should map status 0 to an offline message', () => {
    const msg = mapVerifyOtpError(makeErr(0));
    assertMappedString(msg);
    expect(msg.toLowerCase()).toContain('offline');
  });

  it('should map status 429 to a rate-limit message', () => {
    const msg = mapVerifyOtpError(makeErr(429));
    assertMappedString(msg);
    expect(msg.toLowerCase()).toContain('many');
  });

  it('should map status 400 to an invalid/expired code message', () => {
    const msg = mapVerifyOtpError(makeErr(400));
    assertMappedString(msg);
    expect(msg.toLowerCase()).toMatch(/invalid|expired/);
  });

  it('should map status 401 to an invalid/expired code message', () => {
    const msg = mapVerifyOtpError(makeErr(401));
    assertMappedString(msg);
    expect(msg.toLowerCase()).toMatch(/invalid|expired/);
  });

  it('should return a generic non-empty message for status 500', () => {
    const msg = mapVerifyOtpError(makeErr(500));
    assertMappedString(msg);
  });

  it('should return a non-empty message for null/undefined error', () => {
    const msg = mapVerifyOtpError(null);
    assertMappedString(msg);
  });
});

// ── mapGoogleError ────────────────────────────────────────────────────────────

describe('mapGoogleError', () => {
  it('should map status 0 to an offline message', () => {
    const msg = mapGoogleError(makeErr(0));
    assertMappedString(msg);
    expect(msg.toLowerCase()).toContain('offline');
  });

  it('should map status 429 to a rate-limit message', () => {
    const msg = mapGoogleError(makeErr(429));
    assertMappedString(msg);
    expect(msg.toLowerCase()).toContain('many');
  });

  it('should map status 400 to a google sign-in failed message', () => {
    const msg = mapGoogleError(makeErr(400));
    assertMappedString(msg);
    expect(msg.toLowerCase()).toContain('google');
  });

  it('should map status 401 to a google sign-in failed message', () => {
    const msg = mapGoogleError(makeErr(401));
    assertMappedString(msg);
    expect(msg.toLowerCase()).toContain('google');
  });

  it('should return a generic non-empty message for status 503', () => {
    const msg = mapGoogleError(makeErr(503));
    assertMappedString(msg);
  });

  it('should return a non-empty message for null/undefined error', () => {
    const msg = mapGoogleError(null);
    assertMappedString(msg);
  });
});
