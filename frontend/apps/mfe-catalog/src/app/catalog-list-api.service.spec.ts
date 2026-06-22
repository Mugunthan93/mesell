/**
 * catalog-list-api.service.spec.ts — catalog-list-delete feature (service layer)
 *
 * Contract-conformance tests for CatalogListApiService.
 * Uses HttpTestingController to intercept requests and assert:
 *   — correct HTTP verb + URL for each method
 *   — response mapping (listProducts adapter, deleteProduct void completion)
 *   — error matrix per FEATURE_PLAN.md §2
 *
 * Error matrix:
 *   listProducts: 200 success | 401→emptyListResponse | 404→emptyListResponse | 5xx→rethrow
 *   deleteProduct: 204 success→void | 200 success→void | 401→EMPTY | 404→EMPTY | 5xx→rethrow
 *
 * Auth: jwtInterceptor is NOT in TestBed — interceptor-free test environment.
 *   Assert no Authorization header from this service (interceptor owns it in prod).
 *
 * Harness pattern: mirrors catalog-form-api.service.spec.ts
 *   — provideHttpClient(withFetch()) + provideHttpClientTesting()
 *   — ApiClient provided explicitly (not a root singleton in the test module)
 *   — controller.verify() in afterEach
 *   — vitest describe/it/expect (no fakeAsync — no timer-based logic in this service)
 */

import { TestBed } from '@angular/core/testing';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { provideHttpClient, withFetch } from '@angular/common/http';
import { describe, it, expect, beforeEach, afterEach } from 'vitest';

import { ApiClient } from '@mesell/core';
import { CatalogListApiService } from './catalog-list-api.service';
import type { CatalogListResponse } from './catalog-list.model';

// ── Fixtures ─────────────────────────────────────────────────────────────────

const PRODUCT_ID = 'prod-uuid-001';
const PAGE = 1;
const LIMIT = 20;

/** Minimal wire response that adaptDashboardResponse can map. */
const DASHBOARD_WIRE = {
  products: [
    {
      product_id: PRODUCT_ID,
      name: 'Blue Kurti',
      category_id: 'cat-uuid-001',
      status: 'draft' as const,
      created_at: '2026-06-01T00:00:00Z',
      updated_at: '2026-06-02T00:00:00Z',
    },
    {
      product_id: 'prod-uuid-002',
      name: null,
      category_id: 'cat-uuid-002',
      status: 'ready' as const,
      created_at: '2026-06-03T00:00:00Z',
      updated_at: '2026-06-04T00:00:00Z',
    },
  ],
  total: 2,
  page: PAGE,
  limit: LIMIT,
  onboarding_completeness: { step: 3 }, // intentionally dropped by adapter
};

// ── Test harness ──────────────────────────────────────────────────────────────

describe('CatalogListApiService', () => {
  let svc: CatalogListApiService;
  let controller: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withFetch()),
        provideHttpClientTesting(),
        ApiClient,
        CatalogListApiService,
      ],
    });
    svc        = TestBed.inject(CatalogListApiService);
    controller = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    controller.verify();
  });

  // ── listProducts ───────────────────────────────────────────────────────────

  describe('listProducts()', () => {
    it('GET /api/v1/products — correct URL and method', () => {
      svc.listProducts({ page: PAGE, limit: LIMIT }).subscribe();
      const req = controller.expectOne(r =>
        r.url === '/api/v1/products' &&
        r.params.get('page') === String(PAGE) &&
        r.params.get('limit') === String(LIMIT),
      );
      expect(req.request.method).toBe('GET');
      req.flush(DASHBOARD_WIRE);
    });

    it('uses default limit=20 when limit is omitted', () => {
      svc.listProducts({ page: 1 }).subscribe();
      const req = controller.expectOne(r =>
        r.url === '/api/v1/products' && r.params.get('limit') === '20',
      );
      expect(req.request.params.get('limit')).toBe('20');
      req.flush(DASHBOARD_WIRE);
    });

    it('does NOT send Authorization header (jwtInterceptor owns it)', () => {
      svc.listProducts({ page: PAGE }).subscribe();
      const req = controller.expectOne(r => r.url === '/api/v1/products');
      expect(req.request.headers.has('Authorization')).toBe(false);
      req.flush(DASHBOARD_WIRE);
    });

    it('200 success → adapts DashboardWireResponse → CatalogListResponse', () => {
      let result: CatalogListResponse | undefined;
      svc.listProducts({ page: PAGE, limit: LIMIT }).subscribe(r => (result = r));
      controller.expectOne(r => r.url === '/api/v1/products').flush(DASHBOARD_WIRE);

      expect(result).toBeDefined();
      expect(result!.items).toHaveLength(2);
      expect(result!.total).toBe(2);
      expect(result!.page).toBe(PAGE);
      expect(result!.limit).toBe(LIMIT);
    });

    it('adapter maps product_id → id and null name → "Untitled product"', () => {
      let result: CatalogListResponse | undefined;
      svc.listProducts({ page: PAGE, limit: LIMIT }).subscribe(r => (result = r));
      controller.expectOne(r => r.url === '/api/v1/products').flush(DASHBOARD_WIRE);

      const [first, second] = result!.items;
      expect(first.id).toBe(PRODUCT_ID);
      expect(first.name).toBe('Blue Kurti');
      expect(first.status).toBe('draft');
      expect(second.id).toBe('prod-uuid-002');
      expect(second.name).toBe('Untitled product'); // null name fallback
      expect(second.status).toBe('ready');
    });

    it('adapter drops onboarding_completeness (not in CatalogListItem)', () => {
      let result: CatalogListResponse | undefined;
      svc.listProducts({ page: PAGE, limit: LIMIT }).subscribe(r => (result = r));
      controller.expectOne(r => r.url === '/api/v1/products').flush(DASHBOARD_WIRE);

      // None of the items should carry onboarding_completeness
      result!.items.forEach(item => {
        expect((item as unknown as Record<string, unknown>)['onboarding_completeness']).toBeUndefined();
      });
    });

    it('401 → emptyListResponse (graceful — auth expired, interceptor already retried)', () => {
      let result: CatalogListResponse | undefined;
      svc.listProducts({ page: PAGE, limit: LIMIT }).subscribe(r => (result = r));
      controller
        .expectOne(r => r.url === '/api/v1/products')
        .flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

      expect(result).toBeDefined();
      expect(result!.items).toHaveLength(0);
      expect(result!.total).toBe(0);
      expect(result!.page).toBe(PAGE);
      expect(result!.limit).toBe(LIMIT);
    });

    it('404 → emptyListResponse (guard against unexpected 404)', () => {
      let result: CatalogListResponse | undefined;
      svc.listProducts({ page: PAGE, limit: LIMIT }).subscribe(r => (result = r));
      controller
        .expectOne(r => r.url === '/api/v1/products')
        .flush({ detail: 'Not found' }, { status: 404, statusText: 'Not Found' });

      expect(result!.items).toHaveLength(0);
    });

    it('500 → rethrow (component renders retry button)', () => {
      let errorCalled = false;
      svc.listProducts({ page: PAGE, limit: LIMIT }).subscribe({
        next: () => undefined,
        error: () => (errorCalled = true),
      });
      controller
        .expectOne(r => r.url === '/api/v1/products')
        .flush({ detail: 'Server error' }, { status: 500, statusText: 'Internal Server Error' });

      expect(errorCalled).toBe(true);
    });
  });

  // ── deleteProduct ──────────────────────────────────────────────────────────

  describe('deleteProduct()', () => {
    it('DELETE /api/v1/products/{id} — correct URL and method', () => {
      svc.deleteProduct(PRODUCT_ID).subscribe();
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}`);
      expect(req.request.method).toBe('DELETE');
      req.flush(null, { status: 204, statusText: 'No Content' });
    });

    it('does NOT send Authorization header (jwtInterceptor owns it)', () => {
      svc.deleteProduct(PRODUCT_ID).subscribe();
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}`);
      expect(req.request.headers.has('Authorization')).toBe(false);
      req.flush(null, { status: 204, statusText: 'No Content' });
    });

    it('204 No Content → observable completes (next called once with void)', () => {
      let nextCalled = false;
      let completeCalled = false;
      svc.deleteProduct(PRODUCT_ID).subscribe({
        next: () => (nextCalled = true),
        complete: () => (completeCalled = true),
      });
      controller
        .expectOne(`/api/v1/products/${PRODUCT_ID}`)
        .flush(null, { status: 204, statusText: 'No Content' });

      expect(completeCalled).toBe(true);
    });

    it('200 OK → observable completes (some backends return 200 not 204)', () => {
      let completeCalled = false;
      svc.deleteProduct(PRODUCT_ID).subscribe({
        complete: () => (completeCalled = true),
      });
      controller
        .expectOne(`/api/v1/products/${PRODUCT_ID}`)
        .flush({}, { status: 200, statusText: 'OK' });

      expect(completeCalled).toBe(true);
    });

    it('401 → EMPTY (silent completion — refreshInterceptor owns auth cascade)', () => {
      let nextCalled = false;
      let errorCalled = false;
      let completeCalled = false;
      svc.deleteProduct(PRODUCT_ID).subscribe({
        next: () => (nextCalled = true),
        error: () => (errorCalled = true),
        complete: () => (completeCalled = true),
      });
      controller
        .expectOne(`/api/v1/products/${PRODUCT_ID}`)
        .flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

      expect(nextCalled).toBe(false);
      expect(errorCalled).toBe(false);
      expect(completeCalled).toBe(true); // EMPTY completes without error
    });

    it('404 → EMPTY (product already gone; treat-as-success, info-leak-safe)', () => {
      let nextCalled = false;
      let errorCalled = false;
      let completeCalled = false;
      svc.deleteProduct(PRODUCT_ID).subscribe({
        next: () => (nextCalled = true),
        error: () => (errorCalled = true),
        complete: () => (completeCalled = true),
      });
      controller
        .expectOne(`/api/v1/products/${PRODUCT_ID}`)
        .flush({ detail: 'Not found' }, { status: 404, statusText: 'Not Found' });

      expect(nextCalled).toBe(false);
      expect(errorCalled).toBe(false);
      expect(completeCalled).toBe(true); // EMPTY — caller removes the row
    });

    it('500 → rethrow (component surfaces non-blocking error toast and keeps row)', () => {
      let errorStatus = 0;
      svc.deleteProduct(PRODUCT_ID).subscribe({
        next: () => undefined,
        error: (e: { status: number }) => (errorStatus = e.status),
      });
      controller
        .expectOne(`/api/v1/products/${PRODUCT_ID}`)
        .flush({ detail: 'Server error' }, { status: 500, statusText: 'Internal Server Error' });

      expect(errorStatus).toBe(500);
    });

    it('503 → rethrow (server temporarily unavailable)', () => {
      let errorStatus = 0;
      svc.deleteProduct(PRODUCT_ID).subscribe({
        next: () => undefined,
        error: (e: { status: number }) => (errorStatus = e.status),
      });
      controller
        .expectOne(`/api/v1/products/${PRODUCT_ID}`)
        .flush({ detail: 'Service unavailable' }, { status: 503, statusText: 'Service Unavailable' });

      expect(errorStatus).toBe(503);
    });

    it('request body is null (DELETE has no body)', () => {
      svc.deleteProduct(PRODUCT_ID).subscribe();
      const req = controller.expectOne(`/api/v1/products/${PRODUCT_ID}`);
      expect(req.request.body).toBeNull();
      req.flush(null, { status: 204, statusText: 'No Content' });
    });

    it('uses the exact product id in the URL path', () => {
      const otherId = 'other-product-uuid-999';
      svc.deleteProduct(otherId).subscribe();
      // Must match the specific id, not a wildcard
      const req = controller.expectOne(`/api/v1/products/${otherId}`);
      expect(req.request.url).toBe(`/api/v1/products/${otherId}`);
      req.flush(null, { status: 204, statusText: 'No Content' });
    });
  });
});
