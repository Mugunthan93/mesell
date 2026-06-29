/**
 * global-error-handler.spec.ts
 *
 * Tests GlobalErrorHandler.handleError() covering:
 *   (a) HttpErrorResponse with full envelope body → records all 4 fields from body
 *   (b) HttpErrorResponse with no body → falls back to error.message + HTTP_ERROR code
 *   (c) Error (JS Error) → records CLIENT_ERROR code + message
 *   (d) Non-Error / plain object → records CLIENT_ERROR code + String(error)
 *   (e) isDevMode path: console.error called in dev mode
 */

import { TestBed } from '@angular/core/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { vi } from 'vitest';

import { GlobalErrorHandler } from './global-error-handler';
import { ErrorService } from '../services/error.service';

// ── Setup ─────────────────────────────────────────────────────────────────────

function setup() {
  TestBed.configureTestingModule({
    providers: [
      ErrorService,
      GlobalErrorHandler,
    ],
  });

  return {
    handler:      TestBed.inject(GlobalErrorHandler),
    errorService: TestBed.inject(ErrorService),
  };
}

afterEach(() => {
  TestBed.resetTestingModule();
});

// ── (a) HttpErrorResponse with full body ─────────────────────────────────────

describe('GlobalErrorHandler — HttpErrorResponse', () => {
  it('records all 4 envelope fields from a well-formed error body', () => {
    const { handler, errorService } = setup();

    const httpErr = new HttpErrorResponse({
      error: {
        detail: 'Resource not found',
        code: 'NOT_FOUND',
        validation_message_id: 'val-id-1',
        request_id: 'req-abc',
      },
      status: 404,
      statusText: 'Not Found',
    });

    handler.handleError(httpErr);

    const envelope = errorService.lastError();
    expect(envelope).not.toBeNull();
    expect(envelope!.detail).toBe('Resource not found');
    expect(envelope!.code).toBe('NOT_FOUND');
    expect(envelope!.validation_message_id).toBe('val-id-1');
    expect(envelope!.request_id).toBe('req-abc');
  });

  it('falls back to HTTP_ERROR code and error.message when body is null', () => {
    const { handler, errorService } = setup();

    const httpErr = new HttpErrorResponse({
      error: null,
      status: 503,
      statusText: 'Service Unavailable',
    });

    handler.handleError(httpErr);

    const envelope = errorService.lastError();
    expect(envelope).not.toBeNull();
    expect(envelope!.code).toBe('HTTP_ERROR');
    expect(typeof envelope!.detail).toBe('string');
    expect(envelope!.detail.length).toBeGreaterThan(0);
    expect(envelope!.validation_message_id).toBe('');
    expect(envelope!.request_id).toBe('');
  });

  it('uses body.detail over error.message when body has partial fields', () => {
    const { handler, errorService } = setup();

    const httpErr = new HttpErrorResponse({
      error: { detail: 'Partial body detail' },
      status: 500,
      statusText: 'Internal Server Error',
    });

    handler.handleError(httpErr);

    const envelope = errorService.lastError();
    expect(envelope!.detail).toBe('Partial body detail');
    expect(envelope!.code).toBe('HTTP_ERROR'); // no code in body → fallback
  });
});

// ── (c) JS Error ──────────────────────────────────────────────────────────────

describe('GlobalErrorHandler — Error (JS)', () => {
  it('records CLIENT_ERROR code and the error message', () => {
    const { handler, errorService } = setup();

    handler.handleError(new Error('Something exploded'));

    const envelope = errorService.lastError();
    expect(envelope).not.toBeNull();
    expect(envelope!.code).toBe('CLIENT_ERROR');
    expect(envelope!.detail).toBe('Something exploded');
    expect(envelope!.validation_message_id).toBe('');
    expect(envelope!.request_id).toBe('');
  });

  it('uses fallback message for an Error with empty message', () => {
    const { handler, errorService } = setup();

    handler.handleError(new Error(''));

    const envelope = errorService.lastError();
    expect(envelope!.code).toBe('CLIENT_ERROR');
    expect(envelope!.detail).toBe('Unknown client error');
  });
});

// ── (d) Non-Error (plain string / object) ────────────────────────────────────

describe('GlobalErrorHandler — non-Error values', () => {
  it('records CLIENT_ERROR + String() coercion for a plain string', () => {
    const { handler, errorService } = setup();

    handler.handleError('zone.js unhandled rejection');

    const envelope = errorService.lastError();
    expect(envelope!.code).toBe('CLIENT_ERROR');
    expect(envelope!.detail).toBe('zone.js unhandled rejection');
  });

  it('records CLIENT_ERROR for a plain object', () => {
    const { handler, errorService } = setup();

    handler.handleError({ weird: true });

    const envelope = errorService.lastError();
    expect(envelope!.code).toBe('CLIENT_ERROR');
    expect(typeof envelope!.detail).toBe('string');
  });

  it('records CLIENT_ERROR for null', () => {
    const { handler, errorService } = setup();

    handler.handleError(null);

    const envelope = errorService.lastError();
    expect(envelope!.code).toBe('CLIENT_ERROR');
  });
});

// ── (e) isDevMode console.error ───────────────────────────────────────────────

describe('GlobalErrorHandler — isDevMode console logging', () => {
  it('calls console.error in dev mode (isDevMode() returns true in test env)', () => {
    const { handler } = setup();
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => undefined);

    handler.handleError(new Error('dev error'));

    // Angular test environment runs in dev mode — isDevMode() returns true.
    expect(consoleSpy).toHaveBeenCalledWith('[GlobalErrorHandler]', expect.any(Error));

    consoleSpy.mockRestore();
  });
});
