/**
 * category.service.spec.ts — Updated Wave 6 Wave A (wave6-auth-core)
 *
 * Tests CategoryService with Angular HttpTestingController.
 * Uses TestBed (service-only — no component, no PrimeNG dependency).
 *
 * Wave 6 Wave A changes from the previous version:
 *   1. authHeaders() REMOVED — jwtInterceptor handles Bearer globally.
 *      Tests now assert NO manual Authorization header from the service itself.
 *      (The interceptor is NOT registered in the test's provideHttpClient — that is
 *       intentional: we test the SERVICE contract, not the interceptor. A separate
 *       jwt.interceptor.spec.ts tests the header-attachment behaviour.)
 *   2. selectCategory() URL re-pointed: /api/v1/catalogs → /api/v1/products (DISCREPANCY-1 fix).
 *
 * Error matrix coverage:
 *  - happy path: 200 with SuggestResponse → emits the response
 *  - no manual Authorization header (global interceptor handles it — service must not add one)
 *  - 402: plan-guard quota → emits { suggestions: [], fallback_offered: true }
 *  - 404: feature flag disabled → emits { suggestions: [], fallback_offered: true }
 *  - 401: auth expired → AuthService.logout() called + EMPTY (no emission)
 *  - 400: invalid q → EMPTY (no emission)
 *  - 500: server error → { suggestions: [], fallback_offered: true }
 *  - 503: server unavailable → { suggestions: [], fallback_offered: true }
 *  - selectCategory: POST /api/v1/products (DISCREPANCY-1) with { category_id }
 *  - selectCategory: emits { id } on success
 *  - selectCategory: navigates to /catalogs/:id/edit on success
 *  - selectCategory: EMPTY on error (no re-throw)
 *  - browseRedirect: router.navigate(['/categories/browse'])
 *
 * tsconfig.spec.json has "types": ["vitest/globals"] — no explicit describe/it/expect imports needed.
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
import { CategoryService } from './category.service';
import type { SuggestResponse } from '../smart-picker.model';

// ── Typed mock for AuthService ────────────────────────────────────────────────

interface MockAuthService {
  getToken: () => string | null;
  logout: ReturnType<typeof vi.fn>;
}

// ── Fixture helpers ────────────────────────────────────────────────────────────

const MOCK_SUGGESTION = {
  category_id: 'cat-kurti-uuid',
  super_id: 'super-fashion-uuid',
  super_name: 'Fashion',
  path: 'Fashion > Women > Ethnic > Kurti',
  leaf_name: 'Kurti',
  confidence: 0.94,
  reasons: ['Top seller in Fashion Women'],
};

const MOCK_SUGGEST_RESPONSE: SuggestResponse = {
  suggestions: [MOCK_SUGGESTION],
  fallback_offered: false,
};

const FALLBACK_RESPONSE: SuggestResponse = {
  suggestions: [],
  fallback_offered: true,
};

// ── Test setup ────────────────────────────────────────────────────────────────

function setup(tokenValue: string | null = 'mock-jwt-token') {
  const mockAuth: MockAuthService = {
    getToken: () => tokenValue,
    logout: vi.fn(),
  };

  TestBed.configureTestingModule({
    providers: [
      CategoryService,
      provideHttpClient(withFetch()),
      provideHttpClientTesting(),
      provideRouter([]),
      { provide: AuthService, useValue: mockAuth },
    ],
  });

  const service    = TestBed.inject(CategoryService);
  const controller = TestBed.inject(HttpTestingController);
  const router     = TestBed.inject(Router);

  return { service, controller, auth: mockAuth, router };
}

// ── CategoryService.suggest() — happy path ────────────────────────────────────

describe('CategoryService.suggest() — happy path', () => {
  afterEach(() => {
    TestBed.inject(HttpTestingController).verify();
  });

  it('GETs /api/v1/categories/suggest with { q: description }', () => {
    const { service, controller } = setup();
    const description = 'Blue cotton kurti with mirror work for women';

    service.suggest(description).subscribe();

    const req = controller.expectOne(
      (r) => r.url === '/api/v1/categories/suggest' && r.params.get('q') === description,
    );
    expect(req.request.method).toBe('GET');
    req.flush(MOCK_SUGGEST_RESPONSE);
  });

  it('emits SuggestResponse on 200', () => {
    const { service, controller } = setup();
    const emitted: SuggestResponse[] = [];

    service.suggest('Blue kurti cotton women XL').subscribe((r) => emitted.push(r));

    const req = controller.expectOne((r) => r.url === '/api/v1/categories/suggest');
    req.flush(MOCK_SUGGEST_RESPONSE);

    expect(emitted).toHaveLength(1);
    expect(emitted[0].suggestions).toHaveLength(1);
    expect(emitted[0].fallback_offered).toBe(false);
    expect(emitted[0].suggestions[0].category_id).toBe('cat-kurti-uuid');
  });

  it('does NOT manually set Authorization header — jwtInterceptor handles Bearer globally', () => {
    // Wave 6 Wave A: authHeaders() removed; this test confirms the service
    // does not attach any Authorization header manually. The global jwtInterceptor
    // (registered in app.config + all remote main.ts) attaches Bearer at the
    // interceptor level, not inside service methods. The interceptor is intentionally
    // NOT in this TestBed — we're testing the service contract, not the interceptor.
    const { service, controller } = setup('some-token');

    service.suggest('kurti').subscribe();

    const req = controller.expectOne((r) => r.url === '/api/v1/categories/suggest');
    // Service itself sets no Authorization header (interceptor's responsibility)
    expect(req.request.headers.get('Authorization')).toBeNull();
    req.flush(MOCK_SUGGEST_RESPONSE);
  });
});

// ── CategoryService.suggest() — error matrix ──────────────────────────────────

describe('CategoryService.suggest() — error matrix', () => {
  afterEach(() => {
    TestBed.inject(HttpTestingController).verify();
  });

  it('402 → emits fallback shape { suggestions: [], fallback_offered: true }', () => {
    const { service, controller } = setup();
    const emitted: SuggestResponse[] = [];
    let completed = false;

    service.suggest('kurti').subscribe({
      next: (r) => emitted.push(r),
      complete: () => { completed = true; },
    });

    const req = controller.expectOne((r) => r.url === '/api/v1/categories/suggest');
    req.flush({ detail: 'Quota exceeded' }, { status: 402, statusText: 'Payment Required' });

    expect(emitted).toHaveLength(1);
    expect(emitted[0]).toEqual(FALLBACK_RESPONSE);
    expect(completed).toBe(true);
  });

  it('404 → emits fallback shape { suggestions: [], fallback_offered: true } (feature flag off)', () => {
    const { service, controller } = setup();
    const emitted: SuggestResponse[] = [];
    let completed = false;

    service.suggest('kurti').subscribe({
      next: (r) => emitted.push(r),
      complete: () => { completed = true; },
    });

    const req = controller.expectOne((r) => r.url === '/api/v1/categories/suggest');
    req.flush({ detail: 'Smart Picker is disabled' }, { status: 404, statusText: 'Not Found' });

    expect(emitted).toHaveLength(1);
    expect(emitted[0]).toEqual(FALLBACK_RESPONSE);
    expect(completed).toBe(true);
  });

  it('401 → AuthService.logout() called and EMPTY (no emission, stream completes)', () => {
    const { service, controller, auth } = setup();
    const emitted: SuggestResponse[] = [];
    let completed = false;

    service.suggest('kurti').subscribe({
      next: (r) => emitted.push(r),
      complete: () => { completed = true; },
    });

    const req = controller.expectOne((r) => r.url === '/api/v1/categories/suggest');
    req.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

    expect(auth.logout).toHaveBeenCalledOnce();
    expect(emitted).toHaveLength(0);
    expect(completed).toBe(true);
  });

  it('400 → EMPTY (no emission, stream completes)', () => {
    const { service, controller } = setup();
    const emitted: SuggestResponse[] = [];
    let completed = false;

    service.suggest('').subscribe({
      next: (r) => emitted.push(r),
      complete: () => { completed = true; },
    });

    const req = controller.expectOne((r) => r.url === '/api/v1/categories/suggest');
    req.flush(
      { detail: 'validation.suggest_q.too_short_or_long' },
      { status: 400, statusText: 'Bad Request' },
    );

    expect(emitted).toHaveLength(0);
    expect(completed).toBe(true);
  });

  it('500 → emits fallback shape { suggestions: [], fallback_offered: true }', () => {
    const { service, controller } = setup();
    const emitted: SuggestResponse[] = [];

    service.suggest('kurti').subscribe({
      next: (r) => emitted.push(r),
    });

    const req = controller.expectOne((r) => r.url === '/api/v1/categories/suggest');
    req.flush({ detail: 'Internal Server Error' }, { status: 500, statusText: 'Internal Server Error' });

    expect(emitted).toHaveLength(1);
    expect(emitted[0]).toEqual(FALLBACK_RESPONSE);
  });

  it('503 → emits fallback shape { suggestions: [], fallback_offered: true }', () => {
    const { service, controller } = setup();
    const emitted: SuggestResponse[] = [];

    service.suggest('kurti').subscribe({
      next: (r) => emitted.push(r),
    });

    const req = controller.expectOne((r) => r.url === '/api/v1/categories/suggest');
    req.flush({ detail: 'Service Unavailable' }, { status: 503, statusText: 'Service Unavailable' });

    expect(emitted).toHaveLength(1);
    expect(emitted[0]).toEqual(FALLBACK_RESPONSE);
  });
});

// ── CategoryService.selectCategory() — DISCREPANCY-1 re-point ────────────────

describe('CategoryService.selectCategory() — DISCREPANCY-1: POST /api/v1/products', () => {
  afterEach(() => {
    TestBed.inject(HttpTestingController).verify();
  });

  it('POSTs to /api/v1/products with { category_id } (DISCREPANCY-1 fix)', () => {
    const { service, controller, router } = setup();
    vi.spyOn(router, 'navigate').mockResolvedValue(true);
    const categoryId = 'cat-kurti-uuid';

    service.selectCategory(categoryId).subscribe();

    // Must hit /api/v1/products (NOT /api/v1/catalogs — the old bug)
    const req = controller.expectOne('/api/v1/products');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ category_id: categoryId });
    req.flush({ id: 'product-123' });
  });

  it('emits { id } on success', () => {
    const { service, controller, router } = setup();
    vi.spyOn(router, 'navigate').mockResolvedValue(true);
    const emitted: Array<{ id: string }> = [];

    service.selectCategory('cat-uuid').subscribe((r) => emitted.push(r));

    const req = controller.expectOne('/api/v1/products');
    req.flush({ id: 'new-product-id' });

    expect(emitted).toHaveLength(1);
    expect(emitted[0].id).toBe('new-product-id');
  });

  it('navigates to /catalogs/:id/edit on success (id is product id)', () => {
    const { service, controller, router } = setup();
    const navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);

    service.selectCategory('cat-kurti').subscribe();

    const req = controller.expectOne('/api/v1/products');
    req.flush({ id: 'product-xyz' });

    expect(navigateSpy).toHaveBeenCalledWith(['/catalogs', 'product-xyz', 'edit']);
  });

  it('returns EMPTY on 4xx/5xx error (no re-throw)', () => {
    const { service, controller } = setup();
    const emitted: Array<{ id: string }> = [];
    let completed = false;

    service.selectCategory('cat-uuid').subscribe({
      next: (r) => emitted.push(r),
      complete: () => { completed = true; },
    });

    const req = controller.expectOne('/api/v1/products');
    req.flush({ detail: 'Not Found' }, { status: 404, statusText: 'Not Found' });

    expect(emitted).toHaveLength(0);
    expect(completed).toBe(true);
  });
});

// ── CategoryService.browseRedirect() ─────────────────────────────────────────

describe('CategoryService.browseRedirect()', () => {
  it('navigates to /categories/browse', () => {
    const { service, router } = setup();
    const navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);

    service.browseRedirect();

    expect(navigateSpy).toHaveBeenCalledWith(['/categories/browse']);
  });
});
