/**
 * auth.service.spec.ts — Wave 6 Wave A + stampede fix
 *
 * Tests AuthService extension:
 * - AuthUser additive-optional: both legacy {id,name,phone} and real {user_id,phone,plan,created_at} compile
 * - scheduleRefresh: fires at clamped delay (new D-D formula); logout cancels the timer
 * - bootstrap(): refresh-200 → setSession + me() hydrate + scheduleRefresh scheduled
 * - bootstrap(): refresh-401 → stays logged-out, RESOLVES (never rejects)
 * - setSession/logout/getToken (existing behaviour preserved)
 * - refreshShared(): single-flight → ONE authApi.refresh call; resets after completion
 * - forceLogout(): logout-once; navigate exactly once; _doSilentRefresh 401 → forceLogout
 * - scheduleRefresh clamp: MIN_REFRESH_DELAY_MS floor (expiresIn=10 → ≥5000ms)
 * - bootstrap racing _doSilentRefresh → only ONE authApi.refresh via refreshShared
 *
 * New delay formula (D-D fix):
 *   skew    = min(30, expiresIn * 0.1)
 *   delayMs = max((expiresIn - skew) * 1000, 5000)
 *
 * Examples:
 *   expiresIn=60  → skew=6,  delayMs=54 000 ms
 *   expiresIn=900 → skew=30, delayMs=870 000 ms
 *   expiresIn=10  → skew=1,  delayMs=max(9000,5000)=9000 ms
 *   expiresIn=2   → skew=0.2, delayMs=max(1800,5000)=5000 ms
 *
 * No Zone.js — use vi.useFakeTimers() for timer tests (fakeAsync is NOT available).
 * Pattern: create component/service AFTER vi.useFakeTimers() for timer-dependent tests.
 */

import { TestBed } from '@angular/core/testing';
import { provideHttpClient, withFetch } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
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
      provideRouter([
        { path: 'login', children: [] },
      ]),
    ],
  });
  return {
    service:    TestBed.inject(AuthService),
    controller: TestBed.inject(HttpTestingController),
    router:     TestBed.inject(Router),
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
    const { service, controller } = setup();
    service.setSession('tok', { phone: '+91x' });
    service.logout();
    // Consume the fire-and-forget revoke POST so controller.verify() passes.
    controller.match('/api/v1/auth/logout').forEach((r) =>
      r.flush(null, { status: 200, statusText: 'OK' }),
    );
    expect(service.getToken()).toBeNull();
    expect(service.isAuthenticated()).toBe(false);
    expect(service.currentUser()).toBeNull();
  });
});

// ── logout() — cookie-revoke + navigation (QA-wave-1 regression) ─────────────
//
// Regression tests for the logout fix: logout() must call POST /auth/logout
// (fire-and-forget cookie revoke) AND navigate to /login.
// Previously logout() only nulled in-memory state — the HttpOnly refresh cookie
// survived and bootstrap/refresh re-authenticated the session silently.

describe('AuthService.logout() — cookie-revoke + navigate (QA-wave-1 regression)', () => {
  it('calls POST /api/v1/auth/logout (withCredentials) as fire-and-forget', () => {
    const { service, controller } = setup();
    service.setSession('tok', { phone: '+91x' });

    service.logout();

    const logoutReqs = controller.match('/api/v1/auth/logout');
    expect(logoutReqs.length).toBe(1);
    expect(logoutReqs[0].request.method).toBe('POST');
    // withCredentials=true is required so the browser sends the HttpOnly refresh cookie.
    expect(logoutReqs[0].request.withCredentials).toBe(true);
    logoutReqs[0].flush(null, { status: 200, statusText: 'OK' });
  });

  it('navigates to /login immediately regardless of server revoke success/failure', () => {
    const { service, controller, router } = setup();
    const navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);

    service.setSession('tok', { phone: '+91x' });
    service.logout();

    // Consume the revoke POST (fire-and-forget — the test does not care about outcome).
    controller.match('/api/v1/auth/logout').forEach((r) =>
      r.flush(null, { status: 200, statusText: 'OK' }),
    );

    expect(navigateSpy).toHaveBeenCalledOnce();
    expect(navigateSpy).toHaveBeenCalledWith(['/login']);
  });

  it('navigates even when the server revoke returns 401 (cookie already expired)', () => {
    const { service, controller, router } = setup();
    const navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);

    service.setSession('tok', { phone: '+91x' });
    service.logout();

    // Simulate 401 from server — local logout must still complete.
    controller.match('/api/v1/auth/logout').forEach((r) =>
      r.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' }),
    );

    expect(navigateSpy).toHaveBeenCalledOnce();
    expect(navigateSpy).toHaveBeenCalledWith(['/login']);
    expect(service.getToken()).toBeNull();
    expect(service.isAuthenticated()).toBe(false);
  });
});

// ── scheduleRefresh (D-D fix — new delay formula) ────────────────────────────
//
// New formula: skew=min(30, expiresIn*0.1), delayMs=max((expiresIn-skew)*1000, 5000)
// expiresIn=60 → skew=6, delay=54 000 ms (was 30 000 ms in old formula)

describe('AuthService.scheduleRefresh()', () => {
  it('fires a refresh after the clamped delay (expiresIn=60 → 54 000 ms)', () => {
    vi.useFakeTimers();

    TestBed.configureTestingModule({
      providers: [
        AuthService,
        AuthApiService,
        provideHttpClient(withFetch()),
        provideHttpClientTesting(),
        provideRouter([{ path: 'login', children: [] }]),
      ],
    });

    const service    = TestBed.inject(AuthService);
    const controller = TestBed.inject(HttpTestingController);

    service.setSession('tok', { phone: '+91x' });
    service.scheduleRefresh(60); // skew=6, delay=54 000 ms

    vi.advanceTimersByTime(53_999); // not yet
    controller.expectNone('/api/v1/auth/refresh');

    vi.advanceTimersByTime(1_001); // crosses 54 000 ms
    const refreshReq = controller.match('/api/v1/auth/refresh');
    expect(refreshReq.length).toBeGreaterThanOrEqual(1);
    refreshReq[0].flush({ access_token: 'new-tok', expires_in: 60, token_type: 'bearer' });

    // The /me call follows the refresh in _doSilentRefresh
    const meReq = controller.match('/api/v1/auth/me');
    meReq.forEach((r) =>
      r.flush({
        user_id: 'u', phone: '+91x', plan: 'free', created_at: '',
        last_login_at: null, onboarding_complete: false,
      }),
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
        provideRouter([{ path: 'login', children: [] }]),
      ],
    });

    const service    = TestBed.inject(AuthService);
    const controller = TestBed.inject(HttpTestingController);

    service.setSession('tok', { phone: '+91x' });
    service.scheduleRefresh(60); // delay=54 000 ms
    service.logout(); // cancels timer

    vi.advanceTimersByTime(60_000); // advance past the fire point
    controller.expectNone('/api/v1/auth/refresh');

    // Consume the fire-and-forget revoke POST so controller.verify() passes.
    controller.match('/api/v1/auth/logout').forEach((r) =>
      r.flush(null, { status: 200, statusText: 'OK' }),
    );

    controller.verify();
    vi.useRealTimers();
  });

  // D-D clamp test: expiresIn=10 → skew=1, delayMs=max(9000,5000)=9000ms (>5000)
  it('clamps delay to MIN_REFRESH_DELAY_MS=5000 for tiny TTL (expiresIn=2 → 5000ms floor)', () => {
    vi.useFakeTimers();

    TestBed.configureTestingModule({
      providers: [
        AuthService,
        AuthApiService,
        provideHttpClient(withFetch()),
        provideHttpClientTesting(),
        provideRouter([{ path: 'login', children: [] }]),
      ],
    });

    const service    = TestBed.inject(AuthService);
    const controller = TestBed.inject(HttpTestingController);

    service.setSession('tok', { phone: '+91x' });
    // expiresIn=2 → skew=0.2, raw=(2-0.2)*1000=1800ms → clamped to 5000ms
    service.scheduleRefresh(2);

    vi.advanceTimersByTime(4_999); // 4.999s — must NOT fire yet (floor=5000ms)
    controller.expectNone('/api/v1/auth/refresh');

    vi.advanceTimersByTime(1_001); // crosses 5000ms
    const refreshReq = controller.match('/api/v1/auth/refresh');
    expect(refreshReq.length).toBeGreaterThanOrEqual(1);
    refreshReq[0].flush({ access_token: 'clamped-tok', expires_in: 900, token_type: 'bearer' });

    const meReq = controller.match('/api/v1/auth/me');
    meReq.forEach((r) =>
      r.flush({
        user_id: 'u', phone: '+91x', plan: 'free', created_at: '',
        last_login_at: null, onboarding_complete: false,
      }),
    );

    controller.verify();
    vi.useRealTimers();
  });

  // Verify 900s TTL: skew=30, delay=870 000ms
  it('expiresIn=900 → delayMs≈870 000ms (positive buffer, not zero)', () => {
    vi.useFakeTimers();

    TestBed.configureTestingModule({
      providers: [
        AuthService,
        AuthApiService,
        provideHttpClient(withFetch()),
        provideHttpClientTesting(),
        provideRouter([{ path: 'login', children: [] }]),
      ],
    });

    const service    = TestBed.inject(AuthService);
    const controller = TestBed.inject(HttpTestingController);

    service.setSession('tok', { phone: '+91x' });
    service.scheduleRefresh(900); // skew=30, delay=870 000ms

    vi.advanceTimersByTime(869_999); // not yet
    controller.expectNone('/api/v1/auth/refresh');

    vi.advanceTimersByTime(1_001); // crosses 870 000ms
    const refreshReq = controller.match('/api/v1/auth/refresh');
    expect(refreshReq.length).toBeGreaterThanOrEqual(1);
    refreshReq[0].flush({ access_token: 'long-tok', expires_in: 900, token_type: 'bearer' });

    const meReq = controller.match('/api/v1/auth/me');
    meReq.forEach((r) =>
      r.flush({
        user_id: 'u', phone: '+91x', plan: 'free', created_at: '',
        last_login_at: null, onboarding_complete: false,
      }),
    );

    controller.verify();
    vi.useRealTimers();
  });
});

// ── setSession auto-pair (frozen-surface amendment 2026-06-12) ──────────────────

describe('AuthService.setSession() auto-pair with scheduleRefresh', () => {
  it('AUTO-schedules a refresh when expiresIn is provided (expiresIn=60 → 54 000ms)', () => {
    vi.useFakeTimers();

    TestBed.configureTestingModule({
      providers: [
        AuthService,
        AuthApiService,
        provideHttpClient(withFetch()),
        provideHttpClientTesting(),
        provideRouter([{ path: 'login', children: [] }]),
      ],
    });

    const service    = TestBed.inject(AuthService);
    const controller = TestBed.inject(HttpTestingController);

    // 3-arg form: NO explicit scheduleRefresh() call by the caller.
    service.setSession('tok', { phone: '+91x' }, 60); // skew=6 → delay=54 000ms

    vi.advanceTimersByTime(53_999);
    controller.expectNone('/api/v1/auth/refresh'); // not yet

    vi.advanceTimersByTime(1_001); // 54 000ms — auto-scheduled refresh fires
    const refreshReq = controller.match('/api/v1/auth/refresh');
    expect(refreshReq.length).toBeGreaterThanOrEqual(1);
    refreshReq[0].flush({ access_token: 'new-tok', expires_in: 60, token_type: 'bearer' });

    const meReq = controller.match('/api/v1/auth/me');
    meReq.forEach((r) =>
      r.flush({
        user_id: 'u', phone: '+91x', plan: 'free', created_at: '',
        last_login_at: null, onboarding_complete: false,
      }),
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
        provideRouter([{ path: 'login', children: [] }]),
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
        provideRouter([{ path: 'login', children: [] }]),
      ],
    });

    const service    = TestBed.inject(AuthService);
    const controller = TestBed.inject(HttpTestingController);

    service.setSession('tok', { phone: '+91x' }); // no auto-schedule
    service.scheduleRefresh(60);                   // explicit: delay=54 000ms

    vi.advanceTimersByTime(54_001); // crosses 54 000ms
    const refreshReq = controller.match('/api/v1/auth/refresh');
    expect(refreshReq.length).toBeGreaterThanOrEqual(1);
    refreshReq[0].flush({ access_token: 'n', expires_in: 60, token_type: 'bearer' });
    controller.match('/api/v1/auth/me').forEach((r) =>
      r.flush({
        user_id: 'u', phone: '+91x', plan: 'free', created_at: '',
        last_login_at: null, onboarding_complete: false,
      }),
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
      onboarding_complete: true,
    });

    await bootstrapPromise;

    expect(service.getToken()).toBe('boot-token');
    expect(service.isAuthenticated()).toBe(true);
    expect(service.currentUser()?.user_id).toBe('boot-uuid');
    expect(service.currentUser()?.plan).toBe('free');
    // meToUser threads the Stage-1 onboarding flag onto AuthUser
    expect(service.currentUser()?.onboarding_complete).toBe(true);
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

// ── refreshUser() — re-hydrate user from /me without touching token/timer ──────

describe('AuthService.refreshUser()', () => {
  it('re-fetches /me and updates the user signal (incl. onboarding_complete) without changing the token', () => {
    const { service, controller } = setup();

    // Existing session: token + a user with onboarding_complete=false (pre-submit state).
    service.setSession('keep-token', { phone: '+919876543210', onboarding_complete: false });

    let completed = false;
    service.refreshUser().subscribe({ complete: () => { completed = true; } });

    const meReq = controller.expectOne('/api/v1/auth/me');
    expect(meReq.request.method).toBe('GET');
    meReq.flush({
      user_id: 'uuid-xyz',
      phone: '+919876543210',
      plan: 'free',
      created_at: '2026-01-01T00:00:00Z',
      last_login_at: null,
      onboarding_complete: true, // backend now reports onboarding done
    });

    expect(completed).toBe(true);
    // Token untouched — refreshUser is a user re-hydration, not a token refresh.
    expect(service.getToken()).toBe('keep-token');
    // User signal updated — flag flipped, shell predicate will hide the nav item.
    expect(service.currentUser()?.onboarding_complete).toBe(true);
    expect(service.currentUser()?.user_id).toBe('uuid-xyz');
  });

  it('on /me failure leaves the existing user untouched and still completes', () => {
    const { service, controller } = setup();

    service.setSession('keep-token', { phone: '+91x', user_id: 'orig', onboarding_complete: false });

    let completed = false;
    service.refreshUser().subscribe({ complete: () => { completed = true; } });

    const meReq = controller.expectOne('/api/v1/auth/me');
    meReq.flush(
      { detail: 'Internal Server Error', code: 'SERVER_ERROR', validation_message_id: '', request_id: '' },
      { status: 500, statusText: 'Internal Server Error' },
    );

    // catchError(() => EMPTY) — observable completes, user signal preserved.
    expect(completed).toBe(true);
    expect(service.getToken()).toBe('keep-token');
    expect(service.currentUser()?.user_id).toBe('orig');
    expect(service.currentUser()?.onboarding_complete).toBe(false);
  });
});

// ── completeLogin() — shared post-credential success tail (Google + OTP) ──────

describe('AuthService.completeLogin()', () => {
  const RESP = { access_token: 'cl-tok', expires_in: 900, token_type: 'bearer' as const };

  it('happy path: fetches /me, setSession with full user, routes to /dashboard when onboarding_complete:true', () => {
    const { service, controller } = setup();

    let routed: string[] = [];
    service.completeLogin(RESP).subscribe(({ route }) => { routed = route; });

    // Token set first so the /me call is authorized.
    expect(service.getToken()).toBe('cl-tok');

    const meReq = controller.expectOne('/api/v1/auth/me');
    expect(meReq.request.method).toBe('GET');
    meReq.flush({
      user_id: 'uuid-1', phone: '+919876543210', plan: 'free',
      created_at: '2026-01-01T00:00:00Z', last_login_at: null,
      onboarding_complete: true,
    });

    expect(service.isAuthenticated()).toBe(true);
    expect(service.currentUser()?.user_id).toBe('uuid-1');
    expect(service.currentUser()?.phone).toBe('+919876543210');
    expect(routed).toEqual(['/dashboard']);
  });

  it('onboarding gate: routes to /onboarding when onboarding_complete:false', () => {
    const { service, controller } = setup();

    let routed: string[] = [];
    service.completeLogin(RESP).subscribe(({ route }) => { routed = route; });

    controller.expectOne('/api/v1/auth/me').flush({
      user_id: 'uuid-2', phone: null, plan: 'free',
      created_at: '2026-01-01T00:00:00Z', last_login_at: null,
      onboarding_complete: false,
    });

    expect(routed).toEqual(['/onboarding']);
    // Google-only user with no phone is supported (phone null).
    expect(service.currentUser()?.phone).toBeNull();
  });

  it('/me failure: still sets a minimal session, routes to /dashboard, never errors', () => {
    const { service, controller } = setup();

    let routed: string[] = [];
    let errored = false;
    service.completeLogin(RESP).subscribe({
      next: ({ route }) => { routed = route; },
      error: () => { errored = true; },
    });

    controller.expectOne('/api/v1/auth/me').flush(
      { detail: 'Server Error' },
      { status: 500, statusText: 'Server Error' },
    );

    expect(errored).toBe(false);
    expect(service.isAuthenticated()).toBe(true);
    expect(service.getToken()).toBe('cl-tok');
    expect(service.currentUser()?.phone).toBeNull(); // default fallback user
    expect(routed).toEqual(['/dashboard']);
  });

  it('/me failure with fallbackUser: retains the supplied phone (OTP path)', () => {
    const { service, controller } = setup();

    service.completeLogin(RESP, { phone: '+919876543210' }).subscribe();

    controller.expectOne('/api/v1/auth/me').flush(
      { detail: 'Server Error' },
      { status: 500, statusText: 'Server Error' },
    );

    expect(service.isAuthenticated()).toBe(true);
    expect(service.currentUser()?.phone).toBe('+919876543210');
  });
});

// ── refreshShared() — single-flight gate (stampede fix) ──────────────────────

describe('AuthService.refreshShared() — single-flight gate', () => {
  it('concurrent callers share ONE in-flight Observable — only one authApi.refresh() call', async () => {
    const { service, controller } = setup();

    // Subscribe twice simultaneously before flush — both should share the same Observable
    let resolvedCount = 0;
    const tokens: string[] = [];

    service.refreshShared().subscribe((r) => {
      resolvedCount++;
      tokens.push(r.access_token);
    });
    service.refreshShared().subscribe((r) => {
      resolvedCount++;
      tokens.push(r.access_token);
    });

    // Exactly ONE HTTP call (single-flight)
    const refreshRequests = controller.match('/api/v1/auth/refresh');
    expect(refreshRequests.length).toBe(1);
    refreshRequests[0].flush({ access_token: 'shared-fresh', expires_in: 900, token_type: 'bearer' });

    // Both subscribers received the same token
    expect(resolvedCount).toBe(2);
    expect(tokens).toEqual(['shared-fresh', 'shared-fresh']);
  });

  it('resets _refreshInFlight after completion so next call starts a fresh refresh', async () => {
    const { service, controller } = setup();

    // First call
    let firstToken = '';
    service.refreshShared().subscribe((r) => { firstToken = r.access_token; });
    const firstReqs = controller.match('/api/v1/auth/refresh');
    expect(firstReqs.length).toBe(1);
    firstReqs[0].flush({ access_token: 'token-A', expires_in: 900, token_type: 'bearer' });

    expect(firstToken).toBe('token-A');

    // Second call AFTER first completed — must start a NEW refresh, not replay stale
    let secondToken = '';
    service.refreshShared().subscribe((r) => { secondToken = r.access_token; });
    const secondReqs = controller.match('/api/v1/auth/refresh');
    expect(secondReqs.length).toBe(1); // new HTTP call
    secondReqs[0].flush({ access_token: 'token-B', expires_in: 900, token_type: 'bearer' });

    expect(secondToken).toBe('token-B');
  });
});

// ── forceLogout() — logout-once cascade guard ─────────────────────────────────

describe('AuthService.forceLogout() — logout-once guard', () => {
  it('first call clears token + user and navigates to /login', () => {
    const { service, controller, router } = setup();
    const navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);

    service.setSession('tok', { phone: '+91x' });
    expect(service.isAuthenticated()).toBe(true);

    service.forceLogout();
    // Consume the fire-and-forget revoke POST (forceLogout now calls authApi.logout()).
    controller.match('/api/v1/auth/logout').forEach((r) =>
      r.flush(null, { status: 200, statusText: 'OK' }),
    );

    expect(service.getToken()).toBeNull();
    expect(service.isAuthenticated()).toBe(false);
    expect(service.currentUser()).toBeNull();
    expect(navigateSpy).toHaveBeenCalledOnce();
    expect(navigateSpy).toHaveBeenCalledWith(['/login']);
  });

  it('subsequent calls are no-ops — navigate called ONLY ONCE no matter how many times called', () => {
    const { service, controller, router } = setup();
    const navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);

    service.setSession('tok', { phone: '+91x' });
    service.forceLogout(); // first call — navigates (fires revoke POST)
    service.forceLogout(); // no-op (guard blocks)
    service.forceLogout(); // no-op (guard blocks)

    // Only one revoke POST was fired (on the first call; subsequent calls are no-ops).
    controller.match('/api/v1/auth/logout').forEach((r) =>
      r.flush(null, { status: 200, statusText: 'OK' }),
    );

    expect(navigateSpy).toHaveBeenCalledOnce(); // NOT 3 times
  });

  it('setSession re-arms the guard so forceLogout works again after re-login', () => {
    const { service, controller, router } = setup();
    const navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);

    service.setSession('tok-1', { phone: '+91x' });
    service.forceLogout(); // first login window → logout

    // Re-login
    service.setSession('tok-2', { phone: '+91x' });
    service.forceLogout(); // second login window → logout

    // Consume both revoke POSTs.
    controller.match('/api/v1/auth/logout').forEach((r) =>
      r.flush(null, { status: 200, statusText: 'OK' }),
    );

    // Both logins produced exactly one navigate each = 2 total
    expect(navigateSpy).toHaveBeenCalledTimes(2);
  });
});

// ── _doSilentRefresh 401 → forceLogout (D-C fix) ─────────────────────────────

describe('AuthService._doSilentRefresh() — refresh-401 → forceLogout (D-C fix)', () => {
  it('silent refresh 401 → forceLogout() + navigate to /login (not silent EMPTY)', () => {
    vi.useFakeTimers();

    TestBed.configureTestingModule({
      providers: [
        AuthService,
        AuthApiService,
        provideHttpClient(withFetch()),
        provideHttpClientTesting(),
        provideRouter([{ path: 'login', children: [] }]),
      ],
    });

    const service    = TestBed.inject(AuthService);
    const controller = TestBed.inject(HttpTestingController);
    const router     = TestBed.inject(Router);
    const navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);

    service.setSession('tok', { phone: '+91x' });
    service.scheduleRefresh(60); // delay=54 000ms

    vi.advanceTimersByTime(54_001); // fire silent refresh

    // Silent refresh returns 401 (cookie revoked)
    const refreshReq = controller.match('/api/v1/auth/refresh');
    expect(refreshReq.length).toBeGreaterThanOrEqual(1);
    refreshReq[0].flush(
      { detail: 'Unauthorized' },
      { status: 401, statusText: 'Unauthorized' },
    );

    // forceLogout() must have been called → token null + navigate
    expect(service.getToken()).toBeNull();
    expect(service.isAuthenticated()).toBe(false);
    expect(navigateSpy).toHaveBeenCalledOnce();
    expect(navigateSpy).toHaveBeenCalledWith(['/login']);

    // forceLogout() now fires a best-effort revoke POST — consume it.
    controller.match('/api/v1/auth/logout').forEach((r) =>
      r.flush(null, { status: 200, statusText: 'OK' }),
    );

    controller.verify();
    vi.useRealTimers();
  });

  it('silent refresh non-401 error (5xx) does NOT call forceLogout (swallowed transiently)', () => {
    vi.useFakeTimers();

    TestBed.configureTestingModule({
      providers: [
        AuthService,
        AuthApiService,
        provideHttpClient(withFetch()),
        provideHttpClientTesting(),
        provideRouter([{ path: 'login', children: [] }]),
      ],
    });

    const service    = TestBed.inject(AuthService);
    const controller = TestBed.inject(HttpTestingController);
    const router     = TestBed.inject(Router);
    const navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);

    service.setSession('tok', { phone: '+91x' });
    service.scheduleRefresh(60);

    vi.advanceTimersByTime(54_001); // fire silent refresh

    const refreshReq = controller.match('/api/v1/auth/refresh');
    expect(refreshReq.length).toBeGreaterThanOrEqual(1);
    refreshReq[0].flush(
      { detail: 'Internal Server Error' },
      { status: 500, statusText: 'Internal Server Error' },
    );

    // 5xx is swallowed — token preserved, no navigation
    expect(service.getToken()).toBe('tok');
    expect(service.isAuthenticated()).toBe(true);
    expect(navigateSpy).not.toHaveBeenCalled();

    controller.verify();
    vi.useRealTimers();
  });
});

// ── bootstrap racing _doSilentRefresh → ONE authApi.refresh ───────────────────

describe('AuthService — bootstrap racing _doSilentRefresh', () => {
  it('bootstrap() + simultaneous scheduleRefresh fire → only ONE POST /auth/refresh', async () => {
    vi.useFakeTimers();

    TestBed.configureTestingModule({
      providers: [
        AuthService,
        AuthApiService,
        provideHttpClient(withFetch()),
        provideHttpClientTesting(),
        provideRouter([{ path: 'login', children: [] }]),
      ],
    });

    const service    = TestBed.inject(AuthService);
    const controller = TestBed.inject(HttpTestingController);

    // Pre-arm a scheduled refresh that fires at t=0 (tiny TTL → 5000ms floor)
    service.setSession('old-tok', { phone: '+91x' });
    service.scheduleRefresh(2); // floor→5000ms

    // Start bootstrap concurrently — both will call refreshShared()
    const bootstrapPromise = service.bootstrap();

    // Advance timers to fire the scheduled refresh simultaneously
    vi.advanceTimersByTime(5_001);

    // There must be EXACTLY ONE /auth/refresh request (single-flight gate)
    const refreshRequests = controller.match('/api/v1/auth/refresh');
    expect(refreshRequests.length).toBe(1);
    refreshRequests[0].flush({ access_token: 'race-token', expires_in: 900, token_type: 'bearer' });

    // bootstrap also triggers /me
    const meReqs = controller.match('/api/v1/auth/me');
    meReqs.forEach((r) =>
      r.flush({
        user_id: 'race-uuid', phone: '+91x', plan: 'free', created_at: '',
        last_login_at: null, onboarding_complete: false,
      }),
    );

    await bootstrapPromise;

    expect(service.getToken()).toBe('race-token');
    controller.verify();
    vi.useRealTimers();
  });
});

// ── Wave 3 billing: entitlement() computed + AuthUser widening ───────────────
//
// Tests the new entitlement() computed signal added in Wave 3.
// Source: WAVE5_FRONTEND_TASKSPEC.md §3.2 + handoff_contract_razorpay.md §1.3.

describe('AuthService — entitlement() computed (Wave 3 billing widening)', () => {

  it('returns "free" when not authenticated (no user)', () => {
    const { service } = setup();
    expect(service.entitlement()).toBe('free');
  });

  it('returns "free" when user is logged in but entitlement is undefined (pre-Wave-3 token)', () => {
    const { service } = setup();
    // Simulates a pre-Wave-3 cached /me response where entitlement field is absent
    const legacyUser: AuthUser = { phone: '+919876543210', plan: 'free' };
    service.setSession('tok', legacyUser);
    expect(service.entitlement()).toBe('free');
  });

  it('returns "free" when user.entitlement is explicitly "free"', () => {
    const { service } = setup();
    service.setSession('tok', { phone: '+91x', entitlement: 'free' });
    expect(service.entitlement()).toBe('free');
  });

  it('returns "starter" when user.entitlement is "starter"', () => {
    const { service } = setup();
    service.setSession('tok', { phone: '+91x', entitlement: 'starter' });
    expect(service.entitlement()).toBe('starter');
  });

  it('returns "pro" when user.entitlement is "pro" (plain pro plan)', () => {
    const { service } = setup();
    service.setSession('tok', { phone: '+91x', plan: 'pro', entitlement: 'pro' });
    expect(service.entitlement()).toBe('pro');
  });

  it('returns "pro" when entitlement is "pro" (pro_annual — annual collapses to base)', () => {
    const { service } = setup();
    // Server resolves pro_annual → pro entitlement; FE just reads the server value
    service.setSession('tok', { phone: '+91x', plan: 'pro_annual', entitlement: 'pro' });
    expect(service.entitlement()).toBe('pro');
  });

  it('returns "pro" when entitlement is "pro" (ltd — LTD is Pro-for-life)', () => {
    const { service } = setup();
    service.setSession('tok', { phone: '+91x', plan: 'ltd', entitlement: 'pro' });
    expect(service.entitlement()).toBe('pro');
  });

  it('returns "pro" when entitlement is "pro" (free user with live trial)', () => {
    const { service } = setup();
    // trial still live: plan='free' but server grants 'pro' entitlement
    service.setSession('tok', {
      phone: '+91x',
      plan: 'free',
      trial_ends_at: '2026-07-03T09:15:00Z',
      entitlement: 'pro',
    });
    expect(service.entitlement()).toBe('pro');
  });

  it('returns "business" when user.entitlement is "business"', () => {
    const { service } = setup();
    service.setSession('tok', { phone: '+91x', plan: 'business', entitlement: 'business' });
    expect(service.entitlement()).toBe('business');
  });

  it('returns "business" when entitlement is "business" (business_annual → business collapse)', () => {
    const { service } = setup();
    service.setSession('tok', { phone: '+91x', plan: 'business_annual', entitlement: 'business' });
    expect(service.entitlement()).toBe('business');
  });

  it('resets to "free" on logout', () => {
    const { service, controller } = setup();
    service.setSession('tok', { phone: '+91x', entitlement: 'pro' });
    expect(service.entitlement()).toBe('pro');
    service.logout();
    // Consume the fire-and-forget revoke POST so controller.verify() passes.
    controller.match('/api/v1/auth/logout').forEach((r) =>
      r.flush(null, { status: 200, statusText: 'OK' }),
    );
    expect(service.entitlement()).toBe('free');
  });

  it('updates reactively when refreshUser() re-hydrates /me with new entitlement', async () => {
    const { service, controller } = setup();
    service.setSession('tok', { phone: '+91x', plan: 'free', entitlement: 'free' });
    expect(service.entitlement()).toBe('free');

    // Trigger refreshUser()
    let refreshDone = false;
    service.refreshUser().subscribe({ complete: () => (refreshDone = true) });

    const req = controller.expectOne('/api/v1/auth/me');
    req.flush({
      user_id: 'uuid-123',
      phone: '+91x',
      plan: 'pro',
      created_at: '2026-01-01T00:00:00Z',
      last_login_at: null,
      onboarding_complete: true,
      trial_ends_at: null,
      entitlement: 'pro',
    });

    await new Promise<void>((r) => setTimeout(r, 0));

    expect(service.entitlement()).toBe('pro');
  });
});

// ── AuthUser Wave 3 widening — plain field tests ──────────────────────────────

describe('AuthUser — Wave 3 billing fields (plan literal + trial_ends_at + entitlement)', () => {
  it('accepts all 7 plan literal values without TS error at runtime', () => {
    const { service } = setup();
    const plans = ['free', 'starter', 'pro', 'pro_annual', 'business', 'business_annual', 'ltd'] as const;
    for (const plan of plans) {
      service.setSession('tok', { phone: '+91x', plan });
      expect(service.currentUser()?.plan).toBe(plan);
    }
  });

  it('carries trial_ends_at from MeResponse via meToUser', async () => {
    const { service, controller } = setup();
    service.setSession('tok', { phone: '+91x' }); // prime the token for the /me call

    service.refreshUser().subscribe();
    const req = controller.expectOne('/api/v1/auth/me');
    req.flush({
      user_id: 'uuid-trial',
      phone: '+91x',
      plan: 'free',
      created_at: '2026-01-01T00:00:00Z',
      last_login_at: null,
      onboarding_complete: false,
      trial_ends_at: '2026-07-03T09:15:00Z',
      entitlement: 'pro',
    });

    await new Promise<void>((r) => setTimeout(r, 0));

    expect(service.currentUser()?.trial_ends_at).toBe('2026-07-03T09:15:00Z');
    expect(service.currentUser()?.entitlement).toBe('pro');
  });
});

// ── refreshShared() — cross-context debounce backstop (B03) ──────────────────

describe('refreshShared() — cross-context debounce backstop (B03)', () => {
  it('a second refresh trigger within REFRESH_DEBOUNCE_MS of a completed refresh does NOT fire a second authApi.refresh()', () => {
    vi.useFakeTimers();

    TestBed.configureTestingModule({
      providers: [
        AuthService,
        AuthApiService,
        provideHttpClient(withFetch()),
        provideHttpClientTesting(),
        provideRouter([{ path: 'login', children: [] }]),
      ],
    });

    const service    = TestBed.inject(AuthService);
    const controller = TestBed.inject(HttpTestingController);

    // Establish a live session (token must be non-null for debounce to trigger)
    service.setSession('live-token', { phone: '+919876543210' });

    // First call to refreshShared() — no debounce window yet (_lastRefreshAt=0)
    const tokens1: string[] = [];
    service.refreshShared().subscribe((r) => tokens1.push(r.access_token));

    // Exactly ONE /auth/refresh HTTP call
    const firstRefreshReqs = controller.match('/api/v1/auth/refresh');
    expect(firstRefreshReqs.length).toBe(1);
    firstRefreshReqs[0].flush({ access_token: 'fresh-token', expires_in: 900, token_type: 'bearer' });

    // First subscriber received the minted token
    expect(tokens1).toEqual(['fresh-token']);

    // Advance time by LESS than REFRESH_DEBOUNCE_MS (2 000 ms) — still within the window
    vi.advanceTimersByTime(1_500);

    // Second call to refreshShared() — within debounce window, current in-memory token exists
    // ('live-token' set by setSession above — debounce reads _token() NOT the just-minted token)
    const tokens2: string[] = [];
    service.refreshShared().subscribe((r) => tokens2.push(r.access_token));

    // CRITICAL: NO second HTTP call must have been made
    const secondRefreshReqs = controller.match('/api/v1/auth/refresh');
    expect(secondRefreshReqs.length).toBe(0);

    // Second subscriber gets the current in-memory token (not undefined / empty)
    expect(tokens2.length).toBe(1);
    // The debounce short-circuit returns the current _token() value ('live-token')
    expect(tokens2[0]).toBe('live-token');

    controller.verify();
    vi.useRealTimers();
  });

  it('a refresh trigger AFTER REFRESH_DEBOUNCE_MS elapses fires a new authApi.refresh()', () => {
    vi.useFakeTimers();

    TestBed.configureTestingModule({
      providers: [
        AuthService,
        AuthApiService,
        provideHttpClient(withFetch()),
        provideHttpClientTesting(),
        provideRouter([{ path: 'login', children: [] }]),
      ],
    });

    const service    = TestBed.inject(AuthService);
    const controller = TestBed.inject(HttpTestingController);

    // Establish a live session
    service.setSession('live-token', { phone: '+919876543210' });

    // First refresh
    service.refreshShared().subscribe();
    const firstReqs = controller.match('/api/v1/auth/refresh');
    expect(firstReqs.length).toBe(1);
    firstReqs[0].flush({ access_token: 'first-fresh', expires_in: 900, token_type: 'bearer' });

    // Advance PAST the debounce window (>2 000 ms)
    vi.advanceTimersByTime(2_500);

    // Second refresh — debounce window has expired → must fire a new HTTP call
    const tokens2: string[] = [];
    service.refreshShared().subscribe((r) => tokens2.push(r.access_token));

    const secondReqs = controller.match('/api/v1/auth/refresh');
    expect(secondReqs.length).toBe(1);
    secondReqs[0].flush({ access_token: 'second-fresh', expires_in: 900, token_type: 'bearer' });

    expect(tokens2).toEqual(['second-fresh']);

    controller.verify();
    vi.useRealTimers();
  });
});

// ── FE-AUTH-08: access token is in-memory only — never in localStorage (Decision #14) ──
//
// CLAUDE.md Decision #14: "access JWT held in-memory by the frontend;
// refresh token in HttpOnly+Secure+SameSite=Strict cookie owned by backend ...
// no tokens in localStorage."
//
// This describe block is the spec-side guard for Decision #14.
// Develop had 49 cases covering setSession/logout/refresh/etc. but NO explicit
// localStorage-never assertion — this block fills that gap.

describe('AuthService — access token is in-memory only (FE-AUTH-08, Decision #14)', () => {
  it('should not write any value to localStorage when setSession is called with a token and user', () => {
    const { service } = setup();
    localStorage.clear();

    service.setSession('secret-token', { phone: '+919876543210' });

    // None of the known auth key names must appear in localStorage
    expect(localStorage.getItem('access_token')).toBeNull();
    expect(localStorage.getItem('token')).toBeNull();
    expect(localStorage.getItem('auth_token')).toBeNull();
    expect(localStorage.getItem('jwt')).toBeNull();
    expect(localStorage.getItem('mesell_token')).toBeNull();
    // Belt-and-suspenders: nothing must be written at all
    expect(localStorage.length).toBe(0);
  });

  it('should not write to localStorage even when setSession is called multiple times', () => {
    const { service } = setup();
    localStorage.clear();

    service.setSession('tok-1', { phone: '+91x' });
    service.setSession('tok-2', { phone: '+91x', plan: 'pro' });

    expect(localStorage.length).toBe(0);
  });

  it('should not persist any auth key to localStorage after logout when previously authenticated', () => {
    const { service, controller } = setup();
    localStorage.clear();

    service.setSession('tok', { phone: '+91x' });
    service.logout();
    // Drain the fire-and-forget revoke POST so controller.verify() passes
    controller.match('/api/v1/auth/logout').forEach((r) =>
      r.flush(null, { status: 204, statusText: 'No Content' }),
    );

    expect(localStorage.length).toBe(0);
  });

  it('should return the in-memory token from getToken and NOT any value seeded into localStorage', () => {
    const { service } = setup();
    // Seed a decoy to confirm the service does NOT read from localStorage
    localStorage.setItem('access_token', 'decoy-from-storage');

    service.setSession('real-in-memory-token', { phone: '+91x' });

    // Must return the in-memory value, not the localStorage decoy
    expect(service.getToken()).toBe('real-in-memory-token');

    // Cleanup decoy so other tests start clean
    localStorage.clear();
  });
});
