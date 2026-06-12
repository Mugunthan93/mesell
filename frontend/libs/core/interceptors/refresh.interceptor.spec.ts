/**
 * refresh.interceptor.spec.ts — Wave 6 Wave A (R-W6-11)
 *
 * Tests the 401→refresh→retry single-flight gate using HttpTestingController.
 * Pure-function / fake-http — NO live backend tunnel required.
 *
 * Spec cases (per R-W6-11):
 * (a) A 401 on a protected call triggers exactly ONE POST /api/v1/auth/refresh
 * (b) On refresh-200 the original request is retried with the new Bearer and succeeds
 * (c) On refresh-401 → AuthService.logout() called + Router.navigate('/login') + original errors
 * (d) Single-flight: TWO concurrent 401s fire ONE refresh; BOTH retry with the new token
 * (e) A 401 on /auth/refresh itself does NOT re-enter refresh (no loop)
 *
 * Additionally:
 * (f) /api/v1/auth/* requests are skipped (not retried on 401)
 * (g) Non-401 errors pass through untouched
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
import { provideRouter, Router } from '@angular/router';
import { signal, computed } from '@angular/core';
import { vi } from 'vitest';

import { AuthService, AuthUser } from '../services/auth.service';
import { AuthApiService } from '../services/auth-api.service';
import { refreshInterceptor } from './refresh.interceptor';

// ── Mock AuthService ───────────────────────────────────────────────────────────

function makeAuthMock() {
  const _user = signal<AuthUser | null>(null);
  const _token = signal<string | null>('initial-token');
  return {
    getToken:        () => _token(),
    currentUser:     computed(() => _user()),
    isAuthenticated: computed(() => _token() !== null),
    setSession: vi.fn((token: string, user: AuthUser) => {
      _token.set(token);
      _user.set(user);
    }),
    logout: vi.fn(() => {
      _token.set(null);
      _user.set(null);
    }),
    scheduleRefresh: vi.fn(),
  };
}

// ── Setup ─────────────────────────────────────────────────────────────────────

function setup() {
  const authMock = makeAuthMock();

  TestBed.configureTestingModule({
    providers: [
      provideHttpClient(withFetch(), withInterceptors([refreshInterceptor])),
      provideHttpClientTesting(),
      provideRouter([
        { path: 'login',     children: [] },
        { path: 'dashboard', children: [] },
      ]),
      { provide: AuthService, useValue: authMock },
    ],
  });

  const http       = TestBed.inject(HttpClient);
  const controller = TestBed.inject(HttpTestingController);
  const router     = TestBed.inject(Router);

  return { http, controller, authMock, router };
}

afterEach(() => {
  // Reset module-level state between tests (the _isRefreshing guard)
  // by verifying all pending requests are flushed.
  TestBed.inject(HttpTestingController).verify();
});

// ── (a) A 401 on a protected call triggers ONE POST /auth/refresh ──────────────

describe('refreshInterceptor (a): 401 triggers one POST /api/v1/auth/refresh', () => {
  it('fires exactly one refresh call on 401', () => {
    const { http, controller } = setup();
    let completed = false;

    http.get('/api/v1/products').subscribe({ complete: () => { completed = true; } });

    // Original request → 401
    const orig = controller.expectOne('/api/v1/products');
    orig.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

    // Interceptor fires ONE refresh
    const refresh = controller.expectOne('/api/v1/auth/refresh');
    expect(refresh.request.method).toBe('POST');
    refresh.flush({ access_token: 'new-token', expires_in: 900, token_type: 'bearer' });

    // Retry (second hit to /api/v1/products)
    const retry = controller.expectOne('/api/v1/products');
    retry.flush({ items: [] });

    expect(completed).toBe(true);
  });
});

// ── (b) On refresh-200 retry succeeds with new Bearer ──────────────────────────

describe('refreshInterceptor (b): refresh-200 → retry with new Bearer', () => {
  it('retries original request with the new access token', () => {
    const { http, controller } = setup();
    const emitted: unknown[] = [];

    http.get<{ items: string[] }>('/api/v1/products').subscribe((r) => emitted.push(r));

    const orig = controller.expectOne('/api/v1/products');
    orig.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

    const refresh = controller.expectOne('/api/v1/auth/refresh');
    refresh.flush({ access_token: 'refreshed-token', expires_in: 900, token_type: 'bearer' });

    const retry = controller.expectOne('/api/v1/products');
    // The retry should have the new Bearer (jwtInterceptor reads from AuthService.getToken
    // which is updated by setSession; since jwtInterceptor is NOT in this chain, we verify
    // via the Authorization header set directly by the refreshInterceptor's handle401 path
    // on the cloned request addBearer() call).
    expect(retry.request.headers.get('Authorization')).toBe('Bearer refreshed-token');
    retry.flush({ items: ['product-1'] });

    expect(emitted).toHaveLength(1);
    expect((emitted[0] as { items: string[] }).items).toContain('product-1');
  });
});

// ── (c) On refresh-401 → logout + navigate /login ─────────────────────────────

describe('refreshInterceptor (c): refresh-401 → logout + navigate /login', () => {
  it('calls logout and navigates to /login when refresh fails with 401', () => {
    const { http, controller, authMock, router } = setup();
    const navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    let errorCaught = false;

    http.get('/api/v1/products').subscribe({
      error: () => { errorCaught = true; },
    });

    const orig = controller.expectOne('/api/v1/products');
    orig.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

    const refresh = controller.expectOne('/api/v1/auth/refresh');
    refresh.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

    expect(authMock.logout).toHaveBeenCalledOnce();
    expect(navigateSpy).toHaveBeenCalledWith(['/login']);
    expect(errorCaught).toBe(true);
  });
});

// ── (d) Single-flight: TWO concurrent 401s fire ONE refresh ───────────────────

describe('refreshInterceptor (d): single-flight — two concurrent 401s fire ONE refresh', () => {
  it('queues second 401 request; both retry with the new token after ONE refresh', () => {
    const { http, controller } = setup();
    const results: string[] = [];

    http.get<{ id: string }>('/api/v1/products/a').subscribe((r) => results.push(r.id));
    http.get<{ id: string }>('/api/v1/products/b').subscribe((r) => results.push(r.id));

    // Both requests get 401
    const reqA = controller.expectOne('/api/v1/products/a');
    const reqB = controller.expectOne('/api/v1/products/b');
    reqA.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });
    reqB.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

    // Exactly ONE refresh call (single-flight gate)
    const refreshRequests = controller.match('/api/v1/auth/refresh');
    expect(refreshRequests).toHaveLength(1);
    refreshRequests[0].flush({ access_token: 'shared-token', expires_in: 900, token_type: 'bearer' });

    // Both original requests are retried
    const retryA = controller.expectOne('/api/v1/products/a');
    const retryB = controller.expectOne('/api/v1/products/b');
    expect(retryA.request.headers.get('Authorization')).toBe('Bearer shared-token');
    expect(retryB.request.headers.get('Authorization')).toBe('Bearer shared-token');
    retryA.flush({ id: 'result-a' });
    retryB.flush({ id: 'result-b' });

    expect(results).toContain('result-a');
    expect(results).toContain('result-b');
  });
});

// ── (e) 401 on /auth/refresh itself does NOT re-enter refresh (no loop) ────────

describe('refreshInterceptor (e): 401 on /auth/refresh does not cause refresh loop', () => {
  it('/api/v1/auth/* 401 is passed through without triggering refresh', () => {
    const { http, controller, authMock } = setup();
    let errorCaught = false;

    // Simulate a direct call to /auth/refresh that gets 401 (unusual but must not loop)
    http.post('/api/v1/auth/refresh', {}).subscribe({
      error: () => { errorCaught = true; },
    });

    const req = controller.expectOne('/api/v1/auth/refresh');
    req.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

    // The interceptor skips /api/v1/auth/* — no additional refresh calls
    controller.expectNone('/api/v1/auth/refresh');
    expect(authMock.logout).not.toHaveBeenCalled();
    expect(errorCaught).toBe(true);
  });
});

// ── (f) /api/v1/auth/* requests skipped entirely ──────────────────────────────

describe('refreshInterceptor (f): /api/v1/auth/* requests are not retried on 401', () => {
  it('passes 401 from /api/v1/auth/otp/verify through without refresh', () => {
    const { http, controller } = setup();
    let errorStatus = 0;

    http.post('/api/v1/auth/otp/verify', { phone: '+91123', otp: '999999' }).subscribe({
      error: (e) => { errorStatus = (e as { status: number }).status; },
    });

    const req = controller.expectOne('/api/v1/auth/otp/verify');
    req.flush({ detail: 'Invalid OTP' }, { status: 401, statusText: 'Unauthorized' });

    controller.expectNone('/api/v1/auth/refresh');
    expect(errorStatus).toBe(401);
  });
});

// ── (g) Non-401 errors pass through untouched ─────────────────────────────────

describe('refreshInterceptor (g): non-401 errors pass through without refresh', () => {
  it('500 error is rethrown without firing refresh', () => {
    const { http, controller } = setup();
    let errorStatus = 0;

    http.get('/api/v1/products').subscribe({
      error: (e) => { errorStatus = (e as { status: number }).status; },
    });

    const req = controller.expectOne('/api/v1/products');
    req.flush({ detail: 'Internal Server Error' }, { status: 500, statusText: 'Internal Server Error' });

    controller.expectNone('/api/v1/auth/refresh');
    expect(errorStatus).toBe(500);
  });

  it('404 error is rethrown without firing refresh', () => {
    const { http, controller } = setup();
    let errorStatus = 0;

    http.get('/api/v1/products/unknown').subscribe({
      error: (e) => { errorStatus = (e as { status: number }).status; },
    });

    const req = controller.expectOne('/api/v1/products/unknown');
    req.flush({ detail: 'Not Found' }, { status: 404, statusText: 'Not Found' });

    controller.expectNone('/api/v1/auth/refresh');
    expect(errorStatus).toBe(404);
  });
});
