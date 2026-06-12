/**
 * auth.service.spec.ts — Wave 6 Wave A
 *
 * Tests AuthService extension:
 * - AuthUser additive-optional: both legacy {id,name,phone} and real {user_id,phone,plan,created_at} compile
 * - scheduleRefresh: fires at (expires_in-30)s; logout cancels the timer
 * - bootstrap(): refresh-200 → setSession + me() hydrate + scheduleRefresh scheduled
 * - bootstrap(): refresh-401 → stays logged-out, RESOLVES (never rejects)
 * - setSession/logout/getToken (existing behaviour preserved)
 *
 * No Zone.js — use vi.useFakeTimers() for timer tests (fakeAsync is NOT available).
 * Pattern: create component/service AFTER vi.useFakeTimers() for timer-dependent tests.
 */

import { TestBed } from '@angular/core/testing';
import { provideHttpClient, withFetch } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { vi } from 'vitest';

import { AuthService, AuthUser } from './auth.service';
import { AuthApiService } from './auth-api.service';

// ── Setup ─────────────────────────────────────────────────────────────────────

function setup() {
  TestBed.configureTestingModule({
    providers: [
      AuthService,
      AuthApiService,
      provideHttpClient(withFetch()),
      provideHttpClientTesting(),
    ],
  });
  return {
    service:    TestBed.inject(AuthService),
    controller: TestBed.inject(HttpTestingController),
  };
}

afterEach(() => {
  TestBed.inject(HttpTestingController).verify();
  vi.useRealTimers();
});

// ── AuthUser additive-optional (DECISION-3) ───────────────────────────────────

describe('AuthUser — additive-optional interface (DECISION-3)', () => {
  it('accepts legacy {id, name, phone} shape', () => {
    const { service } = setup();
    const legacyUser: AuthUser = { id: 1, name: 'Seller', phone: '+919876543210' };
    service.setSession('mock-token', legacyUser);
    expect(service.isAuthenticated()).toBe(true);
    expect(service.currentUser()?.phone).toBe('+919876543210');
  });

  it('accepts real MeResponse-derived shape {user_id, phone, plan, created_at}', () => {
    const { service } = setup();
    const realUser: AuthUser = {
      phone: '+919876543210',
      user_id: 'uuid-abc-123',
      plan: 'free',
      created_at: '2026-01-01T00:00:00Z',
      last_login_at: null,
    };
    service.setSession('real-token', realUser);
    expect(service.currentUser()?.user_id).toBe('uuid-abc-123');
    expect(service.currentUser()?.plan).toBe('free');
  });

  it('phone is the only required field', () => {
    const { service } = setup();
    const minimalUser: AuthUser = { phone: '+911234567890' };
    service.setSession('tok', minimalUser);
    expect(service.currentUser()?.phone).toBe('+911234567890');
  });
});

// ── setSession / logout / getToken ────────────────────────────────────────────

describe('AuthService — setSession / logout / getToken', () => {
  it('getToken returns null before setSession', () => {
    const { service } = setup();
    expect(service.getToken()).toBeNull();
    expect(service.isAuthenticated()).toBe(false);
  });

  it('setSession sets token and user', () => {
    const { service } = setup();
    service.setSession('my-token', { phone: '+91x' });
    expect(service.getToken()).toBe('my-token');
    expect(service.isAuthenticated()).toBe(true);
  });

  it('logout clears token and user', () => {
    const { service } = setup();
    service.setSession('tok', { phone: '+91x' });
    service.logout();
    expect(service.getToken()).toBeNull();
    expect(service.isAuthenticated()).toBe(false);
    expect(service.currentUser()).toBeNull();
  });
});

// ── scheduleRefresh ───────────────────────────────────────────────────────────

describe('AuthService.scheduleRefresh()', () => {
  it('fires a refresh after (expires_in - 30) seconds', () => {
    vi.useFakeTimers();

    TestBed.configureTestingModule({
      providers: [
        AuthService,
        AuthApiService,
        provideHttpClient(withFetch()),
        provideHttpClientTesting(),
      ],
    });

    const service    = TestBed.inject(AuthService);
    const controller = TestBed.inject(HttpTestingController);

    service.setSession('tok', { phone: '+91x' });
    service.scheduleRefresh(60); // fire after 60-30 = 30s

    vi.advanceTimersByTime(29_000); // not yet
    controller.expectNone('/api/v1/auth/refresh');

    vi.advanceTimersByTime(1_001); // fire at 30s
    const refreshReq = controller.match('/api/v1/auth/refresh');
    expect(refreshReq.length).toBeGreaterThanOrEqual(1);
    refreshReq[0].flush({ access_token: 'new-tok', expires_in: 60, token_type: 'bearer' });

    // The /me call follows the refresh in _doSilentRefresh
    const meReq = controller.match('/api/v1/auth/me');
    meReq.forEach((r) =>
      r.flush({ user_id: 'u', phone: '+91x', plan: 'free', created_at: '', last_login_at: null }),
    );

    controller.verify();
    vi.useRealTimers();
  });

  it('logout cancels the scheduled refresh timer', () => {
    vi.useFakeTimers();

    TestBed.configureTestingModule({
      providers: [
        AuthService,
        AuthApiService,
        provideHttpClient(withFetch()),
        provideHttpClientTesting(),
      ],
    });

    const service    = TestBed.inject(AuthService);
    const controller = TestBed.inject(HttpTestingController);

    service.setSession('tok', { phone: '+91x' });
    service.scheduleRefresh(60);
    service.logout(); // cancels timer

    vi.advanceTimersByTime(60_000); // advance past the fire point
    controller.expectNone('/api/v1/auth/refresh');

    controller.verify();
    vi.useRealTimers();
  });
});

// ── setSession auto-pair (frozen-surface amendment 2026-06-12) ──────────────────

describe('AuthService.setSession() auto-pair with scheduleRefresh', () => {
  it('AUTO-schedules a refresh when expiresIn is provided', () => {
    vi.useFakeTimers();

    TestBed.configureTestingModule({
      providers: [
        AuthService,
        AuthApiService,
        provideHttpClient(withFetch()),
        provideHttpClientTesting(),
      ],
    });

    const service    = TestBed.inject(AuthService);
    const controller = TestBed.inject(HttpTestingController);

    // 3-arg form: NO explicit scheduleRefresh() call by the caller.
    service.setSession('tok', { phone: '+91x' }, 60); // fire at 60-30 = 30s

    vi.advanceTimersByTime(29_000);
    controller.expectNone('/api/v1/auth/refresh'); // not yet

    vi.advanceTimersByTime(1_001); // 30s — auto-scheduled refresh fires
    const refreshReq = controller.match('/api/v1/auth/refresh');
    expect(refreshReq.length).toBeGreaterThanOrEqual(1);
    refreshReq[0].flush({ access_token: 'new-tok', expires_in: 60, token_type: 'bearer' });

    const meReq = controller.match('/api/v1/auth/me');
    meReq.forEach((r) =>
      r.flush({ user_id: 'u', phone: '+91x', plan: 'free', created_at: '', last_login_at: null }),
    );

    controller.verify();
    vi.useRealTimers();
  });

  it('does NOT schedule a refresh when expiresIn is omitted (existing 2-arg callers unchanged)', () => {
    vi.useFakeTimers();

    TestBed.configureTestingModule({
      providers: [
        AuthService,
        AuthApiService,
        provideHttpClient(withFetch()),
        provideHttpClientTesting(),
      ],
    });

    const service    = TestBed.inject(AuthService);
    const controller = TestBed.inject(HttpTestingController);

    // 2-arg form (otp-verify mock / SP06 C4 smoke / bootstrap pre-hydration).
    service.setSession('tok', { phone: '+91x' });
    expect(service.getToken()).toBe('tok');
    expect(service.isAuthenticated()).toBe(true);

    vi.advanceTimersByTime(120_000); // no timer should ever fire
    controller.expectNone('/api/v1/auth/refresh');

    controller.verify();
    vi.useRealTimers();
  });

  it('explicit scheduleRefresh() remains independently callable', () => {
    vi.useFakeTimers();

    TestBed.configureTestingModule({
      providers: [
        AuthService,
        AuthApiService,
        provideHttpClient(withFetch()),
        provideHttpClientTesting(),
      ],
    });

    const service    = TestBed.inject(AuthService);
    const controller = TestBed.inject(HttpTestingController);

    service.setSession('tok', { phone: '+91x' }); // no auto-schedule
    service.scheduleRefresh(60);                   // explicit, still works

    vi.advanceTimersByTime(30_001);
    const refreshReq = controller.match('/api/v1/auth/refresh');
    expect(refreshReq.length).toBeGreaterThanOrEqual(1);
    refreshReq[0].flush({ access_token: 'n', expires_in: 60, token_type: 'bearer' });
    controller.match('/api/v1/auth/me').forEach((r) =>
      r.flush({ user_id: 'u', phone: '+91x', plan: 'free', created_at: '', last_login_at: null }),
    );

    controller.verify();
    vi.useRealTimers();
  });
});

// ── bootstrap() ───────────────────────────────────────────────────────────────

describe('AuthService.bootstrap()', () => {
  it('refresh-200 → setSession + me() hydration + resolves', async () => {
    const { service, controller } = setup();

    const bootstrapPromise = service.bootstrap();

    const refreshReq = controller.expectOne('/api/v1/auth/refresh');
    expect(refreshReq.request.withCredentials).toBe(true);
    refreshReq.flush({ access_token: 'boot-token', expires_in: 900, token_type: 'bearer' });

    const meReq = controller.expectOne('/api/v1/auth/me');
    meReq.flush({
      user_id: 'boot-uuid',
      phone: '+919876543210',
      plan: 'free',
      created_at: '2026-01-01T00:00:00Z',
      last_login_at: null,
    });

    await bootstrapPromise;

    expect(service.getToken()).toBe('boot-token');
    expect(service.isAuthenticated()).toBe(true);
    expect(service.currentUser()?.user_id).toBe('boot-uuid');
    expect(service.currentUser()?.plan).toBe('free');
  });

  it('refresh-401 → stays logged-out and RESOLVES (never rejects)', async () => {
    const { service, controller } = setup();

    const bootstrapPromise = service.bootstrap();

    const refreshReq = controller.expectOne('/api/v1/auth/refresh');
    refreshReq.flush(
      { detail: 'Unauthorized', code: 'AUTH_REQUIRED', validation_message_id: '', request_id: '' },
      { status: 401, statusText: 'Unauthorized' },
    );

    // Must resolve — never reject
    await expect(bootstrapPromise).resolves.toBeUndefined();

    expect(service.getToken()).toBeNull();
    expect(service.isAuthenticated()).toBe(false);
  });

  it('refresh-200 but /me fails → token set, resolves (minimal state)', async () => {
    const { service, controller } = setup();

    const bootstrapPromise = service.bootstrap();

    const refreshReq = controller.expectOne('/api/v1/auth/refresh');
    refreshReq.flush({ access_token: 'partial-tok', expires_in: 900, token_type: 'bearer' });

    const meReq = controller.expectOne('/api/v1/auth/me');
    meReq.flush(
      { detail: 'Internal Server Error', code: 'SERVER_ERROR', validation_message_id: '', request_id: '' },
      { status: 500, statusText: 'Internal Server Error' },
    );

    await bootstrapPromise;

    // Token is set even if /me fails (the catchError path in bootstrap)
    expect(service.getToken()).toBe('partial-tok');
  });
});
