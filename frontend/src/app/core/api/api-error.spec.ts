// core/api/api-error.spec.ts
// Covers: ApiError construction, normaliseHttpError() status-code mapping

import { HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { describe, expect, it } from 'vitest';
import { ApiError, normaliseHttpError } from './api-error';

describe('ApiError', () => {
  it('constructs with required fields', () => {
    const err = new ApiError({ kind: 'http', status: 500, displayMessage: 'Server error' });
    expect(err.kind).toBe('http');
    expect(err.status).toBe(500);
    expect(err.displayMessage).toBe('Server error');
    expect(err.code).toBeNull();
    expect(err.traceId).toBeNull();
    expect(err.raw).toBeNull();
    expect(err.name).toBe('ApiError');
  });

  it('is an instance of Error', () => {
    const err = new ApiError({ kind: 'network', status: 0, displayMessage: 'Offline' });
    expect(err).toBeInstanceOf(Error);
  });

  it('stores optional fields', () => {
    const raw = new HttpErrorResponse({ status: 422 });
    const err = new ApiError({
      kind: 'http',
      status: 422,
      code: 'validation_failed',
      displayMessage: 'Bad',
      traceId: 'abc-123',
      raw,
    });
    expect(err.code).toBe('validation_failed');
    expect(err.traceId).toBe('abc-123');
    expect(err.raw).toBe(raw);
  });
});

describe('normaliseHttpError', () => {
  function makeResponse(status: number, body?: unknown, headers?: Record<string, string>): HttpErrorResponse {
    return new HttpErrorResponse({
      status,
      error: body ?? null,
      headers: new HttpHeaders(headers ?? {}),
      url: 'https://api.test/api/v1/products',
    });
  }

  it('maps network error (status 0, ProgressEvent) to kind=network', () => {
    const err = new HttpErrorResponse({ status: 0, error: new ProgressEvent('error') });
    const apiError = normaliseHttpError(err);
    expect(apiError.kind).toBe('network');
    expect(apiError.status).toBe(0);
    expect(apiError.displayMessage).toContain('connection');
  });

  it('maps status 0 (no ProgressEvent) to kind=network', () => {
    const err = new HttpErrorResponse({ status: 0, error: null });
    const apiError = normaliseHttpError(err);
    expect(apiError.kind).toBe('network');
  });

  it('maps 400 with detail to displayMessage', () => {
    const err = makeResponse(400, { detail: 'Bad field X' });
    const apiError = normaliseHttpError(err);
    expect(apiError.status).toBe(400);
    expect(apiError.displayMessage).toBe('Bad field X');
  });

  it('maps 400 without detail to fallback message', () => {
    const err = makeResponse(400);
    const apiError = normaliseHttpError(err);
    expect(apiError.displayMessage).toContain('Invalid request');
  });

  it('maps 401 to session-expired message regardless of body', () => {
    const err = makeResponse(401, { detail: 'Unauthorized' });
    const apiError = normaliseHttpError(err);
    expect(apiError.status).toBe(401);
    expect(apiError.displayMessage).toContain('session has expired');
  });

  it('maps 403 to permission-denied message', () => {
    const err = makeResponse(403);
    const apiError = normaliseHttpError(err);
    expect(apiError.displayMessage).toContain('permission');
  });

  it('maps 404 with detail', () => {
    const err = makeResponse(404, { detail: 'Product not found' });
    const apiError = normaliseHttpError(err);
    expect(apiError.displayMessage).toBe('Product not found');
  });

  it('maps 422 with detail to validation message', () => {
    const err = makeResponse(422, { detail: 'Field mrp is required' });
    const apiError = normaliseHttpError(err);
    expect(apiError.status).toBe(422);
    expect(apiError.displayMessage).toBe('Field mrp is required');
  });

  it('maps 422 without detail to fallback validation message', () => {
    const err = makeResponse(422);
    const apiError = normaliseHttpError(err);
    expect(apiError.displayMessage).toContain('Validation failed');
  });

  it('maps 429 to rate-limit message', () => {
    const err = makeResponse(429);
    const apiError = normaliseHttpError(err);
    expect(apiError.displayMessage).toContain('Too many requests');
  });

  it('maps 503 to service-unavailable message', () => {
    const err = makeResponse(503);
    const apiError = normaliseHttpError(err);
    expect(apiError.displayMessage).toContain('temporarily unavailable');
  });

  it('maps 500 to generic server error', () => {
    const err = makeResponse(500);
    const apiError = normaliseHttpError(err);
    expect(apiError.displayMessage).toContain('went wrong on our side');
  });

  it('extracts x-request-id header as traceId', () => {
    const err = makeResponse(500, null, { 'x-request-id': 'trace-xyz-999' });
    const apiError = normaliseHttpError(err);
    expect(apiError.traceId).toBe('trace-xyz-999');
  });

  it('extracts machine-readable code from body', () => {
    const err = makeResponse(400, { detail: 'Limit exceeded', code: 'rate_limit_exceeded' });
    const apiError = normaliseHttpError(err);
    expect(apiError.code).toBe('rate_limit_exceeded');
  });

  it('returns null traceId when header absent', () => {
    const err = makeResponse(422);
    const apiError = normaliseHttpError(err);
    expect(apiError.traceId).toBeNull();
  });

  it('always sets kind=http for non-zero, non-ProgressEvent responses', () => {
    for (const status of [400, 401, 403, 404, 422, 429, 500, 503]) {
      const err = makeResponse(status);
      expect(normaliseHttpError(err).kind).toBe('http');
    }
  });
});
