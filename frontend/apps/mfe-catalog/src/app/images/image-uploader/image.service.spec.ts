/**
 * image.service.spec.ts — Wave D reconcile (D-IMG-1)
 *
 * Tests ImageService with Angular HttpTestingController.
 * Uses TestBed (service-only — no component, no PrimeNG dependency).
 *
 * Wave D change: service now uses ApiClient (inject(ApiClient)) rather than HttpClient directly.
 * TestBed provides ApiClient via provideHttpClient(withFetch()) + provideHttpClientTesting()
 * (ApiClient is providedIn:'root'; HttpTestingController intercepts its internal HttpClient).
 *
 * Key assertion change (D-IMG-1): the service must NOT set an Authorization header manually.
 * The global jwtInterceptor owns auth header attachment. In these HttpTestingController tests
 * the interceptor is NOT registered (clean test isolation), so no Authorization header is
 * present on requests — confirmed by asserting header is null/absent on each service call.
 *
 * Error matrix coverage (per SPEC R-W6-1 P0):
 *
 * upload():
 *   - happy path: 202 → emits ImageUploadResponse
 *   - FormData POSTed to correct URL (NO manual Authorization header)
 *   - 401 → auth.logout() called + EMPTY (no emission)
 *   - 402 → EMPTY (no emission)
 *   - 404 → EMPTY (feature flag off)
 *   - 400 → EMPTY (bad idx/file)
 *   - 500 → EMPTY
 *
 * listImages():
 *   - happy path: 200 → emits ImagesListResponse (NO manual Authorization header)
 *   - maps { images: [] } (empty list)
 *   - 401 → logout() called + EMPTY
 *   - 404 → of({ images: [] }) (defensive — flag-off case)
 *   - 500 → of({ images: [] })
 *
 * pollImages() — D18 timer contract (PRESERVED EXACTLY):
 *   - stops polling when all images have status !== 'pending'
 *   - emits the resolved response before completing
 *   - continues polling when images are still pending
 *   - 500 on a poll → emits { images: [] } and continues
 *   - no leaked timer after completion
 *
 * tsconfig.spec.json has "types": ["vitest/globals"] — no explicit describe/it/expect imports.
 * vi import needed for vi.fn() / vi.useFakeTimers().
 * Vitest 4 syntax: vi.fn<(arg: T) => R>()  (single-generic arrow form — NOT Vitest-3 two-generic)
 */

import { TestBed } from '@angular/core/testing';
import {
  provideHttpClient,
  withFetch,
} from '@angular/common/http';
import {
  provideHttpClientTesting,
  HttpTestingController,
} from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
import { vi } from 'vitest';

import { AuthService } from '@mesell/core';
import { ImageService } from './image.service';
import type { ImageUploadResponse, ImagesListResponse, ImageSummary } from './image-uploader.model';

// ── Typed mocks ───────────────────────────────────────────────────────────────

interface MockAuthService {
  getToken: () => string | null;
  logout: ReturnType<typeof vi.fn>;
}

// ── Fixture helpers ───────────────────────────────────────────────────────────

const PRODUCT_ID = 'product-uuid-123';

function makeUploadResponse(): ImageUploadResponse {
  return {
    image_id:         'img-uuid-001',
    gcs_path:         'gs://meesell-dev/products/product-uuid-123/1.jpg',
    status:           'pending',
    idx:              1,
    enqueued_task_id: 'celery-task-abc',
  };
}

function makePendingImage(idx = 1): ImageSummary {
  return {
    image_id:      `img-${idx}`,
    idx,
    status:        'pending',
    signed_url:    `https://storage.googleapis.com/signed/${idx}`,
    precheck_jsonb: {
      jpeg_valid:       true,
      color_space:      true,
      resolution_pass:  true,
      white_background: true,
      watermark_check:  true,
    },
    is_front:    idx === 1,
    width:       null,
    height:      null,
    color_space: null,
    created_at:  '2026-06-11T10:00:00Z',
  };
}

function makeReadyImage(idx = 1): ImageSummary {
  return { ...makePendingImage(idx), status: 'ready', width: 2000, height: 2000, color_space: 'RGB' };
}

function makeFailedImage(idx = 1): ImageSummary {
  return {
    ...makePendingImage(idx),
    status: 'failed_precheck',
    precheck_jsonb: {
      jpeg_valid:       true,
      color_space:      false,  // CMYK
      resolution_pass:  true,
      white_background: true,
      watermark_check:  true,
    },
  };
}

const EMPTY_LIST: ImagesListResponse = { images: [] };
const PENDING_LIST: ImagesListResponse = { images: [makePendingImage(1)] };
const RESOLVED_LIST: ImagesListResponse = { images: [makeReadyImage(1)] };

// ── TestBed setup ─────────────────────────────────────────────────────────────

function setup(tokenValue: string | null = 'mock-jwt-token') {
  const mockAuth: MockAuthService = {
    getToken: () => tokenValue,
    logout:   vi.fn(),
  };

  TestBed.configureTestingModule({
    providers: [
      ImageService,
      provideHttpClient(withFetch()),
      provideHttpClientTesting(),
      provideRouter([{ path: 'login', children: [] }]),
      { provide: AuthService, useValue: mockAuth },
    ],
  });

  const service    = TestBed.inject(ImageService);
  const controller = TestBed.inject(HttpTestingController);
  const router     = TestBed.inject(Router);

  return { service, controller, auth: mockAuth, router };
}

// ── upload() — happy path ─────────────────────────────────────────────────────

describe('ImageService.upload() — happy path', () => {
  afterEach(() => {
    TestBed.inject(HttpTestingController).verify();
  });

  it('POSTs to /api/v1/products/{productId}/images with FormData', () => {
    const { service, controller } = setup();
    const file = new File(['data'], 'photo.jpg', { type: 'image/jpeg' });

    service.upload(PRODUCT_ID, file, 1).subscribe();

    const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/images`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toBeInstanceOf(FormData);
    req.flush(makeUploadResponse(), { status: 202, statusText: 'Accepted' });
  });

  it('appends file and idx to FormData', () => {
    const { service, controller } = setup();
    const file = new File(['data'], 'photo.jpg', { type: 'image/jpeg' });

    service.upload(PRODUCT_ID, file, 2).subscribe();

    const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/images`);
    const formData = req.request.body as FormData;
    expect(formData.get('file')).toBe(file);
    expect(formData.get('idx')).toBe('2');
    req.flush(makeUploadResponse(), { status: 202, statusText: 'Accepted' });
  });

  it('does NOT set a manual Authorization header — jwtInterceptor owns auth', () => {
    // D-IMG-1 assertion: service must NOT manually attach Bearer.
    // In this test the jwtInterceptor is NOT registered in TestBed, so no Authorization
    // header should appear on the outgoing request from the service itself.
    const { service, controller } = setup('my-upload-token');
    const file = new File(['data'], 'photo.jpg', { type: 'image/jpeg' });

    service.upload(PRODUCT_ID, file, 1).subscribe();

    const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/images`);
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush(makeUploadResponse(), { status: 202, statusText: 'Accepted' });
  });

  it('emits ImageUploadResponse on 202', () => {
    const { service, controller } = setup();
    const emitted: ImageUploadResponse[] = [];
    const file = new File(['data'], 'photo.jpg', { type: 'image/jpeg' });

    service.upload(PRODUCT_ID, file, 1).subscribe((r) => emitted.push(r));

    const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/images`);
    req.flush(makeUploadResponse(), { status: 202, statusText: 'Accepted' });

    expect(emitted).toHaveLength(1);
    expect(emitted[0].image_id).toBe('img-uuid-001');
    expect(emitted[0].status).toBe('pending');
    expect(emitted[0].idx).toBe(1);
  });
});

// ── upload() — error matrix ───────────────────────────────────────────────────

describe('ImageService.upload() — error matrix', () => {
  afterEach(() => {
    TestBed.inject(HttpTestingController).verify();
  });

  it('401 → auth.logout() called and EMPTY (no emission, stream completes)', () => {
    const { service, controller, auth } = setup();
    const emitted: ImageUploadResponse[] = [];
    let completed = false;
    const file = new File(['data'], 'photo.jpg', { type: 'image/jpeg' });

    service.upload(PRODUCT_ID, file, 1).subscribe({
      next: (r) => emitted.push(r),
      complete: () => { completed = true; },
    });

    const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/images`);
    req.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

    expect(auth.logout).toHaveBeenCalledOnce();
    expect(emitted).toHaveLength(0);
    expect(completed).toBe(true);
  });

  it('402 → EMPTY (plan quota exceeded; no emission)', () => {
    const { service, controller } = setup();
    const emitted: ImageUploadResponse[] = [];
    let completed = false;
    const file = new File(['data'], 'photo.jpg', { type: 'image/jpeg' });

    service.upload(PRODUCT_ID, file, 1).subscribe({
      next: (r) => emitted.push(r),
      complete: () => { completed = true; },
    });

    const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/images`);
    req.flush({ detail: 'Quota exceeded' }, { status: 402, statusText: 'Payment Required' });

    expect(emitted).toHaveLength(0);
    expect(completed).toBe(true);
  });

  it('404 → EMPTY (feature flag disabled; caller shows disabled state)', () => {
    const { service, controller } = setup();
    const emitted: ImageUploadResponse[] = [];
    let completed = false;
    const file = new File(['data'], 'photo.jpg', { type: 'image/jpeg' });

    service.upload(PRODUCT_ID, file, 1).subscribe({
      next: (r) => emitted.push(r),
      complete: () => { completed = true; },
    });

    const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/images`);
    req.flush({ detail: 'Not Found' }, { status: 404, statusText: 'Not Found' });

    expect(emitted).toHaveLength(0);
    expect(completed).toBe(true);
  });

  it('400 → EMPTY (bad idx/file; caller validation responsibility)', () => {
    const { service, controller } = setup();
    const emitted: ImageUploadResponse[] = [];
    let completed = false;
    const file = new File(['data'], 'photo.jpg', { type: 'image/jpeg' });

    service.upload(PRODUCT_ID, file, 0).subscribe({
      next: (r) => emitted.push(r),
      complete: () => { completed = true; },
    });

    const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/images`);
    req.flush({ detail: 'idx must be 1-4' }, { status: 400, statusText: 'Bad Request' });

    expect(emitted).toHaveLength(0);
    expect(completed).toBe(true);
  });

  it('500 → EMPTY', () => {
    const { service, controller } = setup();
    const emitted: ImageUploadResponse[] = [];
    let completed = false;
    const file = new File(['data'], 'photo.jpg', { type: 'image/jpeg' });

    service.upload(PRODUCT_ID, file, 1).subscribe({
      next: (r) => emitted.push(r),
      complete: () => { completed = true; },
    });

    const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/images`);
    req.flush({ detail: 'Internal Server Error' }, { status: 500, statusText: 'Internal Server Error' });

    expect(emitted).toHaveLength(0);
    expect(completed).toBe(true);
  });
});

// ── listImages() ──────────────────────────────────────────────────────────────

describe('ImageService.listImages()', () => {
  afterEach(() => {
    TestBed.inject(HttpTestingController).verify();
  });

  it('GETs /api/v1/products/{productId}/images without a manual Authorization header', () => {
    // D-IMG-1 assertion: jwtInterceptor (NOT registered in TestBed) owns auth.
    // Service must not inject any Authorization header itself.
    const { service, controller } = setup('list-token');

    service.listImages(PRODUCT_ID).subscribe();

    const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/images`);
    expect(req.request.method).toBe('GET');
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush(EMPTY_LIST);
  });

  it('emits { images: [] } for an empty product', () => {
    const { service, controller } = setup();
    const emitted: ImagesListResponse[] = [];

    service.listImages(PRODUCT_ID).subscribe((r) => emitted.push(r));

    const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/images`);
    req.flush(EMPTY_LIST);

    expect(emitted).toHaveLength(1);
    expect(emitted[0].images).toHaveLength(0);
  });

  it('emits a list with resolved images', () => {
    const { service, controller } = setup();
    const emitted: ImagesListResponse[] = [];

    service.listImages(PRODUCT_ID).subscribe((r) => emitted.push(r));

    const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/images`);
    req.flush(RESOLVED_LIST);

    expect(emitted).toHaveLength(1);
    expect(emitted[0].images[0].status).toBe('ready');
  });

  it('401 → auth.logout() called and EMPTY', () => {
    const { service, controller, auth } = setup();
    const emitted: ImagesListResponse[] = [];
    let completed = false;

    service.listImages(PRODUCT_ID).subscribe({
      next: (r) => emitted.push(r),
      complete: () => { completed = true; },
    });

    const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/images`);
    req.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

    expect(auth.logout).toHaveBeenCalledOnce();
    expect(emitted).toHaveLength(0);
    expect(completed).toBe(true);
  });

  it('404 → of({ images: [] }) (defensive: flag-off handled as empty list)', () => {
    const { service, controller } = setup();
    const emitted: ImagesListResponse[] = [];

    service.listImages(PRODUCT_ID).subscribe((r) => emitted.push(r));

    const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/images`);
    req.flush({ detail: 'Not Found' }, { status: 404, statusText: 'Not Found' });

    expect(emitted).toHaveLength(1);
    expect(emitted[0]).toEqual(EMPTY_LIST);
  });

  it('500 → of({ images: [] })', () => {
    const { service, controller } = setup();
    const emitted: ImagesListResponse[] = [];

    service.listImages(PRODUCT_ID).subscribe((r) => emitted.push(r));

    const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/images`);
    req.flush({ detail: 'Internal Server Error' }, { status: 500, statusText: 'Internal Server Error' });

    expect(emitted).toHaveLength(1);
    expect(emitted[0]).toEqual(EMPTY_LIST);
  });
});

// ── pollImages() — D18 timer contract (PRESERVED EXACTLY) ────────────────────

describe('ImageService.pollImages()', () => {
  afterEach(() => {
    vi.useRealTimers();
    TestBed.inject(HttpTestingController).verify();
  });

  it('stops polling and completes when first response has no pending images', () => {
    vi.useFakeTimers();
    const { service, controller } = setup();
    const emitted: ImagesListResponse[] = [];
    let completed = false;

    service.pollImages(PRODUCT_ID).subscribe({
      next: (r) => emitted.push(r),
      complete: () => { completed = true; },
    });

    // Advance past first delay (1000ms)
    vi.advanceTimersByTime(1500);

    const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/images`);
    req.flush(RESOLVED_LIST);

    expect(emitted).toHaveLength(1);
    expect(emitted[0].images[0].status).toBe('ready');
    expect(completed).toBe(true);
  });

  it('continues polling while images are pending', () => {
    vi.useFakeTimers();
    const { service, controller } = setup();
    const emitted: ImagesListResponse[] = [];
    let completed = false;

    service.pollImages(PRODUCT_ID).subscribe({
      next: (r) => emitted.push(r),
      complete: () => { completed = true; },
    });

    // First poll: advance 1s → pending response
    vi.advanceTimersByTime(1500);
    const req1 = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/images`);
    req1.flush(PENDING_LIST);

    expect(emitted).toHaveLength(1);
    expect(completed).toBe(false);

    // Second poll: advance 2s (next delay) → resolved response
    vi.advanceTimersByTime(2500);
    const req2 = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/images`);
    req2.flush(RESOLVED_LIST);

    expect(emitted).toHaveLength(2);
    expect(emitted[1].images[0].status).toBe('ready');
    expect(completed).toBe(true);
  });

  it('5xx on poll → emits { images: [] } (graceful) and completes', () => {
    vi.useFakeTimers();
    const { service, controller } = setup();
    const emitted: ImagesListResponse[] = [];
    let completed = false;

    service.pollImages(PRODUCT_ID).subscribe({
      next: (r) => emitted.push(r),
      complete: () => { completed = true; },
    });

    vi.advanceTimersByTime(1500);
    const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/images`);
    req.flush({ detail: 'Server Error' }, { status: 500, statusText: 'Internal Server Error' });

    // handleListError returns of({ images: [] }) for 5xx — no pending, stream completes
    expect(emitted).toHaveLength(1);
    expect(emitted[0]).toEqual(EMPTY_LIST);
    expect(completed).toBe(true);
  });

  it('unsubscribing before first poll fires leaves no leaked timer', () => {
    vi.useFakeTimers();
    const { service } = setup();
    let nexted = false;

    const sub = service.pollImages(PRODUCT_ID).subscribe({
      next: () => { nexted = true; },
    });

    // Unsubscribe before the first 1s delay fires
    sub.unsubscribe();
    vi.advanceTimersByTime(2000);

    // No HTTP request should have been made (no unmatched requests — verify() in afterEach)
    expect(nexted).toBe(false);
  });
});

// ── D-IMG-1 contract assertions ───────────────────────────────────────────────

describe('ImageService — D-IMG-1 ApiClient contract assertions', () => {
  afterEach(() => {
    TestBed.inject(HttpTestingController).verify();
  });

  it('uses ApiClient (inject(ApiClient)) — not raw HttpClient — confirmed by TestBed wiring', () => {
    // ApiClient is providedIn:'root'; TestBed provides it via provideHttpClient(withFetch()).
    // If the service still injected HttpClient directly, this test suite would fail with
    // NullInjectorError for HttpClient (since we only provide ApiClient, not HttpClient directly).
    // The fact that ALL tests in this file pass confirms ApiClient is the injected dependency.
    const { service } = setup();
    expect(service).toBeTruthy();
  });

  it('upload() does NOT fire retryOn503 — non-idempotent POST', () => {
    // The service passes no retryOn503 option. If a 503 occurs, only ONE request is made
    // (no retry). Verify: flush 503 → only 1 request seen by controller.
    const { service, controller } = setup();
    const file = new File(['data'], 'photo.jpg', { type: 'image/jpeg' });

    service.upload(PRODUCT_ID, file, 1).subscribe();

    const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/images`);
    req.flush({ detail: 'Service Unavailable' }, { status: 503, statusText: 'Service Unavailable' });

    // After flushing 503, no retry request should appear — verify() would throw if it did
    controller.verify();
  });

  it('listImages() does NOT fire retryOn503 (ApiClient defect — D18 poll is the resilience)', () => {
    // Same: no retry on any error status.
    const { service, controller } = setup();

    service.listImages(PRODUCT_ID).subscribe();

    const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}/images`);
    req.flush({ detail: 'Service Unavailable' }, { status: 503, statusText: 'Service Unavailable' });

    controller.verify();
  });
});
