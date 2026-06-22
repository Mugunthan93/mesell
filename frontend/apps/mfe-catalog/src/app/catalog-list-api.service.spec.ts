/**
 * catalog-list-api.service.spec.ts — QA Wave 3 W3-FE-2
 *
 * Tests CatalogListApiService with Angular HttpTestingController.
 * Service-only TestBed — no component, no PrimeNG dependencies.
 *
 * Coverage:
 *  W3-FE-2a — listProducts() issues GET /api/v1/products with correct page + limit params
 *  W3-FE-2b — listProducts() maps DashboardWireResponse → CatalogListResponse via adaptDashboardResponse
 *  W3-FE-2c — 401 → graceful emptyListResponse (no re-throw)
 *  W3-FE-2d — 404 → graceful emptyListResponse (no re-throw)
 *  W3-FE-2e — 500 → re-throws (component renders error state)
 *  W3-FE-2f — null name on wire → 'Untitled product' fallback
 *  W3-FE-2g — adaptDashboardResponse maps product_id → id and updated_at → updatedAt
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

import { ApiClient } from '@mesell/core';
import { CatalogListApiService } from './catalog-list-api.service';
import type {
  DashboardWireResponse,
  CatalogListResponse,
} from './catalog-list.model';
import {
  adaptDashboardResponse,
  emptyListResponse,
} from './catalog-list.model';

// ── Wire fixture ──────────────────────────────────────────────────────────────

const MOCK_WIRE: DashboardWireResponse = {
  products: [
    {
      product_id: 'uuid-001',
      name: 'Blue Cotton Kurti',
      category_id: 'cat-uuid-kurti',
      status: 'ready',
      created_at: '2026-06-01T10:00:00Z',
      updated_at: '2026-06-17T14:30:00Z',
    },
    {
      product_id: 'uuid-002',
      name: null,           // null name → 'Untitled product'
      category_id: 'cat-uuid-saree',
      status: 'draft',
      created_at: '2026-06-10T09:00:00Z',
      updated_at: '2026-06-16T12:00:00Z',
    },
  ],
  total: 2,
  page: 1,
  limit: 20,
  onboarding_completeness: { step: 'categories' },  // intentionally dropped by adapter
};

// ── Setup helper ──────────────────────────────────────────────────────────────

function setup() {
  TestBed.configureTestingModule({
    providers: [
      CatalogListApiService,
      ApiClient,
      provideHttpClient(withFetch()),
      provideHttpClientTesting(),
    ],
  });

  const service    = TestBed.inject(CatalogListApiService);
  const controller = TestBed.inject(HttpTestingController);

  return { service, controller };
}

// ── W3-FE-2a — GET method + query params ─────────────────────────────────────

describe('CatalogListApiService.listProducts() — W3-FE-2: GET contract', () => {
  afterEach(() => {
    TestBed.inject(HttpTestingController).verify();
  });

  it('should issue GET /api/v1/products with page and limit params when called with page=1', () => {
    const { service, controller } = setup();

    service.listProducts({ page: 1, limit: 20 }).subscribe();

    const req = controller.expectOne(r =>
      r.url === '/api/v1/products' && r.method === 'GET'
    );
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('page')).toBe('1');
    expect(req.request.params.get('limit')).toBe('20');
    req.flush(MOCK_WIRE);
  });

  it('should default limit to 20 when not specified', () => {
    const { service, controller } = setup();

    service.listProducts({ page: 1 }).subscribe();

    const req = controller.expectOne(r => r.url === '/api/v1/products');
    expect(req.request.params.get('limit')).toBe('20');
    req.flush(MOCK_WIRE);
  });
});

// ── W3-FE-2b — happy-path response mapping ────────────────────────────────────

describe('CatalogListApiService.listProducts() — W3-FE-2: happy-path mapping', () => {
  afterEach(() => {
    TestBed.inject(HttpTestingController).verify();
  });

  it('should map DashboardWireResponse to CatalogListResponse with id from product_id', () => {
    const { service, controller } = setup();
    const emitted: CatalogListResponse[] = [];

    service.listProducts({ page: 1, limit: 20 }).subscribe(r => emitted.push(r));

    const req = controller.expectOne(r => r.url === '/api/v1/products');
    req.flush(MOCK_WIRE);

    expect(emitted).toHaveLength(1);
    const response = emitted[0];
    expect(response.items).toHaveLength(2);
    // product_id → id mapping (W3-FE-2g)
    expect(response.items[0].id).toBe('uuid-001');
    expect(response.items[1].id).toBe('uuid-002');
  });

  it('should map updated_at (snake_case) to updatedAt (camelCase) when mapping wire response', () => {
    const { service, controller } = setup();
    const emitted: CatalogListResponse[] = [];

    service.listProducts({ page: 1 }).subscribe(r => emitted.push(r));

    const req = controller.expectOne(r => r.url === '/api/v1/products');
    req.flush(MOCK_WIRE);

    expect(emitted[0].items[0].updatedAt).toBe('2026-06-17T14:30:00Z');
  });

  it('should replace null product name with "Untitled product" when name is null on wire (W3-FE-2f)', () => {
    const { service, controller } = setup();
    const emitted: CatalogListResponse[] = [];

    service.listProducts({ page: 1 }).subscribe(r => emitted.push(r));

    const req = controller.expectOne(r => r.url === '/api/v1/products');
    req.flush(MOCK_WIRE);

    // Second item has null name on wire
    expect(emitted[0].items[1].name).toBe('Untitled product');
  });

  it('should preserve total, page, and limit from the wire envelope when mapping', () => {
    const { service, controller } = setup();
    const emitted: CatalogListResponse[] = [];

    service.listProducts({ page: 1, limit: 20 }).subscribe(r => emitted.push(r));

    const req = controller.expectOne(r => r.url === '/api/v1/products');
    req.flush(MOCK_WIRE);

    expect(emitted[0].total).toBe(2);
    expect(emitted[0].page).toBe(1);
    expect(emitted[0].limit).toBe(20);
  });
});

// ── W3-FE-2c/d — 401 + 404 graceful fallback ─────────────────────────────────

describe('CatalogListApiService.listProducts() — W3-FE-2: error graceful fallback', () => {
  afterEach(() => {
    TestBed.inject(HttpTestingController).verify();
  });

  it('should emit emptyListResponse on 401 without re-throwing when auth token is missing', () => {
    const { service, controller } = setup();
    const emitted: CatalogListResponse[] = [];
    const errors: unknown[] = [];
    let completed = false;

    service.listProducts({ page: 1, limit: 20 }).subscribe({
      next: r => emitted.push(r),
      error: e => errors.push(e),
      complete: () => { completed = true; },
    });

    const req = controller.expectOne(r => r.url === '/api/v1/products');
    req.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

    expect(emitted).toHaveLength(1);
    expect(emitted[0].items).toHaveLength(0);
    expect(emitted[0].total).toBe(0);
    expect(errors).toHaveLength(0);
    expect(completed).toBe(true);
  });

  it('should emit emptyListResponse on 404 without re-throwing when endpoint is not found', () => {
    const { service, controller } = setup();
    const emitted: CatalogListResponse[] = [];
    const errors: unknown[] = [];

    service.listProducts({ page: 1 }).subscribe({
      next: r => emitted.push(r),
      error: e => errors.push(e),
    });

    const req = controller.expectOne(r => r.url === '/api/v1/products');
    req.flush({ detail: 'Not Found' }, { status: 404, statusText: 'Not Found' });

    expect(emitted).toHaveLength(1);
    expect(emitted[0].items).toHaveLength(0);
    expect(errors).toHaveLength(0);
  });
});

// ── W3-FE-2e — 5xx re-throws ─────────────────────────────────────────────────

describe('CatalogListApiService.listProducts() — W3-FE-2: 5xx re-throw', () => {
  afterEach(() => {
    TestBed.inject(HttpTestingController).verify();
  });

  it('should re-throw on 500 so the component can render an error state', () => {
    const { service, controller } = setup();
    const errors: unknown[] = [];
    const emitted: CatalogListResponse[] = [];

    service.listProducts({ page: 1 }).subscribe({
      next: r => emitted.push(r),
      error: e => errors.push(e),
    });

    const req = controller.expectOne(r => r.url === '/api/v1/products');
    req.flush({ detail: 'Server Error' }, { status: 500, statusText: 'Internal Server Error' });

    expect(errors).toHaveLength(1);
    expect(emitted).toHaveLength(0);
  });
});

// ── Pure-function adapter tests (model layer) ──────────────────────────────────

describe('adaptDashboardResponse — pure-function unit (W3-FE-2: model adapter)', () => {
  it('should map an empty products array to empty items when no products exist', () => {
    const wire: DashboardWireResponse = {
      products: [],
      total: 0,
      page: 1,
      limit: 20,
      onboarding_completeness: null,
    };
    const result = adaptDashboardResponse(wire);
    expect(result.items).toHaveLength(0);
    expect(result.total).toBe(0);
  });

  it('should drop the onboarding_completeness field from the adapted response', () => {
    const result = adaptDashboardResponse(MOCK_WIRE);
    // onboarding_completeness is NOT in CatalogListResponse
    expect((result as unknown as { onboarding_completeness?: unknown }).onboarding_completeness).toBeUndefined();
  });
});

describe('emptyListResponse — pure-function unit', () => {
  it('should return zero-value response with given page and limit', () => {
    const result = emptyListResponse(1, 20);
    expect(result.items).toHaveLength(0);
    expect(result.total).toBe(0);
    expect(result.page).toBe(1);
    expect(result.limit).toBe(20);
  });
});
