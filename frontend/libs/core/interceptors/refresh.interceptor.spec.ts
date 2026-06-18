/**
 * refresh.interceptor.spec.ts — Wave 6 Wave A (R-W6-11) + stampede fix (h/i/j/k)
 *
 * Tests the 401→refresh→retry single-flight gate using HttpTestingController.
 * Pure-function / fake-http — NO live backend tunnel required.
 *
 * Spec cases (per R-W6-11):
 * (a) A 401 on a protected call triggers exactly ONE POST /api/v1/auth/refresh
 * (b) On refresh-200 the original request is retried with the new Bearer and succeeds
 * (c) On refresh-401 → AuthService.forceLogout() called + navigate('/login') + original errors
 * (d) Single-flight: TWO concurrent 401s fire ONE refresh; BOTH retry with the new token
 * (e) A 401 on /auth/refresh itself does NOT re-enter refresh (no loop)
 *
 * Additionally:
 * (f) /api/v1/auth/* requests are skipped (not retried on 401)
 * (g) Non-401 errors pass through untouched
 *
 * Stampede-fix specs (new — h/i/j/k):
 * (h) 20 concurrent 401s → EXACTLY ONE POST /auth/refresh; all 20 retry with new Bearer
 * (i) After first refresh window, a NEW 401 starts a fresh single-flight refresh
 * (j) refresh-401 → forceLogout ONCE + navigate ONCE, no further refresh
 * (k) After cascade, a NEW 401 can start a fresh refresh (gate not wedged)
 *
 * Tests (a)–(g) use a lightweight mock AuthService that delegates refreshShared()
 * to the TestBed HttpClient so controller.expectOne('/api/v1/auth/refresh') works.
 *
 * Tests (d), (h)–(k) use the REAL AuthService (with a spy on AuthApiService.refresh)
 * because they need the actual single-flight shareReplay logic in refreshShared().
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
import { Subject } from 'rxjs';
import { vi } from 'vitest';

import { AuthService, AuthUser } from '../services/auth.service';
import { AuthApiService } from '../services/auth-api.service';
import type { RefreshResponse } from '../services/auth-api.service';
import { refreshInterceptor } from './refresh.interceptor';

// ── Lightweight mock AuthService (for a–g) ────────────────────────────────────

type AuthMock = {
  getToken: () => string | null;
  currentUser: ReturnType<typeof computed<AuthUser | null>>;
  isAuthenticated: ReturnType<typeof computed<boolean>>;
  setSession: ReturnType<typeof vi.fn>;
  logout: ReturnType<typeof vi.fn>;
  forceLogout: ReturnType<typeof vi.fn>;
  scheduleRefresh: ReturnType<typeof vi.fn>;
  refreshShared: ReturnType<typeof vi.fn>;
};

function makeAuthMock(http: HttpClient): AuthMock {
  const _user  = signal<AuthUser | null>(null);
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
    forceLogout: vi.fn(() => {
      _token.set(null);
      _user.set(null);
    }),
    scheduleRefresh: vi.fn(),
    // Routes through HttpClient so controller.expectOne('/api/v1/auth/refresh') works.
    refreshShared: vi.fn(() =>
      http.post<RefreshResponse>('/api/v1/auth/refresh', {}, { withCredentials: true }),
    ),
  };
}

// ── Setup with mock AuthService (a–g + e/f) ───────────────────────────────────

function setup() {
  TestBed.configureTestingModule({
    providers: [
      provideHttpClient(withFetch(), withInterceptors([refreshInterceptor])),
      provideHttpClientTesting(),
      provideRouter([
        { path: 'login',     children: [] },
        { path: 'dashboard', children: [] },
      ]),
      {
        provide: AuthService,
        useFactory: (http: HttpClient) => makeAuthMock(http),
        deps: [HttpClient],
      },
    ],
  });

  const http       = TestBed.inject(HttpClient);
  const controller = TestBed.inject(HttpTestingController);
  const router     = TestBed.inject(Router);
  const authMock   = TestBed.inject(AuthService) as unknown as AuthMock;

  return { http, controller, authMock, router };
}

// ── Setup with REAL AuthService (d, h, i, j, k) ───────────────────────────────
//
// Use the real AuthService so refreshShared()'s single-flight gate is exercised.
// Spy on AuthApiService.refresh() to control responses via a Subject.

function setupReal() {
  TestBed.configureTestingModule({
    providers: [
      AuthService,
      AuthApiService,
      provideHttpClient(withFetch(), withInterceptors([refreshInterceptor])),
      provideHttpClientTesting(),
      provideRouter([
        { path: 'login',     children: [] },
        { path: 'dashboard', children: [] },
      ]),
    ],
  });

  const http       = TestBed.inject(HttpClient);
  const controller = TestBed.inject(HttpTestingController);
  const router     = TestBed.inject(Router);
  const auth       = TestBed.inject(AuthService);
  const authApi    = TestBed.inject(AuthApiService);

  // Set an initial session so the service is in "authenticated" state
  auth.setSession('initial-token', { phone: '+91test' });

  return { http, controller, auth, authApi, router };
}

afterEach(() => {
  TestBed.inject(HttpTestingController).verify();
});

// ── (a) A 401 on a protected call triggers ONE POST /auth/refresh ──────────────

describe('refreshInterceptor (a): 401 triggers one POST /api/v1/auth/refresh', () => {
  it('fires exactly one refresh call on 401', () => {
    const { http, controller } = setup();
    let completed = false;

    http.get('/api/v1/products').subscribe({ complete: () => { completed = true; } });

    const orig = controller.expectOne('/api/v1/products');
    orig.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

    const refresh = controller.expectOne('/api/v1/auth/refresh');
    expect(refresh.request.method).toBe('POST');
    refresh.flush({ access_token: 'new-token', expires_in: 900, token_type: 'bearer' });

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
    expect(retry.request.headers.get('Authorization')).toBe('Bearer refreshed-token');
    retry.flush({ items: ['product-1'] });

    expect(emitted).toHaveLength(1);
    expect((emitted[0] as { items: string[] }).items).toContain('product-1');
  });
});

// ── (c) On refresh-401 → forceLogout + navigate /login ────────────────────────

describe('refreshInterceptor (c): refresh-401 → forceLogout + navigate /login', () => {
  it('calls forceLogout and navigates to /login when refresh fails with 401', () => {
    const { http, controller, authMock, router } = setup();
    const navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);

    authMock.forceLogout.mockImplementation(() => {
      void router.navigate(['/login']);
    });

    let errorCaught = false;

    http.get('/api/v1/products').subscribe({
      error: () => { errorCaught = true; },
    });

    const orig = controller.expectOne('/api/v1/products');
    orig.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

    const refresh = controller.expectOne('/api/v1/auth/refresh');
    refresh.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

    expect(authMock.forceLogout).toHaveBeenCalledOnce();
    expect(navigateSpy).toHaveBeenCalledWith(['/login']);
    expect(errorCaught).toBe(true);
  });
});

// ── (d) Single-flight: TWO concurrent 401s fire ONE refresh ───────────────────
// Uses real AuthService so refreshShared() gating is exercised.

describe('refreshInterceptor (d): single-flight — two concurrent 401s fire ONE refresh', () => {
  it('queues second 401 request; both retry with the new token after ONE refresh', () => {
    const { http, controller } = setupReal();
    const results: string[] = [];

    http.get<{ id: string }>('/api/v1/products/a').subscribe((r) => results.push(r.id));
    http.get<{ id: string }>('/api/v1/products/b').subscribe((r) => results.push(r.id));

    // Both requests get 401
    const reqA = controller.expectOne('/api/v1/products/a');
    const reqB = controller.expectOne('/api/v1/products/b');
    reqA.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });
    reqB.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

    // Exactly ONE refresh call — gated by real refreshShared()
    const refreshRequests = controller.match('/api/v1/auth/refresh');
    expect(refreshRequests).toHaveLength(1);
    refreshRequests[0].flush({ access_token: 'shared-token', expires_in: 900, token_type: 'bearer' });

    // Both original requests are retried with the same new token
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
  it('/api/v1/auth/refresh 401 is passed through without triggering a second refresh', () => {
    const { http, controller, authMock } = setup();
    let errorCaught = false;

    http.post('/api/v1/auth/refresh', {}).subscribe({
      error: () => { errorCaught = true; },
    });

    const req = controller.expectOne('/api/v1/auth/refresh');
    req.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

    controller.expectNone('/api/v1/auth/refresh');
    expect(authMock.forceLogout).not.toHaveBeenCalled();
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

// ── (h) 20 concurrent 401s → EXACTLY ONE POST /auth/refresh ───────────────────
// Uses real AuthService so the shareReplay single-flight gate is exercised.

describe('refreshInterceptor (h): stampede — 20 concurrent 401s fire exactly ONE refresh', () => {
  it('20 concurrent 401s → 1 refresh call; all 20 retry with new Bearer', () => {
    const { http, controller } = setupReal();
    const N = 20;
    const results: string[] = [];
    const errors: unknown[] = [];

    for (let i = 0; i < N; i++) {
      http.get<{ id: string }>(`/api/v1/products/${i}`).subscribe({
        next: (r) => results.push(r.id),
        error: (e) => errors.push(e),
      });
    }

    for (let i = 0; i < N; i++) {
      const req = controller.expectOne(`/api/v1/products/${i}`);
      req.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });
    }

    // Real refreshShared() → exactly ONE POST /auth/refresh
    const refreshRequests = controller.match('/api/v1/auth/refresh');
    expect(refreshRequests.length).toBe(1);

    refreshRequests[0].flush({
      access_token: 'stampede-token',
      expires_in: 900,
      token_type: 'bearer',
    });

    for (let i = 0; i < N; i++) {
      const retry = controller.expectOne(`/api/v1/products/${i}`);
      expect(retry.request.headers.get('Authorization')).toBe('Bearer stampede-token');
      retry.flush({ id: `result-${i}` });
    }

    expect(results).toHaveLength(N);
    expect(errors).toHaveLength(0);
  });
});

// ── (i) After first refresh window, a NEW 401 starts a fresh refresh ───────────
// Uses real AuthService — finalize() in refreshShared resets _refreshInFlight.

describe('refreshInterceptor (i): fresh window after stampede — no stale-token replay', () => {
  it('a second 401 (after a completed refresh cycle) starts a new single-flight refresh', () => {
    const { http, controller } = setupReal();
    const results: string[] = [];

    // ── First cycle ──────────────────────────────────────────────────────────
    http.get<{ id: string }>('/api/v1/products/first').subscribe((r) => results.push(r.id));

    const first = controller.expectOne('/api/v1/products/first');
    first.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

    const firstRefresh = controller.expectOne('/api/v1/auth/refresh');
    firstRefresh.flush({ access_token: 'token-1', expires_in: 900, token_type: 'bearer' });

    const firstRetry = controller.expectOne('/api/v1/products/first');
    expect(firstRetry.request.headers.get('Authorization')).toBe('Bearer token-1');
    firstRetry.flush({ id: 'first-result' });

    expect(results).toContain('first-result');

    // ── Second cycle — gate MUST be reset (finalize cleared _refreshInFlight) ─
    http.get<{ id: string }>('/api/v1/products/second').subscribe((r) => results.push(r.id));

    const second = controller.expectOne('/api/v1/products/second');
    second.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

    // A NEW refresh must be triggered — not replaying stale cached token
    const secondRefresh = controller.expectOne('/api/v1/auth/refresh');
    secondRefresh.flush({ access_token: 'token-2', expires_in: 900, token_type: 'bearer' });

    const secondRetry = controller.expectOne('/api/v1/products/second');
    expect(secondRetry.request.headers.get('Authorization')).toBe('Bearer token-2');
    secondRetry.flush({ id: 'second-result' });

    expect(results).toContain('second-result');
  });
});

// ── (j) refresh-401 → forceLogout called ONCE + navigate ONCE ─────────────────
// Uses real AuthService — forceLogout's _loggedOut guard prevents repeat navigates.

describe('refreshInterceptor (j): cascade — forceLogout called ONCE, navigate ONCE', () => {
  it('5 concurrent 401s → refresh-401 → navigate(["/login"]) ONCE, no further refresh', () => {
    const { http, controller, router } = setupReal();
    const navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    const errors: unknown[] = [];

    const N = 5;
    for (let i = 0; i < N; i++) {
      http.get(`/api/v1/products/${i}`).subscribe({
        error: (e) => errors.push(e),
      });
    }

    for (let i = 0; i < N; i++) {
      const req = controller.expectOne(`/api/v1/products/${i}`);
      req.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });
    }

    // Exactly one refresh attempted
    const refreshRequests = controller.match('/api/v1/auth/refresh');
    expect(refreshRequests.length).toBe(1);

    // The one refresh itself fails with 401
    refreshRequests[0].flush(
      { detail: 'Unauthorized' },
      { status: 401, statusText: 'Unauthorized' },
    );

    // forceLogout() navigates ONCE (logout-once guard prevents duplicate navigations)
    expect(navigateSpy).toHaveBeenCalledTimes(1);
    expect(navigateSpy).toHaveBeenCalledWith(['/login']);

    // All N original calls errored
    expect(errors).toHaveLength(N);

    // No further refresh attempt after forceLogout
    controller.expectNone('/api/v1/auth/refresh');
  });
});

// ── (k) After cascade, a NEW 401 can start a fresh refresh (gate not wedged) ───
// Uses real AuthService — after forceLogout, _refreshInFlight is null.
// A fresh setSession re-arms the guard, then a new 401 can refresh again.

describe('refreshInterceptor (k): gate not wedged after cascade logout', () => {
  it('after a cascade logout, a re-authenticated session can refresh again on new 401', () => {
    const { http, controller, auth, router } = setupReal();
    const navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    const errors: unknown[] = [];
    const results: string[] = [];

    // ── Cascade: first request → 401 → refresh-401 → forceLogout ────────────
    http.get('/api/v1/products/first').subscribe({ error: (e) => errors.push(e) });

    const firstOrig = controller.expectOne('/api/v1/products/first');
    firstOrig.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

    const firstRefresh = controller.expectOne('/api/v1/auth/refresh');
    firstRefresh.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

    expect(errors).toHaveLength(1);
    expect(navigateSpy).toHaveBeenCalledOnce();
    expect(auth.isAuthenticated()).toBe(false);

    // ── Re-login: setSession re-arms the logout guard ─────────────────────────
    auth.setSession('re-auth-token', { phone: '+91x' });
    expect(auth.isAuthenticated()).toBe(true);

    // ── New request → 401 → should trigger a FRESH refresh (gate not wedged) ──
    http.get<{ id: string }>('/api/v1/products/second').subscribe((r) => results.push(r.id));

    const secondOrig = controller.expectOne('/api/v1/products/second');
    secondOrig.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

    // A new refresh is triggered — gate was reset by forceLogout
    const secondRefresh = controller.expectOne('/api/v1/auth/refresh');
    secondRefresh.flush({ access_token: 'fresh-token', expires_in: 900, token_type: 'bearer' });

    const secondRetry = controller.expectOne('/api/v1/products/second');
    expect(secondRetry.request.headers.get('Authorization')).toBe('Bearer fresh-token');
    secondRetry.flush({ id: 'second-result' });

    expect(results).toContain('second-result');
  });
});
