/**
 * DashboardApiService — unit tests (Wave 6 Wave B — 2026-06-12)
 *
 * Uses Angular HttpTestingController pattern (established in auth-api.service.spec.ts).
 * Covers:
 *   Happy path:  GET /api/v1/products?page=1&limit=20  → DashboardResponse shape
 *   Happy path:  DELETE /api/v1/products/{id}          → void (204)
 *   Error matrix: 401, 402, 400, 404 (loadProducts), 404 (deleteProduct), 5xx
 *
 * NO manual Authorization header on any request (jwtInterceptor owns it per R-W6-1).
 * The TestBed here does NOT register the interceptors — we test the SERVICE CONTRACT.
 * The interceptor chain is tested separately in jwt.interceptor.spec.ts etc.
 */

import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient, withFetch } from '@angular/common/http';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

import { DashboardApiService } from './dashboard-api.service';
import { DashboardResponse, ProductListItem } from '../dashboard.model';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Minimal valid ProductListItem matching the backend wire shape. */
function makeItem(n: number): ProductListItem {
  return {
    product_id: `prod-${n}`,
    name: `Product ${n}`,
    category_id: `cat-${n}`,
    status: n % 2 === 0 ? 'ready' : 'draft',
    created_at: new Date(Date.now() - n * 60_000).toISOString(),
    updated_at: new Date(Date.now() - n * 30_000).toISOString(),
  };
}

/** Minimal valid DashboardResponse. */
function makeDashboardResponse(products: ProductListItem[], page = 1, limit = 20): DashboardResponse {
  return {
    products,
    total: products.length,
    page,
    limit,
    onboarding_completeness: {
      base_complete_count: 3,
      base_total_count: 10,
      extension_complete_count: 0,
      extension_total_count: 0,
      onboarding_complete: false,
    },
  };
}

// ---------------------------------------------------------------------------
// Test suite
// ---------------------------------------------------------------------------

describe('DashboardApiService', () => {
  let svc: DashboardApiService;
  let controller: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        DashboardApiService,
        provideHttpClient(withFetch()),
        provideHttpClientTesting(),
      ],
    });
    svc = TestBed.inject(DashboardApiService);
    controller = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    controller.verify();
    vi.restoreAllMocks();
  });

  // ─── loadProducts ──────────────────────────────────────────────────────────

  describe('loadProducts()', () => {

    it('sends GET /api/v1/products with page and limit query params', () => {
      svc.loadProducts({ page: 1, limit: 20 }).subscribe();

      const req = controller.expectOne(r =>
        r.method === 'GET' &&
        r.url === '/api/v1/products' &&
        r.params.get('page') === '1' &&
        r.params.get('limit') === '20',
      );
      expect(req).toBeTruthy();
      req.flush(makeDashboardResponse([makeItem(1), makeItem(2)]));
    });

    it('returns DashboardResponse with products array and onboarding_completeness', () => {
      const items = [makeItem(1), makeItem(2), makeItem(3)];
      const serverResp = makeDashboardResponse(items, 1, 20);

      let result: DashboardResponse | undefined;
      svc.loadProducts({ page: 1, limit: 20 }).subscribe(r => { result = r; });

      controller.expectOne(r => r.method === 'GET' && r.url === '/api/v1/products')
        .flush(serverResp);

      expect(result).toBeDefined();
      expect(result!.products).toHaveLength(3);
      expect(result!.products[0].product_id).toBe('prod-1');
      expect(result!.products[0].category_id).toBe('cat-1');
      expect(result!.total).toBe(3);
      expect(result!.limit).toBe(20);
      expect(result!.onboarding_completeness.base_total_count).toBe(10);
    });

    it('uses page=2 when page param is 2', () => {
      svc.loadProducts({ page: 2, limit: 20 }).subscribe();

      const req = controller.expectOne(r =>
        r.url === '/api/v1/products' && r.params.get('page') === '2',
      );
      expect(req.request.params.get('page')).toBe('2');
      req.flush(makeDashboardResponse([]));
    });

    it('defaults limit to 20 when not provided', () => {
      svc.loadProducts({ page: 1 }).subscribe();

      const req = controller.expectOne(r =>
        r.url === '/api/v1/products' && r.params.get('limit') === '20',
      );
      expect(req.request.params.get('limit')).toBe('20');
      req.flush(makeDashboardResponse([]));
    });

    it('does NOT send an Authorization header (jwtInterceptor owns it)', () => {
      svc.loadProducts({ page: 1, limit: 20 }).subscribe();

      const req = controller.expectOne(r => r.url === '/api/v1/products');
      expect(req.request.headers.has('Authorization')).toBe(false);
      req.flush(makeDashboardResponse([]));
    });

    it('does NOT send status_filter or search to the server (A3 — client-only)', () => {
      svc.loadProducts({ page: 1, limit: 20 }).subscribe();

      const req = controller.expectOne(r => r.url === '/api/v1/products');
      expect(req.request.params.get('status_filter')).toBeNull();
      expect(req.request.params.get('search')).toBeNull();
      req.flush(makeDashboardResponse([]));
    });

    // ─── Error matrix ────────────────────────────────────────────────────────

    it('401 — returns empty DashboardResponse fallback (refreshInterceptor handles retry)', () => {
      let result: DashboardResponse | undefined;
      svc.loadProducts({ page: 1, limit: 20 }).subscribe(r => { result = r; });

      controller.expectOne(r => r.url === '/api/v1/products')
        .flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

      expect(result).toBeDefined();
      expect(result!.products).toHaveLength(0);
      expect(result!.total).toBe(0);
      expect(result!.page).toBe(1);
      expect(result!.limit).toBe(20);
    });

    it('402 — returns empty DashboardResponse fallback', () => {
      let result: DashboardResponse | undefined;
      svc.loadProducts({ page: 1, limit: 20 }).subscribe(r => { result = r; });

      controller.expectOne(r => r.url === '/api/v1/products')
        .flush({ detail: 'Plan limit' }, { status: 402, statusText: 'Payment Required' });

      expect(result!.products).toHaveLength(0);
    });

    it('400 — returns empty DashboardResponse fallback', () => {
      let result: DashboardResponse | undefined;
      svc.loadProducts({ page: 1, limit: 20 }).subscribe(r => { result = r; });

      controller.expectOne(r => r.url === '/api/v1/products')
        .flush({ detail: 'Bad request' }, { status: 400, statusText: 'Bad Request' });

      expect(result!.products).toHaveLength(0);
    });

    it('404 — returns empty DashboardResponse fallback defensively', () => {
      let result: DashboardResponse | undefined;
      svc.loadProducts({ page: 1, limit: 20 }).subscribe(r => { result = r; });

      controller.expectOne(r => r.url === '/api/v1/products')
        .flush({ detail: 'Not found' }, { status: 404, statusText: 'Not Found' });

      expect(result!.products).toHaveLength(0);
    });

    it('500 — returns empty DashboardResponse fallback (component renders error banner)', () => {
      let result: DashboardResponse | undefined;
      svc.loadProducts({ page: 1, limit: 20 }).subscribe(r => { result = r; });

      controller.expectOne(r => r.url === '/api/v1/products')
        .flush({ detail: 'Internal error' }, { status: 500, statusText: 'Internal Server Error' });

      expect(result!.products).toHaveLength(0);
      expect(result!.total).toBe(0);
    });

    it('never throws to the subscriber — error handler absorbs and returns fallback', () => {
      let errorCalled = false;
      let completedCalled = false;
      svc.loadProducts({ page: 1, limit: 20 }).subscribe({
        next: () => { /* no-op */ },
        error: () => { errorCalled = true; },
        complete: () => { completedCalled = true; },
      });

      controller.expectOne(r => r.url === '/api/v1/products')
        .flush({ detail: 'Server error' }, { status: 503, statusText: 'Service Unavailable' });

      expect(errorCalled).toBe(false);
      expect(completedCalled).toBe(true);
    });

  });

  // ─── deleteProduct ─────────────────────────────────────────────────────────

  describe('deleteProduct()', () => {

    it('sends DELETE /api/v1/products/{id} with the correct URL', () => {
      const id = 'abc-123-uuid';
      svc.deleteProduct(id).subscribe();

      const req = controller.expectOne(r =>
        r.method === 'DELETE' && r.url === `/api/v1/products/${id}`,
      );
      expect(req).toBeTruthy();
      req.flush(null, { status: 204, statusText: 'No Content' });
    });

    it('does NOT send an Authorization header (jwtInterceptor owns it)', () => {
      svc.deleteProduct('some-id').subscribe();

      const req = controller.expectOne(r =>
        r.method === 'DELETE' && r.url === '/api/v1/products/some-id',
      );
      expect(req.request.headers.has('Authorization')).toBe(false);
      req.flush(null, { status: 204, statusText: 'No Content' });
    });

    it('204 success — completes without error', () => {
      let completed = false;
      let errorCalled = false;
      svc.deleteProduct('prod-uuid').subscribe({
        complete: () => { completed = true; },
        error: () => { errorCalled = true; },
      });

      controller.expectOne(r => r.method === 'DELETE')
        .flush(null, { status: 204, statusText: 'No Content' });

      expect(errorCalled).toBe(false);
      expect(completed).toBe(true);
    });

    it('404 — treated as success-equivalent (row already gone)', () => {
      let nextCalled = false;
      let errorCalled = false;
      svc.deleteProduct('already-gone').subscribe({
        next: () => { nextCalled = true; },
        error: () => { errorCalled = true; },
      });

      controller.expectOne(r => r.method === 'DELETE')
        .flush({ detail: 'Not found' }, { status: 404, statusText: 'Not Found' });

      expect(errorCalled).toBe(false);
      // 404 emits void (of(undefined)) — subscriber may receive a next emission then complete
    });

    it('401 terminal — returns EMPTY (no next, no error)', () => {
      let nextCalled = false;
      let errorCalled = false;
      svc.deleteProduct('auth-fail').subscribe({
        next: () => { nextCalled = true; },
        error: () => { errorCalled = true; },
      });

      controller.expectOne(r => r.method === 'DELETE')
        .flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

      expect(nextCalled).toBe(false);
      expect(errorCalled).toBe(false);
    });

    it('500 — returns EMPTY (no next, no error)', () => {
      let nextCalled = false;
      let errorCalled = false;
      svc.deleteProduct('server-err').subscribe({
        next: () => { nextCalled = true; },
        error: () => { errorCalled = true; },
      });

      controller.expectOne(r => r.method === 'DELETE')
        .flush({ detail: 'Server error' }, { status: 500, statusText: 'Internal Server Error' });

      expect(nextCalled).toBe(false);
      expect(errorCalled).toBe(false);
    });

  });

  // ─── deriveStatusCounts ────────────────────────────────────────────────────

  describe('deriveStatusCounts()', () => {

    it('returns {draft, ready} — 2-value V1 wire shape (A2)', () => {
      const items: ProductListItem[] = [
        makeItem(1), // draft (odd)
        makeItem(2), // ready (even)
        makeItem(3), // draft
        makeItem(4), // ready
        makeItem(5), // draft
      ];
      const counts = svc.deriveStatusCounts(items);
      expect(counts.draft).toBe(3);
      expect(counts.ready).toBe(2);
      // no 'exported'/'live'/'deleted' keys on the return shape
      expect(Object.keys(counts).sort()).toEqual(['draft', 'ready']);
    });

    it('returns zeros for empty array', () => {
      const counts = svc.deriveStatusCounts([]);
      expect(counts.draft).toBe(0);
      expect(counts.ready).toBe(0);
    });

  });

});
