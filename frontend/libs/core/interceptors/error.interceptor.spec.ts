/**
 * error.interceptor.spec.ts — Wave 6 Wave A
 *
 * Tests errorInterceptor: typed 4-field envelope extraction + ErrorService recording.
 * Verifies that errors are NOT swallowed (re-thrown so callers' catchError still runs).
 */

import { TestBed } from '@angular/core/testing';
import {
  HttpClient,
  provideHttpClient,
  withFetch,
  withInterceptors,
} from '@angular/common/http';
import {
  provideHttpClientTesting,
  HttpTestingController,
} from '@angular/common/http/testing';
import { vi } from 'vitest';

import { ErrorService } from '../services/error.service';
import { errorInterceptor, ApiErrorEnvelope } from './error.interceptor';

// ── Setup ─────────────────────────────────────────────────────────────────────

function setup() {
  TestBed.configureTestingModule({
    providers: [
      provideHttpClient(withFetch(), withInterceptors([errorInterceptor])),
      provideHttpClientTesting(),
      ErrorService,
    ],
  });

  return {
    http:         TestBed.inject(HttpClient),
    controller:   TestBed.inject(HttpTestingController),
    errorService: TestBed.inject(ErrorService),
  };
}

afterEach(() => {
  TestBed.inject(HttpTestingController).verify();
});

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('errorInterceptor — success passthrough', () => {
  it('does not call ErrorService.record on a 200 response', () => {
    const { http, controller, errorService } = setup();
    const recordSpy = vi.spyOn(errorService, 'record');

    http.get('/api/v1/products').subscribe();

    const req = controller.expectOne('/api/v1/products');
    req.flush({ items: [] });

    expect(recordSpy).not.toHaveBeenCalled();
    expect(errorService.lastError()).toBeNull();
  });
});

describe('errorInterceptor — error envelope extraction', () => {
  it('records all 4 envelope fields for a well-formed error body', () => {
    const { http, controller, errorService } = setup();
    let errorCaught = false;

    http.get('/api/v1/products').subscribe({ error: () => { errorCaught = true; } });

    const req = controller.expectOne('/api/v1/products');
    req.flush(
      {
        detail: 'Resource not found',
        code: 'PRODUCT_NOT_FOUND',
        validation_message_id: 'msg-001',
        request_id: 'req-abc-123',
      },
      { status: 404, statusText: 'Not Found' },
    );

    const envelope = errorService.lastError();
    expect(envelope).not.toBeNull();
    expect(envelope!.detail).toBe('Resource not found');
    expect(envelope!.code).toBe('PRODUCT_NOT_FOUND');
    expect(envelope!.validation_message_id).toBe('msg-001');
    expect(envelope!.request_id).toBe('req-abc-123');
    // Error is NOT swallowed
    expect(errorCaught).toBe(true);
  });

  it('records errors[] array on 422 validation failure', () => {
    const { http, controller, errorService } = setup();

    http.post('/api/v1/products', {}).subscribe({ error: () => {} });

    const req = controller.expectOne('/api/v1/products');
    req.flush(
      {
        detail: 'Validation failed',
        code: 'VALIDATION_ERROR',
        validation_message_id: 'val-001',
        request_id: 'req-val',
        errors: [{ field: 'category_id', msg: 'required' }],
      },
      { status: 422, statusText: 'Unprocessable Entity' },
    );

    const envelope = errorService.lastError() as ApiErrorEnvelope;
    expect(envelope.errors).toHaveLength(1);
    expect((envelope.errors as Array<{ field: string }>)[0].field).toBe('category_id');
  });

  it('uses fallback values when error body is missing fields', () => {
    const { http, controller, errorService } = setup();

    http.get('/api/v1/products').subscribe({ error: () => {} });

    const req = controller.expectOne('/api/v1/products');
    // Minimal error body — some fields missing
    req.flush({ detail: 'Oops' }, { status: 500, statusText: 'Internal Server Error' });

    const envelope = errorService.lastError()!;
    expect(envelope.detail).toBe('Oops');
    expect(envelope.code).toBe('UNKNOWN');
    expect(envelope.validation_message_id).toBe('');
    expect(envelope.request_id).toBe('');
  });

  it('handles a completely empty error body gracefully', () => {
    const { http, controller, errorService } = setup();

    http.get('/api/v1/products').subscribe({ error: () => {} });

    const req = controller.expectOne('/api/v1/products');
    req.flush(null, { status: 503, statusText: 'Service Unavailable' });

    const envelope = errorService.lastError()!;
    expect(envelope).not.toBeNull();
    expect(typeof envelope.detail).toBe('string');
    expect(typeof envelope.code).toBe('string');
  });

  it('re-throws the error so callers catchError still runs', () => {
    const { http, controller } = setup();
    let errorStatus = 0;

    http.get('/api/v1/products').subscribe({
      error: (e: { status: number }) => { errorStatus = e.status; },
    });

    const req = controller.expectOne('/api/v1/products');
    req.flush(
      { detail: 'Forbidden', code: 'FORBIDDEN', validation_message_id: '', request_id: 'r1' },
      { status: 403, statusText: 'Forbidden' },
    );

    expect(errorStatus).toBe(403);
  });

  it('does not intercept 401 (that is refreshInterceptor territory)', () => {
    // 401 passes through errorInterceptor but IS recorded in ErrorService
    // (error interceptor records all HttpErrorResponses — it's the 401 the
    // refreshInterceptor handles upstream; error interceptor only sees what
    // refresh let through, which is: refresh-failed 401 or no-refresh-401).
    // In a chain WITHOUT refreshInterceptor (this test), 401 is recorded normally.
    const { http, controller, errorService } = setup();

    http.get('/api/v1/products').subscribe({ error: () => {} });

    const req = controller.expectOne('/api/v1/products');
    req.flush(
      { detail: 'Unauthorized', code: 'AUTH_REQUIRED', validation_message_id: '', request_id: 'r2' },
      { status: 401, statusText: 'Unauthorized' },
    );

    const envelope = errorService.lastError()!;
    expect(envelope.code).toBe('AUTH_REQUIRED');
  });
});

describe('errorInterceptor — ErrorService.clear()', () => {
  it('clear() resets lastError to null', () => {
    const { http, controller, errorService } = setup();

    http.get('/api/v1/products').subscribe({ error: () => {} });
    const req = controller.expectOne('/api/v1/products');
    req.flush({ detail: 'err', code: 'X', validation_message_id: '', request_id: '' }, { status: 500, statusText: 'err' });

    expect(errorService.lastError()).not.toBeNull();
    errorService.clear();
    expect(errorService.lastError()).toBeNull();
  });
});
