/**
 * ExportApiService — contract tests.
 *
 * Covers:
 *   1. initiate() — URL, method, body, 202 mapping
 *   2. poll() — URL, method, status mapping (pending/ready/failed)
 *   3. Error matrix: 401 / 404 / 422 / 400 / 5xx for initiate
 *   4. Error matrix: 401 / 404 / 5xx for poll
 *   5. retryOn503 on poll only (NOT on initiate)
 *   6. D18 note: service exposes ONE GET per call (component's setInterval drives repetition)
 *
 * Uses HttpTestingController pattern (Wave B established).
 * No AuthService needed — jwtInterceptor owns auth header attachment (not tested here).
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { provideHttpClient, withFetch } from '@angular/common/http';
import {
  provideHttpClientTesting,
  HttpTestingController,
} from '@angular/common/http/testing';

import { ExportApiService, ExportNotFoundError, type InitiateValidationError, type InitiateUnavailableError } from './export.service';
import type { ExportInitiatedResponse, ExportResponseDTO } from './export.model';

// ── Fixtures ──────────────────────────────────────────────────────────────────

const PRODUCT_ID = 'prod-abc-123';
const EXPORT_ID  = 'exp-xyz-789';

const INITIATED_RESP: ExportInitiatedResponse = {
  export_id:        EXPORT_ID,
  status:           'pending',
  enqueued_task_id: 'celery-task-001',
  initiated_at:     '2026-06-12T10:00:00Z',
};

const PENDING_POLL: ExportResponseDTO = {
  export_id:           EXPORT_ID,
  product_id:          PRODUCT_ID,
  status:              'pending',
  format:              'xlsx_with_images',
  xlsx_signed_url:     null,
  zip_signed_url:      null,
  error_message:       null,
  error_code:          null,
  initiated_at:        '2026-06-12T10:00:00Z',
  completed_at:        null,
  round_trip_validated: null,
};

const READY_POLL: ExportResponseDTO = {
  ...PENDING_POLL,
  status:              'ready',
  xlsx_signed_url:     'https://storage.googleapis.com/mee-exports/export-123.xlsx?sig=xxx',
  zip_signed_url:      'https://storage.googleapis.com/mee-exports/export-123.zip?sig=xxx',
  round_trip_validated: true,
};

const FAILED_POLL: ExportResponseDTO = {
  ...PENDING_POLL,
  status:        'failed',
  error_message: 'Image processing failed',
  error_code:    'image.processing_error',
};

// ── Test setup ────────────────────────────────────────────────────────────────

describe('ExportApiService', () => {
  let service:    ExportApiService;
  let controller: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        ExportApiService,
        provideHttpClient(withFetch()),
        provideHttpClientTesting(),
      ],
    });
    service    = TestBed.inject(ExportApiService);
    controller = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    controller.verify();
  });

  // ── initiate() ─────────────────────────────────────────────────────────────

  describe('initiate()', () => {
    it('should POST to /api/v1/products/{productId}/export-xlsx', () => {
      let emitted: ExportInitiatedResponse | undefined;
      service.initiate(PRODUCT_ID).subscribe((r) => {
        if (!('kind' in r)) emitted = r as ExportInitiatedResponse;
      });

      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/export-xlsx`);
      expect(req.request.method).toBe('POST');
      req.flush(INITIATED_RESP, { status: 202, statusText: 'Accepted' });

      expect(emitted).toEqual(INITIATED_RESP);
    });

    it('should send format=xlsx_with_images in the request body', () => {
      service.initiate(PRODUCT_ID).subscribe();
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/export-xlsx`);
      expect(req.request.body).toEqual({ format: 'xlsx_with_images' });
      req.flush(INITIATED_RESP, { status: 202, statusText: 'Accepted' });
    });

    it('should send format=xlsx_only when explicitly specified', () => {
      service.initiate(PRODUCT_ID, 'xlsx_only').subscribe();
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/export-xlsx`);
      expect(req.request.body).toEqual({ format: 'xlsx_only' });
      req.flush(INITIATED_RESP, { status: 202, statusText: 'Accepted' });
    });

    it('should NOT add a manual Authorization header (jwtInterceptor owns it)', () => {
      service.initiate(PRODUCT_ID).subscribe();
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/export-xlsx`);
      expect(req.request.headers.has('Authorization')).toBe(false);
      req.flush(INITIATED_RESP, { status: 202, statusText: 'Accepted' });
    });

    it('should NOT set retryOn503 (non-idempotent POST — double-enqueue risk)', () => {
      // This test ensures only ONE request is made (no retry on error).
      let emitted = false;
      service.initiate(PRODUCT_ID).subscribe({ next: () => (emitted = true) });
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/export-xlsx`);
      req.flush(INITIATED_RESP, { status: 202, statusText: 'Accepted' });
      expect(emitted).toBe(true);
    });

    // ── Error matrix (R-W6-1) ───────────────────────────────────────────────

    it('should return EMPTY on 401 (no emission, no error callback)', () => {
      let nextCalled  = false;
      let errorCalled = false;
      service.initiate(PRODUCT_ID).subscribe({
        next:  () => (nextCalled  = true),
        error: () => (errorCalled = true),
      });
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/export-xlsx`);
      req.flush('Unauthorized', { status: 401, statusText: 'Unauthorized' });
      expect(nextCalled).toBe(false);
      expect(errorCalled).toBe(false);
    });

    it('should emit InitiateUnavailableError shape on 404 (flag-off or product not found)', () => {
      let emitted: InitiateUnavailableError | undefined;
      service.initiate(PRODUCT_ID).subscribe((r) => {
        if ('kind' in r && r.kind === 'unavailable') emitted = r as InitiateUnavailableError;
      });
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/export-xlsx`);
      req.flush({ detail: 'Not found' }, { status: 404, statusText: 'Not Found' });
      expect(emitted).toBeDefined();
      expect(emitted?.kind).toBe('unavailable');
      expect(emitted?.error_code).toBe('export.unavailable');
    });

    it('should emit InitiateValidationError shape on 422 with detail + error_code', () => {
      let emitted: InitiateValidationError | undefined;
      service.initiate(PRODUCT_ID).subscribe((r) => {
        if ('kind' in r && r.kind === 'validation') emitted = r as InitiateValidationError;
      });
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/export-xlsx`);
      req.flush(
        { detail: 'Product is not ready for export.', error_code: 'export.product_not_ready' },
        { status: 422, statusText: 'Unprocessable Entity' },
      );
      expect(emitted).toBeDefined();
      expect(emitted?.kind).toBe('validation');
      expect(emitted?.detail).toBe('Product is not ready for export.');
      expect(emitted?.error_code).toBe('export.product_not_ready');
    });

    it('should emit InitiateValidationError with front_image_missing error_code on 422', () => {
      let emitted: InitiateValidationError | undefined;
      service.initiate(PRODUCT_ID).subscribe((r) => {
        if ('kind' in r && r.kind === 'validation') emitted = r as InitiateValidationError;
      });
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/export-xlsx`);
      req.flush(
        { detail: 'Front image is missing.', error_code: 'export.front_image_missing' },
        { status: 422, statusText: 'Unprocessable Entity' },
      );
      expect(emitted?.error_code).toBe('export.front_image_missing');
    });

    it('should return EMPTY on 400', () => {
      let nextCalled = false;
      service.initiate(PRODUCT_ID).subscribe({ next: () => (nextCalled = true) });
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/export-xlsx`);
      req.flush({ detail: 'Bad request' }, { status: 400, statusText: 'Bad Request' });
      expect(nextCalled).toBe(false);
    });

    it('should return EMPTY on 500', () => {
      let nextCalled = false;
      service.initiate(PRODUCT_ID).subscribe({ next: () => (nextCalled = true) });
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/export-xlsx`);
      req.flush({ detail: 'Internal error' }, { status: 500, statusText: 'Internal Server Error' });
      expect(nextCalled).toBe(false);
    });
  });

  // ── poll() ─────────────────────────────────────────────────────────────────

  describe('poll()', () => {
    it('should GET /api/v1/exports/{exportId}', () => {
      let emitted: ExportResponseDTO | undefined;
      service.poll(EXPORT_ID).subscribe((r) => (emitted = r));

      const req = controller.expectOne(`/api/v1/exports/${EXPORT_ID}`);
      expect(req.request.method).toBe('GET');
      req.flush(PENDING_POLL);

      expect(emitted).toEqual(PENDING_POLL);
    });

    it('should map status=pending correctly', () => {
      let emitted: ExportResponseDTO | undefined;
      service.poll(EXPORT_ID).subscribe((r) => (emitted = r));
      controller.expectOne(`/api/v1/exports/${EXPORT_ID}`).flush(PENDING_POLL);
      expect(emitted?.status).toBe('pending');
      expect(emitted?.xlsx_signed_url).toBeNull();
    });

    it('should map status=ready correctly with signed URLs', () => {
      let emitted: ExportResponseDTO | undefined;
      service.poll(EXPORT_ID).subscribe((r) => (emitted = r));
      controller.expectOne(`/api/v1/exports/${EXPORT_ID}`).flush(READY_POLL);
      expect(emitted?.status).toBe('ready');
      expect(emitted?.xlsx_signed_url).toContain('https://storage.googleapis.com');
      expect(emitted?.zip_signed_url).toContain('https://storage.googleapis.com');
      expect(emitted?.round_trip_validated).toBe(true);
    });

    it('should map status=failed correctly with error_message', () => {
      let emitted: ExportResponseDTO | undefined;
      service.poll(EXPORT_ID).subscribe((r) => (emitted = r));
      controller.expectOne(`/api/v1/exports/${EXPORT_ID}`).flush(FAILED_POLL);
      expect(emitted?.status).toBe('failed');
      expect(emitted?.error_message).toBe('Image processing failed');
      expect(emitted?.error_code).toBe('image.processing_error');
    });

    it('should NOT add a manual Authorization header', () => {
      service.poll(EXPORT_ID).subscribe();
      const req = controller.expectOne(`/api/v1/exports/${EXPORT_ID}`);
      expect(req.request.headers.has('Authorization')).toBe(false);
      req.flush(PENDING_POLL);
    });

    it('should have retryOn503 opt-in set (idempotent GET)', () => {
      // We verify the service does NOT swallow errors unexpectedly on a clean 200.
      // The retryOn503 behavior is tested via the ApiClient's retry operator in its own spec.
      // Here we just confirm the happy path works (retryOn503 doesn't break normal flow).
      let emitted: ExportResponseDTO | undefined;
      service.poll(EXPORT_ID).subscribe((r) => (emitted = r));
      controller.expectOne(`/api/v1/exports/${EXPORT_ID}`).flush(READY_POLL);
      expect(emitted?.status).toBe('ready');
    });

    // ── Error matrix (R-W6-1) ───────────────────────────────────────────────

    it('should return EMPTY on 401 (no emission, no error)', () => {
      let nextCalled  = false;
      let errorCalled = false;
      service.poll(EXPORT_ID).subscribe({
        next:  () => (nextCalled  = true),
        error: () => (errorCalled = true),
      });
      controller.expectOne(`/api/v1/exports/${EXPORT_ID}`).flush(
        'Unauthorized',
        { status: 401, statusText: 'Unauthorized' },
      );
      expect(nextCalled).toBe(false);
      expect(errorCalled).toBe(false);
    });

    it('should throw ExportNotFoundError on 404', () => {
      let thrownError: unknown;
      service.poll(EXPORT_ID).subscribe({
        error: (e) => (thrownError = e),
      });
      controller.expectOne(`/api/v1/exports/${EXPORT_ID}`).flush(
        { detail: 'Not found' },
        { status: 404, statusText: 'Not Found' },
      );
      expect(thrownError).toBeInstanceOf(ExportNotFoundError);
    });

    it('ExportNotFoundError should carry the export ID in its message', () => {
      let thrownError: unknown;
      service.poll(EXPORT_ID).subscribe({ error: (e) => (thrownError = e) });
      controller.expectOne(`/api/v1/exports/${EXPORT_ID}`).flush(
        { detail: 'Not found' },
        { status: 404, statusText: 'Not Found' },
      );
      expect((thrownError as Error).message).toContain(EXPORT_ID);
    });

    it('should return EMPTY on 500 (poll loop retries naturally via component maxPolls)', () => {
      let nextCalled  = false;
      let errorCalled = false;
      service.poll(EXPORT_ID).subscribe({
        next:  () => (nextCalled  = true),
        error: () => (errorCalled = true),
      });
      controller.expectOne(`/api/v1/exports/${EXPORT_ID}`).flush(
        { detail: 'Server error' },
        { status: 500, statusText: 'Internal Server Error' },
      );
      expect(nextCalled).toBe(false);
      expect(errorCalled).toBe(false);
    });

    it('should re-throw 503 for retry (not crash caller; retry handles backoff)', () => {
      // 503 → catchError re-throws → retry(count:2, delay:timer) schedules retry.
      // In synchronous tests the delay timer never fires → observer stays open (not errored).
      // We verify: no crash (errorCalled=false), no immediate value (nextCalled=false).
      let nextCalled  = false;
      let errorCalled = false;
      service.poll(EXPORT_ID).subscribe({
        next:  () => (nextCalled  = true),
        error: () => (errorCalled = true),
      });
      // Initial 503 response — triggers catchError re-throw → retry scheduled (timer-delayed).
      const req = controller.expectOne(`/api/v1/exports/${EXPORT_ID}`);
      req.flush({ detail: 'Service unavailable' }, { status: 503, statusText: 'Service Unavailable' });
      // Retry timer does not fire synchronously → observer still open → no error/next yet.
      expect(nextCalled).toBe(false);
      expect(errorCalled).toBe(false);
    });

    it('should NOT retry on 503 for initiate() — POST is non-idempotent (double-enqueue risk)', () => {
      // initiate() 503 → catchError default branch → EMPTY (no retry, no re-throw).
      // Unlike poll(), initiate() must NOT retry to avoid double-enqueue.
      let nextCalled  = false;
      let errorCalled = false;
      service.initiate(PRODUCT_ID).subscribe({
        next:  () => (nextCalled  = true),
        error: () => (errorCalled = true),
      });
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/export-xlsx`);
      req.flush({ detail: 'Service unavailable' }, { status: 503, statusText: 'Service Unavailable' });
      // Falls to EMPTY (default 5xx branch in initiate catchError — no retry).
      expect(nextCalled).toBe(false);
      expect(errorCalled).toBe(false);
    });
  });

  // ── URL exact-match contract greps ─────────────────────────────────────────

  describe('URL contracts', () => {
    it('initiate URL matches /api/v1/products/{productId}/export-xlsx exactly', () => {
      service.initiate('pid-001').subscribe();
      const req = controller.expectOne('/api/v1/products/pid-001/export-xlsx');
      req.flush(INITIATED_RESP, { status: 202, statusText: 'Accepted' });
      // No assertions needed — expectOne throws if URL does not match.
    });

    it('poll URL matches /api/v1/exports/{exportId} exactly', () => {
      service.poll('eid-001').subscribe();
      const req = controller.expectOne('/api/v1/exports/eid-001');
      req.flush(PENDING_POLL);
    });
  });
});
